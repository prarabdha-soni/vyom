"""Literature screening: weekly sweep, review queue and reviewer decisions.

The sweep fetches new articles for each product, records them in the
append-only ledger and asks System One the screening questions. The
deterministic router turns the answers into a band. Auto-close is off by
default, so every article still gets a human decision here; a confirmed
valid case opens a case with day zero = the day of that decision.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from vyom_literature.clients import EuropePMCClient, PubMedClient
from vyom_literature.ingestion import screen_public_records
from vyom_literature.records import LiteratureRecord
from vyom_literature.review import append_review_label
from vyom_literature.system_one import PV_LITERATURE_QUESTIONS
from vyom_os import audit, graph
from vyom_os.ai import demo
from vyom_os.cases import author_label, create_from_literature, literature_reference
from vyom_os.core import Conflict, Ctx, Forbidden, InvalidInput, NotFound, Unavailable
from vyom_os.db import fetch_all, fetch_one, fetch_value
from vyom_os.products import list_products, mentions

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUTCOMES = ("valid_icsr", "safety_information", "not_relevant", "escalated")
FINAL_OUTCOMES = frozenset({"valid_icsr", "safety_information", "not_relevant"})
LABEL_ROLES = {"reviewer": "pv_associate", "safety_physician": "safety_physician", "qppv": "qppv"}
GATES = ("has_identifiable_patient", "has_identifiable_reporter", "has_suspect_drug", "has_adverse_event")
AWARENESS_RULE = "literature-awareness.v1"


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fill_dates(text: str, today: date) -> str:
    """Replace ``{d-N}`` with the date N days before ``today`` (e.g. 12 November 2026)."""

    def replace(match: re.Match[str]) -> str:
        day = today - timedelta(days=int(match.group(1)))
        return f"{day.day} {day.strftime('%B %Y')}"

    return re.sub(r"\{d-(\d+)\}", replace, text)


def demo_records(today: date) -> list[LiteratureRecord]:
    records = []
    for article in load_fixture("literature.json")["articles"]:
        published = today - timedelta(days=int(article["published_days_ago"]))
        authors = []
        for name in article["authors"]:
            surname, _, initials = name.partition(" ")
            authors.append({"surname": surname, "initials": initials})
        records.append(
            LiteratureRecord(
                source="demo_fixture",  # type: ignore[arg-type]
                source_uid=article["id"],
                pmid=None,
                doi=None,
                title=article["title"],
                abstract=article["abstract"],
                journal=article["journal"],
                pub_date=published,
                publication_year=published.year,
                authors=authors,
                raw={"notice": "SAMPLE DATA (FICTIONAL)", "fixture_id": article["id"], "product": article["product"]},
            )
        )
    return records


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def _product_query(product: dict[str, Any]) -> str:
    terms = {product["active_ingredient"], product["name"]}
    return " OR ".join(f'"{term}"[Title/Abstract]' for term in sorted(terms) if term)


def _fetch_live(products: list[dict[str, Any]], from_date: date, to_date: date) -> list[LiteratureRecord]:
    tool, email = os.environ.get("NCBI_TOOL", ""), os.environ.get("NCBI_EMAIL", "")
    if not tool or not email:
        raise Unavailable("Set NCBI_TOOL and NCBI_EMAIL to search PubMed.")
    pubmed = PubMedClient(tool=tool, email=email, api_key=os.environ.get("NCBI_API_KEY") or None)
    records: list[LiteratureRecord] = []
    for product in products:
        records.extend(pubmed.fetch(_product_query(product), from_date=from_date, to_date=to_date))
    if os.environ.get("VYOM_EUROPEPMC", "").lower() in {"1", "true", "yes"}:
        europe = EuropePMCClient(tool=tool, email=email)
        for product in products:
            query = " OR ".join(f'"{t}"' for t in sorted({product["active_ingredient"], product["name"]}) if t)
            records.extend(europe.fetch(query, from_date=from_date, to_date=to_date))
    return records


DEMO_MODE_REAL_TENANT = (
    "This deployment runs the rule-based demo engine, which works only on the fictional sample tenant. "
    "Literature sweeps for real products run in live mode."
)


def sweep(connection: Any, ctx: Ctx, *, from_date: date | None = None, to_date: date | None = None) -> dict[str, Any]:
    """Fetch and screen one window of literature for every active product."""
    to_date = to_date or ctx.today
    from_date = from_date or (to_date - timedelta(days=7))
    if from_date > to_date or (to_date - from_date).days > 92:
        raise InvalidInput("The sweep window must run forward and be at most 92 days.")
    products = list_products(connection, active_only=True)
    if not products:
        raise Conflict("Add a product before running a literature sweep.")
    # The fictional sample articles belong to fictional tenants only. A real tenant is swept from the live
    # sources, which demo mode does not use: its rule engine is tuned to the sample, not to real reports.
    demo_data = ctx.tenant.is_fictional
    if not demo_data and ctx.gateway.mode == "demo":
        raise Conflict(DEMO_MODE_REAL_TENANT)
    records = demo_records(ctx.today) if demo_data else _fetch_live(products, from_date, to_date)
    router = ctx.gateway.literature_router()
    stats = screen_public_records(records, connection=connection, router=router, tenant_id=ctx.tenant.id)

    # Link each screened article to the products it mentions.
    linked = 0
    for record in records:
        state_id = fetch_value(
            connection,
            "select state_id from source_records where source = %s and source_uid = %s",
            (record.source, record.source_uid),
        )
        if state_id is None:
            continue
        codes = set(mentions(f"{record.title} {record.abstract or ''}", products))
        if isinstance(record.raw, dict) and record.raw.get("product"):
            codes.add(str(record.raw["product"]))
        for code in sorted(codes):
            graph.link(
                connection, from_kind="literature", from_ref=str(state_id), relation="mentions", to_kind="product",
                to_ref=code, evidence_status="reported", provenance="deterministic_rule", source_state_id=state_id,
            )
            linked += 1

    summary = {
        "source": "sample articles (FICTIONAL)" if demo_data else "PubMed",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "fetched": stats.fetched,
        "new_articles": stats.states_created,
        "screened": stats.decisions_created,
        "already_screened": stats.decisions_already_present,
        "sent_to_review_after_failure": stats.fail_closed_count,
        "product_links": linked,
        "model_id": router.public_model,
    }
    connection.execute(
        """
        insert into sweep_runs (tenant_id, run_date, from_date, to_date, records_fetched, states_created,
                                decisions_created, already_present, strategy_versions, model_versions, correlation_id)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, null)
        on conflict (tenant_id, run_date, from_date, to_date) do update set
          records_fetched = excluded.records_fetched, states_created = sweep_runs.states_created + excluded.states_created,
          decisions_created = sweep_runs.decisions_created + excluded.decisions_created,
          already_present = excluded.already_present, completed_at = now()
        """,
        (
            ctx.tenant.id, ctx.today, from_date, to_date, stats.fetched, stats.states_created,
            stats.decisions_created, stats.decisions_already_present,
            json.dumps([{"product": p["code"], "query": _product_query(p)} for p in products]),
            json.dumps({"system_one": router.public_model, "sampler": router.sampler_version}),
        ),
    )
    audit.record(
        connection, entity_kind="literature", entity_ref=f"sweep:{ctx.today.isoformat()}",
        event_type="sweep_completed", actor=ctx.actor, detail=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Queue and detail
# ---------------------------------------------------------------------------

_LATEST = """
with latest_decision as (
  select distinct on (d.state_id) d.id, d.state_id, d.model_id, d.sampler_version, d.answers,
         d.confidence_band, d.created_at
  from sys1_decisions d
  order by d.state_id, d.created_at desc, d.id desc
), latest_outcome as (
  select distinct on (o.state_id) o.state_id, o.outcome, o.reason, o.case_id, o.created_at, o.reviewer_role
  from literature_outcomes o
  order by o.state_id, o.created_at desc, o.id desc
)
"""


def _reference(source: str | None, source_uid: str | None, state: dict[str, Any]) -> str:
    if source == "demo_fixture":
        return str(source_uid)
    if state.get("pmid"):
        return f"PMID {state['pmid']}"
    if state.get("doi"):
        return f"DOI {state['doi']}"
    return str(source_uid or "")


def _summarise(answers: dict[str, Any]) -> dict[str, Any]:
    def probability(key: str) -> float | None:
        value = (answers or {}).get(key)
        return float(value["probability"]) if isinstance(value, dict) and "probability" in value else None

    design = (answers or {}).get("study_design") or {}
    priority = (answers or {}).get("triage_priority") or {}
    gates = {key: probability(key) for key in GATES}
    return {
        "gates": gates,
        "criteria_met": sum(1 for value in gates.values() if value is not None and value >= 0.5),
        "p_serious": probability("is_serious_event"),
        "study_design": design.get("choice"),
        "priority": priority.get("score"),
    }


def queue(connection: Any, ctx: Ctx, *, view: str = "open", product: str | None = None, limit: int = 200) -> dict[str, Any]:
    ctx.require("literature.read")
    filters = {
        "open": "(lo.outcome is null or lo.outcome = 'escalated')",
        "decided": "lo.outcome in ('valid_icsr', 'safety_information', 'not_relevant')",
        "all": "true",
    }
    if view not in filters:
        raise InvalidInput("View must be open, decided or all.")
    params: list[Any] = []
    product_filter = ""
    if product:
        product_filter = """and exists (select 1 from graph_edges e where e.from_kind = 'literature'
            and e.from_ref = cs.id::text and e.relation = 'mentions' and e.to_ref = %s)"""
        params.append(product)
    rows = fetch_all(
        connection,
        _LATEST
        + f"""
        select cs.id as state_id, cs.title_or_header as title, cs.normalized_state as state, cs.first_seen_at,
               src.source, src.source_uid,
               ld.id as decision_id, ld.confidence_band as band, ld.answers, ld.model_id, ld.created_at as screened_at,
               lo.outcome, lo.created_at as decided_at, c.case_number,
               coalesce((select array_agg(distinct e.to_ref order by e.to_ref) from graph_edges e
                          where e.from_kind = 'literature' and e.from_ref = cs.id::text
                            and e.relation = 'mentions' and e.to_kind = 'product'), '{{}}') as products
        from clinical_states cs
        join latest_decision ld on ld.state_id = cs.id
        left join latest_outcome lo on lo.state_id = cs.id
        left join cases c on c.id = lo.case_id
        left join lateral (
          select s.source, s.source_uid from source_records s where s.state_id = cs.id order by s.id limit 1
        ) src on true
        where cs.domain = 'pv_literature' and {filters[view]} {product_filter}
        order by
          case when lo.outcome = 'escalated' then 0 when ld.confidence_band = 'RED_ESCALATE' then 1
               when ld.confidence_band = 'YELLOW_REVIEW' then 2 else 3 end,
          coalesce((ld.answers->'triage_priority'->>'score')::int, 0) desc,
          cs.first_seen_at, cs.id
        limit %s
        """,
        (*params, max(1, min(limit, 500))),
    )
    items = []
    for row in rows:
        state = row.pop("state") or {}
        answers = row.pop("answers") or {}
        items.append(
            {
                **row,
                "reference": _reference(row["source"], row["source_uid"], state),
                "journal": state.get("journal"),
                "pub_date": state.get("pub_date"),
                "is_sample": row["source"] == "demo_fixture",
                **_summarise(answers),
            }
        )
    counts = fetch_one(
        connection,
        _LATEST
        + """
        select
          count(*) filter (where lo.outcome is null or lo.outcome = 'escalated') as open,
          count(*) filter (where (lo.outcome is null or lo.outcome = 'escalated') and ld.confidence_band = 'RED_ESCALATE') as open_red,
          count(*) filter (where (lo.outcome is null or lo.outcome = 'escalated') and ld.confidence_band = 'YELLOW_REVIEW') as open_yellow,
          count(*) filter (where (lo.outcome is null or lo.outcome = 'escalated') and ld.confidence_band like 'GREEN%%') as open_green,
          count(*) filter (where lo.outcome = 'escalated') as escalated,
          count(*) filter (where lo.outcome in ('valid_icsr', 'safety_information', 'not_relevant')) as decided
        from clinical_states cs
        join latest_decision ld on ld.state_id = cs.id
        left join latest_outcome lo on lo.state_id = cs.id
        where cs.domain = 'pv_literature'
        """,
    )
    return {"items": items, "counts": counts or {}}


def _highlights(text: str, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans = []
    for product in products:
        for needle in {product["code"], product["name"], product["active_ingredient"]}:
            if not needle:
                continue
            for match in re.finditer(re.escape(str(needle)), text, flags=re.IGNORECASE):
                spans.append({"start": match.start(), "end": match.end(), "kind": "product", "label": product["code"]})
    for _index, match in demo._event_matches(text):  # noqa: SLF001 - shared keyword lexicon
        spans.append({"start": match.start(), "end": match.end(), "kind": "event", "label": match.group(0)})
    spans.sort(key=lambda span: (span["start"], -span["end"]))
    merged: list[dict[str, Any]] = []
    for span in spans:
        if merged and span["start"] < merged[-1]["end"]:
            continue
        merged.append(span)
    return merged


def detail(connection: Any, ctx: Ctx, state_id: int) -> dict[str, Any]:
    ctx.require("literature.read")
    row = fetch_one(
        connection,
        """
        select cs.id as state_id, cs.title_or_header as title, cs.normalized_state as state, cs.first_seen_at,
               src.source, src.source_uid, src.fetched_at
        from clinical_states cs
        left join lateral (
          select s.source, s.source_uid, s.fetched_at from source_records s where s.state_id = cs.id order by s.id limit 1
        ) src on true
        where cs.id = %s and cs.domain = 'pv_literature'
        """,
        (state_id,),
    )
    if row is None:
        raise NotFound("No such article.")
    state = row["state"] or {}
    decisions = fetch_all(
        connection,
        """
        select id, model_id, sampler_version, question_schema_version, threshold_policy_version,
               answers, confidence_band, latency_ms, created_at
        from sys1_decisions where state_id = %s order by created_at desc, id desc
        """,
        (state_id,),
    )
    outcomes = fetch_all(
        connection,
        """
        select o.outcome, o.reason, o.reviewer_role, m.email as reviewer_email, o.created_at, c.case_number
        from literature_outcomes o
        left join tenant_members m on m.id = o.reviewer_id
        left join cases c on c.id = o.case_id
        where o.state_id = %s order by o.created_at desc, o.id desc
        """,
        (state_id,),
    )
    products = list_products(connection)
    abstract = state.get("abstract") or ""
    latest = decisions[0] if decisions else None
    questions = [
        {
            "key": key,
            "prompt": question.prompt,
            "answer": (latest or {}).get("answers", {}).get(key) if latest else None,
        }
        for key, question in PV_LITERATURE_QUESTIONS.items()
    ]
    final = next((o for o in outcomes if o["outcome"] in FINAL_OUTCOMES), None)
    # Once escalated, only a safety physician (or above) may close the article; see decide().
    awaiting_physician = final is None and bool(outcomes) and outcomes[0]["outcome"] == "escalated"
    return {
        "state_id": row["state_id"],
        "reference": _reference(row["source"], row["source_uid"], state),
        "citation": literature_reference(state),
        "title": state.get("title") or row["title"],
        "abstract": abstract,
        "journal": state.get("journal"),
        "pub_date": state.get("pub_date"),
        "authors": [author_label(a) for a in state.get("authors") or [] if isinstance(a, dict)],
        "pmid": state.get("pmid"),
        "doi": state.get("doi"),
        "is_sample": row["source"] == "demo_fixture",
        "first_seen_at": row["first_seen_at"],
        "highlights": {
            "title": _highlights(state.get("title") or "", products),
            "abstract": _highlights(abstract, products),
            "method": "keyword match (rule-based)",
        },
        "products": mentions(f"{state.get('title') or ''} {abstract}", products),
        "decision": latest and {
            key: latest[key]
            for key in ("id", "model_id", "sampler_version", "question_schema_version", "threshold_policy_version",
                        "confidence_band", "latency_ms", "created_at")
        },
        "summary": _summarise((latest or {}).get("answers") or {}),
        "questions": questions,
        "is_ai": bool(latest) and latest["model_id"] != demo.DEMO_MODEL_ID,
        "outcomes": outcomes,
        "final_outcome": final,
        "awaiting_physician": awaiting_physician,
        "can_decide": ctx.can("literature.screen") and final is None and not (awaiting_physician and ctx.actor.role == "reviewer"),
        "history": audit.history(connection, entity_kind="literature", entity_ref=str(state_id)),
    }


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def decide(
    connection: Any, ctx: Ctx, state_id: int, *, decision_id: int, outcome: str, reason: str | None = None
) -> dict[str, Any]:
    ctx.require("literature.screen")
    if outcome not in OUTCOMES:
        raise InvalidInput("Outcome must be valid_icsr, safety_information, not_relevant or escalated.")
    reason = (reason or "").strip()[:2000] or None
    connection.execute("select pg_advisory_xact_lock(hashtext('literature:' || %s::text))", (state_id,))
    row = fetch_one(
        connection,
        """
        select cs.normalized_state as state, d.id as decision_id, d.answers, d.confidence_band
        from clinical_states cs
        join lateral (
          select id, answers, confidence_band from sys1_decisions where state_id = cs.id
          order by created_at desc, id desc limit 1
        ) d on true
        where cs.id = %s and cs.domain = 'pv_literature'
        """,
        (state_id,),
    )
    if row is None:
        raise NotFound("No such screened article.")
    if row["decision_id"] != decision_id:
        raise Conflict("The screening result changed since you opened it. Reload the article.")
    previous = fetch_all(
        connection, "select outcome from literature_outcomes where state_id = %s order by created_at desc, id desc", (state_id,)
    )
    if any(p["outcome"] in FINAL_OUTCOMES for p in previous):
        raise Conflict("This article already has a decision.")
    if previous and previous[0]["outcome"] == "escalated" and ctx.actor.role == "reviewer":
        raise Forbidden("A safety physician decides escalated articles.")
    if outcome == "escalated" and not reason:
        raise InvalidInput("Say what the safety physician should look at.")
    if outcome == "not_relevant" and row["confidence_band"] == "RED_ESCALATE" and not reason:
        raise InvalidInput("The screen flagged this article as urgent. Give a reason for closing it.")

    # Training signal: does the reviewer agree with the model's validity proposal?
    answers = row["answers"] or {}
    gates = [answers.get(key, {}).get("probability") for key in GATES]
    model_valid = bool(answers) and all(isinstance(p, (int, float)) and p >= 0.5 for p in gates)
    if outcome == "escalated":
        action, patch = "ESCALATE", None
    elif not answers:
        action, patch = "CORRECT", {"valid_case": outcome == "valid_icsr", "outcome": outcome}
    elif (outcome == "valid_icsr") == model_valid:
        action, patch = "ACCEPT", None
    else:
        action, patch = "CORRECT", {"valid_case": outcome == "valid_icsr", "outcome": outcome}
    append_review_label(
        connection,
        state_id=state_id,
        decision_id=decision_id,
        reviewer_id=UUID(str(ctx.actor.user_id)),
        reviewer_role=LABEL_ROLES[ctx.actor.role],  # type: ignore[arg-type]
        action=action,  # type: ignore[arg-type]
        override_patch=patch,
        rationale_note=reason,
    )

    case = None
    if outcome == "valid_icsr":
        connection.execute(
            """
            insert into awareness_events (tenant_id, state_id, aware_on, rule_version, region_rule, screener_role)
            values (%s, %s, %s, %s, 'ich-e2d', %s)
            on conflict (tenant_id, state_id) do nothing
            """,
            (ctx.tenant.id, state_id, ctx.today, AWARENESS_RULE, ctx.actor.role),
        )
        codes = [
            edge["to_ref"]
            for edge in graph.edges_for(connection, kind="literature", ref=str(state_id))
            if edge["relation"] == "mentions" and edge["to_kind"] == "product"
        ]
        case = create_from_literature(connection, ctx, state_id=state_id, state=row["state"] or {}, product_codes=codes)
        graph.link(
            connection, from_kind="literature", from_ref=str(state_id), relation="raised_as_case", to_kind="case",
            to_ref=case["case_number"], evidence_status="verified", provenance="human_label", source_state_id=state_id,
        )
    connection.execute(
        """
        insert into literature_outcomes (state_id, decision_id, outcome, reason, reviewer_id, reviewer_role, case_id)
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (state_id, decision_id, outcome, reason, ctx.actor.user_id, ctx.actor.role, case["case_id"] if case else None),
    )
    audit.record(
        connection, entity_kind="literature", entity_ref=str(state_id), event_type=f"screened_{outcome}",
        actor=ctx.actor,
        detail={
            "decision_id": decision_id,
            "band": row["confidence_band"],
            "agreed_with_screen": action == "ACCEPT",
            "case_number": case["case_number"] if case else None,
            "reason": reason,
        },
    )
    return {"state_id": state_id, "outcome": outcome, "case_number": case["case_number"] if case else None}
