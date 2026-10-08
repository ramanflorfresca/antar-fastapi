"""
antar_engine/circle.py - Circle: the two-sided People tab.

Today People is private: a user adds someone by typing THEIR birth details and gets a
reading only they see. Circle adds a second way in: the user INVITES a person; the invitee
opens a link, consents, enters their OWN birth details, and from then on both see a shared
"Between us" page (see circle_overlap.py). Private People are untouched.

Hard rules this module enforces (tests/test_circle.py proves each):
  * CONSENT   - nothing exists about a person until they accept. An invite row holds only
                what the INVITER typed (a first name, a relation). A decline writes nothing
                about the invitee; to the inviter a declined invite simply stays "pending"
                until it expires. Antar never contacts the invitee: the inviter shares the
                link from their own phone.
  * TOKENS    - the code in https://antar.world/c/<code> is 144 random bits, single-use,
                valid ~14 days, stored only as a sha256 hash, never logged. A resend mints a
                new code and kills the old one.
  * PAIR LAYER ONLY - the pair row carries two chart ids and the relation each way. The
                other side's birth details, private reads, questions, notes and Ask history
                are never reachable through any Circle call.
  * LEAVE     - either side can leave; the pair row is DELETED (nothing outlives the link)
                and neither chart is touched.

All functions take a supabase-style client `sb`, are BLOCKING and synchronous (call them from
a `def` endpoint or a thread - never bare inside an `async def`), and read paths FAIL OPEN
(log once, return the empty answer) when the circle_* tables do not exist yet. Write paths
raise CircleUnavailable in that case so the route can answer 503 instead of a 500.

Tables: sql_circle.sql (circle_invites, circle_pairs, circle_sharing).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from antar_engine import circle_copy as CC
from antar_engine.outcomes import _table_missing

logger = logging.getLogger(__name__)

INVITE_TTL_DAYS = 14
MAX_PENDING_INVITES = 10        # live (pending / quietly-declined) invites per inviter chart
MAX_INVITES_PER_DAY = 20        # new invites per inviter account per rolling 24h
MAX_RESENDS = 3                 # per invite, lifetime
LINK_BASE = (os.getenv("CIRCLE_LINK_BASE") or "https://antar.world/c/").rstrip("/") + "/"
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

INVITES, PAIRS, SHARING = "circle_invites", "circle_pairs", "circle_sharing"

_warned: set = set()


class CircleUnavailable(Exception):
    """The circle_* tables are missing or unreachable (write paths only)."""


class CircleError(Exception):
    """A refusal with a stable machine code the route turns into a 4xx."""

    def __init__(self, code: str, status: int = 409, **extra):
        super().__init__(code)
        self.code, self.status, self.extra = code, status, extra


def _warn_once(key: str, msg: str):
    if key not in _warned:
        _warned.add(key)
        logger.warning(msg)


def _handle(e: Exception, where: str):
    """Missing table -> one quiet warning; anything else -> a warning line. Never the token."""
    if _table_missing(e):
        _warn_once("missing", "[circle] circle_* tables not available yet - serving an empty circle")
    else:
        logger.warning("[circle] %s failed: %s", where, str(e)[:200])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat()


def _parse(v) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ── tokens ───────────────────────────────────────────────────────────────────
def new_code() -> str:
    return secrets.token_urlsafe(18)          # 24 chars, 144 bits


def hash_code(code: str) -> str:
    return hashlib.sha256(str(code).encode()).hexdigest()


def link_for(code: str) -> str:
    return LINK_BASE + code


def code_ok(code) -> bool:
    return bool(code) and bool(CODE_RE.match(str(code)))


def redact_path(path: str) -> str:
    """/api/v1/circle/invite/<code>[/accept] -> .../<redacted>: the code must not reach access logs."""
    return re.sub(r"(/api/v1/circle/invite/)[^/?\s]+", r"\1<redacted>", str(path))


class _AccessLogRedactor(logging.Filter):
    def filter(self, record):
        try:
            a = record.args
            if isinstance(a, tuple) and len(a) >= 3 and isinstance(a[2], str):
                record.args = a[:2] + (redact_path(a[2]),) + a[3:]
        except Exception:
            pass
        return True


def install_access_log_redaction():
    """uvicorn's access log prints the request path, which would carry the raw invite code."""
    lg = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _AccessLogRedactor) for f in lg.filters):
        lg.addFilter(_AccessLogRedactor())


