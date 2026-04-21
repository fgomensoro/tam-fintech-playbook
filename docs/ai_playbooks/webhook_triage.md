
# Webhook Triage — AI Playbook

> [!tip] How to use this playbook When a customer reports a webhook issue, use the prompt template below with structured inputs. Review and edit the AI output before sending — never send raw AI output to a customer.

## Prompt template

```
You are a Technical Account Manager diagnosing a webhook delivery issue.

## Inputs

Issue type: [not_received | signature_failed | duplicate_events | delayed_delivery | out_of_order | partial_payload | endpoint_disabled]

Provider: [stripe | modern_treasury | plaid | other]

Severity: [P1_critical | P2_high | P3_medium | P4_low]

Customer tier: [enterprise | growth | starter]

Customer name: [name]

Contact name: [name]

Webhook endpoint URL: [url]

Duration: [how long the issue has been ongoing]

Evidence collected so far:
- Stripe dashboard delivery status: [delivered | failed | pending | not_shown]
- Endpoint HTTP response code: [200 | 4xx | 5xx | timeout | unknown]
- Signature verification: [passing | failing | not_implemented]
- Event IDs affected: [list or "unknown"]
- Recent changes: [deploy | secret_rotation | dns_change | firewall_change | none | unknown]

## What I need

1. Most likely root cause based on the evidence
2. Additional evidence I should collect
3. Suggested fix
4. Draft customer message in [short | normal | exec] format
```

## Decision tree — quick reference

```
Customer says "webhook not arriving"
    │
    ├── Does Stripe dashboard show delivery attempts?
    │   ├── NO → Stripe can't reach endpoint
    │   │   ├── DNS resolving? → check domain
    │   │   ├── Firewall blocking Stripe IPs? → whitelist
    │   │   ├── Endpoint URL correct? → check for typos
    │   │   └── SSL cert valid? → openssl check
    │   │
    │   └── YES → Endpoint is rejecting
    │       ├── What status code?
    │       │   ├── 401 → signature verification failing
    │       │   │   ├── Wrong signing secret?
    │       │   │   ├── Using parsed JSON instead of raw body?
    │       │   │   └── Secret recently rotated?
    │       │   ├── 500 → unhandled exception in endpoint
    │       │   │   ├── Check server logs
    │       │   │   └── Payload schema changed?
    │       │   ├── 404 → endpoint URL wrong or removed
    │       │   └── Timeout → endpoint too slow
    │       │       ├── Processing sync instead of async?
    │       │       └── Downstream dependency slow?
    │       │
    │       └── Status is 200 but customer says "not processed"
    │           ├── Deduplication bug? (rejecting valid events as duplicates)
    │           ├── Event type filtering? (only listening for some events)
    │           ├── Processing error after 200 response? (async worker failing)
    │           └── Wrong environment? (test mode vs live mode)
    │
    └── Customer says "duplicate events"
        ├── Is deduplication implemented? → check event_id tracking
        ├── Are retries expected? → check if endpoint returned non-2xx
        └── Is endpoint returning 409 for duplicates? → change to 200
```

## Example outputs

### Example 1 — Webhook not received (firewall blocking)

**Inputs:**

- Issue type: not_received
- Provider: Stripe
- Customer: PayFlow Inc
- Endpoint: `https://api.payflow.com/webhooks/stripe`
- Duration: 2 hours
- Stripe dashboard: no delivery attempts shown
- Recent changes: migrated to new cloud provider yesterday

**Short (Slack):**

```
🔴 PayFlow Inc — Webhook delivery blocked since cloud migration 2h ago. Stripe dashboard shows zero delivery attempts → Stripe can't reach the endpoint. Most likely: firewall on new cloud provider not whitelisting Stripe IPs. Customer's infra team is checking security groups now. ETA: 30 min.
```

**Normal (email):**

```
Hi [Name],

We've investigated the webhook delivery issue on your endpoint https://api.payflow.com/webhooks/stripe.

Stripe's dashboard shows zero delivery attempts over the past 2 hours, which means Stripe is unable to reach your endpoint at all. Since your team migrated to a new cloud provider yesterday, the most likely cause is that the new environment's firewall or security groups are blocking inbound traffic from Stripe's IP ranges.

To resolve this, your infrastructure team should:
1. Whitelist Stripe's webhook IP ranges (listed at https://docs.stripe.com/ips)
2. Verify the endpoint is publicly accessible: `curl -X POST https://api.payflow.com/webhooks/stripe`
3. Check that DNS for api.payflow.com resolves to the new server

Once the firewall is updated, Stripe will automatically retry any failed events from the past 3 days — no manual replay needed.

I'm standing by to verify delivery once the changes are in place.

Best,
[Your name]
```

### Example 2 — Signature verification failing

**Inputs:**

- Issue type: signature_failed
- Provider: Stripe
- Customer: LedgerSync
- Endpoint: `https://hooks.ledgersync.io/stripe`
- Duration: 30 minutes
- Stripe dashboard: delivery attempts shown, all returning 401
- Recent changes: rotated webhook signing secret this morning

