# Webhook Troubleshooting Guide

> [!tip] When to use this guide
> A customer reports a webhook problem. Before you start diagnosing, figure out **where** the problem lives: customer's side, provider's side, or in the network between them. This guide gives you a symptom-first structure to find out fast.

## Triage — where does the problem live?

```
Customer reports webhook issue
    │
    ▼
Does the PROVIDER dashboard show delivery attempts?
    │
    ├── NO attempts shown
    │   └── Problem is BEFORE the provider sends
    │       (provider-side OR network between customer and provider)
    │
    ├── YES, attempts shown with failures (non-2xx)
    │   └── Problem is AT the customer's endpoint
    │       (customer-side: endpoint rejecting)
    │
    ├── YES, attempts shown as "delivered" (2xx)
    │   └── Problem is AFTER delivery
    │       (customer-side: processing logic, not delivery)
    │
    └── YES, attempts shown as "timed out"
        └── Problem is endpoint latency
            (customer-side: too slow to respond)
```

## Customer-side checklist

The most common class of webhook issues. Customer's endpoint is receiving but something's wrong.

### Endpoint reachability

- [ ] Is the endpoint URL correct? (typo, old URL, wrong environment)
- [ ] Is DNS resolving? `dig endpoint.example.com`
- [ ] Is the endpoint publicly accessible? `curl -I https://endpoint.example.com/webhooks/stripe`
- [ ] Is HTTPS configured with a valid cert? `openssl s_client -connect endpoint.example.com:443`
- [ ] Is the cert chain complete? (some providers reject incomplete chains)
- [ ] Is there a firewall/WAF/load balancer blocking provider IPs?
- [ ] Does the endpoint allow the provider's IP ranges? (Stripe publishes IPs at docs.stripe.com/ips)

### Endpoint response behavior

- [ ] Is the endpoint returning 2xx for valid events?
- [ ] Is the endpoint returning 2xx for **duplicate** events? (not 409 or 400 — those trigger retries)
- [ ] Is the endpoint responding within provider timeout? (Stripe: ~10 sec)
- [ ] Is the endpoint following redirects? (it shouldn't — respond directly)
- [ ] Is the response body valid? (doesn't matter what it says, but must not hang)

### Signature verification

- [ ] Is the signing secret the correct one for this environment (test vs live)?
- [ ] Was the signing secret recently rotated? Has the app been updated?
- [ ] Is the verification using the **raw body**, not parsed JSON?
- [ ] Is the verification using HMAC-SHA256 (or the provider's documented algorithm)?
- [ ] Is the timestamp tolerance check not too strict? (5 min is standard)
- [ ] Is the comparison using a **timing-safe** compare function (e.g., `hmac.compare_digest`)?

### Deduplication

- [ ] Is deduplication implemented at all?
- [ ] Is dedup based on `event_id`, not payload content?
- [ ] Is the dedup check **before** processing (not after)?
- [ ] Is dedup storage persistent across restarts? (not just in-memory)
- [ ] Is dedup storage scoped correctly across workers? (not per-process)
- [ ] How long are event_ids retained? (at least 3 days for Stripe retries)

### Processing logic

- [ ] Is processing async (after returning 200)?
- [ ] Is the background worker actually running?
- [ ] Are processing errors being logged?
- [ ] Is the endpoint filtering events correctly? (not silently ignoring)
- [ ] Are you handling all expected event types?
- [ ] Is there error-handling for malformed payloads?

### Environment

- [ ] Is the correct environment configured? (test mode vs live mode)
- [ ] Are environment variables loaded? (check for missing secret)
- [ ] Is the right API version pinned? (schema changes over time)
- [ ] Are you listening on the right port? (firewall may block non-standard ports)

## Provider-side checklist

Less common but does happen. Start here only if customer-side looks clean.

- [ ] Is the provider experiencing an outage? (check status page: status.stripe.com, status.plaid.com, status.moderntreasury.com)
- [ ] Is the webhook endpoint disabled in the provider dashboard? (automatic after many failures)
- [ ] Is the webhook configured for the right event types?
- [ ] Was the webhook endpoint URL recently changed?
- [ ] Is the API version set correctly on the webhook? (vs the API version used for the API call)
- [ ] Are events being filtered at the provider level?
- [ ] Is the provider's account in good standing? (suspended accounts stop firing events)
- [ ] If using a signing secret rotation, is the new secret active?

## Network-side checklist

Rare but insidious. Suspect this when customer and provider both look healthy.

- [ ] Is there a proxy/CDN between provider and customer? (can modify body → break signatures)
- [ ] Is there a WAF inspecting traffic? (may block "suspicious" POST patterns)
- [ ] Is there packet loss or high latency on the path?
- [ ] Are large payloads being truncated? (MTU issues, proxy limits)
- [ ] Is there an IDS blocking "anomalous" traffic patterns?
- [ ] Did DNS records change recently? (propagation delays)

## Symptom → likely cause matrix

| Symptom | Most likely | Also check |
|---|---|---|
| No delivery attempts in dashboard | DNS, firewall, wrong URL | Provider outage |
| All 401 responses | Signature verification bug | Wrong signing secret |
| All 500 responses | Endpoint crashing | Unhandled exception in processing |
| All timeouts | Endpoint too slow, sync processing | Downstream dependency slow |
| Intermittent 401 | Clock skew, secret rotation | Multiple workers with inconsistent config |
| Intermittent 500 | Race condition, resource exhaustion | Memory leak |
| Events missing in DB | Processing errors after 200 response | Dedup bug (marked "processed" before actual processing) |
| Duplicate processing | Missing dedup, or dedup after processing | Multiple workers, no DB-level lock |
| Events out of order | Normal — at-least-once doesn't guarantee order | Check created timestamps in payload |
| Works in test, fails in prod | Wrong environment config, different signing secret | IP whitelist different per environment |

## First 60 seconds of any webhook incident

> [!tip] Structured triage
> 1. **Which provider?** (Stripe, Modern Treasury, Plaid, custom)
> 2. **What does the customer see?** (symptom, not diagnosis)
> 3. **Does the provider dashboard show delivery attempts?** (yes/no/partial)
> 4. **What status code does the provider see?**
> 5. **Did this work before?** What changed?
> 6. **Which event types are affected?** (all or specific)
> 7. **Which environment?** (test vs live)

## Message templates during a webhook incident

### Short (Slack)
```
🔴 [Customer] — Webhook delivery failing. [Count] events affected. Root cause: [hypothesis]. Investigating. ETA: [time].
```

### Status update (15-30 min in)
```
🟡 [Customer] — Update: [what we've confirmed]. [What we've ruled out]. Next step: [what we're doing]. ETA: [time].
```

### Resolved
```
🟢 [Customer] — Webhooks delivering normally. Root cause: [confirmed cause]. Fix: [what was done]. Events retried by provider automatically — no manual replay needed. [N] events caught up.
```

## Related notes

- [[Webhooks]] — core concepts, delivery model, HMAC verification
- [[Idempotency and Deduplication]] — dedup patterns and storage
- [[Webhook Triage]] — AI playbook with example customer messages
- [[Troubleshooting]] — general OAuth troubleshooting (similar structure)