# ── names, relations ─────────────────────────────────────────────────────────
def norm_first_name(raw) -> str:
    s = re.sub(r"\s+", " ", str(raw or "").strip())
    return s.split(" ")[0][:40] if s else ""


def first_name_of(chart_row: Optional[dict]) -> str:
    r = chart_row or {}
    return norm_first_name(r.get("first_name") or r.get("name"))


def normalise_relation(raw) -> Optional[str]:
    """Any relation word the People flow already accepts -> its people_links key, else None."""
    try:
        from antar_engine import people_links as PL
        n = PL.normalise_relation(raw)
        return n[0] if n else None
    except Exception:
        return None


def compat_type_label(relation: str, language) -> str:
    """The first-person picker label ("My child") from the existing reasons directory, so
    Circle and People name relations identically. Falls back to the plain noun."""
    lang = CC.lang_of(language)
    try:
        from antar_engine import compatibility_reasons as R
        from antar_engine import people_links as PL
        key = PL.relation_to_compat_type(relation)
        for e in R.reasons_directory(lang).get("reasons", []):
            if e.get("key") == key:
                return e.get("label") or CC.rel_noun(relation, lang)
    except Exception:
        pass
    return CC.rel_noun(relation, lang)


def relation_view(relation: str, language) -> dict:
    lang = CC.lang_of(language)
    return {"key": relation, "label": CC.rel_noun(relation, lang),
            "compat_type_label": compat_type_label(relation, lang)}


# ── status vocabulary ────────────────────────────────────────────────────────
def public_status(inv: dict, now: Optional[datetime] = None) -> str:
    """What the INVITEE-facing landing says: valid | used | expired."""
    now = now or _now()
    st = inv.get("status")
    if st in ("accepted", "declined"):
        return "used"
    if st in ("expired", "cancelled"):
        return "expired"
    exp = _parse(inv.get("expires_at"))
    return "expired" if (exp is None or exp <= now) else "valid"


def inviter_status(inv: dict, now: Optional[datetime] = None) -> Optional[str]:
    """What the INVITER sees: pending | expired. A decline is deliberately indistinguishable
    from silence. accepted/cancelled invites are not listed (an accepted one shows as a pair)."""
    now = now or _now()
    st = inv.get("status")
    if st in ("accepted", "cancelled"):
        return None
    exp = _parse(inv.get("expires_at"))
    if st == "expired" or exp is None or exp <= now:
        return "expired"
    return "pending"            # pending, or declined-but-not-yet-expired


# ── charts ───────────────────────────────────────────────────────────────────
def chart_row(sb, chart_id: str, cols: str = "id,user_id,name,first_name,language_preference,language") -> Optional[dict]:
    try:
        rows = (sb.table("charts").select(cols).eq("id", chart_id)
                .is_("deleted_at", "null").limit(1).execute()).data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.warning("[circle] chart lookup failed: %s", str(e)[:160])
        return None


def is_demo(sb, chart_id) -> bool:
    from antar_engine import topic_checkback as tcb
    return tcb.is_demo(sb, chart_id)


# ── invites: create / list / cancel / resend ─────────────────────────────────
def _invite_by_id(sb, invite_id: str) -> Optional[dict]:
    try:
        rows = sb.table(INVITES).select("*").eq("id", invite_id).limit(1).execute().data or []
        return rows[0] if rows else None
    except Exception as e:
        if _table_missing(e):
            raise CircleUnavailable(str(e))
        raise


