"""Model providers behind one interface.

* ``VertexGeminiProvider`` — Gemini on Vertex AI (the hosted, managed path).
  It also implements the System One client protocol for literature
  screening, so one pinned model serves both.
* ``OpenAICompatibleProvider`` — a model inside the client's own network
  (Ollama, vLLM) for case data that may not leave it.
* ``DemoProvider`` — the deterministic rule engine in ``ai.demo``.

Providers only transport and parse JSON. Policy (which provider may see
which data), validation and cost telemetry live in ``ai.gateway``.
"""

from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.parse import urlsplit

from vyom_literature.providers.vertex_ai import (
    VertexAiError,
    VertexAiSystemOneClient,
    VertexSettings,
    validate_system_one_output,
)
from vyom_literature.system_one import Question
from vyom_os.ai import demo
from vyom_os.ai.tasks import AiTask
from vyom_os.settings import LocalModelSettings


class AiProviderError(RuntimeError):
    """The provider failed or answered outside the contract."""


@dataclass(frozen=True)
class AiResult:
    output: dict[str, Any]
    provider: str
    model_id: str
    model_version: str | None
    usage: dict[str, int] | None
    latency_ms: int


class Provider(Protocol):
    provider_name: str
    model_id: str
    #: True when data sent to this provider leaves the client's network.
    hosted: bool
    region: str | None

    def generate(self, task: AiTask, payload: dict[str, Any]) -> AiResult: ...


def _user_message(task: AiTask, payload: dict[str, Any]) -> str:
    return json.dumps(
        {"task": task.name, "task_version": task.version, "input": payload},
        ensure_ascii=False,
        sort_keys=True,
    )


class VertexGeminiProvider(VertexAiSystemOneClient):
    """Gemini over the Vertex AI REST API with structured JSON output."""

    provider_name = "vertex_ai"
    hosted = True

    def __init__(
        self,
        *,
        settings: VertexSettings,
        token_source: Callable[[], tuple[str, str | None]] | None = None,
        transport: Callable[[str, dict[str, Any], int], dict[str, Any]] | None = None,
    ):
        super().__init__(settings=settings, token_source=token_source, transport=transport)
        self.model_id = settings.model_id
        self.region = settings.region

    def build_task_body(self, task: AiTask, payload: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": task.system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": _user_message(task, payload)}]}],
            "generationConfig": {
                "temperature": self.settings.generation.temperature,
                "maxOutputTokens": self.settings.generation.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": task.response_schema,
            },
        }
        if self.settings.safety_settings:
            body["safetySettings"] = list(self.settings.safety_settings)
        return body

    def generate(self, task: AiTask, payload: dict[str, Any]) -> AiResult:
        started = time.perf_counter_ns()
        try:
            response = self._post(self.build_task_body(task, payload))
            output = self.extract_json(response)
        except VertexAiError as error:
            raise AiProviderError(str(error)) from error
        usage = response.get("usageMetadata") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
        }
        self.last_model_version = response.get("modelVersion")
        return AiResult(
            output=output,
            provider=self.provider_name,
            model_id=self.model_id,
            model_version=self.last_model_version,
            usage=self.last_usage,
            latency_ms=(time.perf_counter_ns() - started) // 1_000_000,
        )


_PRIVATE_SUFFIXES = (".svc", ".svc.cluster.local", ".cluster.local", ".internal", ".local")


def validate_local_url(base_url: str) -> None:
    """HTTPS anywhere; plain HTTP only to loopback or private-network hosts."""
    parsed = urlsplit(base_url)
    host = parsed.hostname or ""
    if parsed.scheme == "https" and host:
        return
    if parsed.scheme != "http" or not host:
        raise ValueError("LOCAL_LLM_BASE_URL must be an http(s) URL")
    if host == "localhost" or "." not in host or host.endswith(_PRIVATE_SUFFIXES):
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_loopback or address.is_private):
        return
    raise ValueError("Plain HTTP is allowed only for a model inside the private network; use HTTPS")


