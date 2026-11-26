"""HTTP API for the Vyom drug-safety console.

Every tenant route needs a bearer session token *and* an ``X-Tenant-ID``
header that matches it. Tenant data queries run on the RLS-bound role in a
transaction scoped to that tenant. The API is called server-to-server by the
web console, so it sends no CORS headers.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from datetime import date
from typing import Any, Literal, TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from vyom_literature.cost import CostEvent, record_cost_event
from vyom_os import audit, cases, dashboard, e2b, literature, products, reports
from vyom_os.ai.gateway import AiGateway
from vyom_os.audit import Actor
from vyom_os.core import Ctx, DomainError, Forbidden
from vyom_os.db import Database, fetch_all, fetch_one
from vyom_os.security import (
    Authorizer,
    InvalidToken,
    SessionClaims,
    SignInThrottle,
    issue_token,
    verify_password,
    verify_password_or_dummy,
    verify_token,
)
from vyom_os.settings import AppSettings
from vyom_os.tenancy import TenantContext, load_tenant

CASE_NUMBER = r"^VY-CASE-\d{4,6}$"
REPORT_NUMBER = r"^VY-(PBRER|PADER)-\d{4,6}$"
MAX_BODY_BYTES = 1_000_000

T = TypeVar("T")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignInRequest(_Strict):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class SweepRequest(_Strict):
    from_date: date | None = None
    to_date: date | None = None


class LiteratureDecisionRequest(_Strict):
    decision_id: int = Field(gt=0)
    outcome: Literal["valid_icsr", "safety_information", "not_relevant", "escalated"]
    reason: str | None = Field(default=None, max_length=2000)


class IntakeRequest(_Strict):
    channel: Literal["safety_email", "call_transcript", "manual_entry"]
    source_text: str = Field(min_length=20, max_length=20000)
    subject: str | None = Field(default=None, max_length=200)
    received_on: date | None = None


class CaseSaveRequest(_Strict):
    expected_version: int = Field(gt=0)
    payload: dict[str, Any]
    reason: str = Field(min_length=1, max_length=500)


class VersionRequest(_Strict):
    expected_version: int = Field(gt=0)


class TransitionRequest(_Strict):
    action: Literal["submit", "return", "approve", "close_invalid", "mark_duplicate", "reopen"]
    expected_version: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)
    duplicate_of: str | None = Field(default=None, max_length=32)


class ReportCreateRequest(_Strict):
    product_code: str = Field(min_length=1, max_length=64)
    report_type: Literal["pbrer", "pader"]
    interval_start: date
    data_lock_point: date


class SectionRequest(_Strict):
    expected_version: int = Field(gt=0)
    action: Literal["edit", "accept"]
    text: str | None = Field(default=None, max_length=12000)
    reason: str | None = Field(default=None, max_length=500)


class SignoffRequest(_Strict):
    version: int = Field(gt=0)
    meaning: str = Field(min_length=1, max_length=300)
    password: str = Field(min_length=1, max_length=200)


class ReferenceTermsRequest(_Strict):
    terms: list[str] = Field(max_length=500)
    rsi_version: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=500)


class _TtlCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, load: Callable[[], T]) -> T:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
            if hit and now - hit[0] < self.ttl:
                return hit[1]
        value = load()
        with self._lock:
            self._items[key] = (now, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def database_cost_sink(database: Database) -> Callable[[CostEvent], None]:
    """Cost events commit on their own, so a failed request still records the call."""

    def sink(event: CostEvent) -> None:
        with database.tenant(event.tenant_id) as connection:
            record_cost_event(connection, event)

    return sink


def create_app(settings: AppSettings, *, database: Database | None = None, gateway: AiGateway | None = None) -> FastAPI:
    db = database or Database(settings.database_url, settings.app_database_url)
    gw = gateway or AiGateway.from_settings(settings, cost_sink=database_cost_sink(db))
    throttle = SignInThrottle()
    tenant_cache = _TtlCache(60)
    user_cache = _TtlCache(30)
    policy_cache = _TtlCache(300)
    bearer = HTTPBearer(auto_error=False)
    app = FastAPI(
        title="Vyom OS",
        version="0.2.0",
        docs_url="/docs" if settings.api_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.api_docs else None,
    )
    app.state.database = db
    app.state.gateway = gw

    def authorizer() -> Authorizer:
        def load() -> Authorizer:
            with db.service() as connection:
                return Authorizer.load(connection)

        return policy_cache.get("policies", load)

    def tenant(tenant_id: str) -> TenantContext | None:
        def load() -> TenantContext | None:
            with db.service() as connection:
                return load_tenant(connection, tenant_id)

        return tenant_cache.get(tenant_id, load)

    def account(user_id: str) -> dict[str, Any] | None:
        def load() -> dict[str, Any] | None:
            with db.service() as connection:
                return fetch_one(
                    connection, "select role, status, tenant_id::text as tenant_id from user_accounts where id = %s", (user_id,)
                )

        return user_cache.get(user_id, load)

    @app.middleware("http")
    async def limit_body(request: Request, call_next: Callable[..., Any]) -> Any:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body is too large."}, status_code=413)
        return await call_next(request)

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse({"detail": error.message}, status_code=error.status_code)

    def session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        x_tenant_id: str | None = Header(default=None),
    ) -> SessionClaims:
        if credentials is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
        try:
            claims = verify_token(credentials.credentials, secret=settings.session_secret)
        except InvalidToken as error:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has ended. Sign in again.") from error
        if not x_tenant_id or x_tenant_id != claims.tenant_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "The tenant header does not match your session.")
        current = account(claims.user_id)
        if current is None or current["status"] != "active" or current["role"] != claims.role or current["tenant_id"] != claims.tenant_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your access changed. Sign in again.")
        return claims

    def context(claims: SessionClaims = Depends(session)) -> Ctx:
        found = tenant(claims.tenant_id)
        if found is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown tenant.")
        return Ctx(
            tenant=found,
            actor=Actor(user_id=claims.user_id, role=claims.role, email=claims.email),
            today=settings.today(),
            authorizer=authorizer(),
            gateway=gw,
        )

    def run(ctx: Ctx, work: Callable[[Any], T]) -> T:
        with db.tenant(ctx.tenant.id) as connection:
            return work(connection)

    # -- health -----------------------------------------------------------------
    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        try:
            with db.service() as connection:
                connection.execute("select 1")
            database_status = "ok"
        except Exception:  # noqa: BLE001 - health must answer
            database_status = "unavailable"
        return {"status": "ok" if database_status == "ok" else "degraded", "database": database_status, "ai_mode": gw.mode}

    # -- session ----------------------------------------------------------------
    @app.post("/v1/auth/sign-in")
    def sign_in(body: SignInRequest) -> dict[str, Any]:
        email = body.email.strip().lower()
        if throttle.blocked(email):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again in 15 minutes.")
        with db.service() as connection:
            row = fetch_one(
                connection,
                """
                select u.id::text as id, u.email, u.password_hash, u.role, u.status, t.id::text as tenant_id, t.slug
                from user_accounts u join tenants t on t.id = u.tenant_id
                where u.email = %s
                """,
                (email,),
            )
            matched = verify_password_or_dummy(body.password, row["password_hash"] if row else None)
            if row is None or not matched or row["status"] != "active":
                throttle.failed(email)
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is wrong.")
            connection.execute("update user_accounts set last_login_at = now() where id = %s", (row["id"],))
        throttle.succeeded(email)
        found = tenant(row["tenant_id"])
        if found is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown tenant.")
        token, claims = issue_token(
            user_id=row["id"], email=row["email"], role=row["role"], tenant_id=row["tenant_id"],
            tenant_slug=row["slug"], secret=settings.session_secret, ttl_seconds=settings.session_ttl_seconds,
        )
        with db.tenant(row["tenant_id"]) as connection:
            audit.record(
                connection, entity_kind="user", entity_ref=row["id"], event_type="signed_in",
                actor=Actor(user_id=row["id"], role=row["role"], email=row["email"]),
            )
        return {
            "token": token,
            "expires_at": claims.expires_at,
            "user": {"id": row["id"], "email": row["email"], "role": row["role"]},
            "tenant": found.public(),
            "permissions": authorizer().permissions(row["role"]),
        }

    @app.post("/v1/auth/sign-out")
    def sign_out(ctx: Ctx = Depends(context)) -> dict[str, str]:
        run(ctx, lambda c: audit.record(c, entity_kind="user", entity_ref=str(ctx.actor.user_id), event_type="signed_out", actor=ctx.actor))
        return {"status": "signed_out"}

    @app.get("/v1/me")
    def me(ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return {
            "user": {"id": ctx.actor.user_id, "email": ctx.actor.email, "role": ctx.actor.role},
            "tenant": ctx.tenant.public(),
            "permissions": ctx.authorizer.permissions(ctx.actor.role),
            "ai": gw.describe(ctx.tenant),
            "today": ctx.today.isoformat(),
        }

    @app.get("/v1/dashboard")
    def overview(ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: dashboard.overview(c, ctx))

    # -- products and settings --------------------------------------------------
    @app.get("/v1/products")
    def product_list(ctx: Ctx = Depends(context)) -> list[dict[str, Any]]:
        if ctx.actor.role == "ops":
            raise Forbidden("Operations accounts do not read the product catalogue.")
        return run(ctx, products.list_products)

    @app.put("/v1/products/{code}/reference-terms")
    def product_terms(code: str, body: ReferenceTermsRequest, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        result = run(ctx, lambda c: products.update_reference_terms(c, ctx, code, terms=body.terms, rsi_version=body.rsi_version, reason=body.reason))
        return result

    @app.get("/v1/settings")
    def tenant_settings(ctx: Ctx = Depends(context)) -> dict[str, Any]:
        members = run(ctx, lambda c: fetch_all(c, "select email, role, status from tenant_members order by role, email"))
        return {
            "tenant": ctx.tenant.public(),
            "ai": gw.describe(ctx.tenant),
            "members": members,
            "permissions": {role: ctx.authorizer.permissions(role) for role in ("reviewer", "safety_physician", "qppv", "admin", "ops")},
            "timezone": settings.timezone,
        }

    @app.get("/v1/audit")
    def audit_trail(
        entity_kind: str | None = Query(default=None, max_length=20),
        entity_ref: str | None = Query(default=None, max_length=80),
        ctx: Ctx = Depends(context),
    ) -> list[dict[str, Any]]:
        ctx.require("dashboard.read")
        if entity_kind and entity_ref:
            return run(ctx, lambda c: audit.history(c, entity_kind=entity_kind, entity_ref=entity_ref))
        return run(ctx, lambda c: audit.recent(c, limit=100))

    # -- literature -------------------------------------------------------------
    @app.get("/v1/literature")
    def literature_queue(
        view: Literal["open", "decided", "all"] = "open",
        product: str | None = Query(default=None, max_length=64),
        ctx: Ctx = Depends(context),
    ) -> dict[str, Any]:
        return run(ctx, lambda c: literature.queue(c, ctx, view=view, product=product))

    @app.post("/v1/literature/sweeps")
    def literature_sweep(body: SweepRequest, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        ctx.require("literature.screen")
        return run(ctx, lambda c: literature.sweep(c, ctx, from_date=body.from_date, to_date=body.to_date))

    @app.get("/v1/literature/{state_id}")
    def literature_detail(state_id: int, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: literature.detail(c, ctx, state_id))

    @app.post("/v1/literature/{state_id}/decision")
    def literature_decide(state_id: int, body: LiteratureDecisionRequest, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: literature.decide(c, ctx, state_id, decision_id=body.decision_id, outcome=body.outcome, reason=body.reason))

    # -- cases ------------------------------------------------------------------
    @app.get("/v1/cases")
    def case_list(
        status_filter: str | None = Query(default=None, alias="status", max_length=20),
        product: str | None = Query(default=None, max_length=64),
        serious: bool | None = None,
        q: str | None = Query(default=None, max_length=100),
        ctx: Ctx = Depends(context),
    ) -> dict[str, Any]:
        return run(ctx, lambda c: cases.list_cases(c, ctx, status=status_filter, product=product, serious=serious, query=q))

    @app.post("/v1/cases", status_code=201)
    def case_intake(body: IntakeRequest, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: cases.intake(c, ctx, channel=body.channel, source_text=body.source_text, subject=body.subject, received_on=body.received_on))

    @app.get("/v1/coding/suggest")
    def coding_suggest(verbatim: str = Query(min_length=1, max_length=300), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: cases.suggest_coding(c, ctx, verbatim))

    @app.get("/v1/cases/{case_number}")
    def case_detail(case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: cases.get_case(c, ctx, case_number))

    @app.put("/v1/cases/{case_number}")
    def case_save(body: CaseSaveRequest, case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: cases.save_version(c, ctx, case_number, expected_version=body.expected_version, payload=body.payload, reason=body.reason))

    @app.post("/v1/cases/{case_number}/narrative")
    def case_narrative(body: VersionRequest, case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: cases.draft_narrative(c, ctx, case_number, expected_version=body.expected_version))

    @app.post("/v1/cases/{case_number}/transitions")
    def case_transition(body: TransitionRequest, case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(
            ctx,
            lambda c: cases.transition(
                c, ctx, case_number, action=body.action, expected_version=body.expected_version,
                reason=body.reason, duplicate_of=body.duplicate_of,
            ),
        )

    @app.post("/v1/cases/{case_number}/exports", status_code=201)
    def case_export(case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(ctx, lambda c: e2b.export_case(c, ctx, case_number))

    @app.get("/v1/cases/{case_number}/exports/{export_id}")
    def case_export_download(export_id: int, case_number: str = Depends(_case_number), ctx: Ctx = Depends(context)) -> Response:
        row = run(ctx, lambda c: e2b.get_export(c, ctx, case_number, export_id))
        return Response(
            row["content"],
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="{case_number}-v{row["case_version"]}-e2b-draft.xml"',
                "X-Content-SHA256": row["content_sha256"],
            },
        )

    # -- reports ----------------------------------------------------------------
    @app.get("/v1/reports")
    def report_list(ctx: Ctx = Depends(context)) -> list[dict[str, Any]]:
        return run(ctx, lambda c: reports.list_reports(c, ctx))

    @app.post("/v1/reports", status_code=201)
    def report_create(body: ReportCreateRequest, ctx: Ctx = Depends(context)) -> dict[str, Any]:
        return run(
            ctx,
            lambda c: reports.create_report(
                c, ctx, product_code=body.product_code, report_type=body.report_type,
                interval_start=body.interval_start, data_lock_point=body.data_lock_point,
            ),
        )

    @app.get("/v1/reports/{report_number}")
    def report_detail(
        version: int | None = Query(default=None, gt=0), report_number: str = Depends(_report_number), ctx: Ctx = Depends(context)
    ) -> dict[str, Any]:
        return run(ctx, lambda c: reports.get_report(c, ctx, report_number, version=version))

    @app.post("/v1/reports/{report_number}/sections/{key}")
    def report_section(
        key: str, body: SectionRequest, report_number: str = Depends(_report_number), ctx: Ctx = Depends(context)
    ) -> dict[str, Any]:
        return run(
            ctx,
            lambda c: reports.update_section(
                c, ctx, report_number, key, expected_version=body.expected_version, action=body.action,
                text=body.text, reason=body.reason,
            ),
        )

    @app.post("/v1/reports/{report_number}/signoff")
    def report_signoff(body: SignoffRequest, report_number: str = Depends(_report_number), ctx: Ctx = Depends(context)) -> dict[str, Any]:
        ctx.require("report.signoff")
        email = str(ctx.actor.email or "")
        if throttle.blocked(email):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again in 15 minutes.")
        with db.service() as connection:
            row = fetch_one(connection, "select password_hash from user_accounts where id = %s", (ctx.actor.user_id,))
        if row is None or not verify_password(body.password, row["password_hash"]):
            throttle.failed(email)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Password is wrong. The report was not signed.")
        throttle.succeeded(email)
        return run(ctx, lambda c: reports.signoff(c, ctx, report_number, version=body.version, meaning=body.meaning))

    @app.get("/v1/reports/{report_number}/export")
    def report_export(
        version: int | None = Query(default=None, gt=0), report_number: str = Depends(_report_number), ctx: Ctx = Depends(context)
    ) -> PlainTextResponse:
        view = run(ctx, lambda c: reports.get_report(c, ctx, report_number, version=version))
        return PlainTextResponse(
            reports.to_markdown(view),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{report_number}-v{view["version"]}.md"'},
        )

    # -- operations -------------------------------------------------------------
    @app.get("/v1/ops/summary")
    def ops_summary(ctx: Ctx = Depends(context)) -> dict[str, Any]:
        if ctx.actor.role not in ("ops", "admin"):
            raise Forbidden("Operations view only.")
        scope_all = ctx.actor.role == "ops" and ctx.tenant.kind == "internal"
        where = "" if scope_all else "where t.id = %(tenant)s"
        with db.service() as connection:
            tenants = fetch_all(
                connection,
                f"""
                select t.slug, t.display_name, t.is_fictional,
                       (select max(completed_at) from sweep_runs s where s.tenant_id = t.id) as last_sweep,
                       (select count(*) from model_cost_events m where m.tenant_id = t.id
                          and m.occurred_at > now() - interval '7 days')::int as model_calls_7d,
                       (select count(*) from model_cost_events m where m.tenant_id = t.id and m.outcome <> 'ok'
                          and m.occurred_at > now() - interval '7 days')::int as model_failures_7d,
                       (select count(*) from cases c where c.tenant_id = t.id
                          and c.status in ('data_entry', 'medical_review'))::int as open_cases,
                       (select count(*) from ops_alerts a where a.tenant_id = t.id and a.acked_at is null)::int as open_alerts
                from tenants t {where}
                order by t.slug
                """,
                {"tenant": ctx.tenant.id},
            )
        return {"scope": "all tenants" if scope_all else "this tenant", "ai_mode": gw.mode, "tenants": tenants}

    return app


def _case_number(case_number: str) -> str:
    normalised = case_number.strip().upper()
    if not re.fullmatch(CASE_NUMBER, normalised):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such case.")
    return normalised


def _report_number(report_number: str) -> str:
    normalised = report_number.strip().upper()
    if not re.fullmatch(REPORT_NUMBER, normalised):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such report.")
    return normalised


def create_app_from_env() -> FastAPI:
    return create_app(AppSettings.from_env())