def _invite_by_code(sb, code: str) -> Optional[dict]:
    if not code_ok(code):
        return None
    rows = sb.table(INVITES).select("*").eq("token_hash", hash_code(code)).limit(1).execute().data or []
    return rows[0] if rows else None


def _live_invites(sb, chart_id: str, now: datetime) -> list:
    rows = (sb.table(INVITES).select("*").eq("inviter_chart_id", chart_id)
            .in_("status", ["pending", "declined"]).gt("expires_at", _iso(now))
            .limit(100).execute()).data or []
    return rows


def create_invite(sb, chart_id: str, user_id: Optional[str], relation: str, first_name: str,
                  language: str, private_chart_id: Optional[str] = None,
                  position: Optional[int] = None, now: Optional[datetime] = None) -> dict:
    """-> {invite_id, code, link, expires_at}. The raw code is returned ONCE; only its hash is stored."""
    now = now or _now()
    name = norm_first_name(first_name)
    try:
        live = _live_invites(sb, chart_id, now)
        if len(live) >= MAX_PENDING_INVITES:
            raise CircleError("too_many_pending_invites", 429, limit=MAX_PENDING_INVITES)
        if name:
            for inv in live:
                if (norm_first_name(inv.get("invitee_first_name")).lower() == name.lower()
                        and inv.get("relation_type") == relation):
                    raise CircleError("already_invited", 409, invite_id=inv.get("id"))
        since = _iso(now - timedelta(days=1))
        q = sb.table(INVITES).select("id").gte("created_at", since)
        q = q.eq("inviter_user_id", user_id) if user_id else q.eq("inviter_chart_id", chart_id)
        if len(q.limit(MAX_INVITES_PER_DAY + 1).execute().data or []) >= MAX_INVITES_PER_DAY:
            raise CircleError("daily_invite_limit", 429, limit=MAX_INVITES_PER_DAY)
        code = new_code()
        expires = now + timedelta(days=INVITE_TTL_DAYS)
        row = {"inviter_chart_id": chart_id, "inviter_user_id": user_id, "token_hash": hash_code(code),
               "relation_type": relation, "position": position, "invitee_first_name": name or None,
               "private_chart_id": private_chart_id, "language": CC.lang_of(language),
               "status": "pending", "resend_count": 0, "expires_at": _iso(expires)}
        res = sb.table(INVITES).insert(row).execute().data or []
        if not res:
            raise CircleUnavailable("insert returned nothing")
        return {"invite_id": res[0]["id"], "code": code, "link": link_for(code),
                "expires_at": _iso(expires)}
    except CircleError:
        raise
    except CircleUnavailable:
        raise
    except Exception as e:
        _handle(e, "create_invite")
        raise CircleUnavailable(str(e)[:200])


def list_invites(sb, chart_id: str, now: Optional[datetime] = None) -> list:
    """The inviter's own open invites, with the inviter-facing status. [] if the table is missing."""
    now = now or _now()
    try:
        rows = (sb.table(INVITES).select("*").eq("inviter_chart_id", chart_id)
                .in_("status", ["pending", "declined", "expired"]).order("created_at", desc=True)
                .limit(100).execute()).data or []
    except Exception as e:
        _handle(e, "list_invites")
        return []
    out = []
    for r in rows:
        st = inviter_status(r, now)
        if st:
            out.append(dict(r, _status=st))
    return out


def cancel_invite(sb, chart_id: str, invite_id: str) -> bool:
    """Withdraw an invite the caller sent. True if something was cancelled. An accepted invite
    cannot be cancelled here (that is `leave`). Idempotent."""
    try:
        inv = _invite_by_id(sb, invite_id)
        if not inv or inv.get("inviter_chart_id") != chart_id:
            return False
        if inv.get("status") in ("accepted", "cancelled"):
            return False
        sb.table(INVITES).update({"status": "cancelled", "updated_at": _iso(_now())}) \
            .eq("id", invite_id).neq("status", "accepted").execute()
        return True
    except CircleUnavailable:
        raise
    except Exception as e:
        _handle(e, "cancel_invite")
        raise CircleUnavailable(str(e)[:200])


