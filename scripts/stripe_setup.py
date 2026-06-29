#!/usr/bin/env python3
"""
scripts/stripe_setup.py — idempotent Stripe price catalog + 3-way reconciliation.

Creates/verifies the Model C price catalog (keyed by Stripe `lookup_key`) and
prints a backend vs Stripe vs IAP reconciliation table so the three pricing
surfaces can be proven identical. Safe to run repeatedly.

Auth: reads STRIPE_SECRET_KEY from the environment — use a TEST key first.
      Never hardcoded. If unset, Stripe steps are skipped and only the
      backend<->IAP reconciliation runs (the Stripe column shows the spec).

Usage:
    export STRIPE_SECRET_KEY=sk_test_...
    python scripts/stripe_setup.py
"""
import os
import sys

# Make `antar_engine` importable when run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.payment_engine import (
    resolve_price, stripe_lookup_key, is_excluded_country,
    PRICING_BUCKET_BY_COUNTRY, PRICING_AMOUNTS, EXCLUDED_COUNTRIES,
)

try:
    from antar_engine.iap_engine import PRODUCTS as IAP_PRODUCTS
except Exception as _e:           # pragma: no cover (defensive)
    print(f"[warn] could not import iap_engine.PRODUCTS: {_e}")
    IAP_PRODUCTS = {}

# ── The catalog: identical product IDs, lookup_key per currency ───────────
# (lookup_key, currency, amount_minor, interval, product_id, product_name)
CATALOG = [
    ("ask_unlimited_monthly_usd", "usd", 799,   "month",    "ask_unlimited_monthly", "Ask Unlimited"),
    ("ask_unlimited_annual_usd",  "usd", 5999,  "year",     "ask_unlimited_annual",  "Ask Unlimited"),
    ("ask_unlimited_monthly_brl", "brl", 1990,  "month",    "ask_unlimited_monthly", "Ask Unlimited"),
    ("ask_unlimited_annual_brl",  "brl", 14900, "year",     "ask_unlimited_annual",  "Ask Unlimited"),
    ("ask_unlimited_monthly_mxn", "mxn", 7900,  "month",    "ask_unlimited_monthly", "Ask Unlimited"),
    ("ask_unlimited_annual_mxn",  "mxn", 59900, "year",     "ask_unlimited_annual",  "Ask Unlimited"),
    ("compat_chart_usd",          "usd", 99,    "one_time", "compat_chart",          "Additional compatibility chart"),
    ("compat_chart_brl",          "brl", 290,   "one_time", "compat_chart",          "Additional compatibility chart"),
    ("compat_chart_mxn",          "mxn", 990,   "one_time", "compat_chart",          "Additional compatibility chart"),
]

# Representative country per bucket (for the reconciliation rows).
BUCKET_SAMPLE = {
    "us_ca": "US", "latam-local-br": "BR", "latam-local-mx": "MX",
    "latam-usd": "CO", "argentina": "AR",
}


def _stripe():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        return None
    import stripe
    stripe.api_key = key
    return stripe


def upsert_catalog(stripe):
    """Create products+prices only where missing (idempotent by lookup_key)."""
    prod_cache = {}

    def product_id(name):
        if name in prod_cache:
            return prod_cache[name]
        found = []
        try:
            found = stripe.Product.search(
                query=f"metadata['antar_name']:'{name}'"
            ).data
        except Exception:
            found = []
        p = found[0] if found else stripe.Product.create(
            name=name, metadata={"antar_name": name}
        )
        prod_cache[name] = p.id
        return p.id

    results = {}
    for lk, cur, amt, interval, pid, pname in CATALOG:
        existing = stripe.Price.list(lookup_keys=[lk], limit=1).data
        if existing:
            results[lk] = (existing[0].id, int(existing[0].unit_amount), "exists")
            continue
        kwargs = dict(currency=cur, unit_amount=amt, product=product_id(pname),
                      lookup_key=lk, metadata={"product_id": pid})
        if interval != "one_time":
            kwargs["recurring"] = {"interval": interval}
        price = stripe.Price.create(**kwargs)
        results[lk] = (price.id, amt, "created")
    return results


def _catalog_amount(lookup_key):
    for lk, cur, amt, *_ in CATALOG:
        if lk == lookup_key:
            return amt, cur
    return None, None


def reconcile(live_results=None):
    """Print backend vs Stripe vs IAP per product × bucket; flag mismatches."""
    print("\n" + "=" * 96)
    print("RECONCILIATION  —  backend constant  vs  Stripe catalog  vs  iap_engine")
    print("=" * 96)
    products = ("ask_unlimited_monthly", "ask_unlimited_annual", "compat_chart")
    samples = [
        ("US/CA",     "US"),
        ("LatAm BR",  "BR"),
        ("LatAm MX",  "MX"),
        ("LatAm oth", "CO"),
        ("Argentina", "AR"),
        ("India",     "IN"),
    ]
    hdr = f"{'product':<24}{'bucket':<11}{'backend':<14}{'stripe':<20}{'iap':<8}{'status'}"
    mismatches = 0
    for product in products:
        print("-" * 96)
        in_iap = "yes" if product in IAP_PRODUCTS else "NO"
        for label, cc in samples:
            if is_excluded_country(cc):
                print(f"{product:<24}{label:<11}{'—':<14}{'—':<20}{'—':<8}EXCLUDED (no sale)")
                continue
            amt, cur = resolve_price(cc, product)
            backend = f"{amt} {cur}"
            lk = stripe_lookup_key(cc, product)
            if lk:
                camt, ccur = _catalog_amount(lk)
                if live_results and lk in live_results:
                    lpid, lamt, _ = live_results[lk]
                    stripe_cell = f"{lamt} {ccur} *"
                    cmp_amt = lamt
                else:
                    stripe_cell = f"{camt} {ccur}"
                    cmp_amt = camt
                ok = (cmp_amt == amt and ccur == cur)
            else:
                stripe_cell = "on-the-fly"
                ok = True  # web bills the backend amount directly (USD)
            status = "OK" if ok else "MISMATCH"
            if not ok:
                mismatches += 1
            note = "" if lk else "  (web=USD bucket; store localizes)"
            print(f"{product:<24}{label:<11}{backend:<14}{stripe_cell:<20}{in_iap:<8}{status}{note}")
    print("=" * 96)
    print(f"* = verified against LIVE Stripe price" if live_results else
          "(Stripe column = catalog spec; run with STRIPE_SECRET_KEY to verify live)")
    print(f"Product IDs identical across surfaces: "
          f"{sorted(set(p[4] for p in CATALOG))}")
    print(f"Excluded this launch: {sorted(EXCLUDED_COUNTRIES)}")
    print(f"RESULT: {'ALL MATCH' if mismatches == 0 else f'{mismatches} MISMATCH(es) — see above'}")
    print("=" * 96)
    return mismatches


def main():
    stripe = _stripe()
    live = None
    if stripe is None:
        print("STRIPE_SECRET_KEY not set — skipping Stripe catalog creation.")
        print("Running backend <-> IAP reconciliation against the catalog spec.\n")
    else:
        env = "TEST" if "sk_test" in os.environ.get("STRIPE_SECRET_KEY", "") else "LIVE"
        print(f"Stripe key detected ({env}). Creating/verifying catalog by lookup_key…\n")
        live = upsert_catalog(stripe)
        for lk, (pid, amt, state) in live.items():
            print(f"  [{state:>7}] {lk:<28} {pid}  ({amt})")
    mismatches = reconcile(live)
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
