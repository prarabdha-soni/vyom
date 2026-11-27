"""Event coding with the MedDRA licence boundary.

Without a tenant licence, coding is limited to the 27 publicly listed
system organ classes; the verbatim term is always kept. With a licence, the
tenant loads its own release (``llt.asc`` and ``mdhier.asc``) into
``terminology_terms`` and gets lowest-level and preferred-term suggestions.
Vyom never ships dictionary content.
"""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
from typing import Any

from vyom_os.db import fetch_all
from vyom_os.rules import normalise_term

PUBLIC_SOCS: tuple[str, ...] = (
    "Blood and lymphatic system disorders",
    "Cardiac disorders",
    "Congenital, familial and genetic disorders",
    "Ear and labyrinth disorders",
    "Endocrine disorders",
    "Eye disorders",
    "Gastrointestinal disorders",
    "General disorders and administration site conditions",
    "Hepatobiliary disorders",
    "Immune system disorders",
    "Infections and infestations",
    "Injury, poisoning and procedural complications",
    "Investigations",
    "Metabolism and nutrition disorders",
    "Musculoskeletal and connective tissue disorders",
    "Neoplasms benign, malignant and unspecified (incl cysts and polyps)",
    "Nervous system disorders",
    "Pregnancy, puerperium and perinatal conditions",
    "Product issues",
    "Psychiatric disorders",
    "Renal and urinary disorders",
    "Reproductive system and breast disorders",
    "Respiratory, thoracic and mediastinal disorders",
    "Skin and subcutaneous tissue disorders",
    "Social circumstances",
    "Surgical and medical procedures",
    "Vascular disorders",
)

# Keyword hints for a system-organ-class suggestion. A suggestion only: the
# coder confirms or changes it, and licensed coding replaces it.
_SOC_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("alt", "ast", "transaminase", "liver enzyme", "bilirubin", "qt prolong", "ecg", "inr", "creatinine increased", "blood pressure increased"), "Investigations"),
    (("hepatitis", "liver injury", "jaundice", "hepatotoxic", "cholestasis"), "Hepatobiliary disorders"),
    (("rash", "urticaria", "pruritus", "itch", "stevens johnson", "toxic epidermal", "angioedema", "erythema", "blister", "alopecia"), "Skin and subcutaneous tissue disorders"),
    (("anaphyla", "hypersensitiv", "allergic"), "Immune system disorders"),
    (("nausea", "vomit", "diarrhoea", "diarrhea", "abdominal pain", "pancreatitis", "constipation", "dyspepsia", "gastrointestinal"), "Gastrointestinal disorders"),
    (("headache", "dizziness", "seizure", "convulsion", "somnolence", "syncope", "tremor", "paraesthesia", "neuropathy"), "Nervous system disorders"),
    (("palpitation", "tachycardia", "bradycardia", "arrhythmia", "cardiac arrest", "myocardial"), "Cardiac disorders"),
    (("hypotension", "hypertension", "flushing", "thrombosis", "haemorrhage", "hemorrhage"), "Vascular disorders"),
    (("neutropenia", "thrombocytopenia", "anaemia", "anemia", "agranulocytosis", "leukopenia"), "Blood and lymphatic system disorders"),
    (("kidney injury", "renal failure", "nephr", "haematuria", "proteinuria"), "Renal and urinary disorders"),
    (("hyponatraemia", "hyponatremia", "hypoglycaemia", "hypoglycemia", "hyperkalaemia", "lactic acidosis", "decreased appetite"), "Metabolism and nutrition disorders"),
    (("dyspnoea", "dyspnea", "cough", "bronchospasm", "pneumonitis", "respiratory"), "Respiratory, thoracic and mediastinal disorders"),
    (("myalgia", "arthralgia", "rhabdomyolysis", "muscle", "back pain"), "Musculoskeletal and connective tissue disorders"),
    (("insomnia", "depress", "anxiety", "hallucination", "confusion", "agitation"), "Psychiatric disorders"),
    (("overdose", "medication error", "wrong dose", "wrong drug", "accidental exposure", "occupational exposure"), "Injury, poisoning and procedural complications"),
    (("pregnan", "abortion", "premature", "foetal", "fetal"), "Pregnancy, puerperium and perinatal conditions"),
    (("vision", "visual", "eye", "conjunctiv"), "Eye disorders"),
    (("tinnitus", "vertigo", "hearing"), "Ear and labyrinth disorders"),
    (("fever", "pyrexia", "fatigue", "asthenia", "malaise", "injection site", "oedema", "edema", "chest pain", "lack of efficacy", "drug ineffective", "no effect"), "General disorders and administration site conditions"),
    (("infection", "sepsis", "pneumonia"), "Infections and infestations"),
)


def suggest_soc(verbatim: str) -> str | None:
    text = f" {normalise_term(verbatim)} "
    for keywords, soc in _SOC_HINTS:
        if any(keyword in text for keyword in keywords):
            return soc
    return None


