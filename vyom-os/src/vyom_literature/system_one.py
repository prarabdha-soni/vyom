from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit


Domain = Literal["pv_literature", "pv_icsr"]
QUESTION_SCHEMA_VERSION = 2
THRESHOLD_POLICY_VERSION = 4


@dataclass(frozen=True)
class Question:
    kind: Literal["noul", "choice", "score"]
    prompt: str
    choices: tuple[str, ...] = ()


PV_LITERATURE_QUESTIONS = {
    "has_identifiable_patient": Question(
        "noul", "Does the text describe an identifiable human patient or individual clinical course?"
    ),
    "has_identifiable_reporter": Question(
        "noul", "Does the source identify a reporter who can be followed up?"
    ),
    "has_suspect_drug": Question(
        "noul", "Was the suspected medicinal product used before the untoward event?"
    ),
    "has_adverse_event": Question(
        "noul", "Does a patient experience a suspected adverse event or lack of efficacy?"
    ),
    "is_serious_event": Question(
        "noul", "Does the event meet a seriousness criterion based on the available evidence?"
    ),
    "study_design": Question(
        "choice",
        "Classify the publication design using only the supplied text.",
        (
            "CASE_REPORT_OR_SERIES",
            "CLINICAL_TRIAL",
            "OBSERVATIONAL_COHORT",
            "IN_VITRO_OR_ANIMAL_ONLY",
            "REVIEW_NO_NEW_CASES",
            "UNCERTAIN",
        ),
    ),
    "triage_priority": Question(
        "score",
        "Rate literature-review urgency; this is a queue priority, not a regulatory determination.",
        ("1_LOW", "2_ROUTINE", "3_REVIEW", "4_EXPEDITED_REVIEW", "5_URGENT_REVIEW"),
    ),
}

PV_ICSRS_QUESTIONS = {
    **PV_LITERATURE_QUESTIONS,
    "has_identifiable_patient": Question(
        "noul", "Does this ICSR identify a patient, rather than only an aggregate?"
    ),
    "study_design": Question(
        "choice",
        "Classify the report source.",
        ("INDIVIDUAL_CASE", "AGGREGATE_REPORT", "LITERATURE_CASE", "UNCERTAIN"),
    ),
}

NEGATIVE_STUDY_DESIGNS = {"IN_VITRO_OR_ANIMAL_ONLY", "REVIEW_NO_NEW_CASES"}


class SystemOneClient(Protocol):
    def system_one(self, *, state: dict[str, Any], questions: dict[str, Any], model: str) -> Any: ...


def validate_base_url(base_url: str) -> None:
    parsed = urlsplit(base_url)
    local_http_hosts = {"localhost", "127.0.0.1", "::1", "ollama_sys1", "local_system_one"}
    if parsed.scheme == "https" and parsed.hostname:
        return
    if parsed.scheme == "http" and parsed.hostname in local_http_hosts:
        return
    raise ValueError("System One base URL must use HTTPS or an approved local host")


def _sdk_questions(specs: dict[str, Question]) -> dict[str, Any]:
    try:
        from typesafe_sdk import Choice, Noul, Score
    except ImportError as error:
        raise RuntimeError("Install the configured TypeSafe SDK dependency to run System One") from error

    result = {}
    for key, question in specs.items():
        if question.kind == "noul":
            result[key] = Noul(question.prompt)
        elif question.kind == "choice":
            result[key] = Choice(question.prompt, options=list(question.choices))
        else:
            result[key] = Score(question.prompt, levels=list(question.choices))
    return result


class LazyTypeSafeClient:
    def __init__(self, *, api_key: str, base_url: str):
        if not api_key:
            raise ValueError("TypeSafe API key is required")
        validate_base_url(base_url)
        try:
            from typesafe_sdk import TypeSafeClient
        except ImportError as error:
            raise RuntimeError("Install typesafe-sdk before constructing the live provider") from error
        self.client = TypeSafeClient(api_key=api_key, base_url=base_url)

    def system_one(self, *, state: dict[str, Any], questions: dict[str, Question], model: str) -> Any:
        return self.client.system_one(state=state, questions=_sdk_questions(questions), model=model)


def _answer_value(answer: Any, key: str) -> Any:
    if isinstance(answer, dict):
        return answer[key]
    return getattr(answer, key)


def _answer_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "to_dict"):
        response = response.to_dict()
    if not isinstance(response, dict):
        raise ValueError("System One response must serialize to an object")
    return response


def _probability(answer: Any) -> float:
    probability = float(_answer_value(answer, "probability"))
    if not 0 <= probability <= 1:
        raise ValueError("System One probability must be between 0 and 1")
    return probability


def _route(
    domain: Domain, answers: dict[str, Any]
) -> tuple[str, dict[str, float], float | None, str | None]:
    if domain in {"pv_literature", "pv_icsr"}:
        gate_names = (
            "has_identifiable_patient",
            "has_identifiable_reporter",
            "has_suspect_drug",
            "has_adverse_event",
        )
        gates = {key: _probability(answers[key]) for key in gate_names}
        serious_probability = _probability(answers["is_serious_event"])
        priority = int(_answer_value(answers["triage_priority"], "score"))
        study_design = _answer_value(answers["study_design"], "choice")

        if all(value < 0.04 for value in gates.values()) and study_design in NEGATIVE_STUDY_DESIGNS:
            band = "GREEN_CLOSE"
        elif serious_probability >= 0.50 or priority >= 4:
            band = "RED_ESCALATE"
        else:
            band = "YELLOW_REVIEW"
        return band, {**gates, "is_serious_event": serious_probability}, serious_probability, None

