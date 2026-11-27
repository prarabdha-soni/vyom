"""Deterministic demo engine: rule-based stand-ins for every model task.

Used when ``VYOM_AI_MODE=demo`` so the product runs end to end without cloud
credentials. It returns the same shapes as the Gemini tasks, its output goes
through the same validators, and every result is labelled with
``DEMO_MODEL_ID`` so nobody mistakes it for an AI decision. It is tuned to the
synthetic sample data, not to real-world reports.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

DEMO_PROVIDER = "demo"
DEMO_MODEL_ID = "vyom-demo-rules-v1"
DEMO_SAMPLER_VERSION = "demo-1"

_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)
_DATE = r"(\d{1,2}) (" + "|".join(_MONTHS) + r") (\d{4})"
_DATE_RE = re.compile(_DATE)

_COUNTRIES = (
    "India", "Nepal", "Sri Lanka", "Bangladesh", "United Kingdom", "United States",
    "Germany", "France", "Kenya", "South Africa", "Brazil",
)
_INDIAN_CITIES = (
    "Pune", "Mumbai", "Delhi", "Ahmedabad", "Hyderabad", "Chennai", "Kolkata", "Bengaluru",
    "Jaipur", "Lucknow", "Nagpur", "Baddi", "Indore", "Surat", "Vadodara",
)

# (pattern, medically important) — verbatim is the matched text.
_EVENTS: tuple[tuple[str, bool], ...] = (
    (r"(?:widespread |generalised |severe |mild |pruritic )*(?:maculopapular )?rash", False),
    (r"(?:severe )?angioedema(?: of the [a-z]+(?: and [a-z]+)?)?", False),
    (r"anaphyla(?:xis|ctic reaction|ctic shock)", True),
    (r"Stevens-Johnson syndrome", True),
    (r"toxic epidermal necrolysis", True),
    (r"(?:raised|elevated|increased) liver enzymes", False),
    (r"(?:acute )?hepatitis", False),
    (r"jaundice", False),
    (r"nausea", False),
    (r"vomiting", False),
    (r"diarrh(?:o)?ea", False),
    (r"abdominal pain", False),
    (r"(?:acute )?pancreatitis", True),
    (r"headaches?", False),
    (r"(?:very )?dizz(?:y|iness)(?: on standing)?", False),
    (r"fall at home", False),
    (r"(?:generalised )?(?:tonic-clonic )?seizures?", True),
    (r"syncope", False),
    (r"bradycardia", False),
    (r"tachycardia", False),
    (r"hypotension", False),
    (r"(?:severe )?hyperkal(?:a)?emia", False),
    (r"hyponatr(?:a)?emia", False),
    (r"agranulocytosis", True),
    (r"neutropenia", False),
    (r"pneumonia", False),
    (r"(?:persistent )?(?:dry )?cough", False),
    (r"fever", False),
    (r"lack of efficacy", False),
)

_HOSPITAL = re.compile(
    r"\b(?:hospitalised|hospitalized|admitted to (?:hospital|the intensive care unit)|"
    r"intensive care unit)\b",
    re.IGNORECASE,
)
_HOSPITAL_NEGATED = re.compile(
    r"\b(?:not|never|no need to|did not need to)\b[^.]{0,30}\b(?:hospital|hospitalised|hospitalized|admitted)\b",
    re.IGNORECASE,
)


def _iso(day: str, month: str, year: str) -> str:
    return date(int(year), _MONTHS.index(month) + 1, int(day)).isoformat()


def _sentences(text: str) -> list[tuple[int, str]]:
    """Sentences with their start offsets."""
    result = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        sentence = match.group(0).strip()
        if sentence:
            result.append((match.start() + (len(match.group(0)) - len(match.group(0).lstrip())), sentence))
    return result


def _first(pattern: str, text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    return re.search(pattern, text, flags)


# ---------------------------------------------------------------------------
# Literature screening (System One questions)
# ---------------------------------------------------------------------------

def study_design(text: str) -> str:
    lowered = text.casefold()
    if re.search(r"\b(rats?|mice|mouse|rabbits?|dogs?|animals?)\b", lowered) or "in vitro" in lowered or "cell lines" in lowered:
        return "IN_VITRO_OR_ANIMAL_ONLY"
    if re.search(r"\b(narrative review|systematic review|this review|meta-analysis)\b", lowered):
        return "REVIEW_NO_NEW_CASES"
    if re.search(r"\b(randomi[sz]ed|controlled trial|double-blind|placebo)\b", lowered):
        return "CLINICAL_TRIAL"
    if re.search(r"\b(cohort|retrospective|registry|records of)\b", lowered):
        return "OBSERVATIONAL_COHORT"
    if re.search(r"\b(we report|we describe|case report)\b", lowered) or re.search(r"\d+-year-old", lowered):
        return "CASE_REPORT_OR_SERIES"
    return "UNCERTAIN"


def _event_matches(text: str) -> list[tuple[int, re.Match[str]]]:
    """Event mentions as (lexicon index, match), in text order, without overlaps."""
    found: list[tuple[int, re.Match[str]]] = []
    for index, (pattern, _important) in enumerate(_EVENTS):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if any(match.start() < other.end() and other.start() < match.end() for _i, other in found):
                continue
            found.append((index, match))
    return sorted(found, key=lambda item: item[1].start())


def _serious_signals(text: str) -> set[str]:
    signals: set[str] = set()
    for _start, sentence in _sentences(text):
        if re.search(r"\b(died|death|fatal)\b", sentence, re.IGNORECASE):
            signals.add("death")
        if re.search(r"life-threatening", sentence, re.IGNORECASE):
            signals.add("life_threatening")
        if _HOSPITAL.search(sentence) and not _HOSPITAL_NEGATED.search(sentence):
            signals.add("hospitalisation")
    if any(_EVENTS[index][1] for index, _match in _event_matches(text)):
        signals.add("other_medically_important")
    return signals


def system_one(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    text = f"{state.get('title') or ''}. {state.get('abstract') or ''}"
    design = study_design(text)
    human = design in {"CASE_REPORT_OR_SERIES", "CLINICAL_TRIAL", "OBSERVATIONAL_COHORT", "UNCERTAIN"}
    individual = design == "CASE_REPORT_OR_SERIES" and bool(re.search(r"\d+-year-old|\baged \d+", text))
    has_product = bool(re.search(r"\bVY-\d{3}\b", text))
    events = _event_matches(text) if human else []
    serious = _serious_signals(text) if human else set()
    authors = bool(state.get("authors"))

    def noul(probability: float) -> dict[str, Any]:
        return {"answer": "YES" if probability >= 0.5 else "NO", "probability": probability}

    p_patient = 0.96 if individual else (0.08 if human else 0.02)
    p_reporter = (0.92 if individual else 0.30) if (authors and human) else 0.02
    p_drug = 0.95 if (has_product and human) else 0.03
    p_event = 0.90 if events else (0.10 if human else 0.02)
    p_serious = 0.85 if serious else (0.12 if human else 0.01)
    if "death" in serious or "life_threatening" in serious:
        priority = 5
    elif serious:
        priority = 4
    elif individual and events:
        priority = 3
    elif events or re.search(r"pregnan", text, re.IGNORECASE):
        priority = 2
    else:
        priority = 1
    answers = {
        "has_identifiable_patient": noul(p_patient),
        "has_identifiable_reporter": noul(p_reporter),
        "has_suspect_drug": noul(p_drug),
        "has_adverse_event": noul(p_event),
        "is_serious_event": noul(p_serious),
        "study_design": {"choice": design, "probability": 0.9},
        "triage_priority": {"score": priority, "probability": 0.8},
    }
    return {key: answers[key] for key in questions if key in answers}


# ---------------------------------------------------------------------------
# Case extraction
# ---------------------------------------------------------------------------

def _patient(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "initials": None, "age_value": None, "age_unit": None, "age_group": None,
        "sex": "unknown", "weight_kg": None, "pregnant": None, "evidence": None,
    }
    match = _first(
        r"(\d{1,3})-(year|month|week|day)-old(?: (male|female))? ?(woman|man|boy|girl|patient|infant|lady|gentleman)?",
        text,
    )
    if match:
        result["age_value"] = float(match.group(1))
        result["age_unit"] = match.group(2) + "s"
        result["evidence"] = match.group(0).strip()
    else:
        match = _first(r"(?:(female|male) [a-z]+ )?aged (\d{1,3})", text) or _first(r"\bAge: (\d{1,3})", text)
        if match:
            value = match.group(match.lastindex or 1)
            result["age_value"] = float(value)
            result["age_unit"] = "years"
            result["evidence"] = match.group(0).strip()

    sex_match = _first(r"\bSex: (male|female)\b", text)
    if sex_match:
        result["sex"] = sex_match.group(1).casefold()
    else:
        window = match.group(0) if match else ""
        if re.search(r"\b(female|woman|girl|lady)\b", window, re.IGNORECASE):
            result["sex"] = "female"
        elif re.search(r"\b(male|man|boy|gentleman)\b", window, re.IGNORECASE):
            result["sex"] = "male"
        elif re.search(r"\b(my mother|she|her|woman|female)\b", text, re.IGNORECASE):
            result["sex"] = "female"
        elif re.search(r"\b(my father|he|his|man|male)\b", text, re.IGNORECASE):
            result["sex"] = "male"
        if result["evidence"] is None and re.search(r"\bmy mother\b", text, re.IGNORECASE):
            result["evidence"] = "My mother"
    if re.search(r"\bmy mother\b", text, re.IGNORECASE) and result["sex"] == "unknown":
        result["sex"] = "female"

    initials = _first(r"initials ([A-Z]\.[A-Z]\.?)", text, 0)
    if initials:
        result["initials"] = initials.group(1)
    if re.search(r"\bpregnan(?:t|cy)\b", text, re.IGNORECASE) and not re.search(
        r"\bnot pregnant\b", text, re.IGNORECASE
    ):
        result["pregnant"] = True
    return result


_HCP_ROLES = "physician|rheumatologist|nephrologist|cardiologist|dermatologist|doctor|pharmacist|nurse"


def _hcp_qualification(role: str) -> str:
    role = role.casefold()
    if "pharmacist" in role:
        return "pharmacist"
    if "nurse" in role:
        return "other_health_professional"
    return "physician"


def _reporter(text: str, context: dict[str, Any]) -> dict[str, Any]:
    channel = context.get("channel")
    country = next((c for c in _COUNTRIES if re.search(rf"\b{re.escape(c)}\b", text)), None)
    if country is None and any(re.search(rf"\b{city}\b", text) for city in _INDIAN_CITIES):
        country = "India"
    if channel == "literature":
        reported = _first(r"\bWe (?:report|describe)\b", text)
        return {
            "qualification": "physician" if reported else "unknown",
            "country": country,
            "identifiable": bool(context.get("authors")),
            "description": "Article authors",
            "evidence": reported.group(0) if reported else None,
        }
    # Only the reporter's own words identify the reporter: "His doctor reduced
    # the dose" names a doctor who did not report the case.
    qualification, evidence, description = "unknown", None, None
    self_named = _first(rf"\b(?:I am|Caller is) (?:a|an|the) ((?:[a-z]+ ){{0,2}}?(?:{_HCP_ROLES}))\b", text)
    relative = _first(r"\bI am (?:her|his|the patient's) (son|daughter|husband|wife|mother|father)\b", text)
    form_type = _first(r"\bReporter type: (patient|consumer|physician|pharmacist|nurse)\b", text)
    if self_named:
        qualification, evidence, description = _hcp_qualification(self_named.group(1)), self_named.group(0), self_named.group(1)
    elif relative:
        qualification, evidence = "consumer", relative.group(0)
        description = f"{relative.group(1)} of the patient"
    elif form_type:
        role = form_type.group(1).casefold()
        qualification = "consumer" if role in {"patient", "consumer"} else _hcp_qualification(role)
        evidence, description = form_type.group(0), role
    identifiable = bool(
        re.search(
            r"contact (?:me|us)|can be reached|phone number|contact email|agreed to be contacted|"
            r"contacted for follow-up|for follow-up",
            text,
            re.IGNORECASE,
        )
    )
    if description:
        description = description[0].upper() + description[1:]
    return {
        "qualification": qualification,
        "country": country,
        "identifiable": identifiable,
        "description": description,
        "evidence": evidence,
    }


_ROUTES = {
    "orally": "oral", "oral": "oral", "by mouth": "oral",
    "subcutaneously": "subcutaneous", "subcutaneous": "subcutaneous",
    "intravenously": "intravenous", "intramuscularly": "intramuscular",
    "topically": "topical",
}
_NOT_INDICATIONS = {"observation", "follow-up", "intravenous antibiotics", "a change of treatment", "three months", "three weeks"}


def _products(text: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    codes = [str(p.get("code")) for p in context.get("tenant_products", []) if p.get("code")]
    mentions: list[tuple[int, str]] = []
    for code in codes:
        match = re.search(rf"\b{re.escape(code)}\b", text)
        if match:
            mentions.append((match.start(), code))
    mentions.sort()
    sentences = _sentences(text)
    results = []
    for order, (position, code) in enumerate(mentions):
        before = text[max(0, position - 40):position].casefold()
        role = "concomitant" if order > 0 and re.search(r"also takes|also taking|concomitant|along with", before) else "suspect"
        dose_sentence = next(
            (s for _start, s in sentences if code in s and re.search(rf"{re.escape(code)}\s+\d", s)),
            None,
        ) or next((s for _start, s in sentences if code in s), "")
        dose = None
        dose_match = re.search(
            rf"{re.escape(code)}\s+(\d+(?:\.\d+)?\s?(?:mg|mcg|g|mL|units|IU)(?:/(?:mL|kg|day))?)"
            r"(?:\s+(?:capsules|tablets))?((?:\s+(?:orally|subcutaneously|intravenously))?\s+(?:once daily|twice daily|daily|every two weeks|weekly))?",
            dose_sentence,
        )
        if dose_match:
            dose = dose_match.group(1)
            frequency = re.search(r"(once daily|twice daily|daily|every two weeks|weekly)", dose_match.group(0))
            if frequency:
                dose = f"{dose} {frequency.group(1)}"
        route = None
        route_match = re.search(r"\b(orally|oral|by mouth|subcutaneously|intravenously|intramuscularly|topically)\b", dose_sentence)
        if route_match:
            route = _ROUTES[route_match.group(1).casefold()]
        indication = None
        for match in re.finditer(r"\bfor ([a-z][a-z' -]{2,40}?)(?= on| since| from| during| before| and|[.,;])", dose_sentence):
            candidate = match.group(1).strip()
            if candidate not in _NOT_INDICATIONS and not candidate.startswith(("the ", "a ", "an ", "three", "six", "two")):
                indication = candidate
                break
        start_date = None
        start_match = re.search(r"\b(?:since|from) " + _DATE, dose_sentence) or re.search(
            r"\b(?:started|initiated|began|commenced)\b[^.]*?\bon " + _DATE, dose_sentence
        )
        if start_match:
            start_date = _iso(*start_match.groups()[-3:])
        stop_date = None
        stop_match = re.search(r"(?:stopped|discontinued)[^.]*? on " + _DATE, text)
        if stop_match and role == "suspect":
            stop_date = _iso(*stop_match.groups())
        action = "unknown"
        if role == "suspect":
            if re.search(r"\b(?:withdrawn|discontinued|withheld)\b|\bstopped (?:the capsules|the tablets|VY-)|VY-\d{3} was stopped|\bshe stopped\b|\bhe stopped\b", text, re.IGNORECASE):
                action = "withdrawn"
            elif re.search(r"reduced the dose|dose was reduced", text, re.IGNORECASE):
                action = "dose_reduced"
            elif re.search(r"still taking|while (?:she|he) continued|continued VY-", text, re.IGNORECASE):
                action = "not_changed"
        results.append(
            {
                "name": code,
                "role": role,
                "dose": dose,
                "route": route,
                "indication": indication,
                "start_date": start_date,
                "stop_date": stop_date,
                "action_taken": action,
                "evidence": dose_sentence or None,
            }
        )
    return results


def _sentence_at(sentences: list[tuple[int, str]], position: int) -> tuple[int, str]:
    for start, sentence in sentences:
        if start <= position < start + len(sentence):
            return start, sentence
    return position, ""


def _onset(sentence: str, after_event: int) -> str | None:
    """Onset is a date stated after the event ("developed X on D") or leading the sentence ("On D he developed X")."""
    following = re.search(r"\b(?:on|from|since) " + _DATE, sentence[after_event:])
    if following:
        return _iso(*following.groups())
    leading = re.match(r"On " + _DATE, sentence)
    if leading:
        return _iso(*leading.groups())
    return None


def _outcome(fragment: str) -> str | None:
    if re.search(r"\b(died|death|fatal)\b", fragment, re.IGNORECASE):
        return "fatal"
    if re.search(r"sequelae", fragment, re.IGNORECASE):
        return "recovered_with_sequelae"
    if re.search(r"\b(persistent|ongoing|not recovered|still (?:has|have))\b", fragment, re.IGNORECASE):
        return "not_recovered"
    if re.search(r"\bOutcome unknown\b", fragment, re.IGNORECASE):
        return "unknown"
    if re.search(r"\b(recovered|resolved|settled|was controlled|discharged)\b", fragment, re.IGNORECASE):
        return "recovered"
    if re.search(r"\b(recovering|improved|improving|feeling better)\b", fragment, re.IGNORECASE):
        return "recovering"
    return None


def _reactions(text: str) -> list[dict[str, Any]]:
    sentences = _sentences(text)
    global_outcome = None
    for _start, sentence in sentences:
        candidate = _outcome(sentence)
        if candidate == "fatal":
            global_outcome = candidate
            break
        global_outcome = global_outcome or candidate
    case_level = _serious_signals(text) - {"other_medically_important"}
    # One reaction per lexicon entry: "rash" in the title and "widespread
    # maculopapular rash" in the abstract are the same event.
    grouped: dict[int, list[tuple[re.Match[str], int, str]]] = {}
    for index, match in _event_matches(text):
        start, sentence = _sentence_at(sentences, match.start())
        lowered = sentence.casefold()
        if "history of" in lowered and match.start() - start > lowered.index("history of"):
            continue  # a past condition, not an event
        grouped.setdefault(index, []).append((match, start, sentence))
    results: list[dict[str, Any]] = []
    for index, mentions in grouped.items():
        match, _start, sentence = max(mentions, key=lambda item: (len(item[0].group(0)), item[0].start()))
        outcome = _outcome(sentence) or next(
            (found for _m, _s, other in mentions if (found := _outcome(other))), None
        ) or global_outcome or "unknown"
        criteria: set[str] = set()
        for _m, _s, other in mentions:
            if "life_threatening" in case_level and re.search(r"life-threatening", other, re.IGNORECASE):
                criteria.add("life_threatening")
            if _HOSPITAL.search(other) and not _HOSPITAL_NEGATED.search(other):
                criteria.add("hospitalisation")
        if outcome == "fatal":
            criteria.add("death")
        if _EVENTS[index][1]:
            criteria.add("other_medically_important")
        onset = next((found for m, s, other in mentions if (found := _onset(other, m.end() - s))), None)
        results.append(
            {
                "verbatim": match.group(0).strip(),
                "onset_date": onset,
                "outcome": outcome,
                "serious_criteria": sorted(criteria),
                "evidence": sentence,
            }
        )
    results.sort(key=lambda item: text.find(item["evidence"]))
    # A hospitalisation reported in a sentence without an event belongs to the
    # event described just before it.
    if results and "hospitalisation" in case_level and not any("hospitalisation" in r["serious_criteria"] for r in results):
        results[0]["serious_criteria"] = sorted({*results[0]["serious_criteria"], "hospitalisation"})
    if results and "life_threatening" in case_level and not any("life_threatening" in r["serious_criteria"] for r in results):
        results[0]["serious_criteria"] = sorted({*results[0]["serious_criteria"], "life_threatening"})
    return results


_SITUATIONS: tuple[tuple[str, str], ...] = (
    ("pregnancy", r"[^.]*\bpregnan(?:t|cy)\b[^.]*"),
    ("breastfeeding", r"[^.]*\bbreast-?feeding\b[^.]*"),
    ("overdose", r"[^.]*\b(?:overdose|took \d+ (?:capsules|tablets))\b[^.]*"),
    ("abuse_misuse", r"[^.]*\b(?:misuse|abuse|recreational use)\b[^.]*"),
    ("off_label", r"[^.]*\b(?:off-label|not approved for)\b[^.]*"),
    ("medication_error", r"[^.]*\b(?:medication error|dispensing error|wrong (?:dose|drug|patient))\b[^.]*"),
    ("occupational_exposure", r"[^.]*\boccupational exposure\b[^.]*"),
    ("lack_of_efficacy", r"[^.]*\b(?:lack of efficacy|remained uncontrolled despite|did not respond)\b[^.]*"),
)


def extract(source_text: str, context: dict[str, Any]) -> dict[str, Any]:
    channel = context.get("channel", "")
    patient = _patient(source_text)
    reporter = _reporter(source_text, context)
    products = _products(source_text, context)
    reactions = _reactions(source_text)
    situations = []
    for kind, pattern in _SITUATIONS:
        match = re.search(pattern, source_text, re.IGNORECASE)
        if match:
            situations.append({"kind": kind, "evidence": match.group(0).strip()})
    history = []
    for match in re.finditer(r"history of ([a-z0-9 '-]+?)(?=[.;,]| and was| who)", source_text, re.IGNORECASE):
        history.append(match.group(1).strip())
    for match in re.finditer(r"\b(?:man|woman|patient) with ([a-z0-9 '-]{3,40}?) (?:received|was|who|started)", source_text):
        history.append(match.group(1).strip())

    suspect = next((p for p in products if p["role"] == "suspect"), None)
    outcomes = {r["outcome"] for r in reactions}
    if suspect is None or suspect["action_taken"] in {"unknown"}:
        dechallenge = "unknown"
    elif suspect["action_taken"] != "withdrawn":
        dechallenge = "not_applicable"
    elif outcomes & {"recovered", "recovering"}:
        dechallenge = "positive"
    elif outcomes & {"not_recovered"}:
        dechallenge = "negative"
    else:
        dechallenge = "unknown"

    if channel == "literature":
        report_type = "literature"
    elif re.search(r"\b(clinical trial|study participant)\b", source_text, re.IGNORECASE):
        report_type = "study"
    else:
        report_type = "spontaneous"
    first_event = reactions[0]["evidence"] if reactions else source_text.strip().split("\n", 1)[0]
    return {
        "report_type": report_type,
        "patient": patient,
        "reporter": reporter,
        "products": products,
        "reactions": reactions,
        "special_situations": situations,
        "medical_history": history,
        "dechallenge": dechallenge,
        "rechallenge": "unknown",
        "summary": first_event[:300],
    }


# ---------------------------------------------------------------------------
# Narrative and report drafting
# ---------------------------------------------------------------------------

_QUALIFICATION_TEXT = {
    "physician": "a physician",
    "pharmacist": "a pharmacist",
    "other_health_professional": "a health professional",
    "lawyer": "a lawyer",
    "consumer": "a consumer",
    "unknown": "a reporter of unknown qualification",
}


def _join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _count(number: int, noun: str, plural: str | None = None) -> str:
    return f"{number} {noun if number == 1 else (plural or noun + 's')}"


def _product_label(product: dict[str, Any]) -> str:
    code, name = str(product.get("code") or ""), str(product.get("name") or "")
    if not name or name == code or (code and name.startswith(code)):
        return name or code
    return f"{code} ({name})" if code else name


def narrative(payload: dict[str, Any]) -> dict[str, Any]:
    case = payload.get("case_data", {})
    patient = case.get("patient", {})
    reporter = case.get("reporter", {})
    parts = []
    if case.get("report_type") == "literature":
        parts.append(f"This literature case was identified in a published article ({case.get('literature_reference') or 'reference not reported'}).")
    else:
        where = f" in {reporter['country']}" if reporter.get("country") else ""
        parts.append(f"This spontaneous report was received from {_QUALIFICATION_TEXT.get(reporter.get('qualification', 'unknown'))}{where}.")
    age = patient.get("age_value")
    age_text = f"{int(age) if float(age).is_integer() else age}-{(patient.get('age_unit') or 'years')[:-1]}-old " if age is not None else ""
    sex = patient.get("sex") if patient.get("sex") in {"female", "male"} else ""
    subject = f"a {age_text}{sex} patient".replace("  ", " ") if (age_text or sex) else "a patient of unreported age and sex"
    history = case.get("medical_history") or []
    parts.append(f"The case concerns {subject}" + (f" with a history of {_join(history)}." if history else "."))
    if patient.get("pregnant"):
        parts.append("The patient was pregnant at the time of exposure.")
    for product in case.get("products", []):
        if product.get("role") != "suspect":
            continue
        sentence = f"The patient received {product.get('name')}"
        if product.get("dose"):
            sentence += f" {product['dose']}"
        if product.get("route"):
            sentence += f" by the {product['route']} route"
        if product.get("indication"):
            sentence += f" for {product['indication']}"
        if product.get("start_date"):
            sentence += f" from {product['start_date']}"
        parts.append(sentence + ".")
    concomitant = [p.get("name") for p in case.get("products", []) if p.get("role") == "concomitant"]
    if concomitant:
        parts.append(f"Concomitant medication: {_join(concomitant)}.")
    for reaction in case.get("reactions", []):
        onset = f" on {reaction['onset_date']}" if reaction.get("onset_date") else ""
        parts.append(f"The patient experienced an event reported as “{reaction.get('verbatim')}”{onset}.")
    criteria = sorted({c for r in case.get("reactions", []) for c in r.get("serious_criteria", [])})
    if criteria:
        parts.append("Seriousness criteria reported: " + _join([c.replace("_", " ") for c in criteria]) + ".")
    else:
        parts.append("No seriousness criterion was reported.")
    actions = {p.get("action_taken") for p in case.get("products", []) if p.get("role") == "suspect"}
    if "withdrawn" in actions:
        parts.append("The suspect product was withdrawn.")
    elif "dose_reduced" in actions:
        parts.append("The dose of the suspect product was reduced.")
    elif "not_changed" in actions:
        parts.append("The suspect product was continued unchanged.")
    outcomes = sorted({r.get("outcome", "unknown").replace("_", " ") for r in case.get("reactions", [])})
    if outcomes:
        parts.append(f"Outcome at the time of the report: {_join(outcomes)}.")
    if case.get("dechallenge") == "positive":
        parts.append("Dechallenge was positive.")
    evidence = payload.get("evidence_quotes") or []
    return {"narrative": " ".join(parts), "citations": evidence[:12]}


def report_section(payload: dict[str, Any]) -> dict[str, Any]:
    key = payload.get("section_key")
    data = payload.get("data", {})
    stats = data.get("stats", {})
    product = data.get("product", {})
    interval = f"{data.get('interval_start')} to {data.get('data_lock_point')}"
    cases = [str(number) for number in data.get("case_numbers", [])]
    if key in {"introduction"}:
        text = (
            f"This periodic report covers {_product_label(product)} for the reporting interval "
            f"{interval}, which ends at the data lock point. It summarises individual case safety reports that were "
            "medically reviewed and approved in the interval, and the literature screened by the safety team. "
            "Sections marked as requiring input need information from the marketing authorisation holder."
        )
        return {"text": text, "citations": []}
    if key in {"summary_tabulations", "pader_narrative"}:
        top = data.get("top_events", [])
        top_text = _join([f"{row['term']} ({row['interval']})" for row in top[:3]])
        expedited = data.get("expedited_cases", [])
        included = int(stats.get("interval_cases", 0))
        cumulative = int(stats.get("cumulative_cases", 0))
        text = (
            f"During the interval {interval}, {_count(included, 'case')} {'was' if included == 1 else 'were'} included: "
            f"{stats.get('interval_serious', 0)} serious and {stats.get('interval_non_serious', 0)} non-serious. "
            f"Cumulatively, {_count(cumulative, 'case')} {'has' if cumulative == 1 else 'have'} been included up to the data lock point. "
            + (
                f"The most frequently reported events in the interval were {top_text}."
                if top_text
                else "No events were reported in the interval."
            )
        )
        if expedited:
            text += (
                f" Serious unexpected cases in the interval: {_join(expedited)}. "
                "The safety physician should confirm whether each was submitted within the expedited timeline."
            )
        if stats.get("pending_cases"):
            pending = int(stats["pending_cases"])
            text += (
                f" A further {_count(pending, 'case')} received in the interval {'was' if pending == 1 else 'were'} "
                "still in processing and not included."
            )
        return {"text": text, "citations": sorted(set(cases + expedited))}
    if key == "literature":
        valid = data.get("literature_valid", [])
        info = data.get("literature_information", [])
        text = (
            f"The safety team screened {_count(int(stats.get('literature_screened', 0)), 'article')} in the interval. "
            f"{len(valid)} contained a valid individual case"
            + (f" ({_join(valid)})" if valid else "")
            + f" and {len(info)} contained other safety information"
            + (f" ({_join(info)})" if info else "")
            + ". Each case from the literature is included in the line listing."
        )
        return {"text": text, "citations": valid + info}
    if key in {"conclusions"}:
        expedited = data.get("expedited_cases", [])
        text = (
            "This draft does not reach a benefit-risk conclusion. "
            + (
                f"The safety physician and the QPPV should assess whether the serious unexpected cases ({_join(expedited)}) "
                "indicate a new or changed risk before sign-off."
                if expedited
                else "No serious unexpected case was included in the interval; the safety physician and the QPPV should confirm "
                "that no new or changed risk was identified before sign-off."
            )
        )
        return {"text": text, "citations": expedited}
    return {"text": "Input required from the safety team.", "citations": []}
