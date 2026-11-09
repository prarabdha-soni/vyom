# Task: Transform Vyom Black into an AI-Native Patient Safety OS with Real-World Safety Intelligence

**Website:** https://vyom-black.vercel.app/  
**Positioning reference:** https://graphsafety.ai/

## Objective

Transform the existing Vyom Black website into a premium, enterprise-grade AI-native patient safety and pharmacovigilance platform.

Use Graph Safety as inspiration for positioning and product storytelling, not as a design or content template. Preserve Vyom Black's identity, existing architecture, reusable components, and working functionality.

The website should communicate two connected capabilities:

1. **AI-Native Pharmacovigilance OS:** Help pharmaceutical companies, biotech companies, CROs, hospitals, and safety teams manage adverse-event intake, case processing, regulatory documentation, quality checks, and evidence-linked review.
2. **Live Safety Intelligence:** Help users explore real-world drug-quality incidents, official alerts, historical safety cases, product distribution evidence, and potential cross-location safety concerns.

The most compelling demonstration should show how a drug-quality concern first reported in one location can be investigated across products, batches, distributors, hospitals, and regions—without assuming that a suspected relationship is proven.

**Core message:**

The AI-native operating system for patient safety.

**Supporting message:**

Connect fragmented safety evidence. Trace products across the supply chain. Support faster, accountable safety review.

Do not claim Vyom is market-leading, regulator-approved, clinically validated, or capable of preventing adverse events unless those claims are independently established.

---

## 1. Inspect the Existing Codebase First

Before changing the website:

- Identify the framework, routing, styling system, components, assets, animations, and existing pages.
- Inspect the current homepage and relevant product pages.
- Identify reusable components and existing backend integrations.
- Locate the actual files responsible for content and navigation.
- Preserve existing functionality and working routes.
- Reuse installed libraries and avoid unnecessary dependencies.
- Do not rebuild the application from scratch.

Then implement the changes directly in the codebase.

---

## 2. Homepage: Position Vyom Clearly

### Section A — Hero

Eyebrow:

AI-NATIVE PATIENT SAFETY

Headline:

**The operating system for modern pharmacovigilance.**

Subheadline:

Turn fragmented safety data and manual workflows into connected, intelligent, and traceable safety operations.

Primary CTA: **Book a Demo**

Secondary CTA: **Explore the Platform**

Visual direction:

Create a premium dark enterprise interface preview showing a safety case, incoming reports, product-quality alerts, evidence links, review status, and an audit timeline.

The product UI should be the visual focus. Use realistic fictional records for ordinary dashboard elements and clearly labelled public-source historical records for real incidents.

### Section B — The Problem

Heading:

**Patient safety should not depend on fragmented workflows.**

Explain the operational problems:

- Safety information scattered across emails, documents, literature, spreadsheets, and disconnected systems.
- Manual case intake, transcription, duplicate checks, and medical coding.
- Repeated completeness and quality checks.
- Disconnected clinical, pharmacy, regulatory, and distribution records.
- Difficult reconstruction of product, batch, and clinical timelines.
- Limited visibility into whether a reported product-quality concern requires investigation elsewhere.

Use concise editorial layouts and restrained icons rather than generic healthcare stock imagery.

### Section C — The Platform

Heading:

**One intelligent system across the safety lifecycle.**

Introduce the following modules. Present capabilities as proposed or available according to what the codebase and actual product support.

**1. Intelligent Safety Intake**
- Ingest information from supported sources.
- Extract relevant details.
- Identify potential duplicates.
- Route records for review.

**2. Structured Case Intelligence**
- Organize patient, product, event, reporter, and supporting evidence.
- Highlight missing fields and conflicting information.
- Preserve source links.

**3. Regulatory Documentation**
- Assist with drafting and validating safety documentation.
- Support configured regional requirements.
- Keep human review and submission authorization explicit.

**4. Live Safety Intelligence**
- Explore public drug-quality alerts and historical safety incidents.
- Connect product and batch information to documented distribution records.
- Investigate potential geographic spread.
- Compare reports across locations and timelines.
- Identify evidence gaps and unresolved questions.

**5. Signal Intelligence**
- Surface potential patterns across cases, products, and locations.
- Show supporting evidence and uncertainty.
- Distinguish statistical associations from established causality.

**6. Quality & Audit**
- Track validation findings, review history, regulatory timelines, and outstanding quality issues.
- Preserve traceable changes and approval records.

