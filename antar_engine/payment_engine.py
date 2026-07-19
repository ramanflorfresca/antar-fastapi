"""
antar_engine/payment_engine.py

Stripe + Razorpay payment handling.
Detects provider by country and creates checkout sessions.
"""

import os
from datetime import datetime, timezone, timedelta


# ── Plan price IDs ────────────────────────────────────────────────
# Set these after creating products in Stripe/Razorpay dashboards

# ══════════════════════════════════════════════════════════════════
# STRIPE PRICES — Actual prices from Stripe Dashboard (April 2, 2026)
# Plans: seeker_monthly, navigator_monthly, navigator_annual
# Strategy: Below Spotify in every LATAM market
# ══════════════════════════════════════════════════════════════════

# [pricing-2026-07] ONE paid tier. USD $4.99/mo, $39.99/yr.
#   - paid_monthly / paid_annual are the only live keys.
#   - Regional prices sit at ~45-55% of US for LATAM and ~25% for India,
#     anchored below the local Spotify/Netflix price in each market.
#   - Annual discounts run DEEPER outside the US (36-44% vs 33%): card
#     failure and involuntary churn are much higher there, so twelve months
#     paid up front is worth more than the extra margin.
STRIPE_PRICES = {
    "paid_monthly": os.getenv("STRIPE_PRICE_PAID_MONTHLY", ""),   # $4.99
    "paid_annual":  os.getenv("STRIPE_PRICE_PAID_ANNUAL", ""),    # $39.99
    # [model-c 2026-06-29] Single subscription — the only live plan keys.
    "ask_unlimited_monthly": os.getenv("STRIPE_PRICE_ASK_UNLIMITED_MONTHLY", ""),
    "ask_unlimited_annual":  os.getenv("STRIPE_PRICE_ASK_UNLIMITED_ANNUAL", ""),
    # DEPRECATED tier keys — retained so historical/in-flight webhooks
    # resolve; unreachable from the current pricing UI.
    "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY", ""),
    "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY", ""),
    "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL", ""),
}

# Country-specific Stripe Price IDs
STRIPE_PRICES_BY_COUNTRY = {
    "CO": {  # Colombia — COP | Seeker $14,900 | Nav $24,900 | No annual yet
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_COP", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_COP", ""),
        "navigator_annual":    "",  # Not created in Stripe yet
        # [pricing-2026-07] COP 12,900 / COP 99,900 (~35% off)
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_COP", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_COP", ""),
    },
    "MX": {  # Mexico — MXN | Seeker $79 | Nav $129 | Nav Annual $1,290
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_MXN", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_MXN", ""),
        # [pricing-2026-07] MX$49 / MX$399 (~32% off)
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_MXN", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_MXN", ""),
    },
    "BR": {  # Brazil — BRL | Seeker R$19.90 | Nav R$39.90 | Nav Annual R$399.90
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_BRL", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_BRL", ""),
        # [pricing-2026-07] R$12.90 / R$99 (~36% off)
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_BRL", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_BRL", ""),
    },
    "AR": {  # Argentina — ARS | Seeker $2,990 | Nav $5,990 | Nav Annual $45,900
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_ARS", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_ARS", ""),
        # [pricing-2026-07] priced in USD — ARS inflation makes a fixed price stale in months
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_ARS", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_ARS", ""),
    },
    "PE": {  # Peru — PEN | Seeker S/12.90 | Nav S/21.90 | Nav Annual S/199.90
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_PEN", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_PEN", ""),
        # [pricing-2026-07] S/9.90 / S/79 (~33% off)
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_PEN", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_PEN", ""),
    },
    "EC": {  # Ecuador — USD | Seeker $4.99 | Nav $7.99 | Nav Annual $74.99
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_EC", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_EC", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_EC", ""),
        # [pricing-2026-07] USD $2.99 / $24.99 — Ecuador uses USD but at LATAM purchasing power
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_EC", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_EC", ""),
    },
    "IN": {  # India — INR | ₹149/mo, ₹999/yr (~44% off)
        # [pricing-2026-07] Added — there was no IN block, so Indian users
        # fell through to USD pricing. ₹149 is the local Netflix-mobile /
        # YouTube-Premium anchor; ₹999 is the strong annual price point.
        # NOTE: Stripe requires an Indian entity to charge in INR. Without
        # one these stay empty and IN falls back to USD.
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_INR", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_INR", ""),
    },
    "CA": {  # Canada — CAD | Seeker C$12.99 | Nav C$19.99 | Nav Annual C$199.99
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_CAD", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_CAD", ""),
        # [pricing-2026-07] CA$6.99 / CA$54.99 (~34% off) — near US parity, high-income market
        "paid_monthly":        os.getenv("STRIPE_PRICE_PAID_MONTHLY_CAD", ""),
        "paid_annual":         os.getenv("STRIPE_PRICE_PAID_ANNUAL_CAD", ""),
    },
}

