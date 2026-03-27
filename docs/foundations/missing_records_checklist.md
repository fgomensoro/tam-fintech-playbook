# Missing records checklist (API / integrations)

## 1) Pagination

- Confirm page/limit/cursor usage.
- Ensure the client follows `next_page` / `next_cursor`.
- Validate no duplicates across pages.

## 2) Filters / date range

- Verify time window, timezone, and inclusive/exclusive boundaries.

## 3) Delivery timing (async / settlement)

- Some records appear later (processing/settlement delays).
- Check provider docs for typical delays.

## 4) Caching

- Check Cache-Control / ETag / 304 behavior.
- Ensure you are not serving stale cached responses.

## 5) Rate limits (429)

- Requests might be dropped/limited during high volume.
- Respect Retry-After and reduce throughput.

## 6) Auth / permissions

- Wrong scopes/tenant can hide data (403) or block access (401).

## Evidence to request

- Exact request(s) + headers (redact secrets)
- Timestamp + timezone
- Correlation/request id
- Sample IDs that are missing + expected source system