class OpenAICompatibleProvider:
    """Chat-completions endpoint inside the client's network (Ollama, vLLM)."""

    provider_name = "local_model"
    hosted = False
    region = None

    def __init__(
        self,
        settings: LocalModelSettings,
        *,
        transport: Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]] | None = None,
    ):
        validate_local_url(settings.base_url)
        self.settings = settings
        self.model_id = settings.model_id
        self._transport = transport
        self.last_usage: dict[str, int] | None = None
        self.last_model_version: str | None = None

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        if self._transport is not None:
            return self._transport(url, body, headers, self.settings.timeout_seconds)
        request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise AiProviderError(f"local model returned {error.code}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise AiProviderError("local model request failed") from error

    def _complete(self, system: str, user: str) -> dict[str, Any]:
        body = {
            "model": self.model_id,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        response = self._post(body)
        choices = response.get("choices") or []
        if not choices:
            raise AiProviderError("local model returned no choices")
        content = (choices[0].get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise AiProviderError("local model returned empty content")
        try:
            output = json.loads(content)
        except json.JSONDecodeError as error:
            raise AiProviderError("local model returned malformed JSON") from error
        if not isinstance(output, dict):
            raise AiProviderError("local model returned non-object JSON")
        usage = response.get("usage") or {}
        self.last_usage = (
            {
                "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
                "output_tokens": int(usage.get("completion_tokens", 0) or 0),
            }
            if usage
            else None
        )
        self.last_model_version = response.get("model")
        return output

    def generate(self, task: AiTask, payload: dict[str, Any]) -> AiResult:
        started = time.perf_counter_ns()
        system = (
            f"{task.system_instruction}\n\nReturn one JSON object that conforms to this schema "
            f"(OpenAPI subset; nullable fields may be null):\n{json.dumps(task.response_schema)}"
        )
        output = self._complete(system, _user_message(task, payload))
        return AiResult(
            output=output,
            provider=self.provider_name,
            model_id=self.model_id,
            model_version=self.last_model_version,
            usage=self.last_usage,
            latency_ms=(time.perf_counter_ns() - started) // 1_000_000,
        )

    def system_one(self, *, state: dict[str, Any], questions: dict[str, Question], model: str) -> dict[str, Any]:
        question_block = {key: {"kind": q.kind, "prompt": q.prompt, "choices": list(q.choices)} for key, q in questions.items()}
        system = (
            "Answer each screening question using only the supplied text. noul questions take "
            "{\"answer\": YES|NO|UNCERTAIN, \"probability\": 0..1}; choice questions take "
            "{\"choice\": one of choices, \"probability\"}; score questions take {\"score\": the leading "
            "integer of a level, \"probability\"}. Return one JSON object keyed by question id."
        )
        output = self._complete(system, json.dumps({"state": state, "questions": question_block}, ensure_ascii=False))
        try:
            return validate_system_one_output(output, questions)
        except VertexAiError as error:
            raise AiProviderError(str(error)) from error


class DemoProvider:
    """Deterministic rule engine. Labelled as not AI wherever its output appears."""

    provider_name = demo.DEMO_PROVIDER
    model_id = demo.DEMO_MODEL_ID
    hosted = False
    region = None

    def __init__(self) -> None:
        self.last_usage: dict[str, int] | None = None
        self.last_model_version: str | None = demo.DEMO_MODEL_ID

    def generate(self, task: AiTask, payload: dict[str, Any]) -> AiResult:
        started = time.perf_counter_ns()
        if task.name == "case_extraction":
            output = demo.extract(str(payload.get("source_text", "")), dict(payload.get("context") or {}))
        elif task.name == "case_narrative":
            output = demo.narrative(payload)
        elif task.name == "report_section":
            output = demo.report_section(payload)
        else:
            raise AiProviderError(f"demo engine has no rules for task {task.name}")
        return AiResult(
            output=output,
            provider=self.provider_name,
            model_id=self.model_id,
            model_version=demo.DEMO_MODEL_ID,
            usage=None,
            latency_ms=(time.perf_counter_ns() - started) // 1_000_000,
        )

    def system_one(self, *, state: dict[str, Any], questions: dict[str, Question], model: str) -> dict[str, Any]:
        return validate_system_one_output(demo.system_one(state, questions), questions)
