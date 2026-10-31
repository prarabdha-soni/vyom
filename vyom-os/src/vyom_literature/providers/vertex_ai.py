"""Vertex AI / Gemini provider for the System One and System Two boundaries.

Binding decisions honoured here:
- Google Cloud Vertex AI is the managed AI service boundary; Gemini model ids
  are pinned in configuration and recorded on every decision.
- Implementation sits *behind* the existing provider abstractions
  (``SystemOneClient.system_one`` / ``SynthesisProvider.draft``). No Gemini
  call appears in a FastAPI route or domain module.
- Credentials come from Application Default Credentials / workload identity via
  the metadata server or ``GOOGLE_APPLICATION_CREDENTIALS``. A service-account
  key is never read from source control and never logged.
- Outputs are untrusted proposals: every response is validated against an
  application-owned JSON schema before routing sees it. Timeout, malformed
  output, rate limit or provider failure raises — callers must fail closed to
  human review, never to GREEN/auto-close.
- No new third-party dependency: this uses the Python standard library so the
  existing dependency rule is not triggered (ADR-002). If approved later,
  swapping in ``google-cloud-aiplatform`` is a drop-in change here only.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from vyom_literature.system_one import Question


VERTEX_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
DEFAULT_REGION = "asia-south1"  # Mumbai — Indian data residency preference
DEFAULT_TIMEOUT_SECONDS = 20
MAX_RETRIES = 2  # limited retries with backoff; then fail closed
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

MODEL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REGION_PATTERN = re.compile(r"^[a-z0-9]+-[a-z0-9-]+$")


class VertexAiError(RuntimeError):
    """Provider failed or answered outside contract. Callers must fail closed."""


class VertexAiConfigError(ValueError):
    """Configuration problem (missing project/region/model or bad shape)."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VertexAiConfigError(message)


@dataclass(frozen=True)
class VertexGenerationConfig:
    temperature: float = 0.0
    max_output_tokens: int = 2048
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


SAFETY_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)
SAFETY_LEVELS = {"BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_LOW_AND_ABOVE", "BLOCK_MEDIUM_AND_ABOVE"}


@dataclass(frozen=True)
class VertexSettings:
    project_id: str
    region: str
    model_id: str
    sampler_version: str
    generation: VertexGenerationConfig = VertexGenerationConfig()
    safety_settings: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_env(cls, prefix: str = "VERTEX") -> "VertexSettings":
        project = os.environ.get(f"{prefix}_PROJECT_ID", "")
        region = os.environ.get(f"{prefix}_REGION", DEFAULT_REGION)
        model = os.environ.get(f"{prefix}_MODEL_ID", "")
        sampler = os.environ.get(f"{prefix}_SAMPLER_VERSION", "")
        _require(bool(project), f"{prefix}_PROJECT_ID is required for Vertex AI")
        _require(bool(model), f"{prefix}_MODEL_ID must be pinned (e.g. gemini-2.5-flash)")
        _require(bool(sampler), f"{prefix}_SAMPLER_VERSION is required")
        _require(
            MODEL_ID_PATTERN.match(model) is not None,
            f"{prefix}_MODEL_ID looks malformed: {model!r}",
        )
        _require(REGION_PATTERN.match(region) is not None, f"{prefix}_REGION malformed")
        temperature = float(os.environ.get(f"{prefix}_TEMPERATURE", "0"))
        _require(0 <= temperature <= 2, "temperature must be within 0..2")
        max_tokens = int(os.environ.get(f"{prefix}_MAX_OUTPUT_TOKENS", "2048"))
        _require(1 <= max_tokens <= 8192, "max output tokens must be within 1..8192")
        timeout = int(os.environ.get(f"{prefix}_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        _require(1 <= timeout <= 120, "timeout must be within 1..120 seconds")
        safety: list[dict[str, str]] = []
        raw_safety = os.environ.get(f"{prefix}_SAFETY_SETTINGS_JSON", "")
        if raw_safety:
            try:
                parsed = json.loads(raw_safety)
            except json.JSONDecodeError as error:
                raise VertexAiConfigError("safety settings must be valid JSON") from error
            _require(isinstance(parsed, list), "safety settings must be a JSON array")
            for entry in parsed:
                _require(
                    isinstance(entry, dict)
                    and entry.get("category") in SAFETY_CATEGORIES
                    and entry.get("threshold") in SAFETY_LEVELS,
                    f"unsupported safety setting: {entry!r}",
                )
                safety.append({"category": entry["category"], "threshold": entry["threshold"]})
        return cls(
            project_id=project,
            region=region,
            model_id=model,
            sampler_version=sampler,
            generation=VertexGenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                timeout_seconds=timeout,
            ),
            safety_settings=tuple(safety),
        )

    def endpoint(self) -> str:
        return (
            f"https://{self.region}-aiplatform.googleapis.com/v1/projects/"
            f"{self.project_id}/locations/{self.region}/publishers/google/"
            f"models/{self.model_id}:generateContent"
        )


def default_token_source() -> Callable[[], tuple[str, str | None]]:
    """Application Default Credentials via workload identity / metadata server.

    Returns (access_token, token_source_label). Never logs the token itself.
    """

    def _source() -> tuple[str, str | None]:
        # 1) Explicitly injected token (pre-refreshed workers / tests).
        token = os.environ.get("VERTEX_ACCESS_TOKEN", "")
        if token:
            return token, "injected"
        # 2) GKE / GCE workload identity metadata server.
        try:
            request = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/"
                "service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                payload = json.loads(response.read())
            return payload["access_token"], "metadata_server"
        except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError):
            pass
        # 3) ADC service-account file: exchange requires google-auth which is
        #    not an approved dependency — fail closed with guidance (ADR-002).
        key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if key_path:
            raise VertexAiError(
                "Direct service-account JWT exchange needs the approved google-auth path; "
                "use workload identity or a pre-refreshed VERTEX_ACCESS_TOKEN (ADR-002)."
            )
        raise VertexAiError(
            "No Application Default Credentials found (workload identity, ADC key, "
            "or VERTEX_ACCESS_TOKEN)"
        )

    return _source


