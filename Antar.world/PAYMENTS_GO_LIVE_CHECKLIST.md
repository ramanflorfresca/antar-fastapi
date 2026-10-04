# Payments go-live checklist — Stripe + Razorpay (2026-10-04)

The code is wired end to end. When Stripe and Razorpay approve the accounts, the only work is
**provider setup + testing**. Prices live in the providers (Stripe Prices, Razorpay Plans) — not in code.

## 1. How a subscriber is marked (what the app reads)

`GET /api/v1/subscription/{chart_id}` → `billing`:

| `state` | meaning | access | `is_paid` |
|---|---|---|---|
| `free` | no subscription / ended | free tier | false |
| `active` | paid, renews on `renews_on` | paid | true |
| `cancelling` | user cancelled; **still paid until `ends_on`** | paid | true |
| `payment_failed` | a renewal failed; provider is retrying; ~5 days grace | paid (grace) | true |

`subscriptions` row: `plan` = **`paid`** (always), `status` = active / past_due / cancelled / expired,
`payment_provider` = stripe / razorpay / apple / google, `provider_sub_id`, `current_period_end`,
`is_paid`, and (after the SQL) `cancel_at_period_end`, `canceled_at`, `last_payment_status`.

**Event → result**

| event | result |
|---|---|
| Stripe `checkout.session.completed` / `customer.subscription.created` | paid, period end from Stripe |
| Stripe `invoice.payment_succeeded` / `invoice.paid` | renewed; new period from the invoice line item |
| Stripe `invoice.payment_failed` | `past_due` — access KEPT (grace), not cut on the first failure |
| Stripe `customer.subscription.updated` | active + `cancel_at_period_end` flag, or past_due, or ended (unpaid / canceled) |
| Stripe `customer.subscription.deleted` | cancelled → free |
| Stripe `charge.refunded` (full) / `charge.dispute.created` | ended → free |
| Razorpay `subscription.activated` / `charged` / `resumed` | paid / renewed, period from `current_end` |
| Razorpay `subscription.pending` / `payment.failed` | past_due (grace) |
| Razorpay `subscription.halted` | expired → free |
| Razorpay `subscription.cancelled` / `completed` / `refund.processed` | cancel scheduled (access to `current_end`) / ended |

User actions: `POST /api/v1/subscription/cancel` (at period end; `{"immediate": true}` to end now),
`POST /api/v1/subscription/resume` (Stripe), `POST /api/v1/me/billing/portal` (Stripe customer portal).
Apple / Google subscriptions are cancelled **in the store** (`manage_in_store: true`).

## 2. One-time setup

**Run once (via Lovable):** `sql_subscription_lifecycle.sql` — optional columns; everything works without
them but the app can't show "cancels on …" until they exist.

**Railway variables**
- Stripe: `STRIPE_SECRET_KEY` (live key), `STRIPE_WEBHOOK_SECRET` (signing secret of the webhook below)
- Razorpay: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` (also used for the webhook signature),
  `RAZORPAY_PLAN_ID_MONTHLY`, `RAZORPAY_PLAN_ID_ANNUAL`
- Apple / Google IAP (currently **missing** in Railway): `APPLE_SHARED_SECRET`, `APPLE_BUNDLE_ID`,
  `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`, `GOOGLE_PLAY_PACKAGE`, `GOOGLE_RTDN_TOKEN`

**Stripe dashboard**
1. Create the product "Antar Operator" with a monthly and an annual recurring Price per currency you sell in.
   Give them **lookup keys** `ask_unlimited_monthly_usd`, `ask_unlimited_annual_usd` (and `_brl`, `_mxn`).
   US / CA / BR / MX use these catalog Prices; every other country bills on the fly from `PRICING_AMOUNTS`
   in `payment_engine.py` (that is the part to align with the final regional prices later).
2. Webhook endpoint `https://antar-fastapi-production.up.railway.app/api/v1/payments/stripe/webhook`
   with events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.paid`, `invoice.payment_failed`,
   `charge.refunded`, `charge.dispute.created`. Copy its signing secret → `STRIPE_WEBHOOK_SECRET`.
3. Customer portal → enable "cancel subscription" and "update payment method".

**Razorpay dashboard**
1. Plans: one monthly (₹ amount), one annual → copy the plan ids into the two env vars.
2. Webhook `https://antar-fastapi-production.up.railway.app/api/v1/payments/razorpay/webhook`, secret = the same
   as `RAZORPAY_KEY_SECRET`; events: `subscription.activated`, `.charged`, `.pending`, `.halted`, `.cancelled`,
   `.completed`, `.resumed`, `payment.failed`, `payment.captured` (credit packs), `refund.processed`.

## 3. Test it (use TEST mode first)

**Stripe (test keys, test webhook secret)** — card `4242 4242 4242 4242`, any future date, any CVC.
1. Checkout → expect `billing.state = "active"`, `plan = paid`, `renews_on` set; `GET /entitlements/{chart}` tier `paid`.
2. Renewal: use a **Test Clock** (Billing → Test clocks): attach the customer, advance 1 month →
   `invoice.payment_succeeded` → `renews_on` moves forward one period.
3. Failed renewal: card `4000 0000 0000 0341` (attaches, then fails) + advance the clock →
   `state = "payment_failed"`, access still on; fix the card in the portal → back to `active`.
4. Cancel: `POST /subscription/cancel` (or the portal) → `state = "cancelling"`, still paid; advance the clock past
   the end → `customer.subscription.deleted` → `free`. `POST /subscription/resume` before the end undoes it.
5. Refund the payment fully in the dashboard → `free`.

**Razorpay (test mode)** — UPI `success@razorpay`, card `5267 3181 8797 5449`.
1. `POST /payments/razorpay/create-subscription {chart_id, plan_key}` → open Checkout with `subscription_id`
   + `key_id` → on success `POST /payments/razorpay/verify-subscription {payment_id, subscription_id, signature, chart_id, plan_key}`
   → `active`. The webhook then keeps it in step.
2. Dashboard → subscription → cancel (cycle end) → `cancelling`; let it complete → `free`.

**Automated:** `python -m pytest tests/test_billing_lifecycle.py` (28 tests, runs in CI on every PR).

## 4. Known remaining items
- Final regional prices (`PRICING_AMOUNTS`, Stripe Prices, Razorpay Plans) — set when approved.
- Apple / Google IAP secrets (above) and the Android Play-Billing bridge.
- India: credit packs remain; the subscription turns on when the Razorpay plan ids exist
  (`GET /payments/pricing?country=IN` → `subscription_available`).
