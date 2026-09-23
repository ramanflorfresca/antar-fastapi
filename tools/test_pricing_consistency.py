#!/usr/bin/env python3
"""
tools/test_pricing_consistency.py — guards the pricing tables against drift.

payment_engine.py carries two pricing tables with different jobs:

  PRICING_AMOUNTS / PRICING_LOCAL_CURRENCY   LIVE products, all countries
  PLAN_AMOUNTS_USD / PLAN_AMOUNTS_INR        DEPRECATED tiers, legacy fallback

They drifted once: PLAN_AMOUNTS_USD held ask_unlimited at $7.99/$59.99 while
the live price was $4.99/$39.99. It was unreachable so nobody was mischarged,
but it read as authoritative and one widened fallback would have made it real.

These tests make that class of drift impossible to merge.

Run:  ./venv311/bin/python tools/test_pricing_consistency.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.payment_engine import (
    EXCLUDED_COUNTRIES, PLAN_AMOUNTS_INR, PLAN_AMOUNTS_USD, PRICING_AMOUNTS,
    PRICING_BUCKET_BY_COUNTRY, PRICING_DEFAULT_BUCKET, PRICING_LOCAL_CURRENCY,
    PRICING_PRODUCTS, _fmt_amount, is_excluded_country, pricing_summary,
    resolve_price,
)

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


print("\nTABLE SEPARATION")
for table_name, table in (("PLAN_AMOUNTS_USD", PLAN_AMOUNTS_USD),
                          ("PLAN_AMOUNTS_INR", PLAN_AMOUNTS_INR)):
    overlap = sorted(set(table) & set(PRICING_PRODUCTS))
    check(f"{table_name} holds no live product", not overlap,
          f"-> {overlap}. Live prices belong in PRICING_AMOUNTS only; an entry "
          f"here is unreachable but reads as authoritative.")

print("\nLIVE TABLE COMPLETENESS")
for bucket, amounts in PRICING_AMOUNTS.items():
    missing = [p for p in PRICING_PRODUCTS if p not in amounts]
    check(f"bucket '{bucket}' prices every product", not missing, f"missing {missing}")
    check(f"bucket '{bucket}' amounts are positive ints",
          all(isinstance(amounts[p], int) and amounts[p] > 0 for p in PRICING_PRODUCTS))

for cc, loc in PRICING_LOCAL_CURRENCY.items():
    check(f"{cc} override declares a currency", bool(loc.get("currency")))
    for p in ("ask_unlimited_monthly", "ask_unlimited_annual"):
        check(f"{cc} override prices {p}", isinstance(loc.get(p), int) and loc[p] > 0)

print("\nANNUAL DISCOUNT SANITY")
# Annual must beat 12x monthly, or the annual plan is a worse deal than monthly.
for bucket, a in PRICING_AMOUNTS.items():
    mo, yr = a["ask_unlimited_monthly"], a["ask_unlimited_annual"]
    pct = round((1 - yr / (mo * 12)) * 100)
    check(f"{bucket}: annual cheaper than 12x monthly ({pct}% off)", yr < mo * 12,
          f"{yr} >= {mo}*12")
    check(f"{bucket}: discount is a sane 10-80% ({pct}%)", 10 <= pct <= 80)

for cc, loc in PRICING_LOCAL_CURRENCY.items():
    mo, yr = loc["ask_unlimited_monthly"], loc["ask_unlimited_annual"]
    pct = round((1 - yr / (mo * 12)) * 100)
    check(f"{cc}: annual cheaper than 12x monthly ({pct}% off)", yr < mo * 12)

print("\nRESOLUTION")
check("US resolves to $4.99/mo", resolve_price("US", "ask_unlimited_monthly") == (499, "usd"),
      str(resolve_price("US", "ask_unlimited_monthly")))
check("US resolves to $39.99/yr", resolve_price("US", "ask_unlimited_annual") == (3999, "usd"),
      str(resolve_price("US", "ask_unlimited_annual")))
check("MX resolves in pesos", resolve_price("MX", "ask_unlimited_monthly")[1] == "mxn")
check("CO resolves in COP", resolve_price("CO", "ask_unlimited_monthly")[1] == "cop")
check("unknown country falls back to the default bucket",
      resolve_price("ZZ", "ask_unlimited_monthly")
      == (PRICING_AMOUNTS[PRICING_DEFAULT_BUCKET]["ask_unlimited_monthly"], "usd"))
check("a deprecated key resolves to nothing",
      resolve_price("US", "navigator_monthly") == (None, None),
      str(resolve_price("US", "navigator_monthly")))

print("\nBUCKET MAP")
for cc, bucket in PRICING_BUCKET_BY_COUNTRY.items():
    check(f"{cc} -> known bucket '{bucket}'", bucket in PRICING_AMOUNTS)
check("default bucket exists", PRICING_DEFAULT_BUCKET in PRICING_AMOUNTS)

print("\nDISPLAY")
check("499/usd renders $4.99", _fmt_amount(499, "usd") == "$4.99", _fmt_amount(499, "usd"))
check("3999/usd renders $39.99", _fmt_amount(3999, "usd") == "$39.99", _fmt_amount(3999, "usd"))
check("990000/cop renders with separators", "9,900" in _fmt_amount(990000, "cop"),
      _fmt_amount(990000, "cop"))

print("\nEXCLUSIONS")
check("India is still excluded from the subscription path", is_excluded_country("IN"))
check("excluded country returns the packs model",
      pricing_summary("IN").get("model") == "packs", str(pricing_summary("IN")))
check("a normal country returns the subscription model",
      pricing_summary("US").get("model") == "subscription")
check("US summary displays $4.99",
      (pricing_summary("US").get("monthly") or {}).get("display") == "$4.99",
      str(pricing_summary("US").get("monthly")))
for cc in EXCLUDED_COUNTRIES:
    check(f"{cc} exposes packs with prices",
          bool(pricing_summary(cc).get("packs")))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
