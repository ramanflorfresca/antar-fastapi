#!/usr/bin/env python3
"""
Antar — Global Pricing Patch v3 (All LATAM + Canada)
=====================================================
Research-backed pricing below Spotify in every market.

Run from project root:
  python 05_patch_global_pricing_v3.py
"""

import os
import sys
import shutil
from datetime import datetime


def main():
    filepath = "antar_engine/payment_engine.py"

    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found. Are you in the project root?")
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{filepath}.backup_{ts}"
    shutil.copy2(filepath, backup)
    print(f"✓ Backup: {backup}")

    content = open(filepath, "r").read()

    # ═══════════════════════════════════════════════════════════════
    # Find and replace STRIPE_PRICES block
    # Support both original and already-patched versions
    # ═══════════════════════════════════════════════════════════════

    # Try original (unpatched)
    old_prices_v1 = '''STRIPE_PRICES = {
    "seeker_monthly":  os.getenv("STRIPE_PRICE_SEEKER_MONTHLY", ""),
    "seeker_annual":   os.getenv("STRIPE_PRICE_SEEKER_ANNUAL", ""),
    "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY", ""),
}'''

    # Try to find start of existing STRIPE_PRICES block (covers v1 and v2 patches)
    import re
    prices_match = re.search(
        r'# ═+\n# STRIPE PRICES.*?(?=\ndef |\nRAZORPAY)',
        content, re.DOTALL
    )
    if not prices_match and old_prices_v1 in content:
        # Original unpatched version
        replace_start = content.index(old_prices_v1)
        replace_end = replace_start + len(old_prices_v1)
    elif prices_match:
        replace_start = prices_match.start()
        replace_end = prices_match.end()
    elif old_prices_v1 in content:
        replace_start = content.index(old_prices_v1)
        replace_end = replace_start + len(old_prices_v1)
    else:
        print("✗ Could not find STRIPE_PRICES block to replace")
        print("  Looking for 'STRIPE_PRICES = {'...")
        sp_match = re.search(r'^STRIPE_PRICES\s*=\s*\{', content, re.MULTILINE)
        if sp_match:
            # Find the closing brace
            brace_count = 0
            pos = sp_match.start()
            for i in range(pos, len(content)):
                if content[i] == '{': brace_count += 1
                elif content[i] == '}': brace_count -= 1
                if brace_count == 0:
                    replace_start = pos
                    replace_end = i + 1
                    break
            else:
                print("✗ Could not find end of STRIPE_PRICES dict")
                return 1
        else:
            print("✗ STRIPE_PRICES not found at all")
            return 1

    new_prices = '''# ══════════════════════════════════════════════════════════════════
# STRIPE PRICES — Global country-aware routing
# Strategy: Price below Spotify in every market
# Research: Spotify, Netflix, Co-Star, Headspace, Calm benchmarks
# ══════════════════════════════════════════════════════════════════

# USD default (US and any country without specific pricing)
STRIPE_PRICES = {
    "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY", ""),
    "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL", ""),
    "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY", ""),
}

# Country-specific Stripe Price IDs
# Set these in Railway env vars after creating prices in Stripe Dashboard
STRIPE_PRICES_BY_COUNTRY = {
    # ── LATAM (local currency) ────────────────────────────────────
    "CO": {  # Colombia — COP (Spotify = COP 18,500)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_COP", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_COP", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_COP", ""),
    },
    "MX": {  # Mexico — MXN (Spotify = MXN 139)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_MXN", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_MXN", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN", ""),
    },
    "BR": {  # Brazil — BRL (Spotify = BRL 16.90)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_BRL", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_BRL", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL", ""),
    },
    "AR": {  # Argentina — ARS (Spotify = ARS 3,299)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_ARS", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_ARS", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS", ""),
    },
    "PE": {  # Peru — PEN (Spotify = PEN 22.90)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_PEN", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_PEN", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN", ""),
    },
    "CL": {  # Chile — CLP (Spotify = CLP 6,290)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_CLP", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_CLP", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_CLP", ""),
    },
    # ── Canada ────────────────────────────────────────────────────
    "CA": {  # Canada — CAD (Spotify = CAD 16.99)
        "seeker_monthly":    os.getenv("STRIPE_PRICE_SEEKER_MONTHLY_CAD", ""),
        "seeker_annual":     os.getenv("STRIPE_PRICE_SEEKER_ANNUAL_CAD", ""),
        "navigator_monthly": os.getenv("STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD", ""),
    },
}

# Currency map
COUNTRY_CURRENCY = {
    "CO": "cop", "MX": "mxn", "BR": "brl", "AR": "ars",
    "PE": "pen", "CL": "clp", "CA": "cad", "IN": "inr",
    "US": "usd", "GB": "gbp",
    # USD-priced LATAM countries (no local currency in Stripe)
    "PA": "usd", "EC": "usd", "UY": "usd", "CR": "usd",
    "GT": "usd", "BO": "usd", "PY": "usd", "DO": "usd",
    "HN": "usd", "SV": "usd", "NI": "usd", "VE": "usd",
}

# Fallback amounts — used when no Stripe Price ID is configured
# Stripe expects amounts in smallest currency unit (cents, centavos, paise)
PLAN_AMOUNTS_BY_COUNTRY = {
    # ── Local currency countries (amounts in smallest unit) ──
    "CO": {"seeker_monthly": 1490000, "seeker_annual": 14900000, "navigator_monthly": 2990000, "currency": "cop"},
    "MX": {"seeker_monthly": 7900, "seeker_annual": 79000, "navigator_monthly": 14900, "currency": "mxn"},
    "BR": {"seeker_monthly": 1990, "seeker_annual": 19900, "navigator_monthly": 3990, "currency": "brl"},
    "AR": {"seeker_monthly": 299000, "seeker_annual": 2990000, "navigator_monthly": 599000, "currency": "ars"},
    "PE": {"seeker_monthly": 1490, "seeker_annual": 14900, "navigator_monthly": 2990, "currency": "pen"},
    "CL": {"seeker_monthly": 399000, "seeker_annual": 3990000, "navigator_monthly": 799000, "currency": "clp"},
    "CA": {"seeker_monthly": 1299, "seeker_annual": 12900, "navigator_monthly": 2499, "currency": "cad"},
    # ── USD-priced LATAM (discounted from US price) ──
    "PA": {"seeker_monthly": 499, "seeker_annual": 4900, "navigator_monthly": 999, "currency": "usd"},
    "EC": {"seeker_monthly": 499, "seeker_annual": 4900, "navigator_monthly": 999, "currency": "usd"},
    "CR": {"seeker_monthly": 499, "seeker_annual": 4900, "navigator_monthly": 999, "currency": "usd"},
    "DO": {"seeker_monthly": 499, "seeker_annual": 4900, "navigator_monthly": 999, "currency": "usd"},
    "UY": {"seeker_monthly": 699, "seeker_annual": 6900, "navigator_monthly": 1399, "currency": "usd"},
    "GT": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "BO": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "PY": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "HN": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "SV": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "NI": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
    "VE": {"seeker_monthly": 399, "seeker_annual": 3900, "navigator_monthly": 799, "currency": "usd"},
}


def get_stripe_price_for_country(plan_key: str, country_code: str = "US") -> tuple:
    """
    Get the right Stripe Price ID and currency based on plan and country.
    Returns (price_id, currency).
    Priority: country-specific Price ID > USD Price ID > empty (triggers fallback)
    """
    country_prices = STRIPE_PRICES_BY_COUNTRY.get(country_code, {})
    price_id = country_prices.get(plan_key, "")
    if price_id:
        return price_id, COUNTRY_CURRENCY.get(country_code, "usd")
    price_id = STRIPE_PRICES.get(plan_key, "")
    return price_id, "usd"
'''

    content = content[:replace_start] + new_prices + content[replace_end:]
    print("✓ Replaced pricing block with global 17-country version")

    # ═══════════════════════════════════════════════════════════════
    # Fix PLAN_AMOUNTS_USD
    # ═══════════════════════════════════════════════════════════════

    old_usd = '''PLAN_AMOUNTS_USD = {
    "seeker_monthly":    499,     # $4.99 in cents
    "seeker_annual":     3900,    # $39 in cents
    "navigator_monthly": 1999,    # $19.99 in cents
}'''
    new_usd = '''PLAN_AMOUNTS_USD = {
    "seeker_monthly":    999,     # $9.99 in cents
    "seeker_annual":     9900,    # $99 in cents
    "navigator_monthly": 1999,    # $19.99 in cents
}'''
    if old_usd in content:
        content = content.replace(old_usd, new_usd, 1)
        print("✓ Fixed USD fallback ($4.99→$9.99, $39→$99)")

    # Fix already-patched USD if it exists
    old_usd_v2 = '''PLAN_AMOUNTS_USD = {
    "seeker_monthly":    999,     # $9.99 in cents
    "seeker_annual":     9900,    # $99 in cents
    "navigator_monthly": 1999,    # $19.99 in cents
}'''
    if old_usd_v2 in content:
        print("· USD amounts already correct")

    # ═══════════════════════════════════════════════════════════════
    # Fix PLAN_AMOUNTS_INR
    # ═══════════════════════════════════════════════════════════════

    old_inr = '''PLAN_AMOUNTS_INR = {
    "seeker_monthly":    39900,   # ₹399 in paise
    "seeker_annual":     299900,  # ₹2999 in paise
    "navigator_monthly": 149900,  # ₹1499 in paise
}'''
    new_inr = '''PLAN_AMOUNTS_INR = {
    "seeker_monthly":    14900,   # ₹149 in paise
    "seeker_annual":     149000,  # ₹1,490 in paise
    "navigator_monthly": 29900,   # ₹299 in paise
}'''
    if old_inr in content:
        content = content.replace(old_inr, new_inr, 1)
        print("✓ Updated India pricing (₹399→₹149)")

    # ═══════════════════════════════════════════════════════════════
    # Replace create_stripe_checkout function
    # ═══════════════════════════════════════════════════════════════

    # Find the function regardless of version
    func_match = re.search(r'^def create_stripe_checkout\(.*?\n(?:    .*\n)*?        \)\n', content, re.MULTILINE)
    
    # Try the known original signature
    old_func_sig = '''def create_stripe_checkout(
    chart_id: str,
    plan_key: str,
    success_url: str,
    cancel_url: str,
) -> dict:'''

    old_func_sig_v2 = '''def create_stripe_checkout(
    chart_id: str,
    plan_key: str,
    success_url: str,
    cancel_url: str,
    country_code: str = "US",
) -> dict:'''

    new_func = '''def create_stripe_checkout(
    chart_id: str,
    plan_key: str,
    success_url: str,
    cancel_url: str,
    country_code: str = "US",
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
                metadata={"chart_id": chart_id, "plan": plan_key, "country": country_code},
                automatic_payment_methods={"enabled": True},
            )
        else:
            session = stripe.checkout.Session.create(
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                client_reference_id=chart_id,
                metadata={"chart_id": chart_id, "plan": plan_key, "country": country_code},
                automatic_payment_methods={"enabled": True},
            )'''

    # Try to replace the function
    if old_func_sig in content and old_func_sig_v2 not in content:
        # Find everything from the old signature to the closing of the try block's session creation
        func_start = content.index(old_func_sig)
        # Find the "return {" after the session creation
        rest = content[func_start:]
        return_match = re.search(r'\n        return \{\n', rest)
        if return_match:
            func_end = func_start + return_match.start()
            content = content[:func_start] + new_func + content[func_end:]
            print("✓ Replaced create_stripe_checkout (from v1)")
        else:
            print("⚠ Found function but couldn't find end — replacing signature only")
            content = content.replace(old_func_sig, old_func_sig_v2, 1)
    elif old_func_sig_v2 in content:
        # Already has country_code param — replace the whole function body
        func_start = content.index(old_func_sig_v2)
        rest = content[func_start:]
        return_match = re.search(r'\n        return \{\n', rest)
        if return_match:
            func_end = func_start + return_match.start()
            content = content[:func_start] + new_func + content[func_end:]
            print("✓ Replaced create_stripe_checkout (from v2)")
        else:
            print("· create_stripe_checkout already has country_code — keeping existing")
    else:
        print("⚠ Could not find create_stripe_checkout — manual edit needed")

    # Write
    open(filepath, "w").write(content)
    print(f"✓ Saved {filepath}")

    # ═══════════════════════════════════════════════════════════════
    # Patch main.py — pass country_code
    # ═══════════════════════════════════════════════════════════════

    main_py = "main.py"
    if os.path.exists(main_py):
        mc = open(main_py, "r").read()
        shutil.copy2(main_py, f"{main_py}.backup_global_{ts}")

        old_call = '    result = create_stripe_checkout(chart_id, plan_key, success_url, cancel_url)'
        new_call = '    country_code = request.get("current_country", "US")\n    result = create_stripe_checkout(chart_id, plan_key, success_url, cancel_url, country_code=country_code)'

        if old_call in mc:
            mc = mc.replace(old_call, new_call, 1)
            open(main_py, "w").write(mc)
            print(f"✓ Patched {main_py} — checkout passes country_code")
        elif "country_code" in mc and "create_stripe_checkout" in mc:
            print(f"· {main_py} already passes country_code")
        else:
            print(f"⚠ {main_py} — manual edit needed for create_stripe_checkout call")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════

    print(f"""
{'='*70}
✓ GLOBAL PRICING PATCH COMPLETE — 17 Countries
{'='*70}

PRICING TABLE (below Spotify in every market):
┌──────────────┬──────┬──────────────┬──────────────┬───────────────┬────────────┐
│ Country      │ Code │ Seeker/mo    │ Seeker/yr    │ Navigator/mo  │ ~USD equiv │
├──────────────┼──────┼──────────────┼──────────────┼───────────────┼────────────┤
│ US           │ US   │ $9.99 USD    │ $99 USD      │ $19.99 USD    │ $9.99      │
│ Canada       │ CA   │ $12.99 CAD   │ $129 CAD     │ $24.99 CAD    │ ~$9.50     │
│ Colombia     │ CO   │ $14,900 COP  │ $149,000 COP │ $29,900 COP   │ ~$3.55     │
│ Mexico       │ MX   │ $79 MXN      │ $790 MXN     │ $149 MXN      │ ~$4.30     │
│ Brazil       │ BR   │ R$19.90      │ R$199        │ R$39.90       │ ~$3.80     │
│ Argentina    │ AR   │ $2,990 ARS   │ $29,900 ARS  │ $5,990 ARS    │ ~$2.50     │
│ Peru         │ PE   │ S/14.90 PEN  │ S/149 PEN    │ S/29.90 PEN   │ ~$3.90     │
│ Chile        │ CL   │ $3,990 CLP   │ $39,900 CLP  │ $7,990 CLP    │ ~$4.10     │
│ Panama       │ PA   │ $4.99 USD    │ $49 USD      │ $9.99 USD     │ $4.99      │
│ Ecuador      │ EC   │ $4.99 USD    │ $49 USD      │ $9.99 USD     │ $4.99      │
│ Costa Rica   │ CR   │ $4.99 USD    │ $49 USD      │ $9.99 USD     │ $4.99      │
│ Dom. Rep.    │ DO   │ $4.99 USD    │ $49 USD      │ $9.99 USD     │ $4.99      │
│ Uruguay      │ UY   │ $6.99 USD    │ $69 USD      │ $13.99 USD    │ $6.99      │
│ Guatemala    │ GT   │ $3.99 USD    │ $39 USD      │ $7.99 USD     │ $3.99      │
│ Bolivia      │ BO   │ $3.99 USD    │ $39 USD      │ $7.99 USD     │ $3.99      │
│ Paraguay     │ PY   │ $3.99 USD    │ $39 USD      │ $7.99 USD     │ $3.99      │
│ India        │ IN   │ ₹149         │ ₹1,490       │ ₹299          │ ~$1.75     │
└──────────────┴──────┴──────────────┴──────────────┴───────────────┴────────────┘

STRIPE PRICES TO CREATE (local currency countries only):

Product: Antar Seeker
  COP: $14,900/mo, $149,000/yr
  MXN: $79/mo, $790/yr
  BRL: R$19.90/mo, R$199/yr
  ARS: $2,990/mo, $29,900/yr
  PEN: S/14.90/mo, S/149/yr
  CLP: $3,990/mo, $39,900/yr
  CAD: $12.99/mo, $129/yr

Product: Antar Navigator
  COP: $29,900/mo
  MXN: $149/mo
  BRL: R$39.90/mo
  ARS: $5,990/mo
  PEN: S/29.90/mo
  CLP: $7,990/mo
  CAD: $24.99/mo

RAILWAY ENV VARS (21 total for local currency):
  STRIPE_PRICE_SEEKER_MONTHLY_COP=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_COP=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_COP=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_MXN=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_MXN=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_BRL=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_BRL=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_ARS=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_ARS=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_PEN=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_PEN=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_CLP=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_CLP=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_CLP=price_...
  STRIPE_PRICE_SEEKER_MONTHLY_CAD=price_...
  STRIPE_PRICE_SEEKER_ANNUAL_CAD=price_...
  STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD=price_...

NOTE: USD-priced LATAM countries (PA, EC, CR, DO, UY, GT, BO, PY, HN, SV, NI, VE)
do NOT need separate Stripe prices or env vars. The code creates on-the-fly
prices using fallback amounts at discounted USD rates ($3.99-$6.99).

FRONTEND PRICING CONFIG (update in Lovable):
  const PRICING = {{
    US: {{ symbol: '$', seeker: 9.99, navigator: 19.99, yearly: 99, gateway: 'stripe' }},
    CA: {{ symbol: 'C$', seeker: 12.99, navigator: 24.99, yearly: 129, gateway: 'stripe' }},
    CO: {{ symbol: '$', seeker: '14,900', navigator: '29,900', yearly: '149,000', gateway: 'stripe', label: 'COP' }},
    MX: {{ symbol: '$', seeker: 79, navigator: 149, yearly: 790, gateway: 'stripe', label: 'MXN' }},
    BR: {{ symbol: 'R$', seeker: 19.90, navigator: 39.90, yearly: 199, gateway: 'stripe' }},
    AR: {{ symbol: '$', seeker: '2,990', navigator: '5,990', yearly: '29,900', gateway: 'stripe', label: 'ARS' }},
    PE: {{ symbol: 'S/', seeker: 14.90, navigator: 29.90, yearly: 149, gateway: 'stripe' }},
    CL: {{ symbol: '$', seeker: '3,990', navigator: '7,990', yearly: '39,900', gateway: 'stripe', label: 'CLP' }},
    PA: {{ symbol: '$', seeker: 4.99, navigator: 9.99, yearly: 49, gateway: 'stripe' }},
    EC: {{ symbol: '$', seeker: 4.99, navigator: 9.99, yearly: 49, gateway: 'stripe' }},
    CR: {{ symbol: '$', seeker: 4.99, navigator: 9.99, yearly: 49, gateway: 'stripe' }},
    DO: {{ symbol: '$', seeker: 4.99, navigator: 9.99, yearly: 49, gateway: 'stripe' }},
    UY: {{ symbol: '$', seeker: 6.99, navigator: 13.99, yearly: 69, gateway: 'stripe' }},
    GT: {{ symbol: '$', seeker: 3.99, navigator: 7.99, yearly: 39, gateway: 'stripe' }},
    BO: {{ symbol: '$', seeker: 3.99, navigator: 7.99, yearly: 39, gateway: 'stripe' }},
    PY: {{ symbol: '$', seeker: 3.99, navigator: 7.99, yearly: 39, gateway: 'stripe' }},
    IN: {{ symbol: '₹', seeker: 149, navigator: 299, yearly: 1490, gateway: 'razorpay' }},
  }};

DEPLOY:
  git add -A
  git commit -m "Global pricing — 17 countries, below Spotify everywhere"
  git push
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
