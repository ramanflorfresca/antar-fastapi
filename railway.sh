#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
# Antar — Set Stripe Price IDs in Railway
# Run from your project root where railway CLI is authenticated
#
# Usage:
#   chmod +x 06_set_railway_stripe_vars.sh
#   ./06_set_railway_stripe_vars.sh
#
# If you don't have Railway CLI, copy the variable block below
# and paste into Railway Dashboard → Variables manually.
# ══════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════"
echo "ANTAR — Setting Stripe Price IDs in Railway"
echo "═══════════════════════════════════════════════════"

# Check if railway CLI exists
if ! command -v railway &> /dev/null; then
    echo ""
    echo "Railway CLI not found."
    echo "Option 1: Install it: npm install -g @railway/cli"
    echo "Option 2: Copy the variables below into Railway Dashboard → Variables"
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "COPY THESE INTO RAILWAY DASHBOARD → VARIABLES"
    echo "══════════════════════════════════════════════════════════"
    cat << 'VARS'

# ── USD (US/Global) ──────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY=price_1THuYw9cSELT0FVz5G3fl1AU
STRIPE_PRICE_NAVIGATOR_MONTHLY=price_1THuaj9cSELT0FVzYL2YmN0U
STRIPE_PRICE_NAVIGATOR_ANNUAL=price_1THup39cSELT0FVzvpREfaUk

# ── Colombia COP ─────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_COP=price_1THudm9cSELT0FVzvF2SKx5R
STRIPE_PRICE_NAVIGATOR_MONTHLY_COP=price_1THufK9cSELT0FVzlTYTQG6G

# ── Mexico MXN ───────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_MXN=price_1THv789cSELT0FVz1vir6RWR
STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN=price_1THv7g9cSELT0FVzqY35AGSc
STRIPE_PRICE_NAVIGATOR_ANNUAL_MXN=price_1THv8N9cSELT0FVz6YxyQp6i

# ── Brazil BRL ───────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_BRL=price_1THukV9cSELT0FVzB2pUgBy3
STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL=price_1THuw69cSELT0FVzcPLxraWM
STRIPE_PRICE_NAVIGATOR_ANNUAL_BRL=price_1THuuh9cSELT0FVzjHQf7toD

# ── Argentina ARS ────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_ARS=price_1THur89cSELT0FVzSqTej7Ov
STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS=price_1THuse9cSELT0FVzbprlc4jj
STRIPE_PRICE_NAVIGATOR_ANNUAL_ARS=price_1THutP9cSELT0FVz4L5eYsfT

# ── Peru PEN ─────────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_PEN=price_1THuwi9cSELT0FVzjiR4osYn
STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN=price_1THuy69cSELT0FVz4aYuyrEZ
STRIPE_PRICE_NAVIGATOR_ANNUAL_PEN=price_1THuzr9cSELT0FVzr5r6Eo2Y

# ── Ecuador USD ──────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_EC=price_1THv599cSELT0FVzPDUl5tD9
STRIPE_PRICE_NAVIGATOR_MONTHLY_EC=price_1THv5d9cSELT0FVzsg4dBQDh
STRIPE_PRICE_NAVIGATOR_ANNUAL_EC=price_1THv6M9cSELT0FVzKM4xoAf2

# ── Canada CAD ───────────────────────────────────────────────────
STRIPE_PRICE_SEEKER_MONTHLY_CAD=price_1THvCu9cSELT0FVzqzHWg0bw
STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD=price_1THvCS9cSELT0FVzwQ2wJKgF
STRIPE_PRICE_NAVIGATOR_ANNUAL_CAD=price_1THvDO9cSELT0FVzKacRMOjW

VARS
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "Total: 24 variables"
    echo "══════════════════════════════════════════════════════════"
    exit 0
fi

# Railway CLI is available — set vars directly
echo "Railway CLI found. Setting variables..."

# ── USD (US/Global) ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY=price_1THuYw9cSELT0FVz5G3fl1AU
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY=price_1THuaj9cSELT0FVzYL2YmN0U
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL=price_1THup39cSELT0FVzvpREfaUk

# ── Colombia COP ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_COP=price_1THudm9cSELT0FVzvF2SKx5R
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_COP=price_1THufK9cSELT0FVzlTYTQG6G

# ── Mexico MXN ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_MXN=price_1THv789cSELT0FVz1vir6RWR
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_MXN=price_1THv7g9cSELT0FVzqY35AGSc
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_MXN=price_1THv8N9cSELT0FVz6YxyQp6i

# ── Brazil BRL ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_BRL=price_1THukV9cSELT0FVzB2pUgBy3
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_BRL=price_1THuw69cSELT0FVzcPLxraWM
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_BRL=price_1THuuh9cSELT0FVzjHQf7toD

# ── Argentina ARS ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_ARS=price_1THur89cSELT0FVzSqTej7Ov
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_ARS=price_1THuse9cSELT0FVzbprlc4jj
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_ARS=price_1THutP9cSELT0FVz4L5eYsfT

# ── Peru PEN ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_PEN=price_1THuwi9cSELT0FVzjiR4osYn
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_PEN=price_1THuy69cSELT0FVz4aYuyrEZ
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_PEN=price_1THuzr9cSELT0FVzr5r6Eo2Y

# ── Ecuador USD ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_EC=price_1THv599cSELT0FVzPDUl5tD9
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_EC=price_1THv5d9cSELT0FVzsg4dBQDh
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_EC=price_1THv6M9cSELT0FVzKM4xoAf2

# ── Canada CAD ──
railway variables set STRIPE_PRICE_SEEKER_MONTHLY_CAD=price_1THvCu9cSELT0FVzqzHWg0bw
railway variables set STRIPE_PRICE_NAVIGATOR_MONTHLY_CAD=price_1THvCS9cSELT0FVzwQ2wJKgF
railway variables set STRIPE_PRICE_NAVIGATOR_ANNUAL_CAD=price_1THvDO9cSELT0FVzKacRMOjW

echo ""
echo "✓ All 24 Stripe price variables set"
echo ""
echo "Railway will auto-redeploy. Wait ~60s then test."
