# Rate limit playbook (429)

## What 429 means

- The provider is rate limiting requests (too many requests in a time window).

## Safe client behavior

- Reduce concurrency and overall request rate (throughput).
- Retry with exponential backoff + jitter.
- Respect `Retry-After` if present (sleep at least that many seconds).

## Evidence to request / capture

- Provider rate limit policy (req/s, req/min, per-token vs per-IP).
- Response headers: `Retry-After` and any `X-RateLimit-*`.
- Current request volume and concurrency on our side.
- Correlation IDs / timestamps for failing calls.

## Common pitfalls

- Retrying immediately (causes a retry storm).
- Not batching / not paginating efficiently.
- Treating 429 like a 500 (it’s not a server outage).