# Currency map
COUNTRY_CURRENCY = {
    "CO": "cop", "MX": "mxn", "BR": "brl", "AR": "ars",
    "PE": "pen", "CL": "clp", "CA": "cad", "IN": "inr",
    "US": "usd", "GB": "gbp", "EC": "usd",
    # USD-priced LATAM (no dedicated Stripe prices — use fallback)
    "PA": "usd", "UY": "usd", "CR": "usd", "DO": "usd",
    "GT": "usd", "BO": "usd", "PY": "usd", "HN": "usd",
    "SV": "usd", "NI": "usd", "VE": "usd", "CL": "clp",
}

# Fallback amounts (smallest currency unit) — used when no Stripe Price ID is configured
PLAN_AMOUNTS_BY_COUNTRY = {
    # Amounts from actual Stripe CSV (in smallest currency unit)
    "CO": {"seeker_monthly": 1490000, "navigator_monthly": 2490000, "navigator_annual": 24900000, "currency": "cop"},
    "MX": {"seeker_monthly": 7900, "navigator_monthly": 12900, "navigator_annual": 129000, "currency": "mxn"},
    "BR": {"seeker_monthly": 1990, "navigator_monthly": 3990, "navigator_annual": 39990, "currency": "brl"},
    "AR": {"seeker_monthly": 299000, "navigator_monthly": 599000, "navigator_annual": 4590000, "currency": "ars"},
    "PE": {"seeker_monthly": 1290, "navigator_monthly": 2190, "navigator_annual": 19990, "currency": "pen"},
    "EC": {"seeker_monthly": 499, "navigator_monthly": 799, "navigator_annual": 7499, "currency": "usd"},
    "CA": {"seeker_monthly": 1299, "navigator_monthly": 1999, "navigator_annual": 19999, "currency": "cad"},
    # USD-priced LATAM (discounted from US price)
    "PA": {"seeker_monthly": 499, "navigator_monthly": 799, "navigator_annual": 7499, "currency": "usd"},
    "CR": {"seeker_monthly": 499, "navigator_monthly": 799, "navigator_annual": 7499, "currency": "usd"},
    "DO": {"seeker_monthly": 499, "navigator_monthly": 799, "navigator_annual": 7499, "currency": "usd"},
    "UY": {"seeker_monthly": 699, "navigator_monthly": 1099, "navigator_annual": 10900, "currency": "usd"},
    "GT": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "BO": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "PY": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "HN": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "SV": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "NI": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
    "VE": {"seeker_monthly": 399, "navigator_monthly": 599, "navigator_annual": 5900, "currency": "usd"},
}


def get_stripe_price_for_country(plan_key: str, country_code: str = "US") -> tuple:
    """Get the right Stripe Price ID and currency based on plan and country."""
    country_prices = STRIPE_PRICES_BY_COUNTRY.get(country_code, {})
    price_id = country_prices.get(plan_key, "")
    if price_id:
        return price_id, COUNTRY_CURRENCY.get(country_code, "usd")
    price_id = STRIPE_PRICES.get(plan_key, "")
    return price_id, "usd"

RAZORPAY_PLANS = {
    # [pricing-3bucket 2026-06-29] India excluded this launch — no Ask sub
    # via Razorpay. DEPRECATED tier keys retained for historical orders.
    "seeker_monthly":      os.getenv("RAZORPAY_PLAN_SEEKER_MONTHLY", ""),
    "navigator_monthly":   os.getenv("RAZORPAY_PLAN_NAVIGATOR_MONTHLY", ""),
    "navigator_annual":    os.getenv("RAZORPAY_PLAN_NAVIGATOR_ANNUAL", ""),
}

PLAN_AMOUNTS_INR = {
    # [pricing-3bucket 2026-06-29] India excluded this launch — no Ask sub.
    "seeker_monthly":      14900,    # ₹149 in paise  (deprecated)
    "navigator_monthly":   29900,    # ₹299 in paise  (deprecated)
    "navigator_annual":    299000,   # ₹2,990 in paise (deprecated)
}