# ---------------------------------------------------------------------------
# Structured-output contract for System One over Gemini.
# ---------------------------------------------------------------------------

def system_one_response_schema(questions: dict[str, Question]) -> dict[str, Any]:
    """Application-owned schema the model output must satisfy before routing."""
    properties: dict[str, Any] = {}
    for key, question in questions.items():
        if question.kind == "noul":
            properties[key] = {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "probability": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["answer", "probability"],
            }
        elif question.kind == "choice":
            properties[key] = {
                "type": "object",
                "properties": {
                    "choice": {"type": "string", "enum": list(question.choices)},
                    "probability": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["choice", "probability"],
            }
        else:
            levels = [c.split("_", 1)[0] for c in question.choices]
            properties[key] = {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "enum": [int(v) for v in levels]},
                    "probability": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["score", "probability"],
            }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
    }


def validate_system_one_output(payload: Any, questions: dict[str, Question]) -> dict[str, Any]:
    """Validate the untrusted model proposal against our schema. Raises on any drift."""
    if not isinstance(payload, dict):
        raise VertexAiError("System One output is not a JSON object")
    missing = set(questions) - set(payload)
    if missing:
        raise VertexAiError(f"System One output missing keys: {sorted(missing)}")
    normalised: dict[str, Any] = {}
    for key, question in questions.items():
        answer = payload[key]
        if not isinstance(answer, dict):
            raise VertexAiError(f"answer {key} is not an object")
        probability = answer.get("probability")
        if not isinstance(probability, (int, float)) or not 0 <= float(probability) <= 1:
            raise VertexAiError(f"answer {key} has an out-of-contract probability")
        if question.kind == "noul":
            value = answer.get("answer")
            if value not in {"YES", "NO", "UNCERTAIN"}:
                raise VertexAiError(f"answer {key} outside YES/NO/UNCERTAIN")
        elif question.kind == "choice":
            value = answer.get("choice")
            if value not in question.choices:
                raise VertexAiError(f"answer {key} outside permitted choices")
        else:
            value = answer.get("score")
            allowed = {int(c.split("_", 1)[0]) for c in question.choices}
            if not isinstance(value, int) or value not in allowed:
                raise VertexAiError(f"answer {key} score outside permitted levels")
        normalised[key] = {**answer, "probability": float(probability)}
    return normalised


