# Sample workspace

`snapshot.json` is the fictional tenant **demo-pharma (FICTIONAL)**, captured
from a running Vyom OS seeded with `python -m vyom_os.seed --confirm-fictional`
and then worked through the real API: literature decisions, a narrative
draft, an E2B export, a signed-off PADER and a PBRER part-way through
authoring. Every product, case, article and person in it is fictional
(`VY-201`, `VY-305`, `VY-412`, `VY-CASE-xxxx`, `VY-LIT-xxxx`, `@demo-pharma.example`).

The console serves it when a visitor opens the sample workspace from /login.
Dates move forward by the days since `captured_on`, so it always reads as
current. Changes made there are not saved.

To refresh it, start a local Vyom OS on a fresh database, seed it, and run
`vyom-os/scripts/sample_workspace.py` (`enrich`, then `capture` into this
file). The script refuses any tenant that is not the fictional sample. Never
capture a real tenant, and never edit numbers here by hand.
