# tam-fintech-playbook

Hands-on portfolio to become a Technical Account Manager (fintech/accounting + integrations).

## Repo structure

- `postman/`: Postman collections and environments
- `services/`: demo services (webhook receiver, trace, etc.)
- `sql/`: reconciliation datasets + queries
- `runbooks/`: incident playbooks
- `docs/`: templates (RCA, QBR, success plans) + notes

## Quickstart: webhook receiver (Python)

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --index-url https://pypi.org/simple -r services/webhook_receiver/requirements.txt

## Common failures (Week 1)
- Auth / permissions:
  - `401 vs 403`: `docs/foundations/http_debugging_notes.md`
  - Error drills: see Postman folder `Error Drills`
- Payload / contract:
  - `400 vs 422`: `docs/foundations/http_debugging_notes.md`
  - Error patterns: `docs/foundations/api_error_patterns.md`
- Missing records:
  - Checklist: `docs/foundations/missing_records_checklist.md`
- Rate limits:
  - Playbook: `docs/foundations/rate_limit_playbook.md`
```


## Running Tests via CLI

Start the service (runs on `http://127.0.0.1:5001`):
```bash
python services/webhook_receiver/app.py
```

Run the collection:
```bash
postman collection run "postman/Fintech Integration Starter Kit.postman_collection.json" \
  --environment postman/local.postman_environment.json
```

## CI — GitHub Actions

Tests run automatically on every push to `main`.

[![Postman Tests](https://github.com/fgomensoro/tam-fintech-playbook/actions/workflows/postman-tests.yml/badge.svg)](https://github.com/fgomensoro/tam-fintech-playbook/actions/workflows/postman-tests.yml)


## Week 1 — HTTP + Postman Foundations

- `docs/foundations/` — HTTP debugging notes, error patterns, missing records checklist, rate limit playbook
- `docs/http_postman_interview_pack.md` — 10 interview Q&A pairs
- Postman collection: Fintech Integration Starter Kit with error drills

## Week 2 — Postman Pro + CLI + CI

- GitHub Actions pipeline running collection on every push
- CLI command documented in README
- 35 assertions, 0 failures

## Week 3 — OAuth 2.0 Troubleshooting

- `docs/oauth_for_tams.md` — OAuth concepts, flows, and troubleshooting guide for TAMs
- `runbooks/auth_failing.md` — Auth incident runbook with diagnosis tree and customer messages
- `docs/ai_playbooks/auth_triage_prompt.md` — AI prompt template for auth triage
- Postman collection updated with OAuth 2.0 flows, error drills, and JWT assertions (53 assertions, 0 failures)