"""Periodic safety reports: PBRER (ICH E2C(R2) layout) and PADER drafts.

The data come from approved cases and screened literature up to the data
lock point and are computed deterministically. A model drafts the narrative
sections from those aggregates only (no line-level patient data), and its
text is checked: citations must be case numbers or article references in the
data, and numbers it writes must appear in the data. Sections that need
company input stay marked until a person writes them. Only the QPPV signs
off, and only a report with no unreviewed draft and no missing input.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

from vyom_os import audit, rules
from vyom_os.ai.gateway import AiFailure, AiPolicyBlocked
from vyom_os.ai.tasks import _NUMBER, REPORT_SECTION, AiOutputError, parse_report_section  # noqa: PLC2701
from vyom_os.cases import next_number
from vyom_os.core import Conflict, Ctx, InvalidInput, NotFound
from vyom_os.db import Jsonb, fetch_all, fetch_one, fetch_value
from vyom_os.products import get_product, product_label

REPORT_SCHEMA = "vyom.report.v1"
REPORT_TYPES = ("pbrer", "pader")
SIGNOFF_MEANING = "I have reviewed this periodic report and approve it as the QPPV."
COMPLETE_STATUSES = frozenset({"generated", "accepted", "edited"})

# (key, number, title, mode): mode is draft (model text from data),
# generated (deterministic tables) or input (company input required).
PBRER_SECTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("introduction", "1", "Introduction", "draft"),
    ("approval_status", "2", "Worldwide marketing approval status", "input"),
    ("safety_actions", "3", "Actions taken in the reporting interval for safety reasons", "input"),
    ("rsi_changes", "4", "Changes to reference safety information", "input"),
    ("exposure", "5", "Estimated exposure and use patterns", "input"),
    ("summary_tabulations", "6", "Data in summary tabulations", "draft"),
    ("clinical_trials", "7", "Summaries of significant findings from clinical trials during the reporting interval", "input"),
    ("non_interventional", "8", "Findings from non-interventional studies", "input"),
    ("other_sources", "9", "Information from other clinical trials and sources", "input"),
    ("non_clinical", "10", "Non-clinical data", "input"),
    ("literature", "11", "Literature", "draft"),
    ("other_periodic_reports", "12", "Other periodic reports", "input"),
    ("lack_of_efficacy", "13", "Lack of efficacy in controlled clinical trials", "input"),
    ("late_breaking", "14", "Late-breaking information", "input"),
    ("signals_overview", "15", "Overview of signals: new, ongoing or closed", "input"),
    ("signal_risk_evaluation", "16", "Signal and risk evaluation", "input"),
    ("benefit_evaluation", "17", "Benefit evaluation", "input"),
    ("benefit_risk", "18", "Integrated benefit-risk analysis for approved indications", "input"),
    ("conclusions", "19", "Conclusions and actions", "draft"),
    ("appendices", "20", "Appendices: line listing of cases in the interval", "generated"),
)
PADER_SECTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("pader_narrative", "A", "Narrative summary and analysis, including 15-day Alert reports", "draft"),
    ("pader_actions", "B", "Narrative discussion of actions taken since the last report", "input"),
    ("pader_listing", "C", "Index of case reports not submitted as 15-day Alert reports", "generated"),
)


# ---------------------------------------------------------------------------
# Data snapshot
# ---------------------------------------------------------------------------

def _event_term(reaction: dict[str, Any]) -> str:
    coding = reaction.get("coding") or {}
    if coding.get("status") == "confirmed" and coding.get("pt"):
        return str(coding["pt"])
    return rules.normalise_term(str(reaction.get("verbatim", "")))


def _age_sex(patient: dict[str, Any]) -> str:
    age = patient.get("age_value")
    unit = {"years": "y", "months": "mo", "weeks": "wk", "days": "d"}.get(patient.get("age_unit") or "", "")
    age_text = f"{int(age) if float(age).is_integer() else age}{unit}" if age is not None else "age unknown"
    return f"{age_text} / {patient.get('sex', 'unknown')}"


def snapshot(connection: Any, product: dict[str, Any], interval_start: date, data_lock_point: date) -> dict[str, Any]:
    rows = fetch_all(
        connection,
        """
        select c.case_number, c.status, coalesce(c.serious, false) as serious, c.day_zero, c.source_channel,
               v.payload, v.assessments
        from cases c join case_versions v on v.case_id = c.id and v.version = c.current_version
        where c.product_id = %s and c.day_zero <= %s and c.status not in ('duplicate', 'closed_invalid')
        order by c.day_zero, c.case_number
        """,
        (product["id"], data_lock_point),
    )
    approved = [r for r in rows if r["status"] == "approved"]
    interval = [r for r in approved if r["day_zero"] >= interval_start]
    pending = [r for r in rows if r["status"] in ("data_entry", "medical_review") and r["day_zero"] >= interval_start]

    def is_fatal(row: dict[str, Any]) -> bool:
        return any(r.get("outcome") == "fatal" for r in row["payload"].get("reactions", []))

    def events(selection: list[dict[str, Any]]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for row in selection:
            for term in {_event_term(r) for r in row["payload"].get("reactions", [])}:
                counter[term] += 1
        return counter

    interval_events, cumulative_events = events(interval), events(approved)
    serious_interval_events = events([r for r in interval if r["serious"]])
    top_events = [
        {"term": term, "interval": count, "cumulative": cumulative_events[term], "serious_interval": serious_interval_events[term]}
        for term, count in sorted(interval_events.items(), key=lambda item: (-item[1], item[0]))
    ]
    expedited = [r["case_number"] for r in interval if (r["assessments"] or {}).get("expedited_candidate")]
    line_listing = []
    for row in interval:
        payload, assessments = row["payload"], row["assessments"] or {}
        reactions = payload.get("reactions", [])
        expected = [item.get("expected") for item in assessments.get("expectedness", [])]
        line_listing.append(
            {
                "case_number": row["case_number"],
                "day_zero": row["day_zero"].isoformat(),
                "source": row["source_channel"].replace("_", " "),
                "country": (payload.get("reporter") or {}).get("country") or "unknown",
                "age_sex": _age_sex(payload.get("patient") or {}),
                "events": "; ".join(r.get("verbatim", "") for r in reactions),
                "serious": ", ".join(sorted({c.replace("_", " ") for r in reactions for c in r.get("serious_criteria", [])})) or "no",
                "outcome": ", ".join(sorted({r.get("outcome", "unknown").replace("_", " ") for r in reactions})),
                "expected": "no" if False in expected else ("yes" if expected and all(expected) else "unknown"),
                "causality": ", ".join(sorted({(r.get("causality") or {}).get("category") or "not assessed" for r in reactions})),
                "expedited_candidate": row["case_number"] in expedited,
            }
        )
    literature = fetch_all(
        connection,
        """
        with latest_outcome as (
          select distinct on (o.state_id) o.state_id, o.outcome, o.case_id
          from literature_outcomes o order by o.state_id, o.created_at desc, o.id desc
        )
        select cs.id as state_id, cs.title_or_header as title, cs.normalized_state->>'pmid' as pmid,
               src.source, src.source_uid, lo.outcome, c.case_number
        from graph_edges e
        join clinical_states cs on cs.id::text = e.from_ref and cs.domain = 'pv_literature'
        left join latest_outcome lo on lo.state_id = cs.id
        left join cases c on c.id = lo.case_id
        left join lateral (
          select s.source, s.source_uid from source_records s where s.state_id = cs.id order by s.id limit 1
        ) src on true
        where e.from_kind = 'literature' and e.relation = 'mentions' and e.to_kind = 'product' and e.to_ref = %s
          and cs.first_seen_at::date between %s and %s
        order by cs.id
        """,
        (product["code"], interval_start, data_lock_point),
    )
    for article in literature:
        article["reference"] = (
            article["source_uid"] if article["source"] == "demo_fixture"
            else (f"PMID {article['pmid']}" if article["pmid"] else str(article["source_uid"]))
        )
    lack_of_efficacy = [
        r["case_number"] for r in interval
        if any(s.get("kind") == "lack_of_efficacy" for s in r["payload"].get("special_situations", []))
    ]
    return {
        "stats": {
            "interval_cases": len(interval),
            "interval_serious": sum(1 for r in interval if r["serious"]),
            "interval_non_serious": sum(1 for r in interval if not r["serious"]),
            "interval_fatal": sum(1 for r in interval if is_fatal(r)),
            "interval_expedited_candidates": len(expedited),
            "cumulative_cases": len(approved),
            "cumulative_serious": sum(1 for r in approved if r["serious"]),
            "cumulative_non_serious": sum(1 for r in approved if not r["serious"]),
            "cumulative_fatal": sum(1 for r in approved if is_fatal(r)),
            "pending_cases": len(pending),
            "literature_screened": len(literature),
            "literature_undecided": sum(1 for a in literature if a["outcome"] in (None, "escalated")),
        },
        "top_events": top_events,
        "expedited_cases": expedited,
        "lack_of_efficacy_cases": lack_of_efficacy,
        "line_listing": line_listing,
        "pending_case_numbers": [r["case_number"] for r in pending],
        "literature": [
            {"reference": a["reference"], "title": a["title"], "outcome": a["outcome"] or "not yet decided", "case_number": a["case_number"]}
            for a in literature
        ],
        "literature_valid": [a["reference"] for a in literature if a["outcome"] == "valid_icsr"],
        "literature_information": [a["reference"] for a in literature if a["outcome"] == "safety_information"],
    }


# ---------------------------------------------------------------------------
# Section content
# ---------------------------------------------------------------------------

def _table(title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {"title": title, "columns": columns, "rows": rows}


def _listing_table(rows: list[dict[str, Any]], title: str) -> dict[str, Any]:
    return _table(
        title,
        ["Case", "Day zero", "Source", "Country", "Age / sex", "Event(s)", "Serious", "Outcome", "Expected", "Causality"],
        [[r["case_number"], r["day_zero"], r["source"], r["country"], r["age_sex"], r["events"], r["serious"],
          r["outcome"], r["expected"], r["causality"]] for r in rows],
    )


def _tables_for(key: str, data: dict[str, Any], product: dict[str, Any]) -> list[dict[str, Any]]:
    stats = data["stats"]
    if key in ("summary_tabulations", "pader_narrative"):
        tables = [
            _table(
                "Cases by seriousness",
                ["Measure", "Interval", "Cumulative to data lock point"],
                [
                    ["Cases", stats["interval_cases"], stats["cumulative_cases"]],
                    ["Serious", stats["interval_serious"], stats["cumulative_serious"]],
                    ["Non-serious", stats["interval_non_serious"], stats["cumulative_non_serious"]],
                    ["Fatal outcome", stats["interval_fatal"], stats["cumulative_fatal"]],
                    ["Serious and unexpected (expedited candidates)", stats["interval_expedited_candidates"], "—"],
                ],
            ),
            _table(
                "Reported events",
                ["Event (coded term, or verbatim when not coded)", "Interval", "Cumulative", "Serious in interval"],
                [[e["term"], e["interval"], e["cumulative"], e["serious_interval"]] for e in data["top_events"]],
            ),
        ]
        if key == "pader_narrative":
            tables.append(_listing_table([r for r in data["line_listing"] if r["expedited_candidate"]], "15-day Alert candidates"))
        return tables
    if key == "literature":
        return [
            _table(
                "Articles screened in the interval",
                ["Reference", "Title", "Outcome", "Case"],
                [[a["reference"], a["title"], a["outcome"].replace("_", " "), a["case_number"] or "—"] for a in data["literature"]],
            )
        ]
    if key == "rsi_changes":
        terms = [str(t.get("term")) for t in product.get("reference_safety_terms") or []]
        return [_table("Reference safety information in use", ["Version", "Listed terms"], [[product["rsi_version"], ", ".join(terms) or "none recorded"]])]
    if key == "signals_overview":
        repeated = [e for e in data["top_events"] if e["interval"] > 1]
        return [
            _table(
                "Events reported in more than one case in the interval (counts only; not a signal assessment)",
                ["Event", "Cases in interval", "Cumulative"],
                [[e["term"], e["interval"], e["cumulative"]] for e in repeated],
            )
        ]
    if key == "appendices":
        return [_listing_table(data["line_listing"], "Line listing of cases in the interval")]
    if key == "pader_listing":
        return [_listing_table([r for r in data["line_listing"] if not r["expedited_candidate"]], "Cases not submitted as 15-day Alert reports")]
    return []


def _generated_text(key: str, data: dict[str, Any]) -> str:
    stats = data["stats"]
    if key == "appendices":
        return f"Line listing of the {stats['interval_cases']} approved cases with day zero in the interval."
    if key == "pader_listing":
        count = stats["interval_cases"] - stats["interval_expedited_candidates"]
        return f"Index of the {count} approved cases in the interval that were not 15-day Alert candidates."
    return ""


def _model_data(product: dict[str, Any], interval_start: date, data_lock_point: date, data: dict[str, Any]) -> dict[str, Any]:
    """What the drafting model sees: aggregates and identifiers, no line-level patient data."""
    return {
        "product": {"code": product["code"], "name": product["name"]},
        "interval_start": interval_start.isoformat(),
        "data_lock_point": data_lock_point.isoformat(),
        "stats": data["stats"],
        "top_events": data["top_events"][:15],
        "expedited_cases": data["expedited_cases"],
        "case_numbers": [row["case_number"] for row in data["line_listing"]],
        "literature_valid": data["literature_valid"],
        "literature_information": data["literature_information"],
    }


def _draft_section(
    ctx: Ctx, report_number: str, key: str, title: str, report_type: str, model_data: dict[str, Any]
) -> dict[str, Any]:
    allowed_refs = set(model_data["case_numbers"]) | set(model_data["expedited_cases"])
    allowed_refs |= set(model_data["literature_valid"]) | set(model_data["literature_information"])
    allowed_numbers = set(_NUMBER.findall(json.dumps(model_data)))
    payload = {"section_key": key, "section_title": title, "report_type": report_type, "data": model_data}
    try:
        result = ctx.gateway.run(
            REPORT_SECTION, payload, tenant=ctx.tenant, identifiable=False, item_type="pv_report", item_ref=report_number
        )
    except (AiPolicyBlocked, AiFailure) as error:
        return {"status": "input_required", "text": "", "citations": [], "warnings": [f"Drafting unavailable ({error}). Write this section."], "lineage": {}}
    try:
        text, citations, warnings = parse_report_section(result.output, allowed_refs=allowed_refs, allowed_numbers=allowed_numbers)
    except AiOutputError:
        ctx.gateway.record_contract_failure(REPORT_SECTION, result, tenant=ctx.tenant, item_type="pv_report", item_ref=report_number)
        return {"status": "input_required", "text": "", "citations": [], "warnings": ["The draft failed validation. Write this section."], "lineage": {}}
    return {
        "status": "draft",
        "text": text,
        "citations": citations,
        "warnings": warnings,
        "lineage": {
            "task": REPORT_SECTION.version, "provider": result.provider, "model_id": result.model_id,
            "model_version": result.model_version, "is_ai": result.provider != "demo",
        },
    }


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def _report(connection: Any, report_number: str, *, lock: bool = False) -> dict[str, Any]:
    row = fetch_one(
        connection,
        f"""
        select r.id::text as id, r.report_number, r.report_type, r.interval_start, r.data_lock_point, r.status,
               r.current_version, r.created_at, r.updated_at, p.code as product_code, p.name as product_name,
               creator.email as created_by_email
        from periodic_reports r
        join products p on p.id = r.product_id
        left join tenant_members creator on creator.id = r.created_by
        where r.report_number = %s
        {"for update of r" if lock else ""}
        """,
        (report_number,),
    )
    if row is None:
        raise NotFound(f"No report {report_number}.")
    return row


def _content(connection: Any, report_id: str, version: int) -> dict[str, Any]:
    row = fetch_one(
        connection,
        "select content, author_kind, reason, created_at from periodic_report_versions where report_id = %s and version = %s",
        (report_id, version),
    )
    if row is None:
        raise NotFound("No such report version.")
    return row


def _write_version(
    connection: Any, ctx: Ctx, report: dict[str, Any], version: int, content: dict[str, Any], *, author_kind: str, reason: str, lineage: dict[str, Any]
) -> None:
    connection.execute(
        """
        insert into periodic_report_versions (report_id, version, content, author_kind, author_id, reason, lineage)
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (report["id"], version, Jsonb(content), author_kind, ctx.actor.user_id, reason[:500], Jsonb(lineage)),
    )
    connection.execute(
        "update periodic_reports set current_version = %s, updated_at = now() where id = %s", (version, report["id"])
    )


