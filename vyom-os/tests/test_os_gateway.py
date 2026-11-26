"""Data policy, fail-closed behaviour and provider wire formats, without a network."""

import json

import pytest

from vyom_literature.providers.vertex_ai import VertexSettings
from vyom_os.ai.gateway import AiFailure, AiGateway, AiPolicyBlocked
from vyom_os.ai.providers import OpenAICompatibleProvider, VertexGeminiProvider, validate_local_url
from vyom_os.ai.tasks import CASE_EXTRACTION, CASE_NARRATIVE, REPORT_SECTION
from vyom_os.settings import LocalModelSettings
from vyom_os.tenancy import TenantContext

SETTINGS = VertexSettings(project_id="sample-project", region="asia-south1", model_id="gemini-2.5-flash", sampler_version="s1")


def _tenant(**overrides):
    values = {"id": "00000000-0000-0000-0000-0000000000aa", "slug": "demo-pharma", "display_name": "Demo"}
    values.update(overrides)
    return TenantContext(**values)


def _vertex(output=None, fail=False):
    def transport(url, body, timeout):
        transport.calls.append((url, body))
        if fail:
            raise TimeoutError("slow")
        return {
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(output or {"text": "x", "citations": []})}]}}],
            "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 30},
            "modelVersion": "gemini-2.5-flash-001",
        }

    transport.calls = []
    return VertexGeminiProvider(settings=SETTINGS, token_source=lambda: ("token", "test"), transport=transport)


def _local():
    def transport(url, body, headers, timeout):
        return {"choices": [{"message": {"content": json.dumps({"text": "local", "citations": []})}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}

    return OpenAICompatibleProvider(LocalModelSettings(base_url="http://ollama.vyom.svc.cluster.local:11434", model_id="local-model", api_key=""), transport=transport)


def test_demo_mode_always_uses_the_rule_engine():
    gateway = AiGateway(mode="demo")
    assert gateway.choose(CASE_EXTRACTION, _tenant(), identifiable=True).provider_name == "demo"


def test_case_data_stays_local_unless_the_tenant_allows_hosted_processing():
    gateway = AiGateway(mode="live", hosted_fast=_vertex(), local=_local())
    assert gateway.choose(CASE_EXTRACTION, _tenant(), identifiable=True).provider_name == "local_model"
    assert gateway.choose(REPORT_SECTION, _tenant(), identifiable=False).provider_name == "vertex_ai"
    allowed = _tenant(hosted_processing_allowed=True)
    assert gateway.choose(CASE_EXTRACTION, allowed, identifiable=True).provider_name == "vertex_ai"
    other_region = _tenant(hosted_processing_allowed=True, residency_region="europe-west4")
    assert gateway.choose(CASE_EXTRACTION, other_region, identifiable=True).provider_name == "local_model"


def test_blocked_when_no_permitted_model():
    gateway = AiGateway(mode="live", hosted_fast=_vertex())
    with pytest.raises(AiPolicyBlocked):
        gateway.choose(CASE_NARRATIVE, _tenant(), identifiable=True)
    assert gateway.describe(_tenant())["case_extraction"] is None


def test_failure_fails_closed_and_is_logged():
    events = []
    gateway = AiGateway(mode="live", hosted_fast=_vertex(fail=True), cost_sink=events.append)
    with pytest.raises(AiFailure):
        gateway.run(REPORT_SECTION, {"x": 1}, tenant=_tenant(), identifiable=False, item_type="pv_report", item_ref="VY-PBRER-0001")
    assert [e.outcome for e in events] == ["provider_error"]
    assert events[0].estimated_cost_usd is None


def test_successful_call_records_real_usage():
    events = []
    gateway = AiGateway(mode="live", hosted_fast=_vertex(), cost_sink=events.append)
    result = gateway.run(REPORT_SECTION, {"x": 1}, tenant=_tenant(), identifiable=False, item_type="pv_report", item_ref="VY-PBRER-0001")
    assert result.usage == {"input_tokens": 120, "output_tokens": 30}
    assert events[0].input_tokens == 120 and events[0].estimated_cost_usd is not None
    assert events[0].prompt_version == REPORT_SECTION.version


def test_vertex_request_uses_structured_output_and_system_instruction():
    provider = _vertex()
    provider.generate(CASE_EXTRACTION, {"source_text": "text"})
    url, body = provider._transport.calls[0]
    assert url.startswith("https://asia-south1-aiplatform.googleapis.com/v1/projects/sample-project/locations/asia-south1/")
    assert url.endswith("models/gemini-2.5-flash:generateContent")
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"] == CASE_EXTRACTION.response_schema
    assert body["systemInstruction"]["parts"][0]["text"] == CASE_EXTRACTION.system_instruction


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://models.example.com", True),
        ("http://localhost:11434", True),
        ("http://10.0.3.4:8000", True),
        ("http://ollama:11434", True),
        ("http://ollama.vyom.svc.cluster.local:11434", True),
        ("http://models.example.com", False),
        ("ftp://localhost", False),
    ],
)
def test_local_model_url_policy(url, ok):
    if ok:
        validate_local_url(url)
    else:
        with pytest.raises(ValueError):
            validate_local_url(url)
