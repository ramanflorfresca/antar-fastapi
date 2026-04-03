#!/usr/bin/env python3
"""
Antar — Payment Engine Patch (from actual Stripe CSV)
======================================================
Updates payment_engine.py to match the ACTUAL prices created in Stripe.

Plans: seeker_monthly, navigator_monthly, navigator_annual
Markets: USD, COP, MXN, BRL, ARS, PEN, USD(Ecuador), CAD

Run from project root:
  python 07_patch_payment_actual_prices.py
"""

import os
import sys
import re
import shutil
from datetime import datetime


def main():
    filepath = "antar_engine/payment_engine.py"
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(filepath, f"{filepath}.backup_{ts}")
    print(f"✓ Backup created")

    content = open(filepath, "r").read()

    # ═══════════════════════════════════════════════════════════════
    # Step 1: Replace seeker_annual → navigator_annual everywhere
    # ═══════════════════════════════════════════════════════════════
    content = content.replace("seeker_annual", "navigator_annual")
    content = content.replace("SEEKER_ANNUAL", "NAVIGATOR_ANNUAL")
    print("✓ Replaced seeker_annual → navigator_annual")

    # ═══════════════════════════════════════════════════════════════
    # Step 2: Find and replace the STRIPE_PRICES block completely
    # ═══════════════════════════════════════════════════════════════

    # Find everything from "# USD default" or "STRIPE_PRICES = {" to just before RAZORPAY
    # We'll replace the entire pricing section

    # Find the start
    start_markers = [
        "# ══════════════════════════════════════════════════════════════════\n# STRIPE PRICES",
        "# USD default",
        "# USD (default",
        "STRIPE_PRICES = {",
    ]
    start_pos = None
    for marker in start_markers:
        idx = content.find(marker)
        if idx >= 0:
            start_pos = idx
            break

    if start_pos is None:
        print("✗ Could not find STRIPE_PRICES section start")
        return 1

    # Find the end — look for RAZORPAY_PLANS or def create_stripe
    end_markers = ["RAZORPAY_PLANS", "def create_stripe_checkout", "def create_razorpay"]
    end_pos = len(content)
    for marker in end_markers:
        idx = content.find(marker, start_pos + 100)
        if idx >= 0 and idx < end_pos:
            end_pos = idx

    new_pricing_block = '''# ══════════════════════════════════════════════════════════════════
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

'''

    content = content[:start_pos] + new_pricing_block + content[end_pos:]
    print("✓ Replaced entire pricing section with actual Stripe prices")

    # ═══════════════════════════════════════════════════════════════
    # Step 3: Fix PLAN_AMOUNTS_USD to match actual prices
    # ═══════════════════════════════════════════════════════════════

    # Find and replace USD amounts
    usd_pattern = re.search(r'PLAN_AMOUNTS_USD\s*=\s*\{[^}]+\}', content)
    if usd_pattern:
        new_usd = '''PLAN_AMOUNTS_USD = {
    "seeker_monthly":      799,      # $7.99 in cents
    "navigator_monthly":   1299,     # $12.99 in cents
    "navigator_annual":    10999,    # $109.99 in cents
}'''
        content = content[:usd_pattern.start()] + new_usd + content[usd_pattern.end():]
        print("✓ Updated PLAN_AMOUNTS_USD to match actual prices ($7.99/$12.99/$109.99)")

    # ═══════════════════════════════════════════════════════════════
    # Step 4: Fix PLAN_AMOUNTS_INR
    # ═══════════════════════════════════════════════════════════════

    inr_pattern = re.search(r'PLAN_AMOUNTS_INR\s*=\s*\{[^}]+\}', content)
    if inr_pattern:
        new_inr = '''PLAN_AMOUNTS_INR = {
    "seeker_monthly":      14900,    # ₹149 in paise
    "navigator_monthly":   29900,    # ₹299 in paise
    "navigator_annual":    299000,   # ₹2,990 in paise
}'''
        content = content[:inr_pattern.start()] + new_inr + content[inr_pattern.end():]
        print("✓ Updated PLAN_AMOUNTS_INR")

    # ═══════════════════════════════════════════════════════════════
    # Step 5: Fix Razorpay plans
    # ═══════════════════════════════════════════════════════════════

    rzp_pattern = re.search(r'RAZORPAY_PLANS\s*=\s*\{[^}]+\}', content)
    if rzp_pattern:
        new_rzp = '''RAZORPAY_PLANS = {
    "seeker_monthly":      os.getenv("RAZORPAY_PLAN_SEEKER_MONTHLY", ""),
    "navigator_monthly":   os.getenv("RAZORPAY_PLAN_NAVIGATOR_MONTHLY", ""),
    "navigator_annual":    os.getenv("RAZORPAY_PLAN_NAVIGATOR_ANNUAL", ""),
}'''
        content = content[:rzp_pattern.start()] + new_rzp + content[rzp_pattern.end():]
        print("✓ Updated RAZORPAY_PLANS (seeker_monthly + navigator_monthly + navigator_annual)")

    # ═══════════════════════════════════════════════════════════════
    # Step 6: Make sure create_stripe_checkout accepts country_code
    # ═══════════════════════════════════════════════════════════════

    if "country_code: str = \"US\"" not in content and "def create_stripe_checkout" in content:
        content = content.replace(
            "def create_stripe_checkout(\n    chart_id: str,\n    plan_key: str,\n    success_url: str,\n    cancel_url: str,\n) -> dict:",
            "def create_stripe_checkout(\n    chart_id: str,\n    plan_key: str,\n    success_url: str,\n    cancel_url: str,\n    country_code: str = \"US\",\n) -> dict:"
        )
        print("✓ Added country_code param to create_stripe_checkout")

    # Make sure the function uses get_stripe_price_for_country
    if "get_stripe_price_for_country" not in content.split("def create_stripe_checkout")[1].split("def ")[0] if "def create_stripe_checkout" in content else "":
        # Need to patch the function body
        old_lookup = "price_id = STRIPE_PRICES.get(plan_key, \"\")"
        new_lookup = "price_id, currency = get_stripe_price_for_country(plan_key, country_code)"
        if old_lookup in content:
            content = content.replace(old_lookup, new_lookup, 1)
            print("✓ Patched price lookup to use get_stripe_price_for_country()")

    # Replace payment_method_types=["card"] with automatic_payment_methods
    content = content.replace(
        'payment_method_types=["card"],',
        'automatic_payment_methods={"enabled": True},'
    )
    if 'automatic_payment_methods' in content:
        print("✓ Enabled automatic_payment_methods (PSE, Nequi, OXXO, PIX)")

    # Write
    open(filepath, "w").write(content)

    print(f"""
{'='*60}
✓ payment_engine.py updated with actual Stripe prices
{'='*60}

ACTUAL PRICING TABLE (from Stripe CSV):
┌──────────────┬───────────────┬────────────────┬────────────────┐
│ Market       │ Seeker/mo     │ Navigator/mo   │ Navigator/yr   │
├──────────────┼───────────────┼────────────────┼────────────────┤
│ US           │ $7.99         │ $12.99         │ $109.99        │
│ Colombia     │ $14,900 COP   │ $24,900 COP    │ (not created)  │
│ Mexico       │ $79 MXN       │ $129 MXN       │ $1,290 MXN     │
│ Brazil       │ R$19.90       │ R$39.90        │ R$399.90       │
│ Argentina    │ $2,990 ARS    │ $5,990 ARS     │ $45,900 ARS    │
│ Peru         │ S/12.90       │ S/21.90        │ S/199.90       │
│ Ecuador      │ $4.99         │ $7.99          │ $74.99         │
│ Canada       │ C$12.99       │ C$19.99        │ C$199.99       │
│ India        │ ₹149          │ ₹299           │ ₹2,990         │
└──────────────┴───────────────┴────────────────┴────────────────┘

MISSING: Colombia Navigator Annual — create in Stripe if needed.

NEXT:
  1. Run: chmod +x 06_set_railway_stripe_vars.sh && ./06_set_railway_stripe_vars.sh
     (or copy vars into Railway Dashboard manually)
  2. Deploy: git add -A && git commit -m "Actual Stripe prices from CSV" && git push
  3. Test each country with curl
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
