# Client demo script

A 25-minute walk through Vyom for a pharmacovigilance team. It uses the
fictional tenant **Demo Pharma (FICTIONAL)**: products VY-201, VY-305 and
VY-412, articles `VY-LIT-xxxx`, cases `VY-CASE-xxxx`. Every number on screen
is sample data and carries the `SAMPLE DATA` chip. Before promising anything,
check it against `CAPABILITIES.md`.

## Ground rules

- **Fictional data only.** Never show or type real patient, product or client
  data, not even "just to try it".
- **Say what produces each output.** In this demo, screening answers,
  extraction and drafts come from the **rule-based demo engine**, labelled
  `RULE-BASED`. They are not AI. In a client deployment the same steps run on
  Gemini on Vertex AI, are labelled in blue, and each decision records the
  exact model version.
- **No invented proof.** We have no customers, accuracy figures,
  certifications or results to cite. If asked, say so, and offer the pilot
  evaluation instead.
- **No other vendors by name.** Compare only with "services firms" and
  "software platforms".
- **Planned is planned.** If it is not shipped in `CAPABILITIES.md`, say
  "on the roadmap" and do not give a date unless one is agreed.

## Before the call

Pick one setup:

| | Sample workspace | Local live stack |
| --- | --- | --- |
| Where | the public site, `/login` → "Explore with sample data" | `deploy/compose.yaml` on your laptop (RUNBOOK §1) |
| Backend | none | Vyom OS with PostgreSQL |
| Changes | shown, never saved | saved; a decision really opens a case |
| Switching roles | role menu in the top bar | separate browser profiles, one per role |
| Best for | a first call, or a shaky network | a working session with the safety team |

Checklist:

- [ ] Browser window at about 1440 px wide, other tabs closed, notifications
      off.
- [ ] **Live stack:** re-seed to start clean
      (`docker compose … down -v`, `up -d`, then `--profile demo run --rm seed`).
      Sign in once with each role you will use: reviewer, physician and QPPV.
- [ ] The sample's dates are shifted to today, so the clocks read as if
      the cases arrived recently.
- [ ] Keep `CAPABILITIES.md` open for questions.

## The walk-through

### 1. Opening (1 minute)

> "Vyom covers three pharmacovigilance jobs: literature screening, case
> processing and periodic reports. All three share one evidence record.
> Machines propose and fixed rules check. People decide, and every decision
> is recorded with who made it and what it was based on."

Colour key, worth saying once:

- **blue** means AI;
- **amber** means a human or physician decision;
- **green** means verified or complete;
- **rose** means locked or overdue.

### 2. Dashboard (2 minutes), as **PV reviewer**

- **Literature triage:** 7 open articles (3 red-band, 4 yellow-band). One of
  them is escalated to the physician.
- **Cases:** 7 open, 4 of them serious, and 3 expedited candidates (serious
  and unexpected). The reporting clock shows each case's deadline, for example
  "Day 9 of 15".
- **Reports:** a PADER signed off, and a PBRER being written.
- **Model routing:** in this demo it shows `vyom-demo-rules-v1`. Point it out:
  *"This is the rule-based demo engine. In your deployment this panel lists
  the Gemini versions and calls for your tenant."*

### 3. Radar: literature screening (5 minutes)

1. Open **Radar**. Red-band articles come first. Red means likely a valid case
   or needing a physician. Yellow means needing a closer read.
2. Open **VY-LIT-0008**, bradycardia and hypotension after a VY-412
   overdose. Show:
   - the screening questions (identifiable patient, reporter, suspect drug,
     adverse event), each with an answer and a probability;
   - the highlighted evidence in the abstract;
   - the band and the versions recorded with the decision.
3. Decide **Valid ICSR**. *Live stack:* this opens a new case, with day zero
   set to today. *Sample workspace:* it shows that nothing was saved.
4. Open **VY-LIT-0003**, a seizure in a child on VY-305. It was escalated, so
   the reviewer cannot decide it. Only the **safety physician** can, after
   reading the full text. Switch role to show this.
5. Under **Decided**, show **VY-LIT-0005**, a rat study closed as not
   relevant with its reason. *"Nothing is closed silently. Auto-close is off
   unless you turn it on, and every article gets a human decision."*

### 4. Verify: case processing (6 minutes)

1. Open **Verify**. Cases are sorted by clock. Open **VY-CASE-0004**: VY-305,
   serious (hospitalisation), in medical review, "Day 9 of 15".
