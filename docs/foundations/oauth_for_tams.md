# OAuth 2.0 for TAMs

## What is OAuth 2.0?

OAuth 2.0 is an **authorization** framework — it controls what a user or
system can access, not who they are. Authentication (verifying identity)
is handled separately, often via OpenID Connect (OIDC) on top of OAuth.

---

## The Four Roles

| Role | Description |
|------|-------------|
| **Resource Owner** | The user who owns the data and grants access |
| **Client** | The app requesting access on behalf of the user |
| **Authorization Server** | Validates credentials and issues tokens |
| **Resource Server** | Holds the protected data; accepts tokens |

> The Authorization Server and Resource Server can be the same service.

---

## Grant Types — Which Flow to Use?

| Scenario | Flow | Notes |
|----------|------|-------|
| Server-side web app | Authorization Code | Client secret stored securely on server |
| Mobile app or SPA | Authorization Code + PKCE | No server to store secret; PKCE prevents code interception |
| Machine-to-machine | Client Credentials | No user involved; client authenticates directly |
| ~~User password directly~~ | ~~ROPC~~ | Deprecated — do not use |
| ~~No backend~~ | ~~Implicit~~ | Deprecated — do not use |

---

## Common Errors and How to Diagnose Them

### Errors at token request (`POST /oauth/token`)

| Error | Status | Cause | Action |
|-------|--------|-------|--------|
| `missing_grant_type` | 400 | No `grant_type` in request body | Add `grant_type` field |
| `unsupported_grant_type` | 400 | Grant type not supported by this server | Check supported flows in docs |
| `invalid_client` | 401 | Wrong `client_id` or `client_secret` | Verify credentials with the provider |

### Errors at resource request (`GET/POST /items`, etc.)

| Error | Status | Cause | Action |
|-------|--------|-------|--------|
| `missing_bearer_token` | 401 | No `Authorization` header or missing `Bearer` prefix | Check header format |
| `insufficient_scope` | 403 | Token valid but missing required permission | Request token with correct scope |
| Token expired | 401 | `exp` claim in past | Use refresh token or re-authenticate |

---

## Evidence Checklist — What to Ask the Customer

When a customer reports an auth issue, collect this before escalating:

1. What is the exact error message and status code?
2. What endpoint is failing?
3. What grant type are they using?
4. Is the `Authorization` header present? Does it start with `Bearer `?
5. Is the token expired? Ask them to decode it at [jwt.io](https://jwt.io) and check `exp`
6. What scope does the token have? Does it match what the endpoint requires?
7. Are the `client_id` and `client_secret` correct and from the right environment?