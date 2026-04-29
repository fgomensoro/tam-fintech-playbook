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

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(scope):`, `fix(scope):`, `docs:`, `refactor:`, `ci:`
- **Python**: 3.11+
- **Postman**: collections live in `postman/` and run in CI via Postman CLI
- **Notes**: conceptual learning notes are kept in a separate Obsidian vault. This repo holds shipped artifacts (code, docs, runbooks).