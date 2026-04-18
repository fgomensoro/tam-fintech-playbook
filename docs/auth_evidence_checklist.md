# Auth Evidence Checklist

> [!tip] Use this checklist during any auth incident
> Before you start diagnosing, collect ALL of this from the customer. An incident without evidence takes 4 hours. With evidence, 20 minutes.

## 1. The failing request

- [ ] HTTP method (`GET`, `POST`, etc.)
- [ ] Full URL (including query parameters)
- [ ] `Authorization` header — is it present? Does it start with `Bearer `?
- [ ] `Content-Type` header
- [ ] Request body (with `client_secret` redacted)

## 2. The error response

- [ ] Status code (400, 401, 403, 429, 5xx)
- [ ] Full response body — especially `error` and `error_description` fields
- [ ] `WWW-Authenticate` header (if 401)
- [ ] `Retry-After` header (if 429)

## 3. Token inspection

- [ ] Decode the JWT at [jwt.io](https://jwt.io) or via `atob(token.split(".")[1])` in console
- [ ] `exp` — is the token expired? Compare with current Unix timestamp
- [ ] `nbf` — is the token "not yet valid"? (clock skew indicator)
- [ ] `iat` — when was it issued? How long ago?
- [ ] `sub` — who does the token belong to? (user ID or client_id)
- [ ] `iss` — does the issuer match the expected auth server URL?
- [ ] `aud` — does the audience match the resource server?
- [ ] `scope` — does it include the permission this endpoint requires?
- [ ] `azp` — which client_id requested this token?
- [ ] Token format — is it JWT (three dots) or opaque (random string)?

## 4. OAuth client configuration

- [ ] `client_id` — is it the right one for this environment?
- [ ] `client_secret` — was it rotated recently? (don't ask for the value, just "when was it last changed?")
- [ ] Grant type being used — Authorization Code, Client Credentials, Refresh Token?
- [ ] Scopes requested — what does the client ask for at `/token`?
- [ ] Scopes granted — what does the auth server actually return? (may be narrower)
- [ ] Is PKCE enabled? If yes, `S256` or `plain`?

## 5. Redirect URI (if Authorization Code flow)

- [ ] Registered redirect URI — exact value from auth server dashboard (ask for screenshot)
- [ ] Sent redirect URI — exact value from the `/authorize` request
- [ ] Byte-for-byte comparison:
  - [ ] Trailing slash? (`/callback` vs `/callback/`)
  - [ ] Protocol? (`http` vs `https`)
  - [ ] Case? (`App.com` vs `app.com`)
  - [ ] Port? (`app.com` vs `app.com:8080`)
  - [ ] Subdomain? (`www.app.com` vs `app.com`)

## 6. Environment

- [ ] Which environment? (prod, sandbox, staging, dev)
- [ ] Is the `client_id` from the **same** environment as the `base_url`?
- [ ] Auth server URL — what is the exact issuer URL?
- [ ] Are there multiple tenants? If so, which tenant?

## 7. Timing and context

- [ ] ==Did this work before?==
- [ ] ==When did it stop working?== (exact date/time)
- [ ] ==What changed?==
  - [ ] Deploy in the last 24h?
  - [ ] Secret rotation?
  - [ ] Cert renewal or expiry?
  - [ ] Auth server config change? (Okta, Auth0, Azure AD)
  - [ ] IdP policy update?
- [ ] How many users affected? (1, some, all)
- [ ] Is it reproducible or intermittent?
- [ ] Does it work in another browser/device?

## 8. Clock sync

- [ ] Client server time — is it NTP-synced?
- [ ] Auth server time — is it NTP-synced?
- [ ] Difference between client and server clocks
- [ ] Check: `date -u` on both servers and compare
- [ ] If token appears expired but was just issued → clock skew is the likely cause

## 9. Certificate chain

- [ ] Is the TLS cert valid? `openssl s_client -connect host:443 -servername host`
- [ ] When does it expire? Check `notAfter`
- [ ] Is the full chain trusted? (intermediate certs present?)
- [ ] Was the cert recently renewed? (could have changed the chain)

## Quick triage — which section to jump to

| Customer says | Start at |
|---|---|
| "Getting 401 on all requests" | Section 3 (token) → Section 4 (client config) |
| "Getting 403" | Section 3 (scope) → Section 4 (scopes requested vs granted) |
| "Redirect isn't working" | Section 5 (redirect URI) |
| "It worked yesterday" | Section 7 (timing) → Section 4 (secret rotation) |
| "Works in Postman, fails in prod" | Section 6 (environment) → Section 5 (redirect URI) |
| "Intermittent 401s" | Section 8 (clock sync) → Section 3 (exp/nbf) |
| "Can't connect to auth server" | Section 9 (cert) → Section 6 (environment) |

## After collecting evidence

1. **Identify the symptom** → map to [[Troubleshooting]] Layer 1
2. **Follow the decision tree** → Troubleshooting Layer 3
3. **Match the error code** → Troubleshooting Layer 4
4. **Communicate** → use templates from [[auth_customer_updates]]