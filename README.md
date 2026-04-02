cat > README.md << 'EOF'

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
postman collection run postman/Fintech_Integration_Starter_Kit.postman_collection.json \
  --environment postman/local.postman_environment.json
```