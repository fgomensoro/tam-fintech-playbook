# Webhook Failures — Incident Runbook

> [!tip] When to use this runbook
> A customer reports a webhook issue. Identify the specific failure type and follow the matching runbook. Each one has: symptoms, evidence to collect, diagnosis steps, fix, and customer message templates.

## Quick identification

| Customer says | Runbook |
|---|---|
| "Webhooks aren't arriving" / "Events missing" | [Runbook 1: Webhook not received](#runbook-1-webhook-not-received) |
| "Getting 401 on every webhook" / "Signature errors" | [Runbook 2: Signature verification failed](#runbook-2-signature-verification-failed) |
| "Getting charged twice" / "Duplicate emails/actions" | [Runbook 3: Duplicate events](#runbook-3-duplicate-events) |
| "Events in wrong order" / "State is inconsistent" | [Runbook 4: Events out of order](#runbook-4-events-arriving-out-of-order) |

---

## Runbook 1: Webhook not received

### Symptoms
- Customer says webhook events aren't being processed
- Nothing in application logs for expected events
- Data is missing or stale in customer's system

### Evidence to collect (first 5 minutes)

- [ ] **Provider dashboard view** — screenshot of webhook endpoint showing recent deliveries
- [ ] **Delivery status** — are attempts shown? What status code does the provider see?
- [ ] **Endpoint URL configured** — exact URL in the provider dashboard
- [ ] **Timestamp of last successful delivery** — when did it stop?
- [ ] **Recent changes** — deploys, DNS changes, firewall updates, cert renewals
- [ ] **Environment** — test or live? Right secret loaded?

### Diagnosis tree

```
Does the dashboard show delivery attempts?
├── NO attempts shown
│   ├── Endpoint URL correct? → check for typos, old DNS
│   ├── DNS resolving? → dig endpoint.example.com
│   ├── HTTPS cert valid? → openssl s_client -connect host:443
│   ├── Firewall blocking provider IPs? → check security groups
│   └── Provider status page? → status.stripe.com
│
├── YES, attempts shown as "failed" (non-2xx)
│   ├── What status code? → see dedicated runbooks below
│   ├── 500 → application crash, check server logs
│   ├── 401 → runbook 2 (signature)
│   ├── 404 → endpoint URL wrong
│   └── 502/503/504 → infrastructure issue
│
├── YES, attempts shown as "timed out"
│   ├── Processing synchronous? → refactor to async
│   ├── Downstream dependency slow? → identify bottleneck
│   └── Endpoint under heavy load? → scale up or rate limit
│
└── YES, attempts shown as "delivered" (2xx)
    └── Problem is AFTER delivery → processing logic, not webhook
        ├── Background worker running? → check worker logs
        ├── Events in dedup table but not processed? → worker bug
        └── Event filtering misconfigured? → check event type filters
```

### Fix by root cause

| Root cause | Fix |
|---|---|
| DNS not resolving | Update DNS records, wait for propagation |
| Firewall blocking | Whitelist provider IP ranges |
| Cert expired | Renew + configure auto-renewal |
| Endpoint URL wrong | Update in provider dashboard |
| Sync processing | Refactor to async (return 200 fast, process in worker) |
| Processing error | Fix the bug, provider will retry automatically |

### Customer message templates

**Short (Slack):**
```
🟡 [Customer] — Webhook delivery failing. [Count] events affected.
Root cause: [firewall/DNS/timeout/etc]. Customer's team fixing. ETA: [time].
```

**Normal (email):**
```
Hi [Name],

We've investigated the missing webhook events on your [endpoint URL].

Root cause: [specific cause based on evidence].

To resolve:
1. [action item with owner]
2. [action item with owner]

Once fixed, [provider] will automatically retry failed events from the past 3 days — no manual replay needed.

I'll verify delivery once the changes are in place.

Best,
[Your name]
```

---

## Runbook 2: Signature verification failed

### Symptoms
- All webhook requests returning 401
- Endpoint logs show "signature mismatch" or "invalid signature"
- Started after: secret rotation, deploy, environment change

### Evidence to collect

- [ ] **Signing secret currently in app config** — first 8 chars only, don't share the full value
- [ ] **Signing secret in provider dashboard** — confirm it matches
- [ ] **When was the secret last rotated?**
- [ ] **Raw body verification** — is the code using raw bytes or parsed JSON?
- [ ] **Timestamp tolerance** — is the check too strict (<5 min)?
- [ ] **Framework/middleware** — any body parsing happening before verification?

### Diagnosis tree

```
Signature fails on every request?
├── YES
│   ├── Secret recently rotated? → sync app config with dashboard
│   ├── Wrong environment secret? → test secret in prod or vice versa
│   ├── Framework parsing body first? → use raw body middleware
│   ├── Encoding mismatch? → hex vs base64url vs base64
│   └── Wrong algorithm? → should be HMAC-SHA256 for Stripe
│
└── Signature fails intermittently?
    ├── Clock skew? → sync NTP on all servers
    ├── Load balancer modifying body? → check for proxies
    ├── Multi-worker config drift? → one worker has old secret
    └── Secret rotation in progress? → provider supports dual secrets briefly
```

### Fix by root cause

| Root cause | Fix |
|---|---|
| Wrong secret in app | Update env var with correct secret from dashboard |
| Parsed JSON instead of raw body | Use `request.get_data(as_text=False)` (Flask) or `express.raw()` middleware (Express) |
| Stale worker | Restart all workers after secret rotation |
| Clock skew | Sync NTP, add 5min leeway to timestamp check |
| Wrong algorithm | Confirm HMAC-SHA256 (hex-encoded) for Stripe |

### Customer message templates

**Short (Slack):**
```
🟡 [Customer] — All webhooks failing signature check since [time].
Root cause: [secret rotation/body parsing/wrong env].
Fix in progress. ETA: [time].
```

**Normal (email):**
```
Hi [Name],

Your webhook endpoint is returning 401 on all events since [timestamp].

Root cause: the signing secret used for verification doesn't match what [provider] is using.

[If secret rotation]: Your team rotated the signing secret in the dashboard, but the new value hasn't been deployed to your application config.

To fix:
1. Copy the current signing secret from [provider] Dashboard → Webhooks → [endpoint]
2. Update `WEBHOOK_SECRET` (or equivalent) in your application environment
3. Deploy and restart workers

Note: During rotation, [provider] may send signatures signed with both old and new secrets. Once deployed, retry will pick up failed events automatically.

Best,
[Your name]
```

---

## Runbook 3: Duplicate events

### Symptoms
- Customer reports: charged twice, sent 2 emails, inventory decremented twice
- Database shows duplicate rows with same event_id
- Processing logs show same event_id multiple times

### Evidence to collect

- [ ] **Event IDs affected** — get at least 3 specific examples
- [ ] **Is deduplication implemented?** — check code
- [ ] **What does the endpoint return for duplicates?** — 200 or something else?
- [ ] **Where is the dedup check?** — before or after processing?
- [ ] **Dedup storage** — in-memory, SQLite, Redis, distributed?
- [ ] **Multiple workers?** — are they racing on the same event?

### Diagnosis tree

```
Same event_id processed multiple times?
├── No dedup implemented
│   └── Add dedup using event_id as primary key
│
├── Dedup exists but still duplicating
│   ├── Returns 409 for duplicates? → provider retries indefinitely
│   ├── Dedup check AFTER processing? → crash window = duplicates
│   ├── Race condition across workers? → use DB-level unique constraint
│   └── In-memory dedup lost on restart? → migrate to persistent store
│
└── Duplicates only for specific event types
    └── Specific handler not idempotent? → fix the handler
```

### Fix by root cause

| Root cause | Fix |
|---|---|
| No dedup | Add `INSERT OR IGNORE` on event_id with unique constraint |
| Returns 409 for duplicates | Change to 200 (Stripe reads non-2xx as failure → retries) |
| Dedup after processing | Move dedup check to BEFORE processing (check → insert → process) |
| Race condition | Use DB primary key or `INSERT OR IGNORE`, not in-memory Set |
| In-memory only | Migrate to SQLite/Postgres/Redis |

### Customer message templates

**Short (Slack):**
```
🟡 [Customer] — Duplicate event processing. Root cause: [returning 409/no dedup/race condition].
Customer updating endpoint to [fix]. ETA: [time].
```

**Normal (email):**
```
Hi [Name],

We've identified why your system is processing webhook events multiple times.

Root cause: [specific cause].

[If returning 409]: Your endpoint returns 409 (Conflict) for duplicate event_ids. However, [provider] interprets any non-2xx response as a delivery failure and retries for up to 3 days. This creates a retry loop where every retry is also marked as duplicate → 409 → retry.

Fix:
1. When detecting a duplicate event_id, return 200 (not 409)
2. The event was already processed — from the provider's perspective, that's success
3. Keep the dedup logic intact — just change the status code

This will stop the retry cycle immediately. Events currently queued for retry will resolve on their next attempt.

Best,
[Your name]
```

---

## Runbook 4: Events arriving out of order

### Symptoms
- State inconsistency between customer's DB and provider
- `invoice.paid` logged before `invoice.created`
- `customer.deleted` processed before `customer.created` exists
- Reconciliation shows discrepancies

### Evidence to collect

- [ ] **Event IDs in arrival order** — what order did your endpoint receive them?
- [ ] **Event timestamps from payload** — what order did they actually happen?
- [ ] **State dependency** — does event B require event A to already be processed?
- [ ] **Current strategy** — does code assume order? Any upserts or timestamp checks?
- [ ] **Critical flows** — which business processes break when order is wrong?

### Diagnosis

==Out-of-order delivery is NOT a bug — it's the nature of at-least-once systems.==

Providers don't guarantee order. Any code that assumes ordering will eventually break.

### Fix strategies (choose based on complexity tolerance)

| Strategy | When to use | Pros | Cons |
|---|---|---|---|
| **Idempotent upserts with timestamp** | Simple CRUD, most common case | Easy to implement | Doesn't handle deletes well |
| **Fetch from API** | State must always be accurate | Simple, always correct | Extra API calls per webhook |
| **Event queue with ordering** | Complex state machines | Full control | Infrastructure complexity |
| **Event sourcing** | Financial/audit-critical | Complete history | Major refactor |

### Customer message templates

**Short (Slack):**
```
🟢 [Customer] — Out-of-order delivery is expected behavior (at-least-once).
Recommending idempotent upserts + timestamp comparison to handle it.
```

**Normal (email):**
```
Hi [Name],

Regarding the out-of-order events you've been seeing — I want to confirm this is by design, not a bug.

Webhook providers use at-least-once delivery, which prioritizes "every event gets delivered" over "events arrive in order." This means your endpoint should not depend on receive order.

Recommended approach:

1. **Idempotent upserts**: Instead of separate CREATE/UPDATE logic, use an upsert keyed by the entity ID. Same result whether events arrive in order or not.

2. **Timestamp comparison**: Every event includes a `created` timestamp in the payload. Store this as `last_event_at` in your DB. When a new event arrives:
   - If `event.created > last_event_at` → apply it
   - If `event.created < last_event_at` → skip (late arrival)

3. **For critical flows** (like payment reconciliation): consider fetching state from the API instead of trusting the webhook payload. Slower but guarantees accuracy.

I can share implementation examples for your specific event types if helpful.

Best,
[Your name]
```

---

## General validation checklist — before sending any webhook incident update

- [ ] Did I confirm whether the provider **can reach** the endpoint vs **is being rejected**?
- [ ] Did I check for **recent changes**? (deploy, secret rotation, DNS, firewall)
- [ ] Is the root cause **confirmed by evidence** or still a hypothesis?
- [ ] Did I include **specific examples** (event IDs, status codes, timestamps)?
- [ ] Are **next steps clear** with explicit ownership?
- [ ] Did I mention **automatic retry** behavior (no manual replay needed)?
- [ ] For timeouts: did I recommend **async processing**?
- [ ] For duplicates: did I recommend **200, not 409**?

## Related notes

- [[Webhooks]] — core concepts
- [[Idempotency and Deduplication]] — dedup patterns
- [[Webhook Failure Modes]] — detailed failure analysis
- [[Webhook Troubleshooting Guide]] — triage structure
- [[Webhook Triage]] — AI playbook