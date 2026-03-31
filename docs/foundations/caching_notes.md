# Caching notes (Week 1)

## Cache-Control (what it means)
- `max-age=<seconds>`: response can be reused for that many seconds without revalidating.
- `no-store`: do not store the response at all (most strict).
- `no-cache`: you may store it, but you must revalidate before using it.
- `public`: may be cached by shared caches (CDNs/proxies).
- `private`: only the end client should cache it (not shared caches).

**Debug rule:** If I see stale data, I check Cache-Control because a cached response may be served instead of fresh data.

## ETag / If-None-Match / 304 (the validation flow)
- `ETag`: a version identifier for a resource representation; used to validate cached responses.
- `If-None-Match`: conditional request header - "only send me the body if the ETag has changed."
- `304 Not Modified`: resource hasn't changed; server won't send the body.

**Flow**
- GET returns `ETag` -> client caches body+ETag -> next GET sends `If-None-Match` -> server replies:
- `304` (use cached body) or
- `200` (new body + new ETag)

## How I debug caching issues (TAM checklist)
- Confirm what the client is actually sending: `Cache-Control`, `If-None-Match`, `If-Modified-Since`.
- Inspect response headers: `Cache-Control`, `ETag`, `Age`, `Vary` (if present).
- Verify whether a proxy/CDN is in the path (shared caching).
- Compare with a "fresh" request (disable cache / different client) to validate if data is truly stale.
