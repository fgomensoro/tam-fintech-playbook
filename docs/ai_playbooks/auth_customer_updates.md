# Auth Customer Updates — AI Playbook

> [!tip] How to use this playbook
> When you need to write a customer update about an auth issue, use the prompt template below with structured inputs. Review and edit the AI output before sending — never send raw AI output to a customer.

## Prompt template

```
You are a Technical Account Manager writing a customer update about an authentication issue.

## Inputs

Issue type: [token_expired | invalid_client | insufficient_scope | redirect_uri_mismatch | clock_skew | cert_expired | rate_limited | unknown]

Severity: [P1_critical | P2_high | P3_medium | P4_low]

Customer tier: [enterprise | growth | starter]

Customer name: [name]

Contact name: [name]

Affected endpoint: [endpoint]

Duration: [how long the issue has been ongoing]

Root cause: [what we found]

Evidence collected: [list what was verified]

Current status: [investigating | identified | mitigating | resolved | monitoring]

Next steps: [what needs to happen next]

## Output format: [short | normal | exec]

Write the update in the specified format. Be specific with technical details but accessible to the audience. Include timestamps where relevant. Do not use jargon without explaining it.
```

## Output formats explained

### Short (Slack / internal chat)
- 2-3 lines max
- Status emoji (🔴 active, 🟡 investigating, 🟢 resolved)
- Impact + cause + ETA
- Used for: internal Slack channels, quick updates to team

### Normal (email to customer)
- Greeting + context
- What happened (1-2 sentences)
- What we found (evidence-based)
- What we're doing / what you need to do (next steps with clear ownership)
- Timeline / ETA
- Sign-off
- Used for: direct email to customer's engineering or ops team

### Exec (summary for VP / C-level)
- 3-5 lines max
- Business impact first, technical detail second
- Status + ETA
- No jargon
- Used for: escalation to customer leadership, internal exec briefing

## Example outputs

### Example 1 — Token expired (P3, resolved)

**Inputs:**
- Issue type: token_expired
- Severity: P3_medium
- Customer: Acme Corp
- Contact: Sarah Chen
- Endpoint: `POST /api/payments`
- Duration: 3 hours
- Root cause: Access token expired, refresh token not implemented
- Evidence: JWT decoded, `exp` was 3 hours in the past
- Status: resolved
- Next steps: Customer to implement refresh token logic

**Short (Slack):**
```
🟢 Acme Corp — Auth issue resolved. Root cause: expired access token on POST /api/payments (no refresh logic). Customer regenerated token manually. Recommended they implement refresh token flow to prevent recurrence.
```

**Normal (email):**
```
Hi Sarah,

Following up on the authentication issue your team reported on POST /api/payments.

We've confirmed the root cause: the access token being used had expired approximately 3 hours before the errors started. When we decoded the JWT, the `exp` claim showed the token was no longer valid.

The immediate fix was to generate a new token, which your team has already done — we can confirm the endpoint is responding normally now.

To prevent this from recurring, we recommend implementing a refresh token flow in your integration. This would automatically request a new access token before the current one expires. I can share documentation and examples if that would be helpful.

Please let me know if you have any questions.

Best,
[Your name]
```

**Exec:**
```
Acme Corp experienced 3 hours of failed payment API calls due to an expired authentication token. Issue is now resolved — customer regenerated the token. We've recommended they implement automatic token refresh to prevent recurrence. No data loss occurred.
```

### Example 2 — Redirect URI mismatch (P2, investigating)

**Inputs:**
- Issue type: redirect_uri_mismatch
- Severity: P2_high
- Customer: FinFlow Inc
- Contact: James Park
- Endpoint: `/oauth/authorize`
- Duration: 45 minutes, ongoing
- Root cause: Trailing slash added to redirect URI after recent deploy
- Evidence: Registered URI is `https://app.finflow.com/callback`, sent URI is `https://app.finflow.com/callback/`
- Status: identified
- Next steps: Customer to update either the registered URI or the code

**Short (Slack):**
```
🟡 FinFlow Inc — Login failing for all users since deploy 45 min ago. Cause: redirect URI mismatch (trailing slash). Customer's engineering team is updating the URI in their OAuth app config. ETA: 15 min.
```

**Normal (email):**
```
Hi James,

We've identified the cause of the login failures your users are experiencing since the recent deployment.

The issue is a redirect URI mismatch. Your OAuth application has the following URI registered:

    https://app.finflow.com/callback

However, the authorization request is sending:

    https://app.finflow.com/callback/

The trailing slash makes these two different URIs, and the authorization server rejects the mismatch for security reasons.

To fix this, your team needs to do one of the following:
1. Remove the trailing slash from the redirect URI in your code (recommended), OR
2. Update the registered URI in your OAuth app settings to include the trailing slash

Once updated, login should work immediately — no restart or cache clear needed.

I'm standing by to verify once the change is deployed. Please let me know when it's live.

Best,
[Your name]
```