2. Walk through the record:
   - the source text, with evidence pointers;
   - the fields;
   - the **rules** panel. This shows validity (the four minimum criteria),
     seriousness, expectedness against VY-305's reference safety
     information ("text match — confirm"), and the clock. *"These are fixed,
     versioned rules, not a model. The same input always gives the same
     answer."*
3. Switch to **Safety physician**. Record causality and approve. Every change
   creates a new version, recording who made it and why.
4. Open **VY-CASE-0001** (approved) and its **E2B(R3) export**. *"This is a
   draft document organised by E2B(R3) data element, with a hash. Your team
   reviews it. It is not yet a gateway-ready HL7 message; that is on the
   roadmap."*
5. *Live stack, optional:* **Verify → New case**, channel *Safety email*,
   subject *Dizziness after VY-412*, and paste:

   > Dear safety team, I am a pharmacist in Nagpur, India. A 52-year-old
   > woman started VY-412 250 mg capsules by mouth for back pain on 10
   > November 2026. On 14 November 2026 she developed severe dizziness and
   > vomiting and was hospitalised overnight. She stopped the capsules and
   > recovered by 16 November 2026. Please contact me at my pharmacy for
   > follow-up.

   The demo engine extracts:
   - the patient: 52, female;
   - the reporter: a pharmacist in India;
   - VY-412 as the suspect product, withdrawn;
   - two events with hospitalisation.

   The rules then mark it valid and serious, with dizziness *expected* and
   vomiting *not expected* against VY-412's reference safety information. It
   starts a 15-day clock.

### 5. Dossier: periodic reports (5 minutes)

1. Open **Dossier → VY-PBRER-0001** (VY-201, PBRER in ICH E2C(R2) layout).
   Its progress is 12 of 20 sections complete, 2 drafts and 6 needing input.
2. Show three kinds of section:
   - **assembled**: tabulations built from approved cases and screened
     literature by rules, with no model involved;
   - **drafted**: narrative written from aggregates only, never from
     line-level patient data, with its citations and numbers checked against
     the data;
   - **input required**: company information that stays flagged until a
     person writes it.
3. As **QPPV**, show that sign-off is blocked while drafts or missing input
   remain.
4. Open **VY-PADER-0001** (VY-305, signed off). Show:
   - the signer;
   - the time;
   - the signed version;
   - the meaning statement the QPPV agreed to with a password re-entry.

### 6. Audit and settings (2 minutes)

- **Audit:** every change, decision and sign-off, newest first. Entries
  cannot be edited or deleted from the application.
- **Settings**, as tenant admin, shows:
  - members and roles;
  - the residency region (`asia-south1`);
  - which model handles which data;
  - the MedDRA licence state. Without a licence, coding stays at the system
    organ class level. With one, the client loads its own release, and Vyom
    never ships dictionary content.

### 7. Close (2 minutes)

> "In a pilot, Vyom runs in your own Google Cloud project, in your region.
> The database is private and keys are short-lived. Case data reaches a
> hosted model only with your written approval and only in your region.
> Otherwise it stays with an in-network model, or is entered by hand. We
> would start with one product's literature, measure screening against your
> own past decisions, and agree the validation approach with your QA team."

## Questions you may get

| Question | Honest answer |
| --- | --- |
| Is this AI? | Not in this demo: it is a rule-based engine, labelled as such. In your deployment, Gemini on Vertex AI proposes and rules plus people decide. |
| How accurate is the screening? | We have no validated figures to quote yet. The pilot measures it against your own historical decisions on a frozen gold set. |
| Who else uses it? | We are at the pilot stage and have no customers to cite. |
| Is it validated / GxP / Part 11 compliant? | It has the building blocks: an audit trail, versioning, and a sign-off with a meaning statement and re-authentication. Validation is done with your QA team during the pilot. We do not claim certification. |
| Where does our data live? | In your GCP project and region. See "Close" above for the model-routing rules. |
| Can it submit E2B to the authority? | Not yet. Today it produces a draft E2B(R3) data-element document for review. Gateway submission is on the roadmap. |
| Do we need a MedDRA licence? | Yes, for coding below the system organ class level. You load your own release. |
| MFA or SSO? | On the roadmap. For a pilot we can restrict access by network, with an identity-aware proxy or an IP allow-list. |
| Signal management? | The evidence graph underneath is built; signal detection screens are on the roadmap. |
| PDF or scanned forms? | On the roadmap. Today intake is pasted email, call transcript or manual entry. |
| How is this different from what we use now? | Compare with "services firms" (people-heavy, slower turnaround) or "software platforms" (heavy configuration), in general terms only. Never name a company. |
| What does it cost? | Take it offline. Do not quote numbers in the demo. |
