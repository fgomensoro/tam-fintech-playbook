
# Stripe Data Model

> [!tip] What this doc covers
> The core objects in Stripe's payment flow, how they connect, and what each one tells you when you're troubleshooting. Built around the principle: **reconciliation starts at BalanceTransaction**.

## The core flow

When a customer pays, Stripe creates three objects in sequence. Each lives in a different layer of the stack and answers a different question.

```
PaymentIntent  →  Charge  →  BalanceTransaction
   pi_xxx         ch_xxx        txn_xxx
   
   "intent to     "actual       "accounting
    collect"      attempt"       impact"
```

| Object | Lives in | Question it answers |
|---|---|---|
| **PaymentIntent** | Customer / frontend layer | "Are we trying to collect this money?" |
| **Charge** | Card network layer | "Did the card actually approve?" |
| **BalanceTransaction** | Stripe account / accounting layer | "Did the money move and how much landed in my balance?" |

The separation matters because each layer can fail independently. A PaymentIntent can have multiple Charges (retries with different cards). A Charge can have zero or one BalanceTransaction (failed charges don't create one).

## PaymentIntent (`pi_xxx`)

The intention to collect a specific amount from a specific customer.

### Status lifecycle

```
requires_payment_method → requires_confirmation → requires_action (3DS)
                                                      ↓
                                                  processing
                                                      ↓
                                                  succeeded
```

Other terminal states:
- `canceled` — explicitly canceled by you or the customer
- `requires_payment_method` — last attempt failed, waiting for retry

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `pi_` |
| `amount` | Amount **in cents** of the smallest currency unit |
| `currency` | ISO 4217 lowercase (`usd`, `eur`, `mxn`) |
| `status` | Where in the lifecycle it is |
| `latest_charge` | The most recent Charge ID (`ch_xxx`) — null until first attempt |
| `payment_method` | The card/account that was used |
| `client_secret` | Used by frontend to confirm payment — never log or expose |
| `metadata` | Free-form key/value — used for linking to your internal IDs |
| `livemode` | `true` for prod, `false` for test — always sanity-check this |
| `customer` | Stripe customer ID (`cus_xxx`) if associated |

### Why PaymentIntents persist across retries

A customer's first card is declined. They enter a second card. Same PaymentIntent.

Result:
- 1 PaymentIntent (`pi_xxx`)
- 2 Charges (one failed, one succeeded)
- 1 BalanceTransaction (only the succeeded charge created one)

This design lets you track "did we eventually collect this?" without losing the history of attempts.

## Charge (`ch_xxx`)

A single attempt to charge a payment method through the card network.

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `ch_` |
| `amount` | Amount being charged (centavos) |
| `amount_captured` | What was actually captured (relevant for auth-only flows) |
| `amount_refunded` | How much has been refunded against this charge |
| `paid` | Boolean — was this charge successful |
| `status` | `succeeded`, `pending`, `failed` |
| `outcome` | Detailed risk/decision info from Stripe Radar |
| `failure_code` / `failure_message` | If failed, why |
| `payment_intent` | Backreference to the parent PaymentIntent |
| `balance_transaction` | The BalanceTransaction this charge generated (null if failed) |
| `payment_method_details.card.last4` | Last 4 digits — useful for customer comms |
| `payment_method_details.card.brand` | Visa, Mastercard, etc. |
| `disputed` | Has this charge been disputed? |
| `refunded` | Has this charge been fully refunded? |

### Bidirectional navigation

Stripe's data model lets you traverse in any direction:

- From PaymentIntent → Charge: `pi.latest_charge`
- From Charge → PaymentIntent: `ch.payment_intent`
- From Charge → BalanceTransaction: `ch.balance_transaction`
- From BalanceTransaction → Charge: `txn.source`

When a customer gives you any one ID, you can navigate the entire graph.

### Failed charges

A failed Charge:
- `paid: false`
- `status: failed`
- `balance_transaction: null` ← critical: no balance transaction created
- `failure_code` populated (`card_declined`, `insufficient_funds`, etc.)

A failed charge means **no money moved**. Don't reconcile against it.

## BalanceTransaction (`txn_xxx`)

The accounting unit. Every time money moves in or out of your Stripe balance, a BalanceTransaction is created.

> [!warning] The single most important rule for reconciliation
> ==**Reconciliation starts at BalanceTransaction.**==
>
> Don't reconcile against PaymentIntents (they don't always become money). Don't reconcile against Charges (failed charges don't create money movement). Reconcile against BalanceTransactions because they are the immutable record of actual money movement in your Stripe balance.

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `txn_` |
| `amount` | Gross amount (centavos) |
| `fee` | Total Stripe fee (centavos) |
| `fee_details` | Breakdown of fees (Stripe fee, application fee, etc.) |
| `net` | What you actually receive: `amount - fee` |
| `currency` | The currency of this transaction |
| `status` | `pending` (not yet available), `available` (ready to pay out) |
| `available_on` | Unix timestamp when funds become available |
| `type` | What kind of transaction (`charge`, `refund`, `payout`, `adjustment`) |
| `source` | The object that triggered this BT (`ch_xxx`, `re_xxx`, `po_xxx`) |
| `reporting_category` | Higher-level category for reporting |
| `description` | Human-readable description |

