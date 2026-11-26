"""Build the console's sample workspace from a seeded, local Vyom OS.

The sample workspace (vyom-web/src/content/sample-workspace/snapshot.json) is
the fictional tenant demo-pharma, worked through the real API and captured as
JSON so the console can demo without a backend.

    python -m pip install -e '.[test]'          # httpx
    python -m vyom_os.seed --confirm-fictional   # on a fresh database
    export VYOM_DEMO_PASSWORD=...                # the seed's demo password; never commit it
    python scripts/sample_workspace.py enrich
    python scripts/sample_workspace.py capture ../vyom-web/src/content/sample-workspace/snapshot.json

`enrich` adds activity (literature decisions, a narrative draft, an E2B
export, a signed-off PADER, a PBRER part-way through authoring). Run it once,
on a fresh seed. `capture` writes the snapshot. Both refuse any tenant that is
not marked fictional. VYOM_OS defaults to http://127.0.0.1:8000.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = os.environ.get("VYOM_OS", "http://127.0.0.1:8000")
TENANT = "demo-pharma"
OPS_TENANT = "vyom-internal"


def password() -> str:
    value = os.environ.get("VYOM_DEMO_PASSWORD")
    if not value:
        sys.exit("Set VYOM_DEMO_PASSWORD to the seed's demo password.")
    return value


def session(email: str) -> httpx.Client:
    response = httpx.post(f"{BASE}/v1/auth/sign-in", json={"email": email, "password": password()}, timeout=30)
    response.raise_for_status()
    body = response.json()
    client = httpx.Client(
        base_url=BASE, headers={"Authorization": f"Bearer {body['token']}", "X-Tenant-ID": body["tenant"]["id"]}, timeout=60
    )
    tenant = client.get("/v1/me").json()["tenant"]
    # The operations tenant holds no safety data; every other tenant must be the fictional sample.
    if not (tenant["slug"] == OPS_TENANT or (tenant["slug"] == TENANT and tenant.get("is_fictional"))):
        sys.exit(f"Refusing to use tenant {tenant['slug']!r}: only the fictional sample tenant may be captured.")
    return client


def get(client: httpx.Client, path: str, **params: object) -> object:
    response = client.get(path, params=params)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# enrich
# ---------------------------------------------------------------------------


def enrich() -> None:
    reviewer = session(f"reviewer@{TENANT}.example")
    physician = session(f"physician@{TENANT}.example")
    qppv = session(f"qppv@{TENANT}.example")

    def article(reference: str) -> dict:
        items = get(reviewer, "/v1/literature", view="all")["items"]
        return next(item for item in items if item["reference"] == reference)

    def decide(client: httpx.Client, reference: str, outcome: str, reason: str | None = None) -> None:
        item = article(reference)
        response = client.post(
            f"/v1/literature/{item['state_id']}/decision",
            json={"decision_id": item["decision_id"], "outcome": outcome, "reason": reason},
        )
        print("decide", reference, outcome, response.status_code)

    decide(reviewer, "VY-LIT-0011", "valid_icsr")
    decide(reviewer, "VY-LIT-0009", "safety_information",
           "Aggregate cohort data with no identifiable patient. Logged for the periodic report literature section.")
    decide(reviewer, "VY-LIT-0003", "escalated",
           "Paediatric seizure; physician to review the full text before a validity decision.")

    case = get(reviewer, "/v1/cases/VY-CASE-0006")
    print("narrative VY-CASE-0006",
          reviewer.post("/v1/cases/VY-CASE-0006/narrative", json={"expected_version": case["version"]["number"]}).status_code)
    print("export VY-CASE-0001", physician.post("/v1/cases/VY-CASE-0001/exports").status_code)

    # A PADER for VY-305, signed off.
    today = date.fromisoformat(get(reviewer, "/v1/me")["today"])
    created = qppv.post("/v1/reports", json={
        "product_code": "VY-305", "report_type": "pader",
        "interval_start": (today - timedelta(days=91)).isoformat(),
        "data_lock_point": (today - timedelta(days=1)).isoformat(),
    })
    created.raise_for_status()
    pader = created.json()["report_number"]
    section(qppv, pader, "pader_narrative", "accept")
    section(qppv, pader, "pader_actions", "edit",
            "No safety-related actions were taken for VY-305 during this reporting period, and no changes were made to the "
            "reference safety information (SAMPLE DATA).", "Input provided by the QPPV")
    report = get(qppv, f"/v1/reports/{pader}")
    print("signoff", pader, qppv.post(f"/v1/reports/{pader}/signoff",
                                      json={"version": report["version"], "meaning": report["signoff_meaning"],
                                            "password": password()}).status_code)

    # The seeded PBRER, part-way through authoring.
    pbrer = "VY-PBRER-0001"
    section(physician, pbrer, "introduction", "accept")
    section(physician, pbrer, "summary_tabulations", "accept")
    for client, key, text, reason in PBRER_INPUT:
        section(physician if client == "physician" else qppv, pbrer, key, "edit", text, reason)
    print(pbrer, get(physician, f"/v1/reports/{pbrer}")["progress"])


def section(client: httpx.Client, number: str, key: str, action: str, text: str | None = None, reason: str | None = None) -> None:
    version = get(client, f"/v1/reports/{number}")["version"]
    response = client.post(f"/v1/reports/{number}/sections/{key}",
                           json={"expected_version": version, "action": action, "text": text, "reason": reason})
    print(action, number, key, response.status_code, response.text[:120] if response.status_code >= 300 else "")


PBRER_INPUT = [
    ("qppv", "approval_status",
     "VY-201 (FICTIONAL) holds a sample marketing authorisation in India, with an international birth date of 1 March 2019. "
     "No marketing authorisations were granted, varied, suspended or withdrawn during the reporting interval, and the product "
     "was not withdrawn from any market for safety reasons.", "Regulatory affairs input"),
    ("qppv", "safety_actions",
     "No actions were taken for safety reasons during the reporting interval by the marketing authorisation holder, a regulatory "
     "authority, a data monitoring committee or an ethics committee.", "Regulatory affairs input"),
    ("physician", "rsi_changes",
     "The reference safety information in force at the start of the interval was RSI v1 (FICTIONAL). It was not changed during "
     "the interval, and RSI v1 (FICTIONAL) was used to assess expectedness throughout this report.",
     "Confirmed against the RSI register"),
    ("physician", "clinical_trials",
     "No company-sponsored interventional clinical trials of VY-201 (FICTIONAL) were ongoing or completed during the interval, "
     "and no new safety findings from clinical trials were identified.", "Clinical operations confirmed no active trials"),
    ("physician", "non_interventional",
     "No non-interventional studies of VY-201 (FICTIONAL) were ongoing or completed during the interval.",
     "Clinical operations confirmed no studies"),
    ("physician", "other_sources",
     "No safety information relevant to VY-201 (FICTIONAL) was received from other clinical trial or study sources, including "
     "pooled analyses or investigator-initiated studies.", "No other sources identified"),
    ("physician", "non_clinical",
     "No new non-clinical safety findings for VY-201 (FICTIONAL) were generated during the interval.",
     "Non-clinical safety team confirmed"),
    ("qppv", "other_periodic_reports",
     "Not applicable. No other periodic reports for VY-201 (FICTIONAL) were prepared during the interval.",
     "Not applicable for this product"),
    ("physician", "late_breaking",
     "No significant safety information was received after the data lock point and before this report was finalised.",
     "Checked case intake after the data lock point"),
]


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


def capture(out: Path) -> None:
    reviewer = session(f"reviewer@{TENANT}.example")
    roles = {
        "reviewer": reviewer,
        "safety_physician": session(f"physician@{TENANT}.example"),
        "qppv": session(f"qppv@{TENANT}.example"),
        "admin": session(f"admin@{TENANT}.example"),
    }
    ops = session(f"ops@{OPS_TENANT}.example")

    me = {role: get(client, "/v1/me") for role, client in roles.items()}
    snap: dict = {
        "captured_on": me["reviewer"]["today"],
        "me": me,
        "dashboard": get(reviewer, "/v1/dashboard"),
        "products": get(reviewer, "/v1/products"),
        "settings": get(roles["admin"], "/v1/settings"),
        "audit": get(reviewer, "/v1/audit"),
        "ops": get(ops, "/v1/ops/summary"),
    }
    literature = get(reviewer, "/v1/literature", view="all")
    snap["literature"] = literature
    snap["literature_detail"] = {
        str(item["state_id"]): get(reviewer, f"/v1/literature/{item['state_id']}") for item in literature["items"]
    }
    cases = get(reviewer, "/v1/cases")
    snap["cases"] = cases
    snap["case_detail"] = {item["case_number"]: get(reviewer, f"/v1/cases/{item['case_number']}") for item in cases["items"]}
    exports = {}
    for number, detail in snap["case_detail"].items():
        for exported in detail["exports"]:
            # Downloading needs case.export, which a reviewer does not hold.
            response = roles["safety_physician"].get(f"/v1/cases/{number}/exports/{exported['id']}")
            response.raise_for_status()
            exports[f"{number}/{exported['id']}"] = {"xml": response.text, "sha256": response.headers.get("x-content-sha256")}
    snap["case_exports"] = exports
    reports = get(reviewer, "/v1/reports")
    snap["reports"] = reports
    snap["report_detail"] = {item["report_number"]: get(reviewer, f"/v1/reports/{item['report_number']}") for item in reports}
    snap["report_markdown"] = {}
    for number in snap["report_detail"]:
        response = reviewer.get(f"/v1/reports/{number}/export")
        response.raise_for_status()
        snap["report_markdown"][number] = response.text

    # Sign-ins by this script are noise, not workspace activity.
    def quiet(rows: list[dict]) -> list[dict]:
        return [row for row in rows if row["event_type"] != "signed_in"]

    snap["audit"] = quiet(snap["audit"])
    snap["dashboard"]["activity"] = snap["audit"][:12]
    for group in ("literature_detail", "case_detail", "report_detail"):
        for detail in snap[group].values():
            detail["history"] = quiet(detail["history"])
    # Only the fictional tenant and the operations tenant belong in the sample ops view.
    snap["ops"]["tenants"] = [t for t in snap["ops"]["tenants"] if t["slug"] in (TENANT, OPS_TENANT)]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("captured", snap["captured_on"], "->", out, f"{out.stat().st_size} bytes")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "enrich":
        enrich()
    elif len(sys.argv) == 3 and sys.argv[1] == "capture":
        capture(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
