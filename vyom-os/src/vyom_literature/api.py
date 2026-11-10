from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import date
from typing import Any, Callable, Literal, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from vyom_literature.ledger import (
    append_sys1_decision,
    append_sys2_synthesis,
    get_sys2_synthesis,
    record_state_and_source,
)
from vyom_literature.review import (
    append_review_label,
    evaluate_gold_decisions,
    fetch_gold_decisions,
    fetch_review_queue,
    fetch_screening_log,
)
from vyom_literature.system_one import SystemOneRouter
from vyom_literature.system_two import SystemTwoRouter


MAX_STATE_BYTES = 1_000_000


class IcsrIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["safety_email", "call_transcript", "hospital_adr_form", "partner_e2b"]
    source_uid: str = Field(min_length=1, max_length=256)
    normalized_state: dict[str, Any]
    event_verbatim: Optional[str] = Field(default=None, max_length=2000)


class LiteratureSweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_date: date
    to_date: date


class ReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: int = Field(gt=0)
    action: Literal["ACCEPT", "CORRECT", "ESCALATE"]
    override_patch: Optional[dict[str, Any]] = None
    event_verbatim: Optional[str] = Field(default=None, max_length=2000)
    rationale_note: Optional[str] = Field(default=None, max_length=4000)


class ReviewerIdentity(BaseModel):
    id: UUID
    role: Literal["safety_physician", "pv_associate", "cpc_coder", "tpa_auditor"]


def _validate_state_size(state: dict[str, Any]) -> None:
    if len(json.dumps(state, ensure_ascii=False).encode("utf-8")) > MAX_STATE_BYTES:
        raise HTTPException(status_code=413, detail="Normalized state exceeds the configured size limit")