Do not imply that integrations, regulatory submissions, automated monitoring, or clinical workflows are operational if they have not been implemented.

### Section D — How It Works

Heading:

**Intelligence connected by evidence. Controlled by experts.**

Show four visually connected steps:

1. **Ingest** — Bring supported safety information into a structured workflow.
2. **Connect** — Link relevant product, batch, distribution, clinical, and source records.
3. **Validate** — Highlight missing information, inconsistencies, duplicates, and uncertain relationships.
4. **Review & Act** — Let authorized professionals assess evidence, approve actions, and document decisions.

Make the workflow diagram interactive if practical.

### Section E — Why AI-Native

Heading:

**Built around the safety workflow, not bolted onto it.**

Highlight:

- Context-aware processing across connected safety records.
- Traceability from generated outputs to source evidence.
- Continuous validation throughout the workflow.
- Human review, correction, and override.
- Explainable findings and versioned audit history.
- Configurable controls for regulated environments.

Avoid promises of zero errors, perfect accuracy, guaranteed compliance, or automatic clinical decisions.

### Section F — Enterprise Trust

Heading:

**Designed for accountable safety operations.**

Show:

- Evidence-linked outputs.
- Role-based permissions.
- Traceable changes and review history.
- Configurable validation and approval workflows.
- Data protection and controlled access.
- Support for customer validation and applicable regulatory requirements.

Do not fabricate certifications, customer logos, security badges, or compliance claims.

---

## 3. Build a Product-Grade Live Safety Intelligence Dashboard

This is the key product differentiator and should be a major part of the website—not a small decorative section.

Create a premium, Bloomberg-style safety intelligence workspace with the visual quality of a serious enterprise investigation platform.

### A. Dashboard Overview

Include:

- Recently published drug-safety reports.
- Official drug-quality alerts.
- Historical drug-quality incidents.
- Product and batch investigations.
- Adverse-event reports from permitted sources.
- Literature and regulatory updates.
- Cases awaiting human review.
- Investigations with unresolved evidence gaps.

Display counts only when calculated from actual loaded records. Never invent live activity, case counts, or affected locations.

### B. Search and Filters

Support search by:

- Drug and brand name.
- Active ingredient.
- Manufacturer.
- Batch or lot number.
- Distributor or supplier.
- Hospital or institution.
- City, state, and country.
- Incident category.
- Publication date and investigation status.

Filters should include:

- Drug quality.
- Substandard or suspected counterfeit products.
- Adverse events.
- Recalls and regulatory actions.
- Literature and safety signals.
- Official alerts.
- Historical cases.
- Newly published reports.
- Verified findings versus unverified leads.

### C. Case Cards

Each case card should show:

- Product and active ingredient.
- Location and event date.
- Publication date, separately from event date.
- Manufacturer or distributor, only when verified.
- Batch details, only when supported by evidence.
- Evidence status.
- Source count and clickable source links.
- A concise explanation of why the case matters.
- A **Review Case** action.

Use clear status labels such as:

- Official alert
- Reported by media
- Historical case
- Under investigation
- Distribution verified
- Potential link — unverified
- Causality not established

These labels must accurately reflect each record's evidence status.

---

## 4. Flagship Case: Rajasthan / Kota Oxytocin Investigation, 2026

Make the reported TOCIN oxytocin quality incident the main case study in the website's product preview.

### Case details

**Title:** Rajasthan Oxytocin Quality Investigation

**Product:** TOCIN oxytocin injection, associated with Jackson Laboratories in public reporting.

**Initial location:** Kota, Rajasthan.

**Reported context:**

- Maternal deaths and severe complications were reported in Kota in May 2026.
- A tested product sample was reported to lack the required oxytocin ingredient.
- Authorities took regulatory action against the product supply chain.
- Further investigations examined distribution, clinical monitoring, and documentation.
- Subsequent reporting described additional investigations in other locations.

### Sources

- The Times of India:  
  https://timesofindia.indiatimes.com/city/jaipur/raj-bans-tocin-injection-after-sample-fails-quality-tests-3500-vials-seized-in-kota/articleshow/131313505.cms

- The Indian Express:  
  https://indianexpress.com/article/india/rajasthan-kota-spurious-oxytocin-injections-pharma-license-maternal-deaths-10758736/

- The Indian Express:  
  https://indianexpress.com/article/health-wellness/rajasthan-maternal-deaths-kota-oxytocin-probe-10773003/