def create_report(
    connection: Any, ctx: Ctx, *, product_code: str, report_type: str, interval_start: date, data_lock_point: date
) -> dict[str, Any]:
    ctx.require("report.create")
    if report_type not in REPORT_TYPES:
        raise InvalidInput("Report type must be pbrer or pader.")
    if interval_start > data_lock_point:
        raise InvalidInput("The interval must start on or before the data lock point.")
    if data_lock_point > ctx.today:
        raise InvalidInput("The data lock point cannot be in the future.")
    if (data_lock_point - interval_start).days > 1096:
        raise InvalidInput("The interval is limited to three years.")
    product = get_product(connection, product_code)
    data = snapshot(connection, product, interval_start, data_lock_point)
    prefix = "VY-PBRER" if report_type == "pbrer" else "VY-PADER"
    report_number = next_number(connection, report_type, prefix)
    report_id = fetch_value(
        connection,
        """
        insert into periodic_reports (report_number, product_id, report_type, interval_start, data_lock_point, status, created_by)
        values (%s, %s, %s, %s, %s, 'draft', %s) returning id::text
        """,
        (report_number, product["id"], report_type, interval_start, data_lock_point, ctx.actor.user_id),
    )
    model_data = _model_data(product, interval_start, data_lock_point, data)
    sections = []
    any_ai = False
    for key, number, title, mode in PBRER_SECTIONS if report_type == "pbrer" else PADER_SECTIONS:
        section: dict[str, Any] = {
            "key": key, "number": number, "title": title, "mode": mode,
            "tables": _tables_for(key, data, product), "warnings": [], "citations": [], "lineage": {},
        }
        if mode == "draft":
            section.update(_draft_section(ctx, report_number, key, title, report_type, model_data))
            any_ai = any_ai or bool(section["lineage"].get("is_ai"))
        elif mode == "generated":
            section.update({"status": "generated", "text": _generated_text(key, data)})
        else:
            section.update({"status": "input_required", "text": ""})
        sections.append(section)
    content = {
        "schema": REPORT_SCHEMA,
        "report_type": report_type,
        "product": {
            "code": product["code"], "name": product["name"], "active_ingredient": product["active_ingredient"],
            "international_birth_date": product["international_birth_date"].isoformat() if product["international_birth_date"] else None,
            "rsi_version": product["rsi_version"],
        },
        "interval": {"start": interval_start.isoformat(), "data_lock_point": data_lock_point.isoformat()},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules_version": rules.RULES_VERSION,
        "data": {key: data[key] for key in ("stats", "expedited_cases", "pending_case_numbers", "lack_of_efficacy_cases")},
        "sections": sections,
    }
    report = {"id": report_id}
    _write_version(
        connection, ctx, report, 1, content, author_kind="ai" if any_ai else "system",
        reason=f"Draft created from data locked at {data_lock_point.isoformat()}",
        lineage={"task": REPORT_SECTION.version, "drafted_sections": [s["key"] for s in sections if s["status"] == "draft"]},
    )
    audit.record(
        connection, entity_kind="report", entity_ref=report_number, event_type="report_created", actor=ctx.actor,
        detail={"product": product_code, "type": report_type, "interval_start": interval_start.isoformat(),
                "data_lock_point": data_lock_point.isoformat(), "stats": data["stats"]},
    )
    return {"report_number": report_number, "version": 1}