def resend_invite(sb, chart_id: str, invite_id: str, now: Optional[datetime] = None) -> Optional[dict]:
    """New code, fresh 14 days, old code dead. Revives an expired or quietly-declined invite
    (the inviter cannot tell the difference, by design). None if not theirs / accepted / cancelled."""
    now = now or _now()
    try:
        inv = _invite_by_id(sb, invite_id)
        if not inv or inv.get("inviter_chart_id") != chart_id or inv.get("status") in ("accepted", "cancelled"):
            return None
        if int(inv.get("resend_count") or 0) >= MAX_RESENDS:
            raise CircleError("resend_limit", 429, limit=MAX_RESENDS)
        if inviter_status(inv, now) == "expired" and len(_live_invites(sb, chart_id, now)) >= MAX_PENDING_INVITES:
            raise CircleError("too_many_pending_invites", 429, limit=MAX_PENDING_INVITES)
        code, expires = new_code(), now + timedelta(days=INVITE_TTL_DAYS)
        upd = (sb.table(INVITES).update({
            "token_hash": hash_code(code), "status": "pending", "expires_at": _iso(expires),
            "resend_count": int(inv.get("resend_count") or 0) + 1, "updated_at": _iso(now)})
            .eq("id", invite_id).neq("status", "accepted").execute().data or [])
        if not upd:
            return None
        return {"invite_id": invite_id, "code": code, "link": link_for(code), "expires_at": _iso(expires)}
    except (CircleError, CircleUnavailable):
        raise
    except Exception as e:
        _handle(e, "resend_invite")
        raise CircleUnavailable(str(e)[:200])


# ── the invitee side ─────────────────────────────────────────────────────────
def peek_invite(sb, code: str, now: Optional[datetime] = None) -> Optional[dict]:
    """Public landing data and NOTHING else: {inviter_first_name, relation, status, language}.
    `relation` is what the inviter is to the invitee. None for an unknown code; a missing
    table reads as an expired link, never an error."""
    now = now or _now()
    try:
        inv = _invite_by_code(sb, code)
    except Exception as e:
        _handle(e, "peek_invite")
        return {"inviter_first_name": None, "relation": None, "status": "expired", "language": "en"}
    if not inv:
        return None
    lang = CC.lang_of(inv.get("language"))
    status = public_status(inv, now)
    ch = chart_row(sb, inv.get("inviter_chart_id"))
    if not ch:                                       # inviter deleted their chart
        status = "expired"
    rel_for_invitee = CC.inverse_relation(inv.get("relation_type") or "friend")
    return {"inviter_first_name": first_name_of(ch) or None,
            "relation": {"key": rel_for_invitee, "label": CC.rel_noun(rel_for_invitee, lang)},
            "status": status, "language": lang}


def decline_invite(sb, code: str) -> bool:
    """Consume the link without recording anything about WHO declined. Idempotent; an unknown,
    used or expired code is a quiet no-op. Always safe to answer 'ok'."""
    try:
        inv = _invite_by_code(sb, code)
        if inv and public_status(inv) == "valid":
            sb.table(INVITES).update({"status": "declined", "updated_at": _iso(_now())}) \
                .eq("id", inv["id"]).eq("status", "pending").execute()
        return True
    except Exception as e:
        _handle(e, "decline_invite")
        return True


