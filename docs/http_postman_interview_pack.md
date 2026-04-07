# HTTP + Postman Interview Pack

## Q1
What is the difference between 401 and 403?

<details>
<summary>Answer</summary>

**401 — Unauthenticated:** the server doesn't know who you are. No valid credentials were provided.

**403 — Unauthorized:** the server knows who you are but you don't have permission to access that resource.

</details>

---

## Q2
A customer says they're hitting rate limits. What are your first 3 questions?

<details>
<summary>Answer</summary>

1. Which endpoint is returning the 429 error?
2. When did it start?
3. Are you respecting the `Retry-After` header?
4. How many requests are you sending per minute?

</details>

---

## Q3
What is a webhook and how is it different from a regular API call?

<details>
<summary>Answer</summary>

A webhook is an event-driven HTTP request initiated by the server, not the client. In the most common case (inbound), an external provider like Stripe sends a POST to your endpoint when something happens — for example, when a payment succeeds. In outbound cases, your system exposes an endpoint that an external server calls to pull data on a schedule.

The key difference from a regular API call: **you don't initiate the request — the server does.**

</details>

---

## Q4
What is idempotency and why does it matter in payment systems?

<details>
<summary>Answer</summary>

Idempotency means that making the same operation multiple times produces the same result as doing it once. It matters most for POST requests — GET, PUT, and DELETE are idempotent by design.

In payment systems, idempotency prevents duplicate charges when a request is retried. When a duplicate event ID is received, the server should return 409.

</details>

---

## Q5
What is the purpose of an X-Request-Id header?

<details>
<summary>Answer</summary>

A client-generated ID attached to every request. It allows you to trace a specific request through server logs — useful when debugging incidents. Instead of saying "something failed around 3pm," you can say "request `req_1743612345` failed — what do you see on your side?"

</details>

---

## Q6
What is contract validation and why should a TAM care about it?

<details>
<summary>Answer</summary>

Contract validation is verifying that both the request payload and the response schema match what was agreed upon — correct fields, correct types, no missing required values. A 422 is returned when the request contract is violated.

A TAM should care because a broken contract means the customer can't process transactions — and that escalates fast.

</details>

---

## Q7
What is a breaking change? Give a concrete example.

<details>
<summary>Answer</summary>

A breaking change is a modification to an API that causes existing client code to fail without the client having changed anything on their side.

**Example:** changing an `id` field from a number to a string. A client sending `"id": 123` now gets a validation error — their code is broken, and they didn't touch it.

</details>

---

## Q8
What is the difference between running a Postman collection in the UI vs via CLI vs in CI?

<details>
<summary>Answer</summary>

**UI:** runs on your machine with your local configuration — least reproducible.

**CLI:** runs headlessly on your machine — removes the UI dependency but still relies on your environment.

**CI:** runs on a clean, isolated environment on every push — no manual intervention, no local configuration. Most trustworthy and reproducible.

UI → CLI → CI is a trust progression.

</details>

---

## Q9
How do you assert that a field exists, has the correct type, and is not null in a Postman test?

<details>
<summary>Answer</summary>
```javascript
pm.expect(json).to.have.property("field"); // exists
pm.expect(json.field).to.not.equal(null);  // not null
pm.expect(json.field).to.be.a("type");     // correct type
```

Note: always use separate assertion lines after `.not` — the flag persists through the chain in Chai.

</details>

---

## Q10
A customer says "the API worked yesterday but not today." What do you do in the first 5 minutes?

<details>
<summary>Answer</summary>

1. Check API health — is the service running? Was there a recent deployment?
2. Run the Postman collection — do all tests pass?
3. Ask the customer for the `X-Request-Id` from their failing requests and check server logs.
4. Check if they're hitting 429s — did their traffic pattern change?
5. Verify the specific endpoints they're calling still behave as expected.

</details>