### Stripe's standard fee structure (US, cards)

For a typical card payment in US:

```
fee = (amount × 2.9%) + 30 cents
```

Example: $50.00 charge

```
2.9% of 5000 cents = 145 cents
+ 30 cents fixed   =  30 cents
                   ─────────
total fee          = 175 cents ($1.75)

net = 5000 - 175 = 4825 cents ($48.25)
```

The fixed component (30 cents) makes small transactions disproportionately expensive. A $1 charge has a fee of 33 cents — that's 33% of the transaction. A $1000 charge has a fee of $29.30 — only 2.9%. ==Customers reconciling fees often get confused by this. The percentage isn't constant.==

### `pending` vs `available`

When a charge succeeds, the BalanceTransaction is `pending`. It becomes `available` after the payout schedule (typically 2 business days for US standard accounts, but varies by country and account age).

| Status | What it means | Where the money is |
|---|---|---|
| `pending` | Money charged but not yet usable | "Stripe pending balance" |
| `available` | Ready to be paid out | "Stripe available balance" |
| (after payout) | Sent to your bank | "Cash / Bank" |

## Accounting implications

> [!warning] What this means for your customer's books
> Under accrual accounting, **revenue is recognized when earned**, not when cash is received. So a successful charge means revenue gets recognized **today**, even if the money won't hit the bank for 2 days.
>
> The Stripe balance is a **clearing account** — it represents money owed to your customer that hasn't yet been deposited. It's not cash.
>
> Typical chart of accounts impact:
> - **Charge succeeds**: Revenue recognized + Stripe Receivable (asset) increases + Processing Fees (expense) recognized
> - **BalanceTransaction becomes `available`**: Stripe Receivable stays the same (just status change inside Stripe)
> - **Payout sent to bank**: Stripe Receivable decreases + Cash increases
>
> Customers often ask: "Why is my Stripe dashboard balance different from my bank deposits?" Answer: timing differences between charge → available → payout, plus held reserves.

## Refunds (`re_xxx`)

A Refund undoes part or all of a Charge. It creates its own BalanceTransaction with **negative** amount.

### Lifecycle

```
PaymentIntent  →  Charge (succeeded)  →  BalanceTransaction (+5000)
                       ↓
                   Refund (re_xxx)   →  BalanceTransaction (-5000)
                                        +
                                        BalanceTransaction (+30)  ← in some markets, fees are returned
```

In US, the fixed 30-cent fee is not returned on refunds (only the percentage portion is recoverable in some cases). In Europe, full fees are typically returned.

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `re_` |
| `amount` | Amount being refunded (centavos) |
| `charge` | The Charge being refunded |
| `payment_intent` | The PaymentIntent the charge belongs to |
| `status` | `succeeded`, `pending`, `failed`, `canceled` |
| `reason` | `duplicate`, `fraudulent`, `requested_by_customer`, or null |
| `balance_transaction` | The BT created for this refund (negative amount) |

### Partial vs full refunds

A Charge can have multiple Refunds as long as the cumulative refund amount ≤ original charge. Each one creates its own BalanceTransaction.

## Disputes / Chargebacks

When a customer disputes a charge with their bank, Stripe creates a Dispute object.

### Lifecycle

```
needs_response  →  under_review  →  won
                                  →  lost
                                  →  warning_closed (early warning)
```

### Financial impact

When a dispute is opened:
1. The charge amount is **debited** from your balance immediately (BalanceTransaction with negative amount)
2. A **dispute fee** is charged (typically $15 USD)
3. If you win the dispute → amount is refunded back to your balance (positive BT)
4. If you lose → the debit stays, the customer keeps their money

==Dispute fees are NOT refunded even if you win.== This is critical for reconciliation: the $15 fee is permanent regardless of outcome.

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `dp_` |
| `amount` | Disputed amount |
| `charge` | The Charge being disputed |
| `reason` | `fraudulent`, `unrecognized`, `duplicate`, `subscription_canceled`, etc. |
| `status` | Where in the lifecycle |
| `evidence_due_by` | Deadline to submit evidence (usually 7 days) |
| `balance_transactions` | Array of BTs (initial debit, fee, eventual refund if won) |

## Payouts (`po_xxx`)

A Payout is a deposit from Stripe to your bank account. It groups multiple BalanceTransactions into one bank transfer.

### Lifecycle

```
in_transit  →  paid       (deposit landed)
            →  failed     (bank rejected)
            →  canceled
```

### Key fields

| Field | What it tells you |
|---|---|
| `id` | Identifier, prefix `po_` |
| `amount` | Total amount being paid out (centavos) |
| `arrival_date` | When the deposit hits your bank |
| `currency` | Currency of the payout |
| `destination` | Bank account ID |
| `status` | Lifecycle status |
| `type` | `bank_account`, `card` |