def accept_invite(sb, code: str, invitee_chart_id: str, share_day: bool = False,
                  now: Optional[datetime] = None) -> dict:
    """Bind the invitee's OWN chart to the inviter and create the pair. Idempotent for the same
    chart (a double tap returns the same pair); a different chart on a used link is refused.

    Caller must already have proved the invitee owns `invitee_chart_id` (auth or claim token).
    Raises CircleError(code, status) for: invite_not_found 404, invite_expired 410,
    invite_used 409, cannot_invite_yourself 409, chart_not_found 404, demo_chart 403."""
    now = now or _now()
    try:
        inv = _invite_by_code(sb, code)
    except Exception as e:
        _handle(e, "accept_invite")
        raise CircleUnavailable(str(e)[:200])
    if not inv:
        raise CircleError("invite_not_found", 404)
    inviter_id = inv["inviter_chart_id"]
    try:
        if invitee_chart_id == inviter_id:
            raise CircleError("cannot_invite_yourself", 409)
        mine = chart_row(sb, invitee_chart_id)
        if not mine:
            raise CircleError("chart_not_found", 404)
        if is_demo(sb, invitee_chart_id) or is_demo(sb, inviter_id):
            raise CircleError("demo_chart", 403)
        inviter = chart_row(sb, inviter_id)
        if not inviter:
            raise CircleError("invite_expired", 410)
        if inv.get("inviter_user_id") and mine.get("user_id") == inv["inviter_user_id"]:
            raise CircleError("cannot_invite_yourself", 409)
        if inviter.get("user_id") and mine.get("user_id") == inviter.get("user_id"):
            raise CircleError("cannot_invite_yourself", 409)

        if inv.get("status") == "accepted":
            if inv.get("accepted_chart_id") == invitee_chart_id:
                pair = get_pair(sb, inviter_id, invitee_chart_id)
                if pair:                       # same person, same link, double tap
                    return _accepted_view(sb, pair, invitee_chart_id, inviter, share_day=None)
            raise CircleError("invite_used", 409)
        st = public_status(inv, now)
        if st == "expired":
            raise CircleError("invite_expired", 410)
        if st == "used":
            raise CircleError("invite_used", 409)

        # consume the link first (conditional, so a double tap or a race can't make two pairs)
        upd = (sb.table(INVITES).update({"status": "accepted", "accepted_chart_id": invitee_chart_id,
                                         "updated_at": _iso(now)})
               .eq("id", inv["id"]).eq("status", "pending").execute().data or [])
        if not upd:
            again = _invite_by_id(sb, inv["id"]) or {}
            if again.get("status") == "accepted" and again.get("accepted_chart_id") == invitee_chart_id:
                pair = get_pair(sb, inviter_id, invitee_chart_id)
                if pair:
                    return _accepted_view(sb, pair, invitee_chart_id, inviter, share_day=None)
            raise CircleError("invite_used", 409)

        pair = get_pair(sb, inviter_id, invitee_chart_id)       # already in each other's circle
        if not pair:
            rel = inv.get("relation_type") or "friend"
            row = {"chart_a": inviter_id, "chart_b": invitee_chart_id, "invite_id": inv["id"],
                   "relation_a_to_b": rel, "relation_b_to_a": CC.inverse_relation(rel), "status": "active"}
            try:
                pair = (sb.table(PAIRS).insert(row).execute().data or [None])[0]
            except Exception as e:             # unique index lost a race
                pair = get_pair(sb, inviter_id, invitee_chart_id)
                if not pair:
                    raise
        if share_day:
            set_share(sb, invitee_chart_id, inviter_id, True, now)
        return _accepted_view(sb, pair, invitee_chart_id, inviter, share_day=bool(share_day))
    except CircleError:
        raise
    except CircleUnavailable:
        raise
    except Exception as e:
        _handle(e, "accept_invite")
        raise CircleUnavailable(str(e)[:200])


def _accepted_view(sb, pair: dict, me: str, other_row: dict, share_day) -> dict:
    side = side_of(pair, me)
    return {"pair_id": pair["id"], "chart_id": me, "other_chart_id": side["other"],
            "other_first_name": first_name_of(other_row) or None,
            "relation": {"key": side["relation"]}, "share_day": share_day}


# ── pairs ────────────────────────────────────────────────────────────────────
def get_pair(sb, a: str, b: str) -> Optional[dict]:
    """The pair between two charts, whichever way round it is stored."""
    rows = (sb.table(PAIRS).select("*").eq("chart_a", a).eq("chart_b", b).limit(1).execute().data or [])
    if not rows:
        rows = (sb.table(PAIRS).select("*").eq("chart_a", b).eq("chart_b", a).limit(1).execute().data or [])
    return rows[0] if rows else None


