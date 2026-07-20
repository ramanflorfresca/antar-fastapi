"""
antar_engine/geo_lookup.py

IP → country lookup for the marketing-site pricing block.

Backed by MaxMind GeoLite2-Country.mmdb (~6 MB), loaded once at import time
as a singleton geoip2.database.Reader. Lookups are wrapped in a TTLCache
(10 000 IPs × 1 hour) so repeat hits become pure dict.get().

Failure modes are designed to NEVER raise. A missing .mmdb file, an
unparseable IP, an IP not in the DB, or any other error all return None
from lookup_country(); the calling endpoint then returns the USD fallback
payload.

Single source of truth for "is this country in the Stripe-supported list":
antar_engine.payment_engine.PLAN_AMOUNTS_BY_COUNTRY. Reading from that dict
guarantees the marketing page can never claim a currency Stripe won't
actually charge.
"""

import ipaddress
import logging
from pathlib import Path
from typing import Optional

from cachetools import TTLCache
from fastapi import Request

logger = logging.getLogger(__name__)

# ── DB load (singleton, set once at module import) ──────────────────
_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "GeoLite2-Country.mmdb"
_reader = None

try:
    import geoip2.database  # type: ignore
    if _DB_PATH.exists():
        _reader = geoip2.database.Reader(str(_DB_PATH))
        logger.info(f"[geo] GeoLite2-Country.mmdb loaded from {_DB_PATH}")
    else:
        logger.warning(
            f"[geo] MMDB not found at {_DB_PATH} — /geo/country will fall back to US for all callers"
        )
except Exception as _init_err:
    logger.warning(f"[geo] geoip2 init failed ({_init_err}) — falling back to US")
    _reader = None

# ── Per-IP cache: 10k IPs, 1h TTL, LRU evict ─────────────────────────
# Negative lookups are cached as empty-string sentinel so we don't retry
# DB-not-found / unparseable IPs on every call.
_lookup_cache: TTLCache = TTLCache(maxsize=10_000, ttl=3600)


# ── Public API ───────────────────────────────────────────────────────
def extract_client_ip(request: Request) -> str:
    """Return the originating client IP, parsed from X-Forwarded-For chain.

    Railway (and every standard reverse proxy) forwards X-Forwarded-For as a
    comma-separated chain where the leftmost entry is the original client.
    We fall through to X-Real-IP and then request.client.host so this works
    in local dev and behind any proxy stack.
    """
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


def lookup_country(ip: str) -> Optional[str]:
    """Return 2-letter ISO-3166-1 alpha-2 country code for ip, or None.

    Never raises. Caches both positive (CC) and negative (empty-string)
    results in the TTLCache for one hour.
    """
    if not ip or _reader is None:
        return None

    ip = ip.strip()
    cached = _lookup_cache.get(ip)
    if cached is not None:
        # cached == "" means "we looked this up before and got nothing"
        return cached or None

    # [geo-guard 2026-07-20] Never geolocate a non-public address. Railway sits
    # behind carrier-grade NAT, so request.client.host is routinely 100.64.x.x
    # (RFC 6598) — a PRIVATE range that must never be treated as a user's real
    # location. Also covers 10/8, 192.168/16, 127/8, link-local and IPv6 ULA.
    # MaxMind raises on some of these and silently misses others, so the check
    # belongs here rather than relying on the lookup to fail.
    try:
        _addr = ipaddress.ip_address(ip)
        if (_addr.is_private or _addr.is_loopback or _addr.is_link_local
                or _addr.is_reserved or _addr.is_multicast or _addr.is_unspecified):
            _lookup_cache[ip] = ""
            return None
    except ValueError:
        _lookup_cache[ip] = ""
        return None

    try:
        resp = _reader.country(ip)
        cc = (resp.country.iso_code or "").upper()
        _lookup_cache[ip] = cc  # may be "" — negative cache
        return cc or None
    except Exception:
        # geoip2.errors.AddressNotFoundError + invalid-IP ValueError land here
        _lookup_cache[ip] = ""
        return None


def country_to_pricing_info(country_code: Optional[str]) -> dict:
    """Build the marketing-page pricing payload from a country code.

    Reads PLAN_AMOUNTS_BY_COUNTRY for the in_stripe_supported_list test so
    the answer is always consistent with what create_stripe_checkout will
    actually charge.

    Country names come from country_context.COUNTRY_CONTEXT when available;
    falls back to the raw code if a country isn't in that registry.
    """
    from antar_engine.payment_engine import COUNTRY_CURRENCY, PLAN_AMOUNTS_BY_COUNTRY

    try:
        from antar_engine.country_context import COUNTRY_CONTEXT
    except Exception:
        COUNTRY_CONTEXT = {}

    cc = (country_code or "").upper()
    in_list = cc in PLAN_AMOUNTS_BY_COUNTRY
    currency = (COUNTRY_CURRENCY.get(cc) if in_list else "usd") or "usd"
    name = COUNTRY_CONTEXT.get(cc, {}).get("name", cc) if cc else ""

    return {
        "country_code":             cc or "US",
        "country_name":             name or ("United States" if not cc else cc),
        "currency":                 currency.upper(),
        "in_stripe_supported_list": in_list,
        "fallback_currency":        "USD",
    }