PLAN_AMOUNTS_USD = {
    "ask_unlimited_monthly": 799,     # $7.99 in cents   [model-c]
    "ask_unlimited_annual":  5999,    # $59.99 in cents  [model-c]
    "seeker_monthly":      799,      # $7.99 in cents  (deprecated)
    "navigator_monthly":   1299,     # $12.99 in cents (deprecated)
    "navigator_annual":    10999,    # $109.99 in cents (deprecated)
}


# ── [pricing-3bucket 2026-06-29] SINGLE SOURCE OF TRUTH ───────────────
# Product IDs identical across Stripe + Apple + Google:
#   ask_unlimited_monthly | ask_unlimited_annual | compat_chart
# Amounts are minor units. BR/MX bill local currency; everyone else bills
# the bucket amount in USD (the cheaper LatAm/AR points are realised on the
# app stores via store price tiers). India is excluded this launch.
PRICING_PRODUCTS = ("ask_unlimited_monthly", "ask_unlimited_annual", "compat_chart")
EXCLUDED_COUNTRIES = {"IN"}

PRICING_BUCKET_BY_COUNTRY = {
    "US": "us_ca", "CA": "us_ca",
    "BR": "latam", "MX": "latam", "CO": "latam", "CL": "latam", "PE": "latam",
    "AR": "argentina",
}
PRICING_DEFAULT_BUCKET = "us_ca"   # rest-of-world bills the US/CA bucket in USD

PRICING_AMOUNTS = {
    "us_ca":     {"ask_unlimited_monthly": 799, "ask_unlimited_annual": 5999, "compat_chart": 99},
    "latam":     {"ask_unlimited_monthly": 399, "ask_unlimited_annual": 2999, "compat_chart": 49},
    "argentina": {"ask_unlimited_monthly": 249, "ask_unlimited_annual": 1999, "compat_chart": 49},
}
# Stripe local-currency billing overrides (BR/MX).
PRICING_LOCAL_CURRENCY = {
    "BR": {"currency": "brl", "ask_unlimited_monthly": 1990, "ask_unlimited_annual": 14900, "compat_chart": 290},
    "MX": {"currency": "mxn", "ask_unlimited_monthly": 7900, "ask_unlimited_annual": 59900, "compat_chart": 990},
}
# Countries with a pre-created Stripe Price catalog (lookup_key currency).
# Everyone else uses on-the-fly price_data at the bucket amount in USD.
CATALOG_CURRENCY_BY_COUNTRY = {"US": "usd", "CA": "usd", "BR": "brl", "MX": "mxn"}


def is_excluded_country(country_code: str) -> bool:
    return (country_code or "").upper() in EXCLUDED_COUNTRIES


def resolve_price(country_code: str, product_key: str):
    """(amount_minor_units, currency) for a product in a country. Local
    currency for BR/MX; otherwise the bucket amount billed in USD. Returns
    (None, None) for unknown (deprecated tier) product keys."""
    cc = (country_code or "US").upper()
    loc = PRICING_LOCAL_CURRENCY.get(cc)
    if loc and product_key in loc:
        return loc[product_key], loc["currency"]
    bucket = PRICING_BUCKET_BY_COUNTRY.get(cc, PRICING_DEFAULT_BUCKET)
    amts = PRICING_AMOUNTS.get(bucket, {})
    if product_key in amts:
        return amts[product_key], "usd"
    return None, None


def stripe_lookup_key(country_code: str, product_key: str):
    """lookup_key into the pre-created Stripe catalog, or None when the
    country bills on the fly (LatAm-other / Argentina / rest-of-world)."""
    cur = CATALOG_CURRENCY_BY_COUNTRY.get((country_code or "").upper())
    return f"{product_key}_{cur}" if cur else None


_PRICE_ID_CACHE = {}
def _stripe_price_id_for_lookup(lookup_key: str) -> str:
    """Resolve a Stripe Price id from a lookup_key (cached). Empty on miss."""
    if not lookup_key:
        return ""
    if lookup_key in _PRICE_ID_CACHE:
        return _PRICE_ID_CACHE[lookup_key]
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        res = stripe.Price.list(lookup_keys=[lookup_key], limit=1)
        pid = res.data[0].id if res.data else ""
    except Exception:
        pid = ""
    if pid:
        _PRICE_ID_CACHE[lookup_key] = pid
    return pid