def list_reports(connection: Any, ctx: Ctx) -> list[dict[str, Any]]:
    ctx.require("report.read")
    return fetch_all(
        connection,
        """
        select r.report_number, r.report_type, r.interval_start, r.data_lock_point, r.status, r.current_version,
               r.updated_at, p.code as product_code, s.signed_at, m.email as signed_by_email
        from periodic_reports r
        join products p on p.id = r.product_id
        left join report_signoffs s on s.report_id = r.id and s.version = r.current_version
        left join tenant_members m on m.id = s.signer_id
        order by r.created_at desc
        """,
    )


def progress(sections: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(section["status"] for section in sections)
    return {
        "total": len(sections),
        "complete": sum(counts[s] for s in COMPLETE_STATUSES),
        "draft": counts["draft"],
        "input_required": counts["input_required"],
    }


def get_report(connection: Any, ctx: Ctx, report_number: str, *, version: int | None = None) -> dict[str, Any]:
    ctx.require("report.read")
    report = _report(connection, report_number)
    number = version or report["current_version"]
    current = _content(connection, report["id"], number)
    content = current["content"]
    signoff = fetch_one(
        connection,
        """
        select s.version, s.meaning, s.signer_role, s.signed_at, m.email as signer_email
        from report_signoffs s left join tenant_members m on m.id = s.signer_id
        where s.report_id = %s order by s.signed_at desc limit 1
        """,
        (report["id"],),
    )
    versions = fetch_all(
        connection,
        """
        select v.version, v.author_kind, v.reason, v.created_at, m.email as author_email
        from periodic_report_versions v left join tenant_members m on m.id = v.author_id
        where v.report_id = %s order by v.version desc
        """,
        (report["id"],),
    )
    state = progress(content["sections"])
    return {
        "report": {key: report[key] for key in report if key != "id"},
        "version": number,
        "content": content,
        "progress": state,
        "signoff": signoff,
        "versions": versions,
        "history": audit.history(connection, entity_kind="report", entity_ref=report_number),
        "permissions": {
            "edit": ctx.can("report.edit") and report["status"] == "draft",
            "signoff": ctx.can("report.signoff") and report["status"] == "draft",
        },
        "ready_for_signoff": state["draft"] == 0 and state["input_required"] == 0,
        "signoff_meaning": SIGNOFF_MEANING,
    }


def _locked_draft(connection: Any, report_number: str, expected_version: int) -> dict[str, Any]:
    report = _report(connection, report_number, lock=True)
    if report["status"] != "draft":
        raise Conflict(f"{report_number} is signed off and cannot change. Create a new report.")
    if expected_version != report["current_version"]:
        raise Conflict(f"{report_number} was changed by someone else (version {report['current_version']}). Reload first.")
    return report


def update_section(
    connection: Any,
    ctx: Ctx,
    report_number: str,
    key: str,
    *,
    expected_version: int,
    action: str,
    text: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    ctx.require("report.edit")
    if action not in ("edit", "accept"):
        raise InvalidInput("Action must be edit or accept.")
    report = _locked_draft(connection, report_number, expected_version)
    content = json.loads(json.dumps(_content(connection, report["id"], report["current_version"])["content"]))
    section = next((s for s in content["sections"] if s["key"] == key), None)
    if section is None:
        raise NotFound("No such section.")
    if action == "accept":
        if section["status"] != "draft":
            raise Conflict("Only a machine draft can be accepted as written.")
        section["status"] = "accepted"
        detail = {"section": key, "action": "accepted"}
    else:
        text = (text or "").strip()
        if not text:
            raise InvalidInput("Write the section text. If nothing applies, say so, for example 'No new information in this interval.'")
        if len(text) > 12000:
            raise InvalidInput("Sections are limited to 12,000 characters.")
        if text == section.get("text") and section["status"] in COMPLETE_STATUSES:
            raise Conflict("Nothing changed.")
        section.update({"text": text, "status": "edited", "warnings": []})
        detail = {"section": key, "action": "edited", "reason": (reason or "").strip()[:500] or None}
    section["reviewed_by"] = ctx.actor.email
    section["reviewed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    version = report["current_version"] + 1
    _write_version(
        connection, ctx, report, version, content, author_kind="human",
        reason=(reason or "").strip() or f"Section {section['number']} {detail['action']}", lineage={"section": key},
    )
    audit.record(connection, entity_kind="report", entity_ref=report_number, event_type="section_updated", actor=ctx.actor, detail={**detail, "version": version})
    return {"report_number": report_number, "version": version}


def signoff(connection: Any, ctx: Ctx, report_number: str, *, version: int, meaning: str) -> dict[str, Any]:
    """Record the QPPV's signature. The API re-checks the password before calling this."""
    ctx.require("report.signoff")
    report = _locked_draft(connection, report_number, version)
    sections = _content(connection, report["id"], version)["content"]["sections"]
    state = progress(sections)
    if state["draft"] or state["input_required"]:
        raise Conflict(
            f"Not ready: {state['draft']} draft section(s) to review and {state['input_required']} section(s) needing input."
        )
    meaning = (meaning or "").strip()
    if meaning != SIGNOFF_MEANING:
        raise InvalidInput("Confirm the meaning of the signature.")
    connection.execute(
        """
        insert into report_signoffs (report_id, version, signer_id, signer_role, meaning)
        values (%s, %s, %s, %s, %s)
        """,
        (report["id"], version, ctx.actor.user_id, ctx.actor.role, meaning),
    )
    connection.execute("update periodic_reports set status = 'signed_off', updated_at = now() where id = %s", (report["id"],))
    audit.record(
        connection, entity_kind="report", entity_ref=report_number, event_type="report_signed_off", actor=ctx.actor,
        detail={"version": version, "meaning": meaning},
    )
    return {"report_number": report_number, "version": version, "status": "signed_off"}


def to_markdown(view: dict[str, Any]) -> str:
    """Plain export of one report version for review outside the console."""
    report, content = view["report"], view["content"]
    title = "Periodic benefit-risk evaluation report" if report["report_type"] == "pbrer" else "Periodic adverse drug experience report"
    lines = [
        f"# {title}: {product_label(content['product'])}",
        "",
        f"- Report: {report['report_number']}, version {view['version']}",
        f"- Interval: {content['interval']['start']} to {content['interval']['data_lock_point']} (data lock point)",
        f"- Status: {report['status'].replace('_', ' ')}",
    ]
    if view.get("signoff"):
        signed = view["signoff"]
        lines.append(f"- Signed off by {signed['signer_email']} ({signed['signer_role']}) at {signed['signed_at']}: {signed['meaning']}")
    else:
        lines.append("- Not signed off: DRAFT")
    for section in content["sections"]:
        lines += ["", f"## {section['number']}. {section['title']}", ""]
        if section.get("text"):
            lines.append(section["text"])
        elif section["status"] == "input_required":
            lines.append("_Input required._")
        if section["status"] == "draft":
            lines.append("")
            lines.append("_Machine draft, not yet reviewed._")
        for table in section.get("tables", []):
            lines += ["", f"**{table['title']}**", ""]
            if not table["rows"]:
                lines.append("_None._")
                continue
            lines.append("| " + " | ".join(table["columns"]) + " |")
            lines.append("|" + "---|" * len(table["columns"]))
            for row in table["rows"]:
                lines.append("| " + " | ".join(str(cell).replace("|", "/") for cell in row) + " |")
    return "\n".join(lines) + "\n"
