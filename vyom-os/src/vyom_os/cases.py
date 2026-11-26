"""Case processing: intake, assisted data entry, rules, medical review, approval.

Every change writes an append-only ``case_versions`` row (who, what kind of
author, why, lineage) plus an ``audit_events`` row. ``cases`` holds only the
head: status, current version and the fields the queue sorts on.

Models propose (extraction, coding hint, narrative draft); deterministic
rules decide validity, seriousness, expectedness and the clock; people
decide causality and approval.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Any

from pydantic import ValidationError

from vyom_literature.ledger import record_state_and_source
from vyom_os import audit, graph, rules, terminology
from vyom_os.ai.gateway import AiFailure, AiPolicyBlocked
from vyom_os.ai.tasks import CASE_EXTRACTION, CASE_NARRATIVE, AiOutputError, parse_extraction, parse_narrative
from vyom_os.core import Conflict, Ctx, InvalidInput, NotFound, Unavailable
from vyom_os.db import Jsonb, fetch_all, fetch_one, fetch_value
from vyom_os.models import CaseProduct, Causality, CasePayload, Coding, Narrative
from vyom_os.products import catalogue, list_products

CASE_STATUSES = ("data_entry", "medical_review", "approved", "closed_invalid", "duplicate")
OPEN_STATUSES = frozenset({"data_entry", "medical_review"})
CLOSED_STATUSES = frozenset({"approved", "closed_invalid", "duplicate"})
INTAKE_CHANNELS = ("safety_email", "call_transcript", "manual_entry")
TRANSITIONS = ("submit", "return", "approve", "close_invalid", "mark_duplicate", "reopen")
APPROVAL_MEANING = "Medical review complete. I approve this case version for regulatory reporting."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def next_number(connection: Any, name: str, prefix: str) -> str:
    value = fetch_value(
        connection,
        """
        insert into tenant_counters (name, value) values (%s, 1)
        on conflict (tenant_id, name) do update set value = tenant_counters.value + 1
        returning value
        """,
        (name,),
    )
    return f"{prefix}-{int(value):04d}"


def author_label(author: dict[str, Any]) -> str:
    if author.get("initials") is not None:
        return f"{author.get('surname', '')} {author.get('initials', '')}".strip()
    return str(author.get("name") or author.get("surname") or "").strip()


def literature_reference(state: dict[str, Any]) -> str:
    authors = [author_label(a) for a in state.get("authors") or [] if isinstance(a, dict)]
    names = ", ".join(authors[:6]) + (", et al" if len(authors) > 6 else "")
    year = state.get("publication_year") or (state.get("pub_date") or "")[:4]
    parts = [names, state.get("title"), state.get("journal"), str(year) if year else None]
    return ". ".join(str(part).rstrip(".") for part in parts if part)[:600] + "."


def literature_source_text(state: dict[str, Any]) -> str:
    return f"{state.get('title') or ''}\n\n{state.get('abstract') or ''}".strip()


def source_text_for(state: dict[str, Any] | None) -> str:
    if not state:
        return ""
    if state.get("domain") == "pv_literature":
        return literature_source_text(state)
    return str(state.get("text") or "")


def _is_demo(provider: str) -> bool:
    return provider == "demo"


def _suspect_codes(payload: CasePayload) -> list[str]:
    return [p.product_code for p in payload.products if p.role == "suspect" and p.product_code]


def _product_for(payload: CasePayload, products: list[dict[str, Any]]) -> dict[str, Any] | None:
    by_code = {p["code"]: p for p in products}
    for code in _suspect_codes(payload):
        if code in by_code:
            return by_code[code]
    return None


def _event_ref(reaction: Any) -> str:
    return rules.normalise_term(reaction.coding.pt or reaction.verbatim)


def _assess(
    payload: CasePayload, products: list[dict[str, Any]], ctx: Ctx, day_zero: date, status: str
) -> dict[str, Any]:
    product = _product_for(payload, products)
    reference = None
    if product is not None:
        reference = list(product.get("reference_safety_terms") or [])
    result = rules.assess(
        payload,
        reference_terms=reference,
        day_zero=day_zero,
        clock_policy=ctx.tenant.clock_policy,
        today=ctx.today,
        closed=status in CLOSED_STATUSES,
    )
    result["reference"] = (
        {"product": product["code"], "rsi_version": product["rsi_version"]} if product is not None else None
    )
    return result


def _apply_coding(connection: Any, ctx: Ctx, payload: CasePayload) -> CasePayload:
    reactions = []
    for reaction in payload.reactions:
        if reaction.coding.status == "none":
            suggestion = terminology.suggest_coding(
                connection,
                verbatim=reaction.verbatim,
                licensed=ctx.tenant.licensed,
                dictionary=ctx.tenant.meddra_dictionary,
            )
            reaction = reaction.model_copy(update={"coding": Coding(**suggestion)})
        reactions.append(reaction)
    return payload.model_copy(update={"reactions": reactions})


def _sync_graph(connection: Any, case_number: str, payload: CasePayload, *, provenance: str, state_id: int | None) -> None:
    """Keep the case's product and event edges in step with the current version."""
    status = "verified" if provenance == "human_label" else "reported"
    desired = {("suspect_product", "product", code) for code in _suspect_codes(payload)}
    desired |= {("reports_event", "event", _event_ref(r)) for r in payload.reactions if _event_ref(r)}
    existing = {
        (edge["relation"], edge["to_kind"], edge["to_ref"]): edge["evidence_status"]
        for edge in graph.edges_for(connection, kind="case", ref=case_number)
        if edge["from_kind"] == "case" and edge["relation"] in ("suspect_product", "reports_event")
    }
    for relation, to_kind, to_ref in desired:
        if (relation, to_kind, to_ref) in existing:
            if existing[(relation, to_kind, to_ref)] == "ruled_out":
                graph.set_status(
                    connection, from_kind="case", from_ref=case_number, relation=relation, to_kind=to_kind,
                    to_ref=to_ref, evidence_status=status, provenance=provenance,
                )
            continue
        graph.link(
            connection, from_kind="case", from_ref=case_number, relation=relation, to_kind=to_kind, to_ref=to_ref,
            evidence_status=status, provenance=provenance, source_state_id=state_id,
        )
    for (relation, to_kind, to_ref), evidence_status in existing.items():
        if (relation, to_kind, to_ref) not in desired and evidence_status != "ruled_out":
            graph.set_status(
                connection, from_kind="case", from_ref=case_number, relation=relation, to_kind=to_kind,
                to_ref=to_ref, evidence_status="ruled_out", provenance=provenance,
            )


