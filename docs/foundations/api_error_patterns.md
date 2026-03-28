# API error patterns (Week 1)

This doc maps common HTTP errors to: how to reproduce, likely causes, evidence to request, and safe mitigations.

---

## 400 Bad Request — invalid_json (POST /items)
**Reproduce**
- POST `/items`
- `Content-Type: application/json`
- Body: `hello` (invalid JSON)

**Observed**
- 400 `{ "ok": false, "error": "invalid_json" }`

**Likely cause**
- Request body is not valid JSON (syntax/encoding).

**Evidence to request**
- Exact request payload (redact secrets)
- Content-Type header
- Timestamp + request id

**Safe mitigation**
- Validate JSON serialization; ensure correct Content-Type and body.

---

## 401 Unauthorized — missing_bearer_token (GET /items)
**Reproduce**
- GET `/items` with no Authorization header.

**Observed**
- 401 `{ "ok": false, "error": "missing_bearer_token" }`

**Likely cause**
- Missing/invalid credentials; wrong auth type.

**Evidence to request**
- Authorization method used (API key vs Bearer)
- Full response status/body
- Which environment/tenant base_url

**Safe mitigation**
- Provide correct Authorization header format (`Bearer <token>`).

---

## 403 Forbidden — insufficient_scope (GET /items)
**Reproduce**
- GET `/items` with token_user (valid format, insufficient permission).

**Observed**
- 403 `{ "ok": false, "error": "insufficient_scope" }`

**Likely cause**
- Token is valid but lacks required scopes/roles/permissions.

**Evidence to request**
- Token scopes/roles (or app permissions)
- Endpoint being called and required permission
- Tenant/account context

**Safe mitigation**
- Request correct scope/role or use an admin/service token.

---

## 409 Conflict — duplicate_event (POST /webhook)
**Reproduce**
- POST `/webhook` twice with the same `event_id`.

**Observed**
- 409 `{ "ok": false, "error": "duplicate_event" }`

**Likely cause**
- At-least-once delivery → duplicate webhook events.
- Missing idempotency handling on consumer side.

**Evidence to request**
- event_id and timestamps
- Provider retry policy
- Idempotency keys / dedupe store behavior

**Safe mitigation**
- Implement idempotency (store processed event IDs) and ignore duplicates.

---

## 422 Unprocessable Content — missing_event_id (POST /webhook)
**Reproduce**
- POST `/webhook` without `event_id`.

**Observed**
- 422 `{ "ok": false, "error": "missing_event_id" }`

**Likely cause**
- Payload is valid JSON but fails domain validation (required field missing).

**Evidence to request**
- Full payload schema/contract
- Example payloads that should work
- Required vs optional fields

**Safe mitigation**
- Fix mapping/serialization; ensure required fields are sent.

---

## 429 Too Many Requests — rate_limited (GET /items)
**Reproduce**
- Call GET `/items` repeatedly within the rate window until limited.

**Observed**
- 429 `{ "ok": false, "error": "rate_limited" }` + `Retry-After: <seconds>`

**Likely cause**
- Client request volume exceeds provider policy.

**Evidence to request**
- Rate limit policy and headers (`Retry-After`, `X-RateLimit-*`)
- Current request rate and concurrency
- Time window of failures + request ids

**Safe mitigation**
- Respect Retry-After; reduce concurrency/throughput; exponential backoff + jitter.