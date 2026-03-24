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