def _head(connection: Any, case_number: str, *, lock: bool = False) -> dict[str, Any]:
    row = fetch_one(
        connection,
        f"""
        select c.id::text as id, c.case_number, c.status, c.source_channel, c.source_state_id,
               c.current_version, c.serious, c.day_zero, c.received_at, c.created_at, c.updated_at,
               p.code as product_code, p.name as product_name
        from cases c left join products p on p.id = c.product_id
        where c.case_number = %s
        {"for update of c" if lock else ""}
        """,
        (case_number,),
    )
    if row is None:
        raise NotFound(f"No case {case_number}.")
    return row


def _current(connection: Any, head: dict[str, Any]) -> dict[str, Any]:
    row = fetch_one(
        connection,
        """
        select version, payload, assessments, author_kind, reason, lineage, created_at
        from case_versions where case_id = %s and version = %s
        """,
        (head["id"], head["current_version"]),
    )
    if row is None:
        raise NotFound("The case has no saved version.")
    return row


def _source_state(connection: Any, state_id: int | None) -> dict[str, Any] | None:
    if state_id is None:
        return None
    return fetch_value(connection, "select normalized_state from clinical_states where id = %s", (state_id,))


def _write_version(
    connection: Any,
    ctx: Ctx,
    *,
    case_id: str,
    case_number: str,
    version: int,
    payload: CasePayload,
    author_kind: str,
    reason: str,
    lineage: dict[str, Any],
    products: list[dict[str, Any]],
    day_zero: date,
    status: str,
    state_id: int | None,
) -> dict[str, Any]:
    assessments = _assess(payload, products, ctx, day_zero, status)
    connection.execute(
        """
        insert into case_versions (case_id, version, payload, assessments, author_kind, author_id, reason, lineage)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            case_id,
            version,
            Jsonb(payload.model_dump(mode="json")),
            Jsonb(assessments),
            author_kind,
            ctx.actor.user_id,
            reason[:500],
            Jsonb(lineage),
        ),
    )
    product = _product_for(payload, products)
    connection.execute(
        """
        update cases set current_version = %s, serious = %s, product_id = %s, updated_at = now()
        where id = %s
        """,
        (version, assessments["seriousness"]["serious"], product["id"] if product else None, case_id),
    )
    _sync_graph(
        connection, case_number, payload,
        provenance="human_label" if author_kind == "human" else ("system_one" if author_kind == "ai" else "deterministic_rule"),
        state_id=state_id,
    )
    return assessments


def _extract(
    connection: Any,
    ctx: Ctx,
    *,
    case_number: str,
    source_text: str,
    channel: str,
    products: list[dict[str, Any]],
    identifiable: bool,
    extra_context: dict[str, Any] | None = None,
) -> tuple[CasePayload, str, str, dict[str, Any], list[str]]:
    """Returns (payload, author_kind, reason, lineage, warnings). Never raises for model trouble."""
    report_type = "literature" if channel == "literature" else "spontaneous"
    empty = CasePayload(report_type=report_type)
    tenant_products = catalogue(products)
    try:
        result = ctx.gateway.run(
            CASE_EXTRACTION,
            {"source_text": source_text, "context": {"channel": channel, "tenant_products": tenant_products, **(extra_context or {})}},
            tenant=ctx.tenant,
            identifiable=identifiable,
            item_type="pv_icsr",
            item_ref=case_number,
        )
    except AiPolicyBlocked as error:
        return empty, "system", "Manual entry: no permitted model for this data", {"ai": "blocked", "detail": str(error)}, [str(error)]
    except AiFailure as error:
        return (
            empty, "system", "Manual entry: extraction failed", {"ai": "failed", "detail": str(error)},
            ["Assisted extraction failed. Enter the case by hand."],
        )
    try:
        parsed = parse_extraction(result.output, source_text=source_text, tenant_products=tenant_products, channel=channel)
    except AiOutputError as error:
        ctx.gateway.record_contract_failure(CASE_EXTRACTION, result, tenant=ctx.tenant, item_type="pv_icsr", item_ref=case_number)
        return (
            empty, "system", "Manual entry: extraction output failed validation", {"ai": "malformed", "detail": str(error)},
            ["The extraction did not pass validation. Enter the case by hand."],
        )
    payload = _apply_coding(connection, ctx, parsed.payload)
    demo_engine = _is_demo(result.provider)
    lineage = {
        "ai": "ok",
        "task": CASE_EXTRACTION.version,
        "provider": result.provider,
        "model_id": result.model_id,
        "model_version": result.model_version,
        "is_ai": not demo_engine,
        "latency_ms": result.latency_ms,
        "usage": result.usage,
        "warnings": parsed.warnings,
    }
    reason = f"{'Rule-based demo extraction' if demo_engine else 'AI extraction'} ({CASE_EXTRACTION.version})"
    return payload, ("system" if demo_engine else "ai"), reason, lineage, parsed.warnings


def _check_received_on(ctx: Ctx, received_on: date | None) -> date:
    received_on = received_on or ctx.today
    if received_on > ctx.today:
        raise InvalidInput("The received date cannot be in the future.")
    if (ctx.today - received_on).days > 3650:
        raise InvalidInput("The received date is more than ten years ago.")
    return received_on


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

def intake(
    connection: Any,
    ctx: Ctx,
    *,
    channel: str,
    source_text: str,
    subject: str | None = None,
    received_on: date | None = None,
) -> dict[str, Any]:
    """Receive a report from the safety mailbox, call centre or web form."""
    ctx.require("case.create")
    if channel not in INTAKE_CHANNELS:
        raise InvalidInput("Channel must be safety_email, call_transcript or manual_entry.")
    text = (source_text or "").replace("\r\n", "\n").strip()
    if not 20 <= len(text) <= 20000:
        raise InvalidInput("Paste the full report text (20 to 20,000 characters).")
    subject = (subject or "").strip()[:200] or None
    received_on = _check_received_on(ctx, received_on)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    state = record_state_and_source(
        connection,
        domain="pv_icsr",
        dedup_key=f"intake:{digest}",
        title_or_header=(subject or text.split("\n", 1)[0])[:200],
        normalized_state={
            "domain": "pv_icsr",
            "channel": channel,
            "subject": subject,
            "text": text,
            "received_on": received_on.isoformat(),
        },
        source=channel,
        source_uid=f"{channel}:{digest[:32]}",
        raw_payload={"subject": subject, "text": text},
    )
    duplicate_source = fetch_value(connection, "select case_number from cases where source_state_id = %s", (state.state_id,))
    if duplicate_source:
        raise Conflict(f"This exact report text was already received as {duplicate_source}.")

    products = list_products(connection)
    case_number = next_number(connection, "case", "VY-CASE")
    case_id = fetch_value(
        connection,
        """
        insert into cases (case_number, source_channel, source_state_id, status, day_zero, received_at, created_by)
        values (%s, %s, %s, 'data_entry', %s, %s, %s)
        returning id::text
        """,
        (
            case_number, channel, state.state_id, received_on,
            datetime.combine(received_on, datetime.min.time(), tzinfo=timezone.utc), ctx.actor.user_id,
        ),
    )
    payload, author_kind, reason, lineage, warnings = _extract(
        connection, ctx, case_number=case_number, source_text=text, channel=channel, products=products, identifiable=True
    )
    assessments = _write_version(
        connection, ctx, case_id=case_id, case_number=case_number, version=1, payload=payload,
        author_kind=author_kind, reason=reason, lineage=lineage, products=products, day_zero=received_on,
        status="data_entry", state_id=state.state_id,
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number, event_type="case_received", actor=ctx.actor,
        detail={"channel": channel, "source_state_id": state.state_id, "day_zero": received_on.isoformat()},
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number,
        event_type="extraction_completed" if lineage.get("ai") == "ok" else "extraction_unavailable",
        actor=ctx.actor,
        detail={key: lineage.get(key) for key in ("ai", "task", "provider", "model_id", "is_ai") if key in lineage},
    )
    duplicates = find_duplicates(connection, case_id=case_id, payload=payload)
    likely = [d for d in duplicates if d["likely"]]
    if likely:
        audit.record(
            connection, entity_kind="case", entity_ref=case_number, event_type="possible_duplicate_flagged",
            actor=ctx.actor, detail={"candidates": [d["case_number"] for d in likely]},
        )
    return {
        "case_number": case_number,
        "version": 1,
        "warnings": warnings,
        "validity": assessments["validity"],
        "possible_duplicates": [d["case_number"] for d in likely],
    }


def create_from_literature(
    connection: Any, ctx: Ctx, *, state_id: int, state: dict[str, Any], product_codes: list[str]
) -> dict[str, Any]:
    """A reviewer confirmed a valid case in an article: open it with day zero = today."""
    products = list_products(connection)
    text = literature_source_text(state)
    case_number = next_number(connection, "case", "VY-CASE")
    case_id = fetch_value(
        connection,
        """
        insert into cases (case_number, source_channel, source_state_id, status, day_zero, created_by)
        values (%s, 'literature', %s, 'data_entry', %s, %s)
        returning id::text
        """,
        (case_number, state_id, ctx.today, ctx.actor.user_id),
    )
    payload, author_kind, reason, lineage, warnings = _extract(
        connection, ctx, case_number=case_number, source_text=text, channel="literature", products=products,
        identifiable=False, extra_context={"authors": [author_label(a) for a in state.get("authors") or [] if isinstance(a, dict)]},
    )
    updates: dict[str, Any] = {"literature_reference": literature_reference(state), "report_type": "literature"}
    if not payload.products and product_codes:
        # The screened product is the suspect product unless the reviewer changes it.
        updates["products"] = [CaseProduct(name=product_codes[0], product_code=product_codes[0], role="suspect")]
    payload = payload.model_copy(update=updates)
    _write_version(
        connection, ctx, case_id=case_id, case_number=case_number, version=1, payload=payload,
        author_kind=author_kind, reason=reason, lineage=lineage, products=products, day_zero=ctx.today,
        status="data_entry", state_id=state_id,
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number, event_type="case_received", actor=ctx.actor,
        detail={"channel": "literature", "source_state_id": state_id, "day_zero": ctx.today.isoformat()},
    )
    return {"case_number": case_number, "case_id": case_id, "warnings": warnings}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def list_cases(
    connection: Any,
    ctx: Ctx,
    *,
    status: str | None = None,
    product: str | None = None,
    serious: bool | None = None,
    query: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    ctx.require("case.read")
    conditions, params = ["true"], []
    if status == "open":
        conditions.append("c.status in ('data_entry', 'medical_review')")
    elif status:
        if status not in CASE_STATUSES:
            raise InvalidInput("Unknown case status.")
        conditions.append("c.status = %s")
        params.append(status)
    if product:
        conditions.append("p.code = %s")
        params.append(product)
    if serious is not None:
        conditions.append("coalesce(c.serious, false) = %s")
        params.append(serious)
    if query:
        conditions.append("(c.case_number ilike %s or v.payload::text ilike %s)")
        params.extend([f"%{query.strip()}%", f"%{query.strip()}%"])
    rows = fetch_all(
        connection,
        f"""
        select c.case_number, c.status, c.source_channel, c.serious, c.day_zero, c.current_version,
               c.updated_at, p.code as product_code,
               v.payload->'reactions'->0->>'verbatim' as first_event,
               jsonb_array_length(v.payload->'reactions') as event_count,
               (v.assessments->'validity'->>'valid')::boolean as valid,
               coalesce((v.assessments->>'expedited_candidate')::boolean, false) as expedited_candidate,
               v.author_kind as last_author_kind
        from cases c
        join case_versions v on v.case_id = c.id and v.version = c.current_version
        left join products p on p.id = c.product_id
        where {" and ".join(conditions)}
        order by (c.status in ('data_entry', 'medical_review')) desc, c.day_zero asc, c.case_number
        limit %s
        """,
        (*params, max(1, min(limit, 500))),
    )
    for row in rows:
        row["clock"] = rules.clock(
            row["day_zero"], bool(row["serious"]), ctx.tenant.clock_policy, ctx.today,
            closed=row["status"] in CLOSED_STATUSES,
        )
    counts = fetch_all(connection, "select status, count(*)::int as n from cases group by status")
    return {"items": rows, "counts": {row["status"]: row["n"] for row in counts}}


def find_duplicates(connection: Any, *, case_id: str, payload: CasePayload) -> list[dict[str, Any]]:
    if not _suspect_codes(payload) and not payload.products:
        return []
    rows = fetch_all(
        connection,
        """
        select c.case_number, c.status, v.payload
        from cases c join case_versions v on v.case_id = c.id and v.version = c.current_version
        where c.id <> %s and c.status <> 'duplicate'
        order by c.created_at desc
        limit 500
        """,
        (case_id,),
    )
    found = []
    for row in rows:
        try:
            other = CasePayload.model_validate(row["payload"])
        except ValidationError:
            continue
        score, reasons = rules.duplicate_score(payload, other)
        if score >= 0.5:
            found.append(
                {
                    "case_number": row["case_number"],
                    "status": row["status"],
                    "score": score,
                    "reasons": reasons,
                    "likely": score >= rules.DUPLICATE_THRESHOLD,
                }
            )
    return sorted(found, key=lambda item: (-item["score"], item["case_number"]))[:5]


def get_case(connection: Any, ctx: Ctx, case_number: str) -> dict[str, Any]:
    ctx.require("case.read")
    head = _head(connection, case_number)
    current = _current(connection, head)
    payload = CasePayload.model_validate(current["payload"])
    products = list_products(connection)
    assessment = _assess(payload, products, ctx, head["day_zero"], head["status"])
    state = _source_state(connection, head["source_state_id"])
    versions = fetch_all(
        connection,
        """
        select v.version, v.author_kind, v.reason, v.created_at, m.email as author_email,
               v.lineage->>'model_id' as model_id, (v.lineage->>'is_ai')::boolean as is_ai
        from case_versions v left join tenant_members m on m.id = v.author_id
        where v.case_id = %s order by v.version desc
        """,
        (head["id"],),
    )
    exports = fetch_all(
        connection,
        """
        select e.id, e.case_version, e.format, e.content_sha256, e.created_at, m.email as created_by_email
        from case_exports e left join tenant_members m on m.id = e.created_by
        where e.case_id = %s order by e.created_at desc, e.id desc
        """,
        (head["id"],),
    )
    product = _product_for(payload, products)
    similar = []
    if product is not None:
        similar = graph.similar_reports(
            connection, product_ref=product["code"], event_refs=[_event_ref(r) for r in payload.reactions],
            exclude_case=case_number,
        )
    literature = None
    if state and state.get("domain") == "pv_literature":
        literature = {
            "state_id": head["source_state_id"],
            "reference": literature_reference(state),
            "title": state.get("title"),
        }
    lineage = current["lineage"] or {}
    return {
        "case": {key: head[key] for key in head if key != "id"},
        "version": {
            "number": current["version"],
            "author_kind": current["author_kind"],
            "reason": current["reason"],
            "created_at": current["created_at"],
            "lineage": lineage,
        },
        "payload": payload.model_dump(mode="json"),
        "assessment": assessment,
        "source": {
            "channel": head["source_channel"],
            "subject": (state or {}).get("subject"),
            "text": source_text_for(state),
            "literature": literature,
        },
        "versions": versions,
        "exports": exports,
        "duplicates": find_duplicates(connection, case_id=head["id"], payload=payload)
        if head["status"] in OPEN_STATUSES
        else [],
        "similar_reports": similar,
        "history": audit.history(connection, entity_kind="case", entity_ref=case_number),
        "permissions": {
            "edit": ctx.can("case.edit") and head["status"] in OPEN_STATUSES,
            "assess_causality": ctx.can("case.assess_causality") and head["status"] in OPEN_STATUSES,
            "submit": ctx.can("case.submit"),
            "approve": ctx.can("case.approve") and (not head["serious"] or ctx.can("case.approve_serious")),
            "export": ctx.can("case.export"),
        },
        "terminology": {"licensed": ctx.tenant.licensed, "dictionary": ctx.tenant.meddra_dictionary},
    }


# ---------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------

def _locked_open_case(connection: Any, case_number: str, expected_version: int) -> dict[str, Any]:
    head = _head(connection, case_number, lock=True)
    if head["status"] not in OPEN_STATUSES:
        raise Conflict(f"{case_number} is {head['status'].replace('_', ' ')}. Reopen it to change it.")
    if expected_version != head["current_version"]:
        raise Conflict(
            f"{case_number} was saved by someone else (version {head['current_version']}). Reload and apply your change again."
        )
    return head


def _validation_message(error: ValidationError) -> str:
    first = error.errors()[0]
    where = ".".join(str(part) for part in first.get("loc", ()))
    return f"{where}: {first.get('msg')}" if where else str(first.get("msg"))


def save_version(
    connection: Any, ctx: Ctx, case_number: str, *, expected_version: int, payload: dict[str, Any], reason: str
) -> dict[str, Any]:
    ctx.require("case.edit")
    reason = (reason or "").strip()
    if not reason:
        raise InvalidInput("Say why you are changing the case, for example 'Data entry from source'.")
    head = _locked_open_case(connection, case_number, expected_version)
    old = CasePayload.model_validate(_current(connection, head)["payload"])
    try:
        new = CasePayload.model_validate(payload)
    except ValidationError as error:
        raise InvalidInput(_validation_message(error)) from error

    # Causality belongs to the physician. Match reactions by verbatim so a
    # reorder does not move someone's assessment.
    old_by_verbatim = {r.verbatim: r for r in old.reactions}
    causality_changes = []
    reactions = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for reaction in new.reactions:
        before = old_by_verbatim.get(reaction.verbatim)
        previous = before.causality if before else Causality()
        changed = (reaction.causality.category, reaction.causality.comment) != (previous.category, previous.comment)
        if changed:
            ctx.require("case.assess_causality")
            causality = reaction.causality.model_copy(
                update={"assessed_by": ctx.actor.email or ctx.actor.user_id, "assessed_at": now}
            )
            causality_changes.append({"event": reaction.verbatim, "category": causality.category})
        else:
            causality = previous
        reactions.append(reaction.model_copy(update={"causality": causality}))

    narrative = new.narrative
    if narrative.text != old.narrative.text:
        narrative = Narrative(
            text=narrative.text,
            status="edited" if narrative.text.strip() else "empty",
            citations=old.narrative.citations if narrative.text.strip() else [],
        )
    elif narrative.status == "edited" and old.narrative.status == "ai_draft":
        # The reviewer read the draft and confirmed it unchanged.
        narrative = old.narrative.model_copy(update={"status": "edited"})
    else:
        narrative = old.narrative

    # Evidence comes from the source document and cannot be edited by hand.
    evidence = {
        key: value
        for key, value in old.evidence.items()
        if not key.startswith(("products.", "reactions."))
        or int(key.split(".")[1]) < len(new.products if key.startswith("products.") else new.reactions)
    }
    updated = new.model_copy(update={"reactions": reactions, "narrative": narrative, "evidence": evidence})
    changed = [
        field
        for field in ("report_type", "patient", "reporter", "products", "reactions", "special_situations",
                      "medical_history", "dechallenge", "rechallenge", "narrative", "literature_reference")
        if getattr(updated, field) != getattr(old, field)
    ]
    if not changed:
        raise Conflict("Nothing changed.")
    version = head["current_version"] + 1
    products = list_products(connection)
    assessments = _write_version(
        connection, ctx, case_id=head["id"], case_number=case_number, version=version, payload=updated,
        author_kind="human", reason=reason, lineage={"changed": changed}, products=products,
        day_zero=head["day_zero"], status=head["status"], state_id=head["source_state_id"],
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number, event_type="case_edited", actor=ctx.actor,
        detail={"version": version, "changed": changed, "reason": reason[:500]},
    )
    if causality_changes:
        audit.record(
            connection, entity_kind="case", entity_ref=case_number, event_type="causality_assessed",
            actor=ctx.actor, detail={"version": version, "assessments": causality_changes, "method": "WHO-UMC"},
        )
    return {"case_number": case_number, "version": version, "assessment": assessments}


def draft_narrative(connection: Any, ctx: Ctx, case_number: str, *, expected_version: int) -> dict[str, Any]:
    ctx.require("case.edit")
    head = _locked_open_case(connection, case_number, expected_version)
    payload = CasePayload.model_validate(_current(connection, head)["payload"])
    if not payload.reactions:
        raise Conflict("Add at least one event before drafting the narrative.")
    source_text = source_text_for(_source_state(connection, head["source_state_id"]))
    case_data = payload.model_dump(mode="json", exclude={"evidence", "narrative"})
    quotes = [item.quote for item in payload.evidence.values() if item.status == "verified"]
    try:
        result = ctx.gateway.run(
            CASE_NARRATIVE,
            {"case_data": case_data, "source_text": source_text, "evidence_quotes": quotes},
            tenant=ctx.tenant,
            identifiable=head["source_channel"] != "literature",
            item_type="pv_icsr",
            item_ref=case_number,
        )
    except AiPolicyBlocked as error:
        raise Unavailable(f"{error} Write the narrative by hand.") from error
    except AiFailure as error:
        raise Unavailable("Narrative drafting failed. Write the narrative by hand.") from error
    try:
        text, citations, warnings = parse_narrative(result.output, source_text=source_text)
    except AiOutputError as error:
        ctx.gateway.record_contract_failure(CASE_NARRATIVE, result, tenant=ctx.tenant, item_type="pv_icsr", item_ref=case_number)
        raise Unavailable("The drafted narrative did not pass validation. Write it by hand.") from error
    demo_engine = _is_demo(result.provider)
    updated = payload.model_copy(update={"narrative": Narrative(text=text, status="ai_draft", citations=citations)})
    version = head["current_version"] + 1
    _write_version(
        connection, ctx, case_id=head["id"], case_number=case_number, version=version, payload=updated,
        author_kind="system" if demo_engine else "ai",
        reason=f"{'Rule-based demo narrative' if demo_engine else 'AI narrative draft'} ({CASE_NARRATIVE.version})",
        lineage={
            "task": CASE_NARRATIVE.version, "provider": result.provider, "model_id": result.model_id,
            "model_version": result.model_version, "is_ai": not demo_engine, "usage": result.usage,
            "latency_ms": result.latency_ms, "warnings": warnings,
        },
        products=list_products(connection), day_zero=head["day_zero"], status=head["status"],
        state_id=head["source_state_id"],
    )
    audit.record(
        connection, entity_kind="case", entity_ref=case_number, event_type="narrative_drafted", actor=ctx.actor,
        detail={"version": version, "model_id": result.model_id, "is_ai": not demo_engine, "warnings": len(warnings)},
    )
    return {"case_number": case_number, "version": version, "warnings": warnings}


def suggest_coding(connection: Any, ctx: Ctx, verbatim: str) -> dict[str, Any]:
    ctx.require("case.edit")
    verbatim = (verbatim or "").strip()
    if not verbatim or len(verbatim) > 300:
        raise InvalidInput("Give the event as reported (up to 300 characters).")
    return terminology.suggest_coding(
        connection, verbatim=verbatim, licensed=ctx.tenant.licensed, dictionary=ctx.tenant.meddra_dictionary
    )


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def transition(
    connection: Any,
    ctx: Ctx,
    case_number: str,
    *,
    action: str,
    expected_version: int,
    reason: str | None = None,
    duplicate_of: str | None = None,
) -> dict[str, Any]:
    if action not in TRANSITIONS:
        raise InvalidInput("Unknown case action.")
    reason = (reason or "").strip()
    head = _head(connection, case_number, lock=True)
    if expected_version != head["current_version"]:
        raise Conflict(f"{case_number} changed since you opened it. Reload first.")
    payload = CasePayload.model_validate(_current(connection, head)["payload"])
    assessment = _assess(payload, list_products(connection), ctx, head["day_zero"], head["status"])
    status = head["status"]
    detail: dict[str, Any] = {"version": head["current_version"]}

    def need(*allowed: str) -> None:
        if status not in allowed:
            raise Conflict(f"{case_number} is {status.replace('_', ' ')}; you cannot {action.replace('_', ' ')} it now.")

    def need_reason() -> None:
        if not reason:
            raise InvalidInput("Give a reason.")

    if action == "submit":
        ctx.require("case.submit")
        need("data_entry")
        if not assessment["validity"]["valid"]:
            missing = ", ".join(m.replace("_", " ") for m in assessment["validity"]["missing"])
            raise Conflict(f"Not a valid case yet. Missing: {missing}. Complete it or close it as invalid.")
        new_status = "medical_review"
    elif action == "return":
        ctx.require("case.approve")
        need("medical_review")
        need_reason()
        new_status = "data_entry"
    elif action == "approve":
        ctx.require("case.approve")
        if assessment["seriousness"]["serious"]:
            ctx.require("case.approve_serious")
        need("medical_review")
        problems = []
        if not assessment["validity"]["valid"]:
            problems.append("the case does not meet the minimum criteria")
        if not assessment["causality_complete"]:
            problems.append("causality is missing for at least one event")
        if not payload.narrative.text.strip():
            problems.append("there is no narrative")
        if payload.narrative.status == "ai_draft":
            problems.append("the narrative is an unreviewed draft; edit or confirm it")
        if problems:
            raise Conflict("Cannot approve: " + "; ".join(problems) + ".")
        new_status = "approved"
        detail["meaning"] = APPROVAL_MEANING
        detail["expedited_candidate"] = assessment["expedited_candidate"]
        detail["clock"] = assessment["clock"]["label"]
    elif action == "close_invalid":
        ctx.require("case.submit")
        need("data_entry", "medical_review")
        need_reason()
        if assessment["validity"]["valid"]:
            raise Conflict("This case meets the four minimum criteria, so it cannot be closed as invalid.")
        new_status = "closed_invalid"
        detail["missing"] = assessment["validity"]["missing"]
    elif action == "mark_duplicate":
        ctx.require("case.submit")
        need("data_entry", "medical_review")
        need_reason()
        target = (duplicate_of or "").strip().upper()
        if not target or target == case_number:
            raise InvalidInput("Name the case this one duplicates.")
        original = _head(connection, target)
        if original["status"] == "duplicate":
            raise Conflict(f"{target} is itself a duplicate. Link to the master case.")
        graph.link(
            connection, from_kind="case", from_ref=case_number, relation="duplicate_of", to_kind="case",
            to_ref=target, evidence_status="verified", provenance="human_label", source_state_id=head["source_state_id"],
        )
        new_status = "duplicate"
        detail["duplicate_of"] = target
    else:  # reopen
        ctx.require("case.approve")
        need("approved", "closed_invalid", "duplicate")
        need_reason()
        new_status = "data_entry"

    connection.execute("update cases set status = %s, updated_at = now() where id = %s", (new_status, head["id"]))
    if reason:
        detail["reason"] = reason[:500]
    detail.update({"from": status, "to": new_status})
    audit.record(connection, entity_kind="case", entity_ref=case_number, event_type=f"case_{action}", actor=ctx.actor, detail=detail)
    return {"case_number": case_number, "status": new_status}
