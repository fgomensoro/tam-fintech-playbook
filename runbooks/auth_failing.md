# Auth Failing — Runbook

## Symptoms

- I'm getting 401/403 errors on all requests
- We're getting intermittent auth errors
- The API stopped returning data
- Our integration broke — it was working yesterday

---

## Quick Triage (first 2 minutes)

1. What is the error code — 401, 403, or 400?
2. Is the customer sending a valid token in the Authorization header?
3. Is the token expired? Ask them to check `exp` at [jwt.io](https://jwt.io)

---

## Diagnosis Tree

**401 — Unauthorized**
→ Is the token present in the Authorization header?
→ Does it start with `Bearer `?
→ Is the token expired? Check `exp` claim.
→ Was the token generated with the correct `client_id` and `client_secret`?

**403 — Forbidden**
→ What scopes does the token have?
→ What scope does the failing endpoint require?
→ Are they using the right environment (prod vs staging)?

**400 — Bad Request**
→ Is `grant_type` present in the request body?
→ Is the request body formatted correctly (`x-www-form-urlencoded`)?
→ Is the `grant_type` value supported by this auth server?

---

## Evidence to Collect from Customer

1. Exact error message and status code
2. Endpoint that is failing
3. Grant type being used
4. Full `Authorization` header — is `Bearer` prefix present?
5. Token decoded at [jwt.io](https://jwt.io) — share `exp`, `scope`, `sub`
6. `client_id` and environment (prod vs staging)

---

## Customer Messages

### Slack (short)
🔴 Auth issue identified for [Customer]. Root cause: expired API token.
Customer is regenerating now. Monitoring for resolution. ETA: 15 min.

### Email (normal)
Hi [Name],

We've identified an auth issue affecting [Customer] for the past 3 hours.

**Details:**
- Root cause: expired API token
- Affected endpoint: `/items`
- Status: customer is regenerating the token and will retry

I'm monitoring the situation and will confirm resolution within 15 minutes.
Please let me know if you have any questions.

Best,
[Your name]

### Exec Summary
High-impact issue for [Customer] affecting payments collection.
Root cause: expired API token. Customer is regenerating now. ETA: 15 min.

---

## Escalation Criteria

Escalate to engineering when:
- Customer has regenerated the token and the issue persists
- Error code is unexpected — 5xx or undocumented error
- Multiple customers are affected simultaneously
- Root cause requires a code or server configuration change