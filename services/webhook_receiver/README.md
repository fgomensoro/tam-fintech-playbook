# Webhook Receiver

A Stripe-style webhook ingestion service with HMAC signature verification, persistent dedup queue, and async worker for processing events.

Built to demonstrate the **golden architecture pattern** for production webhooks: the receiver verifies and queues fast, the worker processes async.

## What it does

The service has two processes:

1. **Receiver (`app.py`)** — Flask app on port 5001. Accepts webhooks at `/webhook/stripe`, verifies HMAC signature + timestamp, persists to SQLite queue with `status='pending'`, returns 200 in <100ms.

2. **Worker (`worker.py`)** — Standalone process. Polls the queue every 1s, atomically claims pending events using SQL `UPDATE ... WHERE status='pending'`, processes them, writes results to `business_events` table.

The split prevents Stripe timeouts during heavy processing and demonstrates the pattern used by production systems (Sidekiq, Celery, RQ, AWS SQS + Lambda).

## How to run

Requires `just` (`brew install just`) and Python 3.11+.

```bash
just dev          # runs receiver + worker in parallel (Ctrl+C stops both)
just receiver     # only the Flask receiver
just worker       # only the async worker
just test         # runs the Postman collection against the local service
```

## How to test

Send a valid signed webhook:

```bash
just test
```

Inspect the queue and the processed events:

```bash
sqlite3 webhook_events.db
```

Inside SQLite:

```sql
-- The queue: incoming events, their state, retry attempts
SELECT event_id, status, attempts FROM processed_events;

-- The output: events successfully processed by the worker
SELECT event_id, worker_id, processing_duration_ms FROM business_events;
```

You should see all events in `status='processed'` with a corresponding row in `business_events`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/webhook/stripe` | Production endpoint — verifies signature, queues event |
| `POST` | `/webhook/stripe/simulate-500` | Simulates endpoint crash (always returns 500) |
| `POST` | `/webhook/stripe/simulate-slow` | Sleeps 12s — triggers Stripe timeout retry |
| `POST` | `/webhook/stripe/simulate-wrong-secret` | Verifies with wrong secret — always 401 |
| `POST` | `/oauth/token` | OAuth 2.0 token endpoint (client credentials + auth code with PKCE) |
| `GET` | `/oauth/authorize` | OAuth 2.0 authorize endpoint with PKCE support |
| `GET` | `/items` | Protected resource (requires Bearer token with valid scope) |
| `POST` | `/items` | Create an item (requires `write:items` scope) |

## Architecture

```
Stripe                Receiver              SQLite Queue          Worker
  │                      │                      │                   │
  │ POST /webhook/stripe │                      │                   │
  ├─────────────────────►│                      │                   │
  │                      │ verify signature     │                   │
  │                      │ check timestamp      │                   │
  │                      │ INSERT pending       │                   │
  │                      ├─────────────────────►│                   │
  │ 200 OK (queued)      │                      │                   │
  │◄─────────────────────┤                      │                   │
  │                      │                      │                   │
  │                      │                      │ poll every 1s     │
  │                      │                      │◄──────────────────┤
  │                      │                      │ claim atomic      │
  │                      │                      │ UPDATE pending→   │
  │                      │                      │   processing      │
  │                      │                      │◄──────────────────┤
  │                      │                      │                   │
  │                      │                      │ process event     │
  │                      │                      │ INSERT into       │
  │                      │                      │   business_events │
  │                      │                      │                   │
  │                      │                      │ UPDATE processing │
  │                      │                      │   →processed      │
```

### Why two processes

Stripe's webhook timeout is ~10 seconds. If processing (DB writes, external API calls, emails) is done synchronously in the request handler, slow operations cause timeouts → Stripe retries → duplicate processing.

The receiver does only what's cheap and fast (verify + queue). The worker does the slow business logic separately. Stripe always sees a fast 200.

### Why SQLite as a queue

For a portfolio project, SQLite is sufficient: persistent, race-safe writes (`INSERT OR IGNORE`), atomic claims via `UPDATE ... WHERE status='pending'`. Production would use Postgres, Redis Streams, RabbitMQ, or AWS SQS.

The pattern is identical regardless of storage: **claim atomically, process, mark done, recover stuck events after a timeout**.

### State machine

Events in `processed_events` move through three states:

```
pending → processing → processed
   ▲          │
   └──────────┘
   (retry on failure or worker crash)
```

If a worker crashes mid-processing, the event stays in `processing` indefinitely. The worker's claim query reclaims any event stuck in `processing` for more than 5 minutes:

```sql
UPDATE processed_events
SET status = 'processing', claimed_at = datetime('now')
WHERE status = 'pending'
   OR (status = 'processing' AND claimed_at < datetime('now', '-5 minutes'))
```

## Troubleshooting

### "Address already in use" on port 5001

Another process is using port 5001 — most often a previous run that didn't shut down cleanly. Find and kill it:

```bash
lsof -i :5001
kill -9 <PID>
```

Then `just dev` again.

### Worker arranca pero los eventos quedan en `pending`

Two likely causes:

1. **The `business_events` table doesn't exist yet** — the worker creates it on startup via `init_business_table()`. If it failed (permission denied on the DB file, disk full), the worker logs an error and skips processing. Check terminal output.

2. **The worker is running against a different DB file** — check `DB_PATH` env var. Both Flask and the worker must point to the same SQLite file. By default both use `webhook_events.db` in the working directory.

### `signature_mismatch` from Postman

Two common causes:

1. **`WEBHOOK_SECRET` mismatch** — the value in `app.py` config must match what's used in the Postman pre-request script. Default for both is `whsec_test_secret`.

2. **The signature is being computed against the wrong payload** — the signed payload is `timestamp + "." + raw_body`. If the script changes the body order or whitespace between signing and sending, the bytes differ → mismatch.

Verify by adding `console.log(timestamp, body, signature)` in the pre-request and matching against the server-side computation.

### `business_events` is empty after sending events

The receiver returned 200, but the worker hasn't processed yet. Check:

1. **Is the worker running?** `ps -ef | grep worker.py` — confirm there's a process.
2. **Is it polling but failing?** Check terminal output for `[worker ...] FAILED` lines with stack traces.
3. **Are the events still in `processed_events`?** Run `SELECT event_id, status, last_error FROM processed_events WHERE status != 'processed'`. Anything in `pending` or `processing` shows what's stuck and why.

If `last_error` is set, the worker tried to process but failed. The event will be retried on the next poll cycle.

## Configuration

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `WEBHOOK_SECRET` | `whsec_test_secret` | HMAC signing secret for `/webhook/stripe` |
| `OAUTH_CLIENT_ID` | `test-client` | OAuth client identifier |
| `OAUTH_CLIENT_SECRET` | `test-secret` | OAuth client secret |
| `JWT_SECRET` | `dev-secret-key` | Secret for signing JWT access tokens |
| `DB_PATH` | `webhook_events.db` | SQLite database file path |
| `WORKER_ID` | `<hostname>-<pid>` | Identifier written into `business_events.worker_id` |

## Dependencies

- **Flask 3.0.2** — HTTP server for the receiver
- **PyJWT 2.8.0** — JWT encoding/decoding for OAuth tokens
- **SQLite** (stdlib) — persistent queue and result store
- **gunicorn 21.2.0** — production WSGI (not used in `just dev`)

## Related docs

- [Webhook Triage Playbook](../../docs/ai_playbooks/webhook_triage.md)
- [Webhook Failures Runbook](../../runbooks/webhook_failures.md)
- [Webhook Troubleshooting Guide](../../docs/webhook_troubleshooting_guide.md)