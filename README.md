# tam-fintech-playbook

Hands-on portfolio building toward a Technical Account Manager role in fintech and accounting integrations. Each week ships a new capability: working code, runbooks, troubleshooting guides, and customer-facing documentation.

[![Postman Tests](https://github.com/fgomensoro/tam-fintech-playbook/actions/workflows/postman-tests.yml/badge.svg)](https://github.com/fgomensoro/tam-fintech-playbook/actions/workflows/postman-tests.yml)

## Services

| Service | What it is | Docs |
|---|---|---|
| `services/webhook_receiver` | Stripe-style webhook ingestion + async worker | [README](services/webhook_receiver/README.md) |

## Quickstart

```bash
# Install dependencies
pip install -r services/webhook_receiver/requirements.txt
brew install just  # task runner

# Run everything (receiver + worker)
just dev

# Run the Postman test suite
just test
```

For service-specific setup and troubleshooting, see the README inside each service folder.

## Configuration

This project uses environment variables for all configurable values. Local development uses a `.env` file (gitignored), CI uses GitHub Secrets.

### Local setup

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env` and replace `STRIPE_SECRET_KEY` with your real Stripe test mode key from https://dashboard.stripe.com/test/apikeys.

The `justfile` automatically loads `.env` via `set dotenv-load := true`. Both the Flask app and Postman CLI receive these variables when you run `just dev` or `just test`.

### CI setup (GitHub Actions)

The workflow `.github/workflows/postman-tests.yml` reads non-sensitive defaults inline and pulls secrets from GitHub Secrets. To configure:

1. Go to your repo -> Settings -> Secrets and variables -> Actions
2. Add a new repository secret named `STRIPE_SECRET_KEY` with your test mode key

Without this secret configured, Stripe API tests will fail with 401 in CI but local development will work fine.

### Variables reference

| Variable | Purpose | Required for | Has default |
|---|---|---|---|
| `BASE_URL` | Local Flask service URL | Local + CI | Yes (`http://127.0.0.1:5001`) |
| `BEARER_TOKEN_ADMIN` | Test admin token for OAuth flows | Local + CI | Yes (`token_admin`) |
| `BEARER_TOKEN_USER` | Test user token for OAuth flows | Local + CI | Yes (`token_user`) |
| `JWT_SECRET` | JWT signing secret | Local + CI | Yes (`dev-secret-key`) |
| `OAUTH_CLIENT_ID` | Test OAuth client ID | Local + CI | Yes (`test-client`) |
| `OAUTH_CLIENT_SECRET` | Test OAuth client secret | Local + CI | Yes (`test-secret`) |
| `WEBHOOK_SECRET` | Webhook signing secret for HMAC verification | Local + CI | Yes (`whsec_test_secret`) |
| `DB_PATH` | SQLite database path | Local + CI | Yes (`webhook_events.db`) |
| `STRIPE_SECRET_KEY` | Stripe test mode API key | Stripe API tests only | **NO** -- must be configured |

## Repo structure

```
services/                    # runnable demo services
  webhook_receiver/          # Flask receiver + SQLite queue + async worker
postman/                     # Postman collections + environments
docs/
  foundations/               # core concepts: HTTP, OAuth, webhooks, errors
  ai_playbooks/              # AI prompt templates for triage and customer comms
  english_talk_tracks/       # phrase banks for customer conversations
  auth_evidence_checklist.md
  webhook_troubleshooting_guide.md
runbooks/                    # incident response playbooks
sql/                         # reconciliation datasets and queries
justfile                     # task runner: dev, test, receiver, worker
```

## Progress by week

### Week 1 — HTTP + Postman Foundations
HTTP debugging notes, error patterns, missing records checklist, rate limit playbook. Postman collection with error drills.

### Week 2 — Postman Pro + CLI + CI
GitHub Actions pipeline running the full collection on every push. Conventional commits. 35 assertions.

### Week 3 — OAuth 2.0 Troubleshooting
OAuth concepts and flows for TAMs. Auth incident runbook with diagnosis tree and customer message templates. AI triage prompt. 53 assertions.

### Week 4 — OIDC + PKCE + Edge Cases
OIDC `id_token` + `access_token` flow merged into `/oauth/token`. `/oauth/authorize` with redirect URI validation and PKCE (S256). Auth evidence checklist. AI playbook for customer auth updates.

### Week 5 — Webhooks: Receive + Verify + Process
Stripe-style webhook receiver with HMAC signature verification, replay protection (timestamp tolerance), and persistent SQLite queue. Async worker with atomic claim pattern. Webhook troubleshooting guide, failure runbook, and AI triage playbook.

### Week 6 — Stripe Data Model

Hands-on with the Stripe API: PaymentIntent, Charge, BalanceTransaction lifecycle. Refunds, payouts, balance reconciliation. Subscriptions chain (Customer, PaymentMethod, Product, Price, Subscription, Invoice). Webhook events mapping.

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(scope):`, `fix(scope):`, `docs:`, `refactor:`, `ci:`
- **Python**: 3.11+
- **Postman**: collections live in `postman/` and run in CI via Postman CLI
- **Notes**: conceptual learning notes are kept in a separate Obsidian vault. This repo holds shipped artifacts (code, docs, runbooks).