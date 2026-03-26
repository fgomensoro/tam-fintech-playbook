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