class SystemOneRouter:
    def __init__(
        self,
        *,
        public_literature_client: SystemOneClient,
        local_client: SystemOneClient,
        public_model: str,
        local_model: str,
        sampler_version: str,
    ):
        self.public_literature_client = public_literature_client
        self.local_client = local_client
        self.public_model = public_model
        self.local_model = local_model
        self.sampler_version = sampler_version
        self.question_schema_version = QUESTION_SCHEMA_VERSION
        self.threshold_policy_version = THRESHOLD_POLICY_VERSION

    @classmethod
    def from_env(cls) -> SystemOneRouter:
        public_key = os.environ.get("TYPESAFE_API_KEY", "")
        local_key = os.environ.get("LOCAL_SYS1_API_KEY", "")
        local_url = os.environ.get("LOCAL_SYS1_BASE_URL", "")
        public_model = os.environ.get("CLOUD_SYS1_MODEL", "")
        local_model = os.environ.get("LOCAL_SYS1_MODEL", "")
        sampler_version = os.environ.get("SYS1_SAMPLER_VERSION", "")
        if not all((public_key, local_key, local_url, public_model, local_model, sampler_version)):
            raise ValueError(
                "TYPESAFE_API_KEY, LOCAL_SYS1_API_KEY, LOCAL_SYS1_BASE_URL, "
                "CLOUD_SYS1_MODEL, LOCAL_SYS1_MODEL, and SYS1_SAMPLER_VERSION are required"
            )
        return cls(
            public_literature_client=LazyTypeSafeClient(
                api_key=public_key,
                base_url=os.environ.get("CLOUD_SYS1_BASE_URL", "https://typesafe.ai"),
            ),
            local_client=LazyTypeSafeClient(api_key=local_key, base_url=local_url),
            public_model=public_model,
            local_model=local_model,
            sampler_version=sampler_version,
        )

    def evaluate(self, domain: Domain, normalized_state: dict[str, Any]) -> dict[str, Any]:
        if domain not in {"pv_literature", "pv_icsr"}:
            raise ValueError(f"Unsupported domain: {domain}")
        public_literature = domain == "pv_literature"
        client = self.public_literature_client if public_literature else self.local_client
        model = self.public_model if public_literature else self.local_model
        questions = PV_LITERATURE_QUESTIONS if domain == "pv_literature" else PV_ICSRS_QUESTIONS

        state_sha256 = hashlib.sha256(
            json.dumps(
                normalized_state,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        started = time.perf_counter_ns()
        # A0 fail-closed rule: any provider exception (timeout, 5xx, rate limit,
        # malformed or out-of-schema output) must NOT be swallowed into a GREEN
        # band. We record an explicit PROVIDER_FAILURE decision whose band is
        # YELLOW_REVIEW so the deterministic router sends the item to a human.
        # Only genuine model answers can ever produce a GREEN band.
        try:
            response = client.system_one(state=normalized_state, questions=questions, model=model)
        except Exception as error:
            latency_ms = (time.perf_counter_ns() - started) // 1_000_000
            return {
                "model_id": model,
                "provider": getattr(client, "provider_name", "unknown"),
                "model_version": getattr(client, "last_model_version", None),
                "usage": getattr(client, "last_usage", None),
                "sampler_version": self.sampler_version,
                "question_schema_version": QUESTION_SCHEMA_VERSION,
                "threshold_policy_version": THRESHOLD_POLICY_VERSION,
                "state_sha256": state_sha256,
                "latency_ms": latency_ms,
                "answers": {},
                "gate_probabilities": {},
                "p_valid_case": None,
                "p_serious_event": None,
                "confidence_band": "YELLOW_REVIEW",
                "recommended_route": None,
                "outcome": "provider_failure",
                "fail_closed_reason": f"{type(error).__name__}: {str(error)[:200]}",
            }
        latency_ms = (time.perf_counter_ns() - started) // 1_000_000
        try:
            answers = _answer_dict(response)
            band, gate_probabilities, p_risk, recommended_route = _route(domain, answers)
        except (KeyError, TypeError, ValueError) as error:
            # Malformed / incomplete proposal — untrusted output never routes.
            return {
                "model_id": model,
                "provider": getattr(client, "provider_name", "unknown"),
                "model_version": getattr(client, "last_model_version", None),
                "usage": getattr(client, "last_usage", None),
                "sampler_version": self.sampler_version,
                "question_schema_version": QUESTION_SCHEMA_VERSION,
                "threshold_policy_version": THRESHOLD_POLICY_VERSION,
                "state_sha256": state_sha256,
                "latency_ms": latency_ms,
                "answers": {},
                "gate_probabilities": {},
                "p_valid_case": None,
                "p_serious_event": None,
                "confidence_band": "YELLOW_REVIEW",
                "recommended_route": None,
                "outcome": "malformed_output",
                "fail_closed_reason": f"{type(error).__name__}: {str(error)[:200]}",
            }

        return {
            "model_id": model,
            "provider": getattr(client, "provider_name", "unknown"),
            "model_version": getattr(client, "last_model_version", None),
            "usage": getattr(client, "last_usage", None),
            "sampler_version": self.sampler_version,
            "question_schema_version": QUESTION_SCHEMA_VERSION,
            "threshold_policy_version": THRESHOLD_POLICY_VERSION,
            "state_sha256": state_sha256,
            "latency_ms": latency_ms,
            "answers": answers,
            "gate_probabilities": gate_probabilities,
            "p_valid_case": None,
            "p_serious_event": p_risk,
            "confidence_band": band,
            "recommended_route": recommended_route,
            "outcome": "ok",
        }