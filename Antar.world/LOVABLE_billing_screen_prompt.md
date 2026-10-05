# Lovable prompt — Billing screen (paste into Lovable, Build mode)

```
Build the Billing screen (Settings → Billing) for the Antar web app. The backend owns ALL billing logic —
this screen only reads state and starts hosted checkouts. Do not compute prices, access, trial days or renewal
dates in the browser, and never hardcode a price or a plan name. API base: https://antar-fastapi-production.up.railway.app
(use the existing API client; send the signed-in user's Supabase JWT as `Authorization: Bearer <token>` on every call).

## What to show (one card, mobile-first, our existing design system, dark mode)
Load, in parallel:
  GET /api/v1/subscription/{chart_id}      -> { billing: {state, is_paid, plan, provider, renews_on, ends_on,
                                               cancel_at_period_end, can_cancel, can_resume, manage_in_store} , ...}
  GET /api/v1/me/entitlements              -> { tier, flagship_trial: {active, days_left, ends_on}, ... }
  GET /api/v1/payments/pricing             -> { provider: "stripe"|"razorpay", monthly:{display}, annual:{display},
                                               model: "subscription"|"packs", packs?:[...], subscription_available? }
(chart_id = the user's primary chart. The pricing endpoint auto-detects country; show `monthly.display` / `annual.display`
exactly as returned — they are already formatted and localised.)

Render by `billing.state`:
- "free": headline "You're on the free plan". If `flagship_trial.active`: a calm banner "Full access for N more days
  (until {ends_on})" with `days_left`. Below it the Upgrade block (see below).
- "active": "Antar Operator — active", "Renews on {renews_on}", a "Manage payment method" button (Stripe only) and a
  quiet "Cancel subscription" text button (only if `can_cancel`).
- "cancelling": "Your subscription ends on {ends_on}. You keep full access until then." + a primary "Keep my
  subscription" button (only if `can_resume`; otherwise a "Subscribe again" button after the end date).
- "payment_failed": a warm warning "We couldn't renew your subscription. You still have access until {ends_on} — please
  update your payment method." with a primary "Update payment method" button (Stripe portal).
- If `billing.manage_in_store` is true: show "Your subscription is managed in the App Store / Google Play" with no
  cancel button.
Dates: format in the user's locale. Never show raw status strings, provider ids, or the word "plan: paid".

## Upgrade block (free users)
Two options side by side (stack on mobile): Monthly `monthly.display` and Annual `annual.display` (mark Annual
"Best value" — do NOT compute a savings percentage yourself). One button each: "Start monthly" / "Start annual".

### provider === "stripe"  (use Stripe's HOSTED Checkout page — we do not build a card form)
  POST /api/v1/payments/stripe/create-checkout
  body: { chart_id, plan_key: "ask_unlimited_monthly" | "ask_unlimited_annual",
          success_url: "https://antar.world/settings/billing?checkout=success&session_id={CHECKOUT_SESSION_ID}",
          cancel_url:  "https://antar.world/settings/billing?checkout=cancelled",
          current_country: <ISO code from the pricing response if present, else omit> }
  -> { checkout_url }   then window.location.assign(checkout_url).
  On return with ?checkout=success&session_id=...: show "Confirming your payment…", call
  POST /api/v1/payments/stripe/verify { session_id, chart_id }, then poll GET /api/v1/subscription/{chart_id}
  every 2s up to 20s until billing.state === "active" (the webhook is the source of truth and can lag a few seconds).
  On timeout: "Your payment went through — it can take a minute to show. Refresh in a moment." (never say it failed).
  ?checkout=cancelled: back to the Upgrade block with a neutral note, no error styling.
  "Manage payment method" / "Update payment method": POST /api/v1/me/billing/portal -> { url } -> open it (Stripe's
  hosted customer portal also handles invoices and card changes).

### provider === "razorpay"  (India — use Razorpay's own Checkout modal)
  If `subscription_available` is true (a subscription exists):
    POST /api/v1/payments/razorpay/create-subscription { chart_id, plan_key } -> { subscription_id, key_id }
    Load https://checkout.razorpay.com/v1/checkout.js once, then:
      new Razorpay({ key: key_id, subscription_id, name: "Antar", description: "Antar Operator",
        handler: (r) => POST /api/v1/payments/razorpay/verify-subscription
                       { payment_id: r.razorpay_payment_id, subscription_id: r.razorpay_subscription_id,
                         signature: r.razorpay_signature, chart_id, plan_key } })
      .open()
    After verify succeeds, poll /subscription/{chart_id} as above until state === "active".
  Otherwise (model === "packs"): show `packs` as three cards (label, display price, per-ask price). Tap ->
    POST /api/v1/payments/razorpay/create-pack-order { chart_id, pack_key } -> open Razorpay Checkout with order_id
    -> on success POST /api/v1/payments/razorpay/verify-pack { payment_id, order_id, signature, chart_id, pack_key }
    -> "Added N asks" toast and refresh /me/entitlements.

## Cancel / resume (Stripe + Razorpay subscriptions)
- "Cancel subscription" opens a confirm sheet: "You'll keep access until {renews_on}. Cancel?" [Keep it] [Cancel at period end].
  POST /api/v1/subscription/cancel (no body) -> returns { subscription: <billing view> }; re-render from it.
  409 { error: "manage_in_store" } -> show the store message. Any other error -> "Couldn't cancel right now — try again
  or contact support" (never claim it worked).
- "Keep my subscription": POST /api/v1/subscription/resume -> re-render from the returned view.

## Mobile app (Capacitor wrapper) — IMPORTANT
The iOS and Android apps load this same site. Apple and Google require in-app purchase for digital subscriptions, so
when `Capacitor.isNativePlatform()` is true DO NOT show the Stripe/Razorpay upgrade buttons: show a placeholder
"Upgrade in the app" slot wired to a `startNativePurchase(planKey)` function that currently shows "Coming soon" (the
native IAP bridge is a separate piece of work). Status, cancel-in-store messaging and the trial banner still render
on native. On the web everything above applies.

## Rules
- No pricing copy anywhere else on the site; prices appear only on this screen, straight from the API.
- Loading: skeletons, never a flash of "free" for a paying user (hold the card until the subscription call returns).
- Errors from the API: friendly one-liners; never expose raw JSON or provider messages.
- Accessibility: buttons have visible focus, state changes announced (aria-live) after cancel / resume / payment.
- Add data-testid on: billing-state, upgrade-monthly, upgrade-annual, cancel-subscription, resume-subscription,
  manage-payment, trial-banner.
```

## Notes for Raman (not part of the prompt)
- **Stripe** → hosted Checkout (redirect) + hosted Customer Portal: no card form to build or secure.
- **India** → Razorpay's own Checkout modal (supports UPI, cards, netbanking, and recurring UPI AutoPay for
  subscriptions); it is the hosted screen, so **Dodo isn't needed**. Dodo Payments would only make sense as a
  merchant-of-record (they handle tax/VAT/GST on your behalf) — a separate commercial decision, and it would be a
  third integration we haven't built.
- **Apple/Google**: digital subscriptions inside the iOS/Android apps must use in-app purchase (App Store 3.1.1),
  which is why the prompt hides the web checkout on native.
- Backend contract is final in `Antar.world/PAYMENTS_GO_LIVE_CHECKLIST.md`.