def create_app(
    *,
    router: SystemOneRouter,
    connection_factory: Callable[[], Any],
    api_token: str,
    reviewer_tokens: dict[str, ReviewerIdentity] | None = None,
    literature_runner: Callable[[date, date], list[dict[str, Any]]] | None = None,
    system_two_router: SystemTwoRouter | None = None,
) -> FastAPI:
    if not api_token:
        raise ValueError("An API bearer token is required")

    app = FastAPI(title="Vyom OS Decision API", version="2.0.0")
    bearer = HTTPBearer(auto_error=False)
    reviewer_tokens = reviewer_tokens or {}

    def require_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> None:
        if credentials is None or not secrets.compare_digest(credentials.credentials, api_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    def require_reviewer(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    ) -> ReviewerIdentity:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reviewer token required")
        for token_value, identity in reviewer_tokens.items():
            if secrets.compare_digest(credentials.credentials, token_value):
                return identity
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reviewer token")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/icsr/intake", dependencies=[Depends(require_token)])
    def icsr_intake(request: IcsrIntakeRequest) -> dict[str, Any]:
        normalized_state = {**request.normalized_state, "domain": "pv_icsr"}
        if request.event_verbatim is not None:
            normalized_state["event_verbatim"] = request.event_verbatim
        _validate_state_size(normalized_state)

        try:
            decision = router.evaluate("pv_icsr", normalized_state)
        except Exception as error:
            raise HTTPException(status_code=502, detail="Local ICSR System One evaluation failed") from error

        raw_source_key = f"{request.source}:{request.source_uid}"
        source_key_hash = hashlib.sha256(raw_source_key.encode("utf-8")).hexdigest()
        source_uid = f"{source_key_hash}:{decision['state_sha256']}"
        dedup_key = f"pv_icsr:{source_key_hash}:{decision['state_sha256']}"
        try:
            with connection_factory() as connection:
                state_write = record_state_and_source(
                    connection,
                    domain="pv_icsr",
                    dedup_key=dedup_key,
                    title_or_header="Identifiable safety report",
                    normalized_state=normalized_state,
                    source=request.source,
                    source_uid=source_uid,
                    raw_payload=normalized_state,
                )
                decision_id = append_sys1_decision(
                    connection, state_id=state_write.state_id, decision=decision
                )
                synthesis = (
                    get_sys2_synthesis(connection, decision_id=decision_id)
                    if system_two_router is not None
                    else None
                )
        except Exception as error:
            raise HTTPException(status_code=503, detail="ICSR decision ledger write failed") from error

        if system_two_router is not None and synthesis is None:
            try:
                generated = system_two_router.synthesize(
                    domain="pv_icsr", state=state_write.normalized_state, decision=decision
                )
                if generated is not None:
                    with connection_factory() as synthesis_connection:
                        append_sys2_synthesis(
                            synthesis_connection,
                            decision_id=decision_id,
                            synthesis=generated,
                        )
                    synthesis = {
                        "model_id": generated.model_id,
                        "draft_narrative": generated.draft_narrative,
                        "cited_passages": generated.cited_passages,
                    }
            except Exception as error:
                raise HTTPException(
                    status_code=502,
                    detail="ICSR System One decision was recorded, but System Two synthesis failed",
                ) from error

        return {
            "state_id": state_write.state_id,
            "decision_id": decision_id,
            "event_verbatim": request.event_verbatim,
            "confidence_band": decision["confidence_band"],
            "gate_probabilities": decision["gate_probabilities"],
            "requires_human_review": True,
            "synthesis": synthesis,
        }

    @app.post("/v1/literature/sweep", dependencies=[Depends(require_token)])
    def literature_sweep(request: LiteratureSweepRequest) -> dict[str, Any]:
        if request.from_date > request.to_date:
            raise HTTPException(status_code=422, detail="from_date must be on or before to_date")
        if literature_runner is None:
            raise HTTPException(status_code=503, detail="Literature sweep is not configured")
        try:
            reports = literature_runner(request.from_date, request.to_date)
        except Exception as error:
            raise HTTPException(status_code=502, detail="Literature sweep failed") from error
        return {"strategies": reports}

    @app.get("/v1/review/queue")
    def review_queue(
        domain: Optional[str] = None,
        limit: int = 50,
        _: ReviewerIdentity = Depends(require_reviewer),
    ) -> dict[str, Any]:
        try:
            with connection_factory() as connection:
                items = fetch_review_queue(connection, domain=domain, limit=limit)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="Review queue unavailable") from error
        return {"items": items}

    @app.post("/v1/review/states/{state_id}/actions")
    def review_action(
        state_id: int,
        request: ReviewActionRequest,
        reviewer: ReviewerIdentity = Depends(require_reviewer),
    ) -> dict[str, Any]:
        try:
            with connection_factory() as connection:
                label_id = append_review_label(
                    connection,
                    state_id=state_id,
                    decision_id=request.decision_id,
                    reviewer_id=reviewer.id,
                    reviewer_role=reviewer.role,
                    action=request.action,
                    override_patch=request.override_patch,
                    event_verbatim=request.event_verbatim,
                    rationale_note=request.rationale_note,
                )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="Review action could not be recorded") from error
        return {"label_id": label_id, "split": "pool", "action": request.action}

    @app.get("/v1/reports/gold/{gold_set_version}")
    def gold_report(
        gold_set_version: str,
        model_id: str,
        sampler_version: str,
        question_schema_version: int,
        threshold_policy_version: int,
        _: ReviewerIdentity = Depends(require_reviewer),
    ) -> dict[str, Any]:
        try:
            with connection_factory() as connection:
                rows = fetch_gold_decisions(
                    connection,
                    gold_set_version=gold_set_version,
                    model_id=model_id,
                    sampler_version=sampler_version,
                    question_schema_version=question_schema_version,
                    threshold_policy_version=threshold_policy_version,
                )
            return {
                "gold_set_version": gold_set_version,
                "model_id": model_id,
                "sampler_version": sampler_version,
                "question_schema_version": question_schema_version,
                "threshold_policy_version": threshold_policy_version,
                **evaluate_gold_decisions(rows),
            }
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="Gold evaluation unavailable") from error

    @app.get("/v1/reports/screening-log")
    def screening_log(
        days: int = 7,
        _: ReviewerIdentity = Depends(require_reviewer),
    ) -> dict[str, Any]:
        try:
            with connection_factory() as connection:
                groups = fetch_screening_log(connection, days=days)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="Screening log unavailable") from error
        return {"days": days, "groups": groups}

    return app


def create_app_from_env() -> FastAPI:
    from dotenv import load_dotenv

    from vyom_literature.config import BACKEND_ROOT, Settings
    from vyom_literature.sweep import build_environment_sweep

    load_dotenv(BACKEND_ROOT / ".env.local", override=False)
    settings = Settings.from_env()
    router = SystemOneRouter.from_env()
    system_two_router = SystemTwoRouter.from_env()
    token = os.environ.get("API_BEARER_TOKEN", "")
    if not token:
        raise ValueError("API_BEARER_TOKEN is required")
    reviewer_tokens_raw = os.environ.get("REVIEWER_TOKENS_JSON", "")
    try:
        reviewer_tokens = {
            secret: ReviewerIdentity.model_validate(identity)
            for secret, identity in json.loads(reviewer_tokens_raw).items()
        }
    except (json.JSONDecodeError, AttributeError, TypeError) as error:
        raise ValueError("REVIEWER_TOKENS_JSON must be a JSON object of reviewer tokens and identities") from error
    database_url = settings.require_database_url()

    def connection_factory():
        import psycopg

        return psycopg.connect(database_url)

    def literature_runner(from_date: date, to_date: date) -> list[dict[str, Any]]:
        with connection_factory() as connection:
            return build_environment_sweep(
                connection=connection,
                router=router,
                settings=settings,
                from_date=from_date,
                to_date=to_date,
                system_two_router=system_two_router,
            )

    return create_app(
        router=router,
        connection_factory=connection_factory,
        api_token=token,
        reviewer_tokens=reviewer_tokens,
        literature_runner=literature_runner,
        system_two_router=system_two_router,
    )