**Exec:**
```
FinFlow users cannot log in since a deployment 45 minutes ago. Root cause identified: a configuration mismatch in their OAuth redirect URI (trailing slash difference). Engineering team is deploying the fix now. ETA to resolution: 15 minutes. No data at risk — this is a login flow issue only.
```

### Example 3 — Clock skew causing intermittent 401s (P2, mitigating)

**Inputs:**
- Issue type: clock_skew
- Severity: P2_high
- Customer: PayBridge
- Contact: Maria Lopez
- Endpoint: `GET /api/transactions`
- Duration: Intermittent over 2 days
- Root cause: Customer's API server clock is 4 minutes ahead of auth server
- Evidence: Token `exp` valid for 60 min, but server rejects at 56 min. `date -u` shows 4 min drift.
- Status: mitigating
- Next steps: Customer to sync NTP, we to add 5 min leeway on validation

**Short (Slack):**
```
🟡 PayBridge — Intermittent 401s on GET /api/transactions for 2 days. Root cause: server clock 4 min ahead (NTP drift). Customer syncing NTP now. We're adding 5 min leeway to token validation. ETA: 1 hour.
```

**Normal (email):**
```
Hi Maria,

We've found the root cause of the intermittent 401 errors your team has been seeing on GET /api/transactions over the past two days.

The issue is clock skew — your API server's clock is approximately 4 minutes ahead of our authorization server. This means tokens that should be valid for 60 minutes are being rejected after only 56 minutes, because your server thinks the token has already expired.

We verified this by comparing `date -u` on both servers and checking the `exp` claim in the rejected tokens against the actual time of rejection.

Two actions are needed:
1. **Your team**: Sync your API server's clock using NTP (`sudo ntpdate pool.ntp.org` or ensure `ntpd`/`chronyd` is running)
2. **Our side**: We're adding a 5-minute leeway to our token validation to absorb minor clock differences going forward

We expect both changes to be in place within the next hour. I'll confirm once our validation update is deployed.

Best,
[Your name]
```

**Exec:**
```
PayBridge has experienced intermittent API authentication failures over 2 days. Root cause: their server's clock drifted 4 minutes out of sync, causing valid tokens to appear expired. Customer is correcting their clock sync now, and we're adding tolerance on our side. ETA: 1 hour. No data loss — affected requests can be safely retried.
```

### Example 4 — insufficient_scope (P3, resolved)

**Inputs:**
- Issue type: insufficient_scope
- Severity: P3_medium
- Customer: LedgerPro
- Contact: Alex Kim
- Endpoint: `POST /api/journal-entries`
- Duration: 30 minutes
- Root cause: Token requested with `read:items` scope, endpoint requires `write:journal`
- Evidence: JWT decoded, scope claim shows `read:items` only
- Status: resolved
- Next steps: Customer updated scope in token request

**Short (Slack):**
```
🟢 LedgerPro — 403 on POST /api/journal-entries resolved. Customer was requesting token with `read:items` scope instead of `write:journal`. Updated their token request, confirmed working.
```

**Normal (email):**
```
Hi Alex,

Quick update on the 403 errors your team was seeing on POST /api/journal-entries.

When we decoded the access token being used, the `scope` claim showed `read:items`. However, the journal entries endpoint requires `write:journal` permission.

Your team updated the scope in the token request to include `write:journal`, and we've confirmed the endpoint is now responding successfully.

For reference, you can always check which scopes a token has by decoding it at jwt.io and looking at the `scope` field in the payload.

Let me know if anything else comes up.

Best,
[Your name]
```

**Exec:**
```
LedgerPro had 30 minutes of failed journal entry submissions. Cause: their integration was requesting the wrong permission scope. Fixed by updating their token configuration. Resolved, no data impact.
```

## Validation checklist — before sending any update

- [ ] Is the root cause **confirmed** or still a hypothesis? Don't state hypotheses as facts.
- [ ] Did I include **specific evidence** (error codes, timestamps, claim values)?
- [ ] Are the **next steps clear** with explicit ownership (us vs customer)?
- [ ] Did I include an **ETA** or explicitly say "no ETA yet"?
- [ ] Is the **tone appropriate** for the audience (technical for engineers, business for execs)?
- [ ] Did I avoid **blaming the customer**? Frame as "we found" not "you broke".
- [ ] Did I **redact sensitive data**? (no client_secrets, no full tokens, no PII)
- [ ] For exec summaries: **business impact first**, technical detail second?