# HTTP debugging notes (Week 1)

## 401 vs 403

- 401 Unauthorized = authentication failed (missing/invalid/expired credentials).
  - First checks: Authorization header present + correct format, environment/issuer correct, token not expired.
- 403 Forbidden = authenticated, but not allowed (insufficient scopes/roles/permissions).

## 400 vs 422

- 400 Bad Request = malformed request (syntax/params/body not parseable).
  - First checks: method + params, Content-Type/Accept, JSON validity.
- 422 Unprocessable Content = request format valid, but fails domain validation (business rules).
  - Example: refund amount exceeds captured amount.

---

## HTTP foundations + RFC 9110 highlights

- RFC9110: Status codes are a 3-digit result + response semantics indicator (100-599; first digit is the class).
  - 1xx informational
  - 2xx success
  - 3xx redirection
  - 4xx client error (bad request / cannot be fulfilled)
  - 5xx server error (server failed to fulfill a valid request)
- RFC9110: Request semantics = the HTTP method primarily defines the request's meaning/expected result; headers can add semantics if they don't conflict.
- Body semantics reminders:
  - If method = `HEAD` or status = `204` / `304` -> no response content (no body).
  - If method = `GET` and status = `200` -> body is a representation of the target resource.