def side_of(pair: dict, me: str) -> dict:
    """{other, relation}: who the other chart is, and what THEY are to ME."""
    if pair.get("chart_a") == me:
        return {"other": pair.get("chart_b"), "relation": pair.get("relation_a_to_b"), "i_invited": True}
    return {"other": pair.get("chart_a"), "relation": pair.get("relation_b_to_a"), "i_invited": False}


def pair_for(sb, me: str, other: str) -> Optional[dict]:
    """The pair if (and only if) it exists. Fail-open: None when the table is missing."""
    try:
        return get_pair(sb, me, other)
    except Exception as e:
        _handle(e, "pair_for")
        return None


def list_pairs(sb, chart_id: str) -> list:
    try:
        a = sb.table(PAIRS).select("*").eq("chart_a", chart_id).limit(200).execute().data or []
        b = sb.table(PAIRS).select("*").eq("chart_b", chart_id).limit(200).execute().data or []
        return a + b
    except Exception as e:
        _handle(e, "list_pairs")
        return []


def leave(sb, chart_id: str, other_chart_id: str) -> bool:
    """Remove the pair for BOTH sides (and both sharing choices). Never touches either chart.
    Idempotent: leaving an already-gone pair is a quiet True."""
    try:
        for a, b in ((chart_id, other_chart_id), (other_chart_id, chart_id)):
            sb.table(PAIRS).delete().eq("chart_a", a).eq("chart_b", b).execute()
            sb.table(SHARING).delete().eq("chart_id", a).eq("other_chart_id", b).execute()
        return True
    except Exception as e:
        _handle(e, "leave")
        raise CircleUnavailable(str(e)[:200])


# ── sharing ("share my day") ─────────────────────────────────────────────────
def get_share(sb, chart_id: str, other_chart_id: str) -> bool:
    """Has `chart_id` chosen to share their day with `other_chart_id`? Default False."""
    try:
        rows = (sb.table(SHARING).select("share_day").eq("chart_id", chart_id)
                .eq("other_chart_id", other_chart_id).limit(1).execute().data or [])
        return bool(rows and rows[0].get("share_day"))
    except Exception as e:
        _handle(e, "get_share")
        return False


def set_share(sb, chart_id: str, other_chart_id: str, share_day: bool,
              now: Optional[datetime] = None) -> bool:
    try:
        sb.table(SHARING).upsert({"chart_id": chart_id, "other_chart_id": other_chart_id,
                                  "share_day": bool(share_day), "updated_at": _iso(now or _now())},
                                 on_conflict="chart_id,other_chart_id").execute()
        return bool(share_day)
    except Exception as e:
        _handle(e, "set_share")
        raise CircleUnavailable(str(e)[:200])


# ── delete / purge ───────────────────────────────────────────────────────────
def purge_chart(sb, chart_id: str) -> list:
    """Chart delete / account delete: drop every invitation and pair row that mentions this
    chart, on either side, plus its sharing choices both ways. The OTHER person's chart is
    never touched. Returns a list of non-fatal errors; a missing table is fine."""
    errs = []
    steps = ((INVITES, "inviter_chart_id"), (INVITES, "accepted_chart_id"),
             (PAIRS, "chart_a"), (PAIRS, "chart_b"),
             (SHARING, "chart_id"), (SHARING, "other_chart_id"))
    for table, col in steps:
        try:
            sb.table(table).delete().eq(col, chart_id).execute()
        except Exception as e:
            if not _table_missing(e):
                errs.append({"table": f"{table}.{col}", "error": str(e)[:160]})
    try:      # a private person's chart going away only unlinks the hint; the invite stays valid
        sb.table(INVITES).update({"private_chart_id": None}).eq("private_chart_id", chart_id).execute()
    except Exception as e:
        if not _table_missing(e):
            errs.append({"table": f"{INVITES}.private_chart_id", "error": str(e)[:160]})
    return errs