class VertexAiSystemOneClient:
    """Gemini-backed System One provider implementing the SystemOneClient protocol."""

    provider_name = "vertex_ai"

    def __init__(
        self,
        *,
        settings: VertexSettings,
        token_source: Callable[[], tuple[str, str | None]] | None = None,
        transport: Callable[[str, dict[str, Any], int], dict[str, Any]] | None = None,
    ):
        self.settings = settings
        self.token_source = token_source or default_token_source()
        self._transport = transport
        self.last_usage: dict[str, int] | None = None
        self.last_model_version: str | None = None

    # -- request building ---------------------------------------------------
    def _contents(self, state: dict[str, Any], questions: dict[str, Question]) -> str:
        question_block = {
            key: {"kind": q.kind, "prompt": q.prompt, "choices": list(q.choices)}
            for key, q in questions.items()
        }
        return json.dumps(
            {
                "task": "system_one_screening",
                "instructions": [
                    "Answer each question using ONLY the supplied text.",
                    "If evidence is insufficient, answer UNCERTAIN with probability below 0.5.",
                    "You propose; a deterministic router and qualified humans decide.",
                ],
                "state": state,
                "questions": question_block,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def build_request_body(self, state: dict[str, Any], questions: dict[str, Question]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": self._contents(state, questions)}]}],
            "generationConfig": {
                "temperature": self.settings.generation.temperature,
                "maxOutputTokens": self.settings.generation.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": system_one_response_schema(questions),
            },
        }
        if self.settings.safety_settings:
            body["safetySettings"] = list(self.settings.safety_settings)
        return body

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        if self._transport is not None:
            return self._transport(
                self.settings.endpoint(), body, self.settings.generation.timeout_seconds
            )
        token, _origin = self.token_source()
        request = urllib.request.Request(
            self.settings.endpoint(),
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.settings.generation.timeout_seconds
                ) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in RETRYABLE_STATUS or attempt == MAX_RETRIES:
                    raise VertexAiError(f"Vertex AI returned {error.code}") from error
                retry_after = error.headers.get("Retry-After")
                try:
                    delay = min(float(retry_after) if retry_after else 2**attempt, 30)
                except ValueError:
                    delay = min(2**attempt, 30)
                time.sleep(delay)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
                if attempt == MAX_RETRIES:
                    raise VertexAiError("Vertex AI request failed after bounded retries") from error
                time.sleep(min(2**attempt, 30))
        raise VertexAiError(f"unreachable retry loop: {last_error}")

    @staticmethod
    def extract_json(response: dict[str, Any]) -> dict[str, Any]:
        candidates = response.get("candidates") or []
        if not candidates:
            raise VertexAiError("Vertex AI returned no candidates")
        finish = candidates[0].get("finishReason")
        if finish not in (None, "STOP", "MAX_TOKENS"):
            raise VertexAiError(f"Vertex AI finished with {finish} (blocked/safety); failing closed")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise VertexAiError("Vertex AI returned empty content")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise VertexAiError("Vertex AI returned malformed JSON") from error
        if not isinstance(payload, dict):
            raise VertexAiError("Vertex AI returned non-object JSON")
        return payload

    def system_one(
        self, *, state: dict[str, Any], questions: dict[str, Question], model: str
    ) -> dict[str, Any]:
        if model and model != self.settings.model_id:
            raise VertexAiConfigError(
                f"requested model {model!r} is not the pinned model of this client"
            )
        response = self._post(self.build_request_body(state, questions))
        usage = response.get("usageMetadata") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
        }
        self.last_model_version = response.get("modelVersion")
        return validate_system_one_output(self.extract_json(response), questions)


# ---------------------------------------------------------------------------
# System Two drafting over Gemini (same trust rules: drafts need human review).
# ---------------------------------------------------------------------------

SYNTHESIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "draft_narrative": {"type": "string"},
        "cited_passages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"quote": {"type": "string"}},
                "required": ["quote"],
            },
        },
    },
    "required": ["draft_narrative", "cited_passages"],
}


class VertexAiSynthesisProvider:
    """Gemini-backed System Two drafter implementing the SynthesisProvider protocol."""

    provider_name = "vertex_ai"

    def __init__(
        self,
        *,
        settings: VertexSettings,
        token_source: Callable[[], tuple[str, str | None]] | None = None,
        transport: Callable[[str, dict[str, Any], int], dict[str, Any]] | None = None,
    ):
        self.settings = settings
        self.model_id = settings.model_id
        self.token_source = token_source or default_token_source()
        self._transport = transport
        self.last_usage: dict[str, int] | None = None

    def draft(self, *, domain: str, state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        from vyom_literature.system_two import build_system_two_prompt

        body = {
            "contents": [
                {"role": "user", "parts": [{"text": build_system_two_prompt(domain, state, decision)}]}
            ],
            "generationConfig": {
                "temperature": self.settings.generation.temperature,
                "maxOutputTokens": self.settings.generation.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": SYNTHESIS_RESPONSE_SCHEMA,
            },
        }
        if self.settings.safety_settings:
            body["safetySettings"] = list(self.settings.safety_settings)
        if self._transport is not None:
            response = self._transport(
                self.settings.endpoint(), body, self.settings.generation.timeout_seconds
            )
        else:
            token, _origin = self.token_source()
            request = urllib.request.Request(
                self.settings.endpoint(),
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=self.settings.generation.timeout_seconds
                ) as http:
                    response = json.loads(http.read())
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                raise VertexAiError("Vertex AI synthesis request failed") from error
        usage = response.get("usageMetadata") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
        }
        payload = VertexAiSystemOneClient.extract_json(response)
        narrative = payload.get("draft_narrative")
        citations = payload.get("cited_passages")
        if not isinstance(narrative, str) or not narrative.strip():
            raise VertexAiError("synthesis draft missing")
        if not isinstance(citations, list) or not citations:
            raise VertexAiError("synthesis citations missing")
        for citation in citations:
            if not isinstance(citation, dict) or not isinstance(citation.get("quote"), str):
                raise VertexAiError("malformed citation object")
        return payload


def record_metadata(client: Any) -> dict[str, Any]:
    """Effective provider/model/version metadata for decision lineage."""
    settings = getattr(client, "settings", None)
    return {
        "provider": getattr(client, "provider_name", "unknown"),
        "model_id": getattr(settings, "model_id", None) or getattr(client, "model_id", None),
        "model_version": getattr(client, "last_model_version", None),
        "usage": getattr(client, "last_usage", None),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