### Essential evidentiary caveat

Investigations reported by The Indian Express did not establish that the ineffective oxytocin caused the maternal deaths. Reporting also described deficiencies in clinical monitoring and documentation.

Display this distinction prominently in the case interface. Do not convert an association, reported allegation, or shared investigation into a proven causal relationship.

### The product demonstration

Create a polished case-detail workspace containing:

1. Executive summary.
2. Verified facts.
3. Reported claims.
4. Unknown or unestablished findings.
5. Timeline of reports and regulatory actions.
6. Product and batch traceability.
7. Distribution evidence.
8. Geographic investigation map.
9. Clinical chronology, where supported by records.
10. Evidence gaps.
11. Source documents.
12. Suggested human-review steps.
13. Audit trail.

Add a prominent panel titled:

**How Vyom Could Support This Investigation**

Explain how Vyom could help investigators assemble available product identity, batch, distribution, storage, administration, clinical, and regulatory records into a connected evidence trail.

Clearly label this as a retrospective illustration of potential capabilities. Never claim Vyom actually detected, investigated, or prevented the historical incident.

---

## 5. Cross-City and Cross-State Traceability

Make this the most distinctive interaction within the Kota case.

A product-quality concern may require investigation beyond the city where it was first reported. However, geographic proximity, use of the same medicine, or a shared manufacturer does not prove that a location received the same affected batch.

Vyom should help users investigate those relationships with evidence.

### A. Interactive Geographic Map

Build a map showing India and, where supported, city-level details.

Display locations only when grounded in source records or clearly labelled as investigation leads.

Potential locations to investigate for the Kota case include Jaipur, Bikaner, Rampur, New Delhi, and Uttar Pradesh, but **do not automatically mark all these locations as confirmed recipients of the affected batch**.

Use distinct marker states:

- Verified batch presence.
- Reported distribution.
- Potential exposure — unverified.
- Investigation pending.
- Batch relationship not established.
- Ruled out, only where supported by evidence.

Each marker should open a detail panel with the source, date, product or batch evidence, and verification status.

Do not display invented affected-location counts or imply a confirmed cross-state outbreak without supporting evidence.

### B. Supply-Chain Relationship Graph

Create a visual graph connecting:

Manufacturer → Batch / Lot → Distributor → Wholesaler → Hospital → Administration record → Safety report.

Each relationship should show whether it is verified, reported, inferred, or unverified.

Allow users to:

- Open product and batch records.
- Inspect distribution documents.
- Compare documented quantities.
- Identify missing invoices and procurement records.
- See conflicting product or batch information.
- Trace which source supports a relationship.
- Export an evidence-linked investigation report.

Never infer batch identity from a brand name alone.

### C. Cross-Hospital Comparison

Where authorized records are available, compare:

- Drug and batch identity.
- Manufacturer and distributor.
- Administration dates.
- Clinical chronology.
- Reported symptoms and outcomes.
- Product-quality test results.
- Other medications and relevant clinical context.
- Investigation findings.

Highlight similarities, differences, and missing evidence for qualified reviewers. Do not present similar symptoms or timing as proof of a common cause.

### D. Investigation Timeline

Display a chronological timeline of:

- Initial report.
- Laboratory testing.
- Regulatory notices.
- Distribution and recall actions.
- Additional reports.
- Hospital investigation findings.
- Follow-up testing.
- Final or pending conclusions.

Every milestone must have a source or be explicitly labelled as unverified.

---

## 6. Add a Second Real Historical Case

### India — Contaminated Oral Liquid Medicines, 2025

Use the WHO medical product alert as a second case in the dashboard.

Products named in the alert:

- COLDRIF.
- Respifresh TR.
- ReLife.

Reported issue: Diethylene glycol contamination in specific products or batches.

Official source:

https://www.who.int/news/item/13-10-2025-medical-product-alert-n-5-2025--substandard-%28contaminated%29-oral-liquid-medicines

Display:

- The official WHO alert.
- Affected products and batches, exactly as specified by the source.
- Publication date.
- Reported health concerns.
- Documented regulatory actions.
- Source-backed status and unresolved information.

Never imply every batch or every product bearing a particular brand name was affected.

---

## 7. Official Drug-Quality Alert Feed

Create a separate **Official Alerts** view based on real records from the Central Drugs Standard Control Organisation (CDSCO).

Source:

https://cdsco.gov.in/opencms/opencms/en/Notifications/Alerts/

