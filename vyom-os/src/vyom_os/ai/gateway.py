"""The only door to a model.

The gateway decides which provider may see the data, makes the call, and
records one cost event per call. Domain services never import a provider.

Data policy:
* published literature (public text) may go to the hosted model;
* case data from a company channel (safety mailbox, call centre, web form)
  goes to the hosted model only when the tenant allows hosted processing and
  the model runs in the tenant's residency region; otherwise to the model in
  the client's network; if there is none, the call is blocked and the case is
  entered by hand.
Any failure raises ``AiFailure`` and the caller fails closed to manual work.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from vyom_literature.cost import CostEvent, build_cost_event
from vyom_literature.observability import new_correlation_id
from vyom_literature.system_one import SystemOneRouter
from vyom_os.ai import demo
from vyom_os.ai.providers import AiResult, DemoProvider, OpenAICompatibleProvider, Provider, VertexGeminiProvider
from vyom_os.ai.tasks import AiTask
from vyom_os.settings import AppSettings
from vyom_os.tenancy import TenantContext

CostSink = Callable[[CostEvent], None]


class AiPolicyBlocked(RuntimeError):
    """No permitted model may see this data. The case is entered by hand."""


class AiFailure(RuntimeError):
    """The model call failed or broke the contract. The caller fails closed."""


class _UnavailableSystemOneClient:
    provider_name = "unavailable"
    last_usage = None
    last_model_version = None

    def system_one(self, **_: Any) -> Any:
        raise AiPolicyBlocked("no in-network model is configured for case data")


class AiGateway:
    def __init__(
        self,
        *,
        mode: str,
        hosted_fast: VertexGeminiProvider | None = None,
        hosted_drafting: VertexGeminiProvider | None = None,
        local: OpenAICompatibleProvider | None = None,
        cost_sink: CostSink | None = None,
    ):
        if mode not in ("demo", "live"):
            raise ValueError("mode must be 'demo' or 'live'")
        if mode == "live" and hosted_fast is None and local is None:
            raise ValueError("live mode needs Vertex AI settings or an in-network model")
        self.mode = mode
        self.demo = DemoProvider()
        self.hosted_fast = hosted_fast
        self.hosted_drafting = hosted_drafting or hosted_fast
        self.local = local
        self.cost_sink = cost_sink

    @classmethod
    def from_settings(cls, settings: AppSettings, *, cost_sink: CostSink | None = None) -> AiGateway:
        if settings.ai_mode == "demo":
            return cls(mode="demo", cost_sink=cost_sink)
        fast = VertexGeminiProvider(settings=settings.vertex_fast) if settings.vertex_fast else None
        drafting = VertexGeminiProvider(settings=settings.vertex_drafting) if settings.vertex_drafting else None
        local = OpenAICompatibleProvider(settings.local_model) if settings.local_model else None
        return cls(mode="live", hosted_fast=fast, hosted_drafting=drafting, local=local, cost_sink=cost_sink)

    # -- policy -----------------------------------------------------------------
    def choose(self, task: AiTask, tenant: TenantContext, *, identifiable: bool) -> Provider:
        if self.mode == "demo":
            return self.demo
        hosted = self.hosted_drafting if task.call_kind == "system_two" else self.hosted_fast
        if hosted is not None:
            if not identifiable:
                return hosted
            if tenant.hosted_processing_allowed and hosted.region == tenant.residency_region:
                return hosted
        if self.local is not None:
            return self.local
        raise AiPolicyBlocked(
            "This tenant's case data may not be sent to the hosted model and no in-network model is "
            "configured. Enter the case by hand."
        )

    def describe(self, tenant: TenantContext) -> dict[str, Any]:
        """What the settings page shows: which model handles which data."""

        def info(provider: Any) -> dict[str, Any] | None:
            if provider is None:
                return None
            return {
                "provider": provider.provider_name,
                "model_id": provider.model_id,
                "hosted": provider.hosted,
                "region": provider.region,
            }

        def route(identifiable: bool, kind: str) -> dict[str, Any] | None:
            task = AiTask(name="probe", version="probe", call_kind=kind, system_instruction="", response_schema={})  # type: ignore[arg-type]
            try:
                return info(self.choose(task, tenant, identifiable=identifiable))
            except AiPolicyBlocked:
                return None

        return {
            "mode": self.mode,
            "is_ai": self.mode == "live",
            "literature_screening": info(self.demo if self.mode == "demo" else self.hosted_fast),
            "case_extraction": route(True, "system_one"),
            "case_narrative": route(True, "system_two"),
            "literature_case_extraction": route(False, "system_one"),
            "report_drafting": route(False, "system_two"),
        }

    # -- calls ------------------------------------------------------------------
    def run(
        self,
        task: AiTask,
        payload: dict[str, Any],
        *,
        tenant: TenantContext,
        identifiable: bool,
        item_type: str,
        item_ref: str,
        correlation_id: str | None = None,
    ) -> AiResult:
        provider = self.choose(task, tenant, identifiable=identifiable)
        correlation_id = correlation_id or new_correlation_id()
        started = time.perf_counter_ns()
        try:
            result = provider.generate(task, payload)
        except Exception as error:  # noqa: BLE001 - every failure fails closed
            self._record(
                tenant, task, provider.provider_name, provider.model_id, item_type, item_ref, correlation_id,
                outcome="provider_error", usage=None, latency_ms=(time.perf_counter_ns() - started) // 1_000_000,
            )
            raise AiFailure(f"{task.name} failed: {type(error).__name__}") from error
        self._record(
            tenant, task, result.provider, result.model_id, item_type, item_ref, correlation_id,
            outcome="ok", usage=result.usage, latency_ms=result.latency_ms,
        )
        return result

    def record_contract_failure(
        self, task: AiTask, result: AiResult, *, tenant: TenantContext, item_type: str, item_ref: str
    ) -> None:
        """A call that returned but failed validation is logged as malformed."""
        self._record(
            tenant, task, result.provider, result.model_id, item_type, item_ref, new_correlation_id(),
            outcome="malformed", usage=None, latency_ms=None,
        )

    def _record(
        self,
        tenant: TenantContext,
        task: AiTask,
        provider: str,
        model_id: str,
        item_type: str,
        item_ref: str,
        correlation_id: str,
        *,
        outcome: str,
        usage: dict[str, Any] | None,
        latency_ms: int | None,
    ) -> None:
        if self.cost_sink is None:
            return
        event = build_cost_event(
            tenant_id=tenant.id,
            item_type=item_type,
            item_ref=item_ref,
            provider=provider,
            model_id=model_id,
            call_kind=task.call_kind,
            correlation_id=correlation_id,
            prompt_version=task.version,
            schema_version=task.version,
            outcome=outcome,
            usage=usage,
            latency_ms=latency_ms,
        )
        try:
            self.cost_sink(event)
        except Exception:  # noqa: BLE001 - telemetry must never break the work
            pass

    def literature_router(self) -> SystemOneRouter:
        """System One router for published literature (public text)."""
        local = self.local or _UnavailableSystemOneClient()
        local_model = self.local.model_id if self.local else "unavailable"
        if self.mode == "demo":
            return SystemOneRouter(
                public_literature_client=self.demo,
                local_client=local,
                public_model=demo.DEMO_MODEL_ID,
                local_model=local_model,
                sampler_version=demo.DEMO_SAMPLER_VERSION,
            )
        if self.hosted_fast is None:
            raise AiPolicyBlocked("literature screening needs the Vertex AI model")
        return SystemOneRouter(
            public_literature_client=self.hosted_fast,
            local_client=local,
            public_model=self.hosted_fast.model_id,
            local_model=local_model,
            sampler_version=self.hosted_fast.settings.sampler_version,
        )
