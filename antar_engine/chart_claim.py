"""Guest chart claim tokens.

A guest creates a chart with no account. `/chart/create` hands back a claim token;
after Google/Apple sign-in the app presents it to `/chart/claim` to attach the
chart to the new account. The chart id alone must never be enough to take a chart
(ids appear in URLs and logs), so claiming needs the token, which only the
creating client ever receives.

Stateless: token = HMAC-SHA256(secret, chart_id). No DB column, no expiry — it is
only honoured while the chart still has no owner.
"""
import hashlib
import hmac
import os


def _secret() -> bytes:
    s = os.getenv("CHART_CLAIM_SECRET")
    if not s:
        base = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        s = "antar-chart-claim|" + base
    return s.encode()


def make_claim_token(chart_id: str) -> str:
    return hmac.new(_secret(), str(chart_id).encode(), hashlib.sha256).hexdigest()[:48]


def claim_token_ok(chart_id: str, token: str) -> bool:
    if not chart_id or not token:
        return False
    return hmac.compare_digest(make_claim_token(chart_id), str(token))