**Short (Slack):**

```
🟡 LedgerSync — All webhooks failing signature check (401) since secret rotation 30 min ago. Customer rotated the signing secret in Stripe dashboard but hasn't updated the new secret in their application config. Waiting on their deploy. ETA: 15 min.
```

**Normal (email):**

```
Hi [Name],

We've identified why your webhook endpoint is returning 401 on all deliveries since this morning.

The issue is that your team rotated the webhook signing secret in the Stripe dashboard, but the new secret hasn't been updated in your application's configuration yet. Your endpoint is still using the old secret to verify signatures, which causes every verification to fail.

To fix this:
1. Copy the new signing secret from Stripe Dashboard → Developers → Webhooks → your endpoint → Signing secret
2. Update the `WEBHOOK_SECRET` (or equivalent) in your application's environment variables
3. Deploy the change

Note: During secret rotation, Stripe sends signatures with both the old and new secrets for a brief period. If you update your app within the next few hours, you won't miss any events — Stripe will retry all failed deliveries once your endpoint starts returning 200.

Let me know when the deploy is out and I'll verify delivery.

Best,
[Your name]
```

### Example 3 — Duplicate events

**Inputs:**

- Issue type: duplicate_events
- Provider: Stripe
- Customer: BillBot
- Endpoint: `https://api.billbot.com/stripe/events`
- Duration: Ongoing since launch
- Evidence: endpoint returns 409 for duplicates

**Short (Slack):**

```
🟡 BillBot — Reporting duplicate webhook processing. Root cause: endpoint returns 409 for duplicate event_ids instead of 200. Stripe interprets 409 as failure and retries → creates more duplicates. Customer updating endpoint to return 200 for known event_ids. ETA: 1 hour.
```

**Normal (email):**

```
Hi [Name],

We've found the cause of the duplicate event processing on your webhook endpoint.

Your endpoint currently returns 409 (Conflict) when it receives an event_id it has already processed. While this seems logical, Stripe interprets any non-2xx response as a delivery failure and schedules a retry. This creates a cycle: Stripe sends → you reject with 409 → Stripe retries → you reject again → and so on for up to 3 days.

The fix is straightforward: when your endpoint detects a duplicate event_id, it should return 200 instead of 409. The event was already processed successfully — that's a success from Stripe's perspective.

Recommended implementation:
1. Check if the event_id exists in your database
2. If yes → return 200 with no further processing
3. If no → process the event, store the event_id, return 200

This change will stop the retry cycle immediately. Events that are currently in Stripe's retry queue will resolve on their next attempt.

Let me know if you'd like me to review the implementation.

Best,
[Your name]
```

### Example 4 — Endpoint timeout

**Inputs:**

- Issue type: not_received
- Provider: Stripe
- Customer: ReconcileAI
- Endpoint: `https://api.reconcileai.com/webhooks`
- Duration: intermittent over 1 week
- Stripe dashboard: some deliveries show "timed out"
- Evidence: endpoint does DB writes + API calls synchronously before returning

**Short (Slack):**

```
🟡 ReconcileAI — Intermittent webhook timeouts for 1 week. Endpoint processes events synchronously (DB writes + API calls) before returning 200. Exceeds Stripe's ~10 sec timeout. Recommending async processing pattern. Customer scheduling refactor. ETA: 3 days.
```

**Normal (email):**

```
Hi [Name],

We've identified why some of your webhook deliveries are timing out intermittently.

Your endpoint currently processes each event synchronously — including database writes and downstream API calls — before returning a response to Stripe. When these operations take longer than Stripe's ~10 second timeout window, Stripe marks the delivery as failed and schedules a retry.

This creates two problems:
1. Retried events may get processed again (duplicate processing)
2. Under load, more events timeout, creating a cascade of retries

The recommended pattern is:
1. Receive the webhook
2. Verify the signature
3. Store the raw event in a queue (database table or message queue)
4. Return 200 immediately (< 1 second)
5. A background worker picks up events from the queue and processes them

This decouples receiving from processing. Stripe always gets a fast 200, and your processing can take as long as it needs without causing timeouts.

I can share implementation examples if that would be helpful. For the short term, if there are any specific events stuck in retry, I can help identify them in the dashboard.

Best,
[Your name]
```

## Validation checklist — before sending any webhook update

- [ ] Did I confirm whether Stripe **can reach** the endpoint vs **is being rejected**? (dashboard delivery status)
- [ ] Did I check for **recent changes**? (deploy, secret rotation, DNS, firewall)
- [ ] Is the root cause **confirmed** or still a hypothesis?
- [ ] Did I include the **specific evidence** (status codes, dashboard screenshots, timestamps)?
- [ ] Are **next steps clear** with explicit ownership?
- [ ] Did I avoid telling the customer to "just return 200 for everything"? (they should still validate)
- [ ] Did I mention the **retry behavior**? (customer needs to know Stripe will auto-retry failed events)
- [ ] For timeout issues: did I recommend the **async processing pattern**?