Show the actual:

- Alert title.
- Issuing authority.
- Publication date.
- Product and batch information.
- Reported quality issue.
- Regulatory action.
- Original document link.
- Last-checked timestamp, only when a real check occurred.

Use a functioning source integration where available. If live retrieval is not implemented, provide a clearly labelled historical dataset and a functional manual-import workflow.

Never populate the feed with invented official alerts or present static records as real-time monitoring.

---

## 8. AI-Assisted Investigation Panel

Inside the case-detail view, provide an AI assistant that helps users explore the evidence.

Example questions:

- Where has this batch been documented?
- Which locations have verified distribution records?
- Which reports mention the same product?
- What evidence supports this relationship?
- Which claims remain unverified?
- What documents are missing?
- What changed since the last source review?
- Which regulatory actions have been documented?

Every material answer should link to supporting evidence.

When evidence is insufficient, explicitly say the connection cannot be established.

AI may summarize records, identify inconsistencies, suggest investigation questions, and surface potential patterns. It must not independently diagnose patients, establish causality, or present an unverified hypothesis as fact.

---

## 9. Source Integrity and Data Architecture

Maintain a clear distinction between:

- **Live source monitoring:** A functioning connection that checks current sources.
- **Recently published:** A report discovered during a successful recent check.
- **Historical case:** A previously reported incident used for analysis or demonstration.
- **Hospital-integrated case:** Data received through an approved institutional integration.
- **Manual entry:** Information added by an authorized user.

Each record should preserve:

- Original source URL.
- Publication date.
- Retrieval or verification timestamp.
- Extracted statements.
- Evidence classification.
- Batch and product details, where available.
- Reviewer corrections.
- Record history.

If a source cannot be retrieved or verified, display the limitation.

Keep public-source records separate from private hospital records. Do not expose patient-identifiable information in public examples.

Do not fabricate API connections, hospital integrations, source timestamps, case IDs, batch numbers, or real-time monitoring capabilities.

---

## 10. Visual Design

Use a premium dark enterprise design consistent with Vyom Black:

- Deep navy backgrounds.
- Restrained teal accents.
- High-contrast typography.
- Carefully aligned layouts.
- Refined cards and tables.
- Clear evidence-status chips.
- Interactive geographic maps.
- Supply-chain relationship graphs.
- Source-linked timelines.
- Expandable evidence panels.
- Subtle purposeful animations.
- Responsive desktop, tablet, and mobile layouts.

The Live Safety Intelligence case-detail view should be the visual centrepiece.

Avoid generic AI landing-page patterns, excessive glowing effects, decorative charts without real data, low-contrast text, random healthcare stock images, and fabricated KPI statistics.

Use Graph Safety for positioning inspiration only. Create an original Vyom Black experience.

---

## 11. Functional Requirements

- Preserve existing routes, navigation, components, and working functionality.
- Implement working search, filters, case navigation, source links, and timeline interactions.
- Make all CTAs functional.
- Ensure responsive layouts.
- Preserve working forms and integrations.
- Add accessible labels, keyboard navigation, and focus states.
- Maintain or improve performance.
- Update page metadata and favicon references where appropriate.
- Reuse existing dependencies and architecture.
- Clearly identify demo data and incomplete capabilities.

### Homepage CTA

Primary: **Book a Demo**

Secondary: **Explore the Platform**

The demo CTA should lead to a real contact flow or existing booking destination. Do not create a fake booking success state.

---

## 12. Final Implementation Checklist

Make actual code changes rather than returning only a proposal.

Before finishing:

1. Review the existing codebase and relevant source files.
2. Implement the homepage repositioning and product dashboard.
3. Add the historical case records with source links and evidence labels.
4. Build the Kota investigation detail view and cross-location traceability interface.
5. Verify that all case claims are supported by the supplied sources.
6. Run available lint, type-check, and build commands.
7. Fix errors introduced by the changes.
8. Check responsive layouts, accessibility, navigation, and CTA destinations.
9. Identify any features that still require real integrations or production data.
10. Summarize the files changed and the remaining implementation work.

## Final Product Vision

Vyom is building an AI-native system for connected, traceable, expert-governed patient safety operations.

**Connect the evidence. Trace the product. Surface the gaps. Support faster, accountable safety review.**

Prioritize credible product storytelling, real-world case intelligence, transparent uncertainty, and an exceptional enterprise experience over unnecessary features or unsupported claims.