def suggest_coding(connection: Any, *, verbatim: str, licensed: bool, dictionary: str | None) -> dict[str, Any]:
    """Coding proposal for one verbatim term, within the tenant's licence."""
    if licensed and dictionary:
        rows = fetch_all(
            connection,
            """
            select llt_code, llt_name, pt_code, pt_name, soc_name
            from terminology_terms
            where dictionary = %s and lower(llt_name) = lower(%s)
            limit 1
            """,
            (dictionary, verbatim.strip()),
        )
        if rows:
            row = rows[0]
            return {
                "dictionary": dictionary,
                "soc": row["soc_name"],
                "pt": row["pt_name"],
                "pt_code": row["pt_code"],
                "llt": row["llt_name"],
                "llt_code": row["llt_code"],
                "status": "suggested",
            }
    soc = suggest_soc(verbatim)
    if soc is None:
        return {"dictionary": None, "soc": None, "pt": None, "pt_code": None, "llt": None, "llt_code": None, "status": "none"}
    return {"dictionary": "soc-public", "soc": soc, "pt": None, "pt_code": None, "llt": None, "llt_code": None, "status": "suggested"}


def search_terms(connection: Any, *, query: str, dictionary: str, limit: int = 20) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        select llt_code, llt_name, pt_code, pt_name, soc_name
        from terminology_terms
        where dictionary = %s and lower(llt_name) like lower(%s)
        order by length(llt_name), llt_name
        limit %s
        """,
        (dictionary, f"{query.strip()}%", limit),
    )


def parse_release(llt_text: str, hierarchy_text: str) -> list[tuple[str, str, str, str, str, str]]:
    """Parse MedDRA ASCII ``llt.asc`` and ``mdhier.asc`` ($-delimited).

    Returns (llt_code, llt_name, pt_code, pt_name, soc_code, soc_name) for
    current lowest-level terms, using each preferred term's primary SOC.
    """
    hierarchy: dict[str, tuple[str, str, str]] = {}
    for row in csv.reader(io.StringIO(hierarchy_text), delimiter="$"):
        if len(row) < 12:
            continue
        pt_code, _hlt, _hlgt, soc_code, pt_name, _hlt_name, _hlgt_name, soc_name = row[:8]
        primary = row[11].strip().upper() == "Y"
        if primary or pt_code not in hierarchy:
            hierarchy[pt_code] = (pt_name, soc_code, soc_name)
    terms = []
    for row in csv.reader(io.StringIO(llt_text), delimiter="$"):
        if len(row) < 10:
            continue
        llt_code, llt_name, pt_code = row[0], row[1], row[2]
        current = row[9].strip().upper() != "N"
        if not current or pt_code not in hierarchy:
            continue
        pt_name, soc_code, soc_name = hierarchy[pt_code]
        terms.append((llt_code, llt_name, pt_code, pt_name, soc_code, soc_name))
    return terms


def main(argv: list[str] | None = None) -> None:
    """Load a tenant's own licensed release: vyom-terminology-load --tenant slug ..."""
    from vyom_os.db import Database
    from vyom_os.settings import AppSettings

    parser = argparse.ArgumentParser(description="Load a licensed MedDRA release for one tenant")
    parser.add_argument("--tenant", required=True, help="tenant slug")
    parser.add_argument("--dictionary", required=True, help="label, e.g. meddra-27.1")
    parser.add_argument("--llt", required=True, type=Path, help="path to llt.asc")
    parser.add_argument("--hierarchy", required=True, type=Path, help="path to mdhier.asc")
    parser.add_argument("--confirm-licence", action="store_true", help="confirm the tenant holds a valid licence")
    args = parser.parse_args(argv)
    if not args.confirm_licence:
        raise SystemExit("Refusing to load: pass --confirm-licence once the tenant's licence is verified")

    settings = AppSettings.from_env()
    database = Database(settings.database_url, settings.app_database_url)
    terms = parse_release(
        args.llt.read_text(encoding="utf-8", errors="replace"),
        args.hierarchy.read_text(encoding="utf-8", errors="replace"),
    )
    with database.service() as connection:
        row = fetch_all(connection, "select id from tenants where slug = %s", (args.tenant,))
        if not row:
            raise SystemExit(f"Unknown tenant {args.tenant}")
        tenant_id = str(row[0]["id"])
    with database.tenant(tenant_id) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                insert into terminology_terms
                  (dictionary, llt_code, llt_name, pt_code, pt_name, soc_code, soc_name)
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (tenant_id, dictionary, llt_code) do nothing
                """,
                [(args.dictionary, *term) for term in terms],
            )
    with database.service() as connection:
        connection.execute(
            "update tenants set meddra_licence_state = 'licensed', "
            "feature_flags = feature_flags || jsonb_build_object('meddra_dictionary', %s::text) where id = %s",
            (args.dictionary, tenant_id),
        )
    print(f"Loaded {len(terms)} current lowest-level terms into {args.tenant} ({args.dictionary}).")
