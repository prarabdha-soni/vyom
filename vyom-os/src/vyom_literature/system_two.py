from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from vyom_literature.system_one import Domain, validate_base_url


REVIEW_BANDS = {"YELLOW_REVIEW", "RED_ESCALATE"}
SYNTHESIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "draft_narrative": {"type": "string"},
        "cited_passages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"quote": {"type": "string"}},
                "required": ["quote"],
            },
        },
    },
    "required": ["draft_narrative", "cited_passages"],
}


class SynthesisProvider(Protocol):
    model_id: str

    def draft(self, *, domain: Domain, state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SynthesisResult:
    model_id: str
    draft_narrative: str
    cited_passages: list[dict[str, Any]]


def _source_text(state: dict[str, Any]) -> str:
    preferred_keys = (
        "source_text",
        "abstract",
        "discharge_summary",
        "clinical_note",
        "medical_record_text",
    )
    parts = [str(state[key]) for key in preferred_keys if isinstance(state.get(key), str) and state[key].strip()]
    if not parts:
        raise ValueError("state must include source_text or an abstract/clinical note")
    return "\n".join(parts)


def _prompt(domain: Domain, state: dict[str, Any], decision: dict[str, Any]) -> str:
    return build_system_two_prompt(domain, state, decision)


def build_system_two_prompt(domain: Domain, state: dict[str, Any], decision: dict[str, Any]) -> str:
    """Single prompt builder shared by every System Two provider (incl. Vertex)."""
    return json.dumps(
        {
            "domain": domain,
            "state": state,
            "system_one_decision": decision["answers"],
            "instructions": [
                "Draft a concise human-review aid; do not make the final regulatory or payer decision.",
                "Return JSON with draft_narrative and cited_passages, an array of exact source quotations.",
                "Every factual statement must be supported by an exact quotation from source_text.",
                "Do not infer missing facts or assign MedDRA/ICD codes not explicitly supplied in state.",
                "For RCM, recommend holds or missing evidence only; never submit or approve a claim.",
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class AnthropicPublicSynthesizer:
    def __init__(self, *, api_key: str, model_id: str):
        if not api_key or not model_id:
            raise ValueError("Anthropic System Two API key and pinned model are required")
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model_id = model_id

    def draft(self, *, domain: Domain, state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=2048,
            system="You are System Two. Synthesize only for human review; never decide or submit.",
            output_config={"format": {"type": "json_schema", "schema": SYNTHESIS_SCHEMA}},
            messages=[{"role": "user", "content": _prompt(domain, state, decision)}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return json.loads(text)


class LocalChatCompletionsSynthesizer:
    def __init__(self, *, base_url: str, api_key: str, model_id: str, timeout_seconds: int = 30):
        validate_base_url(base_url)
        host = urlsplit(base_url).hostname
        if host not in {"localhost", "127.0.0.1", "::1", "local_system_one", "ollama_sys1"}:
            raise ValueError("PHI synthesis is allowed only on an approved local inference host")
        if not model_id:
            raise ValueError("a pinned local System Two model is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    def draft(self, *, domain: Domain, state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        url = self.base_url
        if not url.endswith("/v1"):
            url += "/v1"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            f"{url}/chat/completions",
            data=json.dumps(
                {
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": "Return only JSON. Do not make final decisions."},
                        {"role": "user", "content": _prompt(domain, state, decision)},
                    ],
                    "response_format": {"type": "json_object"},
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read())
        return json.loads(payload["choices"][0]["message"]["content"])


class SystemTwoRouter:
    def __init__(self, *, public_literature_provider: SynthesisProvider, local_provider: SynthesisProvider):
        self.public_literature_provider = public_literature_provider
        self.local_provider = local_provider

    @classmethod
    def from_env(cls) -> SystemTwoRouter:
        import os

        public_key = os.environ.get("ANTHROPIC_API_KEY", "")
        public_model = os.environ.get("ANTHROPIC_SYSTEM2_MODEL", "")
        local_url = os.environ.get("LOCAL_SYS2_BASE_URL", "")
        local_key = os.environ.get("LOCAL_SYS2_API_KEY", "")
        local_model = os.environ.get("LOCAL_SYS2_MODEL", "")
        if not all((public_key, public_model, local_url, local_model)):
            raise ValueError(
                "ANTHROPIC_API_KEY, ANTHROPIC_SYSTEM2_MODEL, LOCAL_SYS2_BASE_URL, and LOCAL_SYS2_MODEL are required"
            )
        return cls(
            public_literature_provider=AnthropicPublicSynthesizer(
                api_key=public_key,
                model_id=public_model,
            ),
            local_provider=LocalChatCompletionsSynthesizer(
                base_url=local_url,
                api_key=local_key,
                model_id=local_model,
            ),
        )

    def synthesize(
        self, *, domain: Domain, state: dict[str, Any], decision: dict[str, Any]
    ) -> SynthesisResult | None:
        if decision.get("confidence_band") not in REVIEW_BANDS:
            return None
        provider = (
            self.public_literature_provider if domain == "pv_literature" else self.local_provider
        )
        response = provider.draft(domain=domain, state=state, decision=decision)
        narrative = response.get("draft_narrative")
        citations = response.get("cited_passages")
        if not isinstance(narrative, str) or not narrative.strip() or not isinstance(citations, list) or not citations:
            raise ValueError("System Two must return a non-empty draft and cited_passages")

        source_text = _source_text(state)
        validated_citations = []
        for citation in citations:
            quote = citation.get("quote") if isinstance(citation, dict) else None
            if not isinstance(quote, str) or not quote or quote not in source_text:
                raise ValueError("System Two citation is not an exact source quotation")
            start = source_text.index(quote)
            validated_citations.append(
                {"quote": quote, "start_char": start, "end_char": start + len(quote)}
            )
        return SynthesisResult(
            model_id=provider.model_id,
            draft_narrative=narrative.strip(),
            cited_passages=validated_citations,
        )