def create_stripe_checkout(
    chart_id: str,
    plan_key: str,
    success_url: str,
    cancel_url: str,
    country_code: str = "US",
    customer: str = "",
    user_id: str = "",
) -> dict:
    """
    Create Stripe checkout session with global country-aware pricing.
    
    17 countries supported:
      US/CA: USD/CAD — standard pricing
      CO/MX/BR/AR/PE/CL: local currency — below Spotify
      PA/EC/CR/DO/UY/GT/BO/PY/HN/SV/NI/VE: USD discounted
    
    Uses automatic_payment_methods for PSE, Nequi, OXXO, PIX, SPEI.
    """
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

        # [pricing-3bucket 2026-06-29] region gating + single-model pricing.
        if is_excluded_country(country_code):
            return {"error": "unavailable_in_region",
                    "country": (country_code or "").upper()}

        price_id, currency, amount = "", "usd", None
        if plan_key in ("ask_unlimited_monthly", "ask_unlimited_annual"):
            # Catalog Price for US/CA(usd), BR(brl), MX(mxn); everyone else
            # bills the bucket amount in USD on the fly.
            _lk = stripe_lookup_key(country_code, plan_key)
            if _lk:
                price_id = _stripe_price_id_for_lookup(_lk)
            if not price_id:
                amount, currency = resolve_price(country_code, plan_key)
        else:
            # DEPRECATED tier keys — legacy env-var catalog + fallback.
            price_id, currency = get_stripe_price_for_country(plan_key, country_code)
            if not price_id:
                _ca = PLAN_AMOUNTS_BY_COUNTRY.get(country_code, {})
                amount = _ca.get(plan_key, PLAN_AMOUNTS_USD.get(plan_key, 999))
                currency = _ca.get("currency", "usd")

        if not price_id:
            # Build on the fly from the resolved amount/currency.
            plan_name = plan_key.replace("_", " ").title()
            interval = "year" if "annual" in plan_key else "month"

            session = stripe.checkout.Session.create(
                line_items=[{
                    "price_data": {
                        "currency":     currency,
                        "unit_amount":  amount,
                        "product_data": {
                            "name":        f"Antar {plan_name}",
                            "description": "AI life navigation platform",
                        },
                        "recurring": {"interval": interval},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                client_reference_id=chart_id,
                metadata={"chart_id": chart_id, "plan": plan_key, "country": country_code, "user_id": user_id},
                subscription_data={"metadata": {"chart_id": chart_id, "plan": plan_key, "user_id": user_id}},
                **({"customer": customer} if customer else {}),
                payment_method_types=["card"],
            )
        else:
            session = stripe.checkout.Session.create(
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                client_reference_id=chart_id,
                metadata={"chart_id": chart_id, "plan": plan_key, "country": country_code, "user_id": user_id},
                subscription_data={"metadata": {"chart_id": chart_id, "plan": plan_key, "user_id": user_id}},
                **({"customer": customer} if customer else {}),
                payment_method_types=["card"],
            )
        return {
            "provider":    "stripe",
            "checkout_url": session.url,
            "session_id":  session.id,
        }
    except Exception as e:
        return {"error": str(e)}


def create_compat_slot_checkout(
    chart_id: str,
    success_url: str,
    cancel_url: str,
    country_code: str = "US",
    customer: str = "",
    user_id: str = "",
) -> dict:
    """[compat-slots] One-time $0.99 payment for one additional compatibility
    chart slot. mode="payment" — the webhook routes on metadata.type, so this
    can NEVER activate a subscription. Single global USD price at launch;
    IN/Razorpay + LATAM (Nequi/PSE/PIX) localisation is a follow-up."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        if is_excluded_country(country_code):
            return {"error": "unavailable_in_region",
                    "country": (country_code or "").upper()}
        _amt, _cur = resolve_price(country_code, "compat_chart")
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": _cur,
                    "unit_amount": _amt,
                    "product_data": {
                        "name": "Antar — additional compatibility chart",
                        "description": "Permanently unlock full compatibility with one more chart",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            client_reference_id=chart_id,
            metadata={"type": "compat_slot", "chart_id": chart_id,
                      "country": country_code, "user_id": user_id},
            **({"customer": customer} if customer else {}),
            payment_method_types=["card"],
        )
        return {"provider": "stripe", "checkout_url": session.url,
                "session_id": session.id}
    except Exception as e:
        return {"error": str(e)}


def verify_stripe_session(session_id: str) -> dict:
    """Verify a completed Stripe checkout session."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status in ("paid", "no_payment_required"):
            chart_id = session.client_reference_id or                        session.metadata.get("chart_id", "")
            plan_key = session.metadata.get("plan", "ask_unlimited_monthly")
            plan     = plan_key.split("_")[0]  # "seeker" or "navigator"
            sub_id   = session.subscription or session.payment_intent or ""
            # P1 fix: derive the real period from the Stripe subscription.
            # Previously hardcoded 30 days, so annual plans expired early in the DB.
            period_end = None
            try:
                if session.subscription:
                    _sub = stripe.Subscription.retrieve(str(session.subscription))
                    _cpe = _sub.get("current_period_end")
                    if _cpe:
                        period_end = datetime.fromtimestamp(_cpe, tz=timezone.utc).isoformat()
            except Exception:
                period_end = None
            if not period_end:
                _days = 366 if ("annual" in plan_key or "yearly" in plan_key) else 32
                period_end = (
                    datetime.now(timezone.utc) + timedelta(days=_days)
                ).isoformat()
            return {
                "verified":   True,
                "chart_id":   chart_id,
                "plan":       plan,
                "sub_id":     str(sub_id),
                "period_end": period_end,
            }
        return {"verified": False, "status": session.payment_status}
    except Exception as e:
        return {"error": str(e)}


def create_razorpay_order(
    chart_id: str,
    plan_key: str,
) -> dict:
    """Create Razorpay order for Indian payments."""
    # [pricing-3bucket 2026-06-29] India is excluded this launch — the Ask
    # subscription is not sold via Razorpay.
    if plan_key in ("ask_unlimited_monthly", "ask_unlimited_annual"):
        return {"error": "unavailable_in_region", "country": "IN"}
    try:
        import razorpay
        client = razorpay.Client(
            auth=(
                os.getenv("RAZORPAY_KEY_ID", ""),
                os.getenv("RAZORPAY_KEY_SECRET", ""),
            )
        )

        amount   = PLAN_AMOUNTS_INR.get(plan_key, 39900)
        plan_name = plan_key.replace("_", " ").title()

        # Try subscription plan first
        plan_id = RAZORPAY_PLANS.get(plan_key, "")
        if plan_id:
            sub = client.subscription.create({
                "plan_id":         plan_id,
                "total_count":     12,
                "quantity":        1,
                "notes":           {"chart_id": chart_id, "plan": plan_key},
            })
            return {
                "provider":       "razorpay",
                "subscription_id": sub["id"],
                "key_id":         os.getenv("RAZORPAY_KEY_ID", ""),
                "amount":         amount,
                "currency":       "INR",
                "plan_name":      f"Antar {plan_name}",
                "chart_id":       chart_id,
                "plan_key":       plan_key,
            }
        else:
            # One-time order fallback
            order = client.order.create({
                "amount":   amount,
                "currency": "INR",
                "notes":    {"chart_id": chart_id, "plan": plan_key},
            })
            return {
                "provider":  "razorpay",
                "order_id":  order["id"],
                "key_id":    os.getenv("RAZORPAY_KEY_ID", ""),
                "amount":    amount,
                "currency":  "INR",
                "plan_name": f"Antar {plan_name}",
                "chart_id":  chart_id,
                "plan_key":  plan_key,
            }
    except Exception as e:
        return {"error": str(e)}


def verify_razorpay_payment(
    payment_id: str,
    order_id: str,
    signature: str,
    chart_id: str,
    plan_key: str,
) -> dict:
    """Verify Razorpay payment signature."""
    try:
        import razorpay, hmac, hashlib
        client = razorpay.Client(
            auth=(
                os.getenv("RAZORPAY_KEY_ID", ""),
                os.getenv("RAZORPAY_KEY_SECRET", ""),
            )
        )

        # Verify signature
        secret  = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
        message = f"{order_id}|{payment_id}".encode()
        digest  = hmac.new(secret, message, hashlib.sha256).hexdigest()

        if digest == signature:
            plan       = plan_key.split("_")[0]
            period_end = (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat()
            return {
                "verified":   True,
                "chart_id":   chart_id,
                "plan":       plan,
                "sub_id":     payment_id,
                "period_end": period_end,
            }
        return {"verified": False, "reason": "signature_mismatch"}
    except Exception as e:
        return {"error": str(e)}
