# Vyom runbook

How to run Vyom OS and the console. The local stack uses Docker Compose. A
client environment uses GKE Autopilot with Cloud SQL in the client's region.
The public marketing site and the fictional sample workspace can stay on
Vercel (see `DEPLOY.md`).

> **Status (2026-11-27).** Both images build for `arm64` and `amd64`. The
> Compose stack has run end to end with the cluster's restrictions (read-only
> root, no capabilities, non-root): migrations, the seed, every role's console
> flow, `vyom-admin` and the sweep. The manifests render with `kubectl
> kustomize`. The `gcloud` steps have **not** been run against a real project
> yet. Rehearse the whole of §2–§5 on a staging project before a client
> environment. `CAPABILITIES.md` lists what is shipped, demo-only or planned.

Contents: [0 What runs where](#0-what-runs-where) ·
[1 Local stack](#1-local-stack-docker-compose) ·
[2 GCP setup](#2-a-client-environment-on-gcp-once) ·
[3 Build a release](#3-build-and-push-a-release) ·
[4 First deploy](#4-first-deploy) · [5 Each release](#5-each-release-and-rollback) ·
[6 Clients](#6-onboarding-and-offboarding) · [7 Operating](#7-operating) ·
[8 Existing databases](#8-adopting-a-database-migrated-by-hand) ·
[9 Before a pilot](#9-before-a-client-pilot)

---

## 0. What runs where

| Piece | Image / command | Talks to |
| --- | --- | --- |
| Console (`vyom-web`) | `vyom-web`, `node server.js`, port 3000 | Vyom OS over the cluster network |
| Vyom OS API | `vyom-os`, `vyom-os-api`, port 8000 | PostgreSQL; Vertex AI and PubMed in live mode |
| Migrations | `vyom-os`, `vyom-migrate` (Job, before each release) | PostgreSQL as the owner |
| Weekly literature sweep | `vyom-os`, `vyom-weekly-sweep` (CronJob, Mondays 02:30 IST) | PostgreSQL; PubMed in live mode |
| Operator commands | `vyom-admin` (run inside the API pod) | PostgreSQL |
| PostgreSQL 16 | Cloud SQL, private IP only (Compose: `postgres:16-alpine`) | — |

Three database identities, each with one job:

- **`postgres`** owns the schema. Only `vyom-migrate` uses it.
- **`vyom_service`** bypasses row-level security. It is used for sign-in, the
  sweep, `vyom-admin` and cross-tenant operations views.
- **`vyom_app`** is subject to row-level security. Every client request runs
  as `vyom_app`, scoped to one tenant.

Migration `004` creates both application roles without passwords.
`vyom-migrate` sets their passwords from `VYOM_APP_DB_PASSWORD` and
`VYOM_SERVICE_DB_PASSWORD`, hashing them on the client side.

**Where client data lives.** Run the signed-in console for client data in GCP,
in the client's region, next to Vyom OS. That way case data never passes
through a third-party host. Vercel serves only the public site and the
fictional sample workspace, which needs no backend.

---

## 1. Local stack (Docker Compose)

For a laptop or a single demo machine. Compose publishes only the console, and
only on `127.0.0.1`. The API and the database stay on an internal network.

From the repository root:

```bash
cp deploy/.env.example deploy/.env
```

Fill every secret with a fresh random value. Nothing is printed:

```bash
(umask 077; for key in POSTGRES_PASSWORD VYOM_APP_DB_PASSWORD VYOM_SERVICE_DB_PASSWORD VYOM_SESSION_SECRET VYOM_DEMO_PASSWORD; do sed -i.bak "s/^$key=.*/$key=$(openssl rand -hex 32)/" deploy/.env; done; rm deploy/.env.bak)
```

Start PostgreSQL, run the migrations, then start the API and the console:

```bash
docker compose -f deploy/compose.yaml --env-file deploy/.env up --build -d
```

Add the fictional `demo-pharma` tenant and its sample work:

```bash
docker compose -f deploy/compose.yaml --env-file deploy/.env --profile demo run --rm seed
```

Open <http://localhost:3000/login/>. Sign in as `reviewer@demo-pharma.example`,
`physician@…`, `qppv@…`, `admin@…` or `ops@vyom-internal.example`, with the
`VYOM_DEMO_PASSWORD` from `deploy/.env`. With `VYOM_SAMPLE_WORKSPACE=on`,
`/login` also offers the sample workspace, which uses no database.

> The session cookie is `Secure`. Chrome and Firefox accept it on plain-http
> `localhost`. If sign-in returns you to `/login` in another browser, use one
> of those two. Before anyone connects from another machine, put TLS in
> front.

| Task | Command (prefix `docker compose -f deploy/compose.yaml --env-file deploy/.env`) |
| --- | --- |
| Migration status | `run --rm migrate vyom-migrate --status` |
| Run the sweep now | `--profile jobs run --rm sweep vyom-weekly-sweep --include-fictional` |
| Operator commands | `exec api vyom-admin list` |
| API logs | `logs -f api` |
| Stop (keeps data) | `down` |
| Stop and **delete the database** | `down -v` (permanent) |

The sweep skips fictional tenants unless you pass `--include-fictional`. Demo
mode sweeps only fictional tenants, from the sample articles, and never calls
PubMed. A real tenant is skipped until the deployment runs in live mode, so
sample articles never reach a client's queue.

---

## 2. A client environment on GCP (once)

One GCP project per client environment, in the client's region. The commands
use `asia-south1` (Mumbai). Run them from a machine with `gcloud`, `kubectl`
and Docker, signed in as a project owner.

```bash
export PROJECT=your-project-id REGION=asia-south1 DOMAIN=console.your-domain
gcloud config set project "$PROJECT"
```

### 2.1 APIs

```bash
gcloud services enable container.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com servicenetworking.googleapis.com compute.googleapis.com
```

### 2.2 Private network path to Cloud SQL

Cloud SQL gets a private IP on the VPC and no public IP:

```bash
gcloud compute addresses create google-managed-services-default --global --purpose=VPC_PEERING --prefix-length=16 --network=default
```

```bash
gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com --ranges=google-managed-services-default --network=default
```

### 2.3 Cloud SQL for PostgreSQL 16

Regional (HA), with point-in-time recovery. The backup time is in UTC:
20:30 UTC is 02:00 IST.

```bash
gcloud sql instances create vyom-pg --database-version=POSTGRES_16 --edition=ENTERPRISE --tier=db-custom-2-7680 --region="$REGION" --availability-type=REGIONAL --network=default --no-assign-ip --enable-point-in-time-recovery --retained-transaction-log-days=7 --backup-start-time=20:30 --storage-auto-increase --deletion-protection
```

```bash
gcloud sql databases create vyom --instance=vyom-pg
```

Set the `postgres` password. Use hex (`openssl rand -hex 32`) so it fits in a
URL unescaped, and keep it in your password manager:

```bash
gcloud sql users set-password postgres --instance=vyom-pg --prompt-for-password
```

### 2.4 GKE Autopilot

Autopilot turns on Workload Identity by default. The manifests use native
sidecars, which need Kubernetes 1.29 or later. Check the version with
`gcloud container clusters describe vyom --region "$REGION" --format='value(currentMasterVersion)'`.

```bash
gcloud container clusters create-auto vyom --region="$REGION" --release-channel=regular --enable-private-nodes
```

```bash
gcloud container clusters get-credentials vyom --region="$REGION"
```

Private nodes have no external IP. Cloud NAT gives them outbound access to
PubMed, Europe PMC and image registries outside Google, with nothing
inbound:

```bash
gcloud compute routers create vyom-nat-router --network=default --region="$REGION"
```

```bash
gcloud compute routers nats create vyom-nat --router=vyom-nat-router --region="$REGION" --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges
```

For a client pilot, also encrypt Kubernetes Secrets with a Cloud KMS key
(`--database-encryption-key`) and limit who can reach the control plane
(authorised networks).

### 2.5 Artifact Registry

```bash
gcloud artifacts repositories create vyom --repository-format=docker --location="$REGION"
```

### 2.6 Service accounts and Workload Identity

Each Kubernetes service account acts as one Google service account, and
nothing else holds a key:

| Kubernetes SA | Google SA | Roles |
| --- | --- | --- |
| `vyom-os` (API and sweep) | `vyom-os@` | `roles/cloudsql.client`, `roles/aiplatform.user` |
| `vyom-migrate` | `vyom-migrate@` | `roles/cloudsql.client` |
| `vyom-web` | none | none; no Google access, and no token is mounted |

```bash
for sa in vyom-os vyom-migrate; do gcloud iam service-accounts create "$sa"; done
```

```bash
for sa in vyom-os vyom-migrate; do gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$sa@$PROJECT.iam.gserviceaccount.com" --role=roles/cloudsql.client --condition=None; done
```

```bash
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:vyom-os@$PROJECT.iam.gserviceaccount.com" --role=roles/aiplatform.user --condition=None
```

```bash
for sa in vyom-os vyom-migrate; do gcloud iam service-accounts add-iam-policy-binding "$sa@$PROJECT.iam.gserviceaccount.com" --role=roles/iam.workloadIdentityUser --member="serviceAccount:$PROJECT.svc.id.goog[vyom/$sa]"; done
```

### 2.7 Static IP, TLS policy and DNS

```bash
gcloud compute addresses create vyom-console --global
```

```bash
gcloud compute ssl-policies create vyom-tls12-modern --profile=MODERN --min-tls-version=1.2
```

```bash
gcloud compute addresses describe vyom-console --global --format='value(address)'
```

Point an `A` record for `$DOMAIN` at that address. The Google-managed
certificate is issued only after DNS resolves, which can take up to an hour.

### 2.8 Secrets

The values live in Secret Manager, in the client's region, and are copied into
three Kubernetes Secrets. No secret is in the repository or in the manifests.

| Kubernetes Secret | Keys |
| --- | --- |
| `vyom-os-secrets` | `DATABASE_URL`, `APP_DATABASE_URL`, `VYOM_SESSION_SECRET`, optional `NCBI_API_KEY` |
| `vyom-web-secrets` | `VYOM_SESSION_SECRET` (the same value) |
| `vyom-migrate-secrets` | `MIGRATION_DATABASE_URL`, `VYOM_APP_DB_PASSWORD`, `VYOM_SERVICE_DB_PASSWORD` |

The pods reach Cloud SQL through the Auth Proxy sidecar on `127.0.0.1:5432`.
The proxy encrypts the connection, so the URLs point at localhost. This block
generates the role passwords and the session secret, stores them, and prints
nothing. Run it once, in a fresh shell:

```bash
umask 077; d=$(mktemp -d)
read -rs -p 'Cloud SQL postgres password: ' PG; echo
APP=$(openssl rand -hex 32); SVC=$(openssl rand -hex 32); SESSION=$(openssl rand -hex 32)
printf 'DATABASE_URL=postgresql://vyom_service:%s@127.0.0.1:5432/vyom\nAPP_DATABASE_URL=postgresql://vyom_app:%s@127.0.0.1:5432/vyom\nVYOM_SESSION_SECRET=%s\n' "$SVC" "$APP" "$SESSION" > "$d/os.env"
printf 'VYOM_SESSION_SECRET=%s\n' "$SESSION" > "$d/web.env"
printf 'MIGRATION_DATABASE_URL=postgresql://postgres:%s@127.0.0.1:5432/vyom\nVYOM_APP_DB_PASSWORD=%s\nVYOM_SERVICE_DB_PASSWORD=%s\n' "$PG" "$APP" "$SVC" > "$d/migrate.env"
for s in os web migrate; do gcloud secrets create "vyom-$s-env" --replication-policy=user-managed --locations="$REGION" --data-file="$d/$s.env"; done
rm -rf "$d"; unset PG APP SVC SESSION
```

Copy them into the cluster. Repeat this step after any rotation (§7.4):

```bash
kubectl apply -f deploy/k8s/overlays/production/namespace.yaml
```

```bash
for s in os web migrate; do kubectl -n vyom create secret generic "vyom-$s-secrets" --from-env-file=<(gcloud secrets versions access latest --secret="vyom-$s-env") --dry-run=client -o yaml | kubectl apply -f -; done
```

### 2.9 Vertex AI (live mode only)

Live mode sends work to Gemini on Vertex AI through the provider gateway. It
does this only as follows:

- **Public literature** always goes to the hosted model.
- **Identifiable case data** goes to the hosted model only if the tenant was
  created with `--hosted-processing` (the client's written approval) **and**
  the model's region matches the tenant's residency region.
- **Otherwise** case data goes to an in-network model (`LOCAL_LLM_BASE_URL`),
  or AI assistance is refused and the case is entered by hand.

Before you set `VYOM_AI_MODE=live`:

1. Choose current GA Gemini versions that are served in `asia-south1`.
   Confirm that neither is near its retirement date.
2. Run the gold-set evaluation on public literature.
3. Pin the exact IDs as `VERTEX_MODEL_ID` and `VERTEX_DRAFTING_MODEL_ID` in
   the production overlay. Change `VERTEX_SAMPLER_VERSION` whenever a model
   or a setting changes, so every decision records what produced it.

Live mode has not yet been exercised against Vertex.

### 2.10 Check that Cloud SQL accepts the `bypassrls` role

Migration `004` runs `create role vyom_service login bypassrls`. Cloud SQL's
`postgres` user is not a true superuser. Check that this works **before** the
first migration. The pod runs in the `default` namespace because the `vyom`
namespace only admits non-root pods. `psql` asks for the `postgres` password:

```bash
gcloud sql instances describe vyom-pg --format='value(ipAddresses[0].ipAddress)'
```

```bash
kubectl run pg-probe -n default --rm -it --restart=Never --image=postgres:16-alpine -- psql "host=PRIVATE_IP user=postgres dbname=vyom sslmode=require" -c "create role vyom_bypassrls_probe nologin bypassrls" -c "drop role vyom_bypassrls_probe"
```

If the `create role` is refused, **stop**. The fix is a schema change, such as
explicit service policies instead of `bypassrls`. Do not work around it by
loosening row-level security.

---

## 3. Build and push a release

Autopilot nodes are `amd64`, so build for that platform, including on Apple
silicon. Tag every release with the commit:

```bash
export TAG=$(git rev-parse --short=12 HEAD) REG="$REGION-docker.pkg.dev/$PROJECT/vyom"
gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

```bash
docker build --platform linux/amd64 -t "$REG/vyom-os:$TAG" vyom-os
```

`NEXT_PUBLIC_SITE_URL` is set at build time. Use the public site's address, so
the sitemap and the Open Graph links on the console host point at the public
site:

`VYOM_SAMPLE_WORKSPACE=off` at build time leaves the sample-workspace link off
the pre-rendered pages. The overlay also sets it at runtime.

```bash
docker build --platform linux/amd64 --build-arg NEXT_PUBLIC_SITE_URL=https://your-domain --build-arg VYOM_SAMPLE_WORKSPACE=off -t "$REG/vyom-web:$TAG" vyom-web
```

```bash
docker push "$REG/vyom-os:$TAG" && docker push "$REG/vyom-web:$TAG"
```

In `deploy/k8s/overlays/production/kustomization.yaml`, set both images'
`newTag` to `$TAG`. Pinning by digest is better still: replace `newTag` with
`digest: sha256:…`, taken from
`gcloud artifacts docker images describe "$REG/vyom-os:$TAG" --format='value(image_summary.digest)'`.
Commit that change, so the repository records what ran. Pin the Cloud SQL Auth
Proxy image by digest in `deploy/k8s/base/kustomization.yaml` the same way.

---

## 4. First deploy

After §2, with the production overlay's `YOUR_*` values replaced. This must
print nothing:

```bash
kubectl kustomize deploy/k8s/overlays/production | grep -nE 'YOUR_|example\.invalid|image: vyom-(os|web)$'
```

Run the migrations first. `vyom/phase=migrate` selects the namespace, the
migrate service account, its config and the Job:

```bash
kubectl apply -k deploy/k8s/overlays/production -l vyom/phase=migrate
```

```bash
kubectl -n vyom wait --for=condition=complete job/vyom-migrate --timeout=15m; kubectl -n vyom logs job/vyom-migrate -c migrate
```

The log lists `applied 002_…` to `009_…`, then `set login password for
vyom_app` and `vyom_service`. Then deploy everything else:

```bash
kubectl apply -k deploy/k8s/overlays/production
```

```bash
kubectl -n vyom rollout status deploy/vyom-os && kubectl -n vyom rollout status deploy/vyom-web
```

Create the operations tenant and your own `ops` account. The command prompts
for the password twice; use at least 12 characters:

```bash
kubectl -n vyom exec -it deploy/vyom-os -c api -- vyom-admin create-ops-tenant
```

```bash
kubectl -n vyom exec -it deploy/vyom-os -c api -- vyom-admin add-user vyom-internal you@your-domain ops
```

Check the deployment:

- `kubectl -n vyom describe managedcertificate vyom-console` shows `Active`.
- `curl -sI https://$DOMAIN/healthz/` returns `200`.
- `/login` shows no sample workspace.
- You can sign in and open `/ops`.

Never run `vyom-seed-demo` against a client database. A client environment
has no fictional tenant.

---

## 5. Each release, and rollback

1. Build and push (§3), then commit the new tag in the overlay.
2. A Job's pod template cannot change, so remove last release's Job:
   `kubectl -n vyom delete job vyom-migrate --ignore-not-found`.
3. Migrate:
   `kubectl apply -k deploy/k8s/overlays/production -l vyom/phase=migrate`,
   then the same `wait` and `logs` as in §4. When nothing is pending, the log
   says `schema is up to date`.
4. Roll out: `kubectl apply -k deploy/k8s/overlays/production`, then
   `rollout status` for both Deployments.
5. Check `/healthz/` and sign in.

**If the migration fails**, nothing in this release is live yet. Each file
runs in one transaction with its ledger row, so a failed file leaves nothing
behind. Read the log, fix the migration, and release again. Never edit a
migration that has already been applied: `vyom-migrate` refuses a changed
file. Write a new migration instead.

**Rollback.** Re-apply the previous release's overlay (check out that commit)
and skip the migrate step. The previous build's migrate Job would refuse to
run, by design, because the database has migrations that build does not. This
works only if every migration is backward compatible. Add columns and tables
in one release, and remove what the old code reads only in a later release.
To return to an earlier database state, use point-in-time recovery (§7.3).

---

## 6. Onboarding and offboarding

Run `vyom-admin` inside the API pod, for example
`kubectl -n vyom exec -it deploy/vyom-os -c api -- vyom-admin list`. Every
change is written to the tenant's audit trail as `via: vyom-admin`. Passwords
come from a prompt or stdin, never from arguments, and are never printed.

**A new client:**

1. Create the tenant. Add `--hosted-processing` only with the client's
   written approval to send identifiable case data to the hosted model
   (§2.9):
   ```bash
   kubectl -n vyom exec -it deploy/vyom-os -c api -- vyom-admin create-tenant client-slug --name "Client name" --kind mah
   ```
2. Add users. The roles are `reviewer`, `safety_physician`, `qppv` and `admin`.
   Each command prompts for the password, or reads it from stdin with
   `--password-stdin` (`kubectl exec -i`, without `-t`):
   ```bash
   kubectl -n vyom exec -it deploy/vyom-os -c api -- vyom-admin add-user client-slug person@client.example qppv
   ```
3. Add each product with its reference safety information, from a JSON
   file on your machine. The file needs `code`, `name`, `active_ingredient`,
   `rsi_version` and `reference_safety_terms` (a list). `dosage_form`,
   `strength` and `international_birth_date` (`YYYY-MM-DD`) are optional:
   ```bash
   kubectl -n vyom exec -i deploy/vyom-os -c api -- vyom-admin add-product client-slug /dev/stdin < product.json
   ```

**Someone leaves:**
`vyom-admin disable-user person@client.example`. They can no longer sign in,
and any open session stops working within 30 seconds, because each API
replica caches account status for that long.

**A client leaves:** tenant export and deletion are not built yet; see
`CAPABILITIES.md`. Until they are, disable every account and agree the
export and deletion steps in writing.

---

## 7. Operating

### 7.1 Health and logs

| Check | Healthy | Unhealthy |
| --- | --- | --- |
| API `GET /healthz` (readiness) | `200` with `database: ok` | `503`; the pod leaves the Service but is not restarted |
| Console `GET /healthz/` | `200 ok` | the load balancer stops sending traffic to that pod |
| Cloud SQL Auth Proxy `/startup` | the app containers start only after it passes | the pod waits |

The liveness probe is a TCP check on purpose, so a database outage does not
restart every pod at once. Add a Cloud Monitoring uptime check on
`https://$DOMAIN/healthz/`. Read logs with `kubectl -n vyom logs deploy/vyom-os -c api`
or in Cloud Logging.

### 7.2 The weekly literature sweep

The sweep runs every Monday at 02:30 IST for every client tenant (live mode
only; demo mode skips them). If a tenant's sweep fails, the failure is recorded
as an ops alert, visible on `/ops`, and the other tenants still run. To run it now:

```bash
kubectl -n vyom create job --from=cronjob/vyom-weekly-sweep "sweep-manual-$(date +%Y%m%d%H%M)"
```

Live sweeps identify themselves to NCBI with `NCBI_TOOL` and `NCBI_EMAIL`. Use
a team mailbox. An `NCBI_API_KEY` raises the rate limit.

### 7.3 Backups and restore

Cloud SQL takes a daily backup and keeps 7 days of transaction logs for
point-in-time recovery. A restore creates a new instance and leaves the
current one untouched:

```bash
gcloud sql instances clone vyom-pg vyom-pg-restore --point-in-time='2026-11-27T08:00:00Z'
```

Then set `CLOUDSQL_INSTANCE` to the new instance, apply the overlay, and run
`kubectl rollout restart` on both Vyom OS workloads. Rehearse a restore before
the pilot, then every quarter.

### 7.4 Rotating secrets

To rotate a secret, add a new Secret Manager version, re-run the `kubectl
create secret … | kubectl apply` loop from §2.8, then restart the affected
workloads.

| Secret | Steps | Effect |
| --- | --- | --- |
| `VYOM_SESSION_SECRET` | Change it in `vyom-os-env` **and** `vyom-web-env`, then `kubectl -n vyom rollout restart deploy/vyom-os deploy/vyom-web` | Everyone is signed out |
| `vyom_app` / `vyom_service` passwords | Change them in `vyom-migrate-env` and `vyom-os-env`, run the migrate Job (§5 steps 2–3), then restart `deploy/vyom-os` | The Job sets the new passwords even when no migration is pending. Open connections keep working until the restart |
| `postgres` password | `gcloud sql users set-password postgres …`, then update `vyom-migrate-env` | None until the next release |

### 7.5 Scaling, and what is per replica

The API runs 2 replicas and the console 2, each with a disruption budget.
These are held in each replica's memory:

- the account-status cache (30 seconds);
- the tenant cache (60 seconds);
- the sign-in throttle.

So with *n* replicas, an attacker gets *n* times the sign-in attempts. Move the
throttle to the database or to Cloud Armor before scaling out.

---

## 8. Adopting a database migrated by hand

A database set up with `psql -f migrations/…` before `vyom-migrate` existed
has the schema but no `schema_migrations` ledger. Run these from a machine
that can reach it, with an owner connection:

```bash
MIGRATION_DATABASE_URL='postgresql://owner@host:5432/vyom' vyom-migrate --status
```

First confirm by hand that the schema matches the files listed as pending.
Then record them as applied without running them:

```bash
MIGRATION_DATABASE_URL='postgresql://owner@host:5432/vyom' vyom-migrate --baseline
```

A new Cloud SQL instance never needs this.

---

## 9. Before a client pilot

Settle each of these, in writing where it involves the client:

- [ ] **Cloud SQL `bypassrls`** works (§2.10).
- [ ] **TLS location.** The global external load balancer may terminate TLS
      outside `asia-south1`. If the client requires TLS to end in-region,
      switch to the regional external Application Load Balancer (Gateway
      API, `gke-l7-regional-external-managed`).
- [ ] **Load balancer to pod traffic** is plain HTTP inside Google's network,
      and console to API is plain HTTP inside the cluster (NetworkPolicy
      allows only the console to reach the API). If the client requires
      encryption in transit end to end, add HTTPS backends or a service
      mesh.
- [ ] **Vertex models** are chosen, evaluated, served in-region and pinned
      (§2.9), and the hosted-processing approval is on file.
- [ ] **Images.** The Auth Proxy, `python:3.12-slim` and `node:22-alpine` are
      pinned by digest, and Artifact Registry vulnerability scanning is on.
- [ ] **Accounts.** There is no MFA or SSO yet: passwords only, with an 8-hour
      session. Agree that this is acceptable for the pilot, or put
      Identity-Aware Proxy or Cloud Armor (allowed IP ranges, see the
      production overlay) in front.
- [ ] **Sign-in throttle** per replica (§7.5).
- [ ] **Restore rehearsed** (§7.3).
- [ ] **Validation.** The client's computerised-system validation approach is
      agreed. E2B output is a draft for review, not a validated gateway
      submission.
- [ ] **Credentials.** Credentials ever shared outside a secret store (for
      example in chat, or in git history) have been rotated.