### Composition

A Payout's amount equals the sum of `net` from all BalanceTransactions in that payout window. Example:

```
Payout po_xxx (amount: 9450)
├── BT txn_001 (charge,  +5000 amount, -175 fee, +4825 net)
├── BT txn_002 (charge,  +5000 amount, -175 fee, +4825 net)
└── BT txn_003 (refund,  -200  amount, 0 fee,    -200 net)
                                       ─────
                                       net total: 9450
```

When a customer says "my payout is less than expected," walk through the BalanceTransactions for that payout window. The math always reconciles.

## "Where does each dollar show up?"

For a typical $100 charge to a US merchant:

| Step | What changes | Object |
|---|---|---|
| Customer charged | Gross volume | Charge ($100) |
| Fee deducted | Stripe revenue | BalanceTransaction (fee: -$3.20) |
| Net credited to balance | Pending balance | BalanceTransaction (net: +$96.80) |
| 2 days later | Available balance | (no new object — same BT changes status) |
| Next payout | Cash to bank | Payout (po_xxx, amount: $96.80) |

For the same $100 charge that gets refunded:

| Step | What changes | Object |
|---|---|---|
| Refund issued | Available balance | Refund (re_xxx, $100) + BalanceTransaction (-$100 amount, $0 fee, -$100 net) |
| Net effect on your balance | -$3.20 (fee not returned) | The original fee stays as a loss |

For a $100 charge that gets disputed and lost:

| Step | What changes | Object |
|---|---|---|
| Dispute opened | Available balance debited | BalanceTransaction (-$100) + dispute fee BT (-$15) |
| Dispute lost | No reversal | The debits stay |
| Net loss | $115 from your balance | Even though customer paid you $96.80 net originally |

This last case is critical: a chargeback costs you **more** than the original transaction was worth.

## Common TAM questions

### "What's the difference between a Charge and a PaymentIntent?"

PaymentIntent is the umbrella for the customer's intent to pay. It can have multiple Charges (retry attempts). The PaymentIntent represents the goal; Charges represent each attempt against the card network.

### "Why is my payout less than expected?"

The structured approach (do these in order):

**Step 1 — Identify the specific payout**
Get the `po_xxx` from the customer. Without it you don't know which window to investigate. If they only have the bank deposit info, find it via `GET /v1/payouts?arrival_date=...`.

**Step 2 — List the BalanceTransactions for that payout**
```
GET /v1/balance_transactions?payout=po_xxx
```
This is the source of truth. Don't start from charges or payment intents — start from the payout's BTs.

**Step 3 — Sum the `net` column**
The sum should equal the payout's `amount`. If it doesn't, something is wrong (extremely rare — usually means you missed a BT in pagination).

**Step 4 — Identify the unexpected deductions**
Filter the BTs for negative or surprising entries:
- Refunds (`type: refund`) — money the customer doesn't always remember they refunded
- Disputes (`type: adjustment` with reason indicating dispute) — chargebacks
- Chargeback fees (typically $15 each, NOT refunded even if dispute is won)
- Connect fees (if using a platform)
- Stripe processing fees (the cumulative 2.9% + 30c on every charge)

**Step 5 — Communicate with concrete numbers**
> "Your payout was $X. You expected $Y. The $Z difference breaks down as:
> - $A in refunds (3 specific transactions: ch_001, ch_002, ch_003)
> - $B in chargeback fees (1 dispute: dp_001)
> - $C in Stripe processing fees for the period"

==The wrong approach is to start by listing payments and summing them.== That works backwards from the customer's perspective but doesn't tell you what actually composed the payout. Always start from the payout, follow its BTs, and let the BTs lead you to the source objects.

### "Why does Stripe show different amounts than my bank?"

The Stripe balance and your bank balance are not the same:
- **Stripe pending balance**: charges that haven't reached `available` status
- **Stripe available balance**: ready for payout
- **Bank balance**: only includes payouts that have actually deposited

There's typically a 2-3 day lag between charge and bank deposit for US standard accounts.

### "Is my charge real?"

Check `livemode` first. If `false`, it's a test mode charge — no actual money moved.

## Field expansion (preview for Thursday)

Stripe lets you expand related objects in a single request, avoiding multiple round trips:

```
GET /v1/charges/ch_xxx?expand[]=balance_transaction&expand[]=payment_intent
```

This returns the Charge with the full BalanceTransaction and PaymentIntent objects nested inside. Useful for triage when you don't want 3 separate API calls.

We'll cover this in detail Thursday with `payment_intent.latest_charge` and `charge.balance_transaction` patterns.

## Related notes

- `stripe_payment_lifecycle.md` — full flow with timings (subscriptions, invoices, payouts)
- `stripe_issue_triage.md` — AI playbook for diagnosing payment issues
- `Webhooks.md` — how these objects appear in webhook events