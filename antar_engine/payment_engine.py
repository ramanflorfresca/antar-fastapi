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

# USD (US/Global) — Seeker $7.99/mo, Navigator $12.99/mo, Nav Annual $109.99/yr
STRIPE_PRICES = {
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
    },
    "MX": {  # Mexico — MXN | Seeker $79 | Nav $129 | Nav Annual $1,290
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_MXN", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_MXN", ""),
    },
    "BR": {  # Brazil — BRL | Seeker R$19.90 | Nav R$39.90 | Nav Annual R$399.90
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_BRL", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_BRL", ""),
    },
    "AR": {  # Argentina — ARS | Seeker $2,990 | Nav $5,990 | Nav Annual $45,900
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_ARS", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_ARS", ""),
    },
    "PE": {  # Peru — PEN | Seeker S/12.90 | Nav S/21.90 | Nav Annual S/199.90
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_PEN", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_PEN", ""),
    },
    "EC": {  # Ecuador — USD | Seeker $4.99 | Nav $7.99 | Nav Annual $74.99
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_EC", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_EC", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_EC", ""),
    },
    "CA": {  # Canada — CAD | Seeker C$12.99 | Nav C$19.99 | Nav Annual C$199.99
        "seeker_monthly":      os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_CAD", ""),
        "navigator_monthly":   os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD", ""),
        "navigator_annual":    os.getenv("STRIPE_PRICE_NAVIGATOR_ANNUAL_CAD", ""),
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
    "seeker_monthly":      os.getenv("RAZORPAY_PLAN_SEEKER_MONTHLY", ""),
    "navigator_monthly":   os.getenv("RAZORPAY_PLAN_NAVIGATOR_MONTHLY", ""),
    "navigator_annual":    os.getenv("RAZORPAY_PLAN_NAVIGATOR_ANNUAL", ""),
}

PLAN_AMOUNTS_INR = {
    "seeker_monthly":      14900,    # ₹149 in paise
    "navigator_monthly":   29900,    # ₹299 in paise
    "navigator_annual":    299000,   # ₹2,990 in paise
}

PLAN_AMOUNTS_USD = {
    "seeker_monthly":      799,      # $7.99 in cents
    "navigator_monthly":   1299,     # $12.99 in cents
    "navigator_annual":    10999,    # $109.99 in cents
}


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

        price_id, currency = get_stripe_price_for_country(plan_key, country_code)

        if not price_id:
            # No pre-created Price — build on the fly from fallback amounts
            country_amounts = PLAN_AMOUNTS_BY_COUNTRY.get(country_code, {})
            if country_amounts:
                amount = country_amounts.get(plan_key, 999)
                currency = country_amounts.get("currency", "usd")
            else:
                amount = PLAN_AMOUNTS_USD.get(plan_key, 999)
                currency = "usd"

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


def verify_stripe_session(session_id: str) -> dict:
    """Verify a completed Stripe checkout session."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status in ("paid", "no_payment_required"):
            chart_id = session.client_reference_id or                        session.metadata.get("chart_id", "")
            plan_key = session.metadata.get("plan", "seeker_monthly")
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
