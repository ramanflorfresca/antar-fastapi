"""
Streaks, earned Ask credits, and the monthly free compatibility read.

The product goal is daily return. The mechanic that actually produces that is
loss aversion around a streak — people protect a number they've built far more
reliably than they chase a reward they haven't earned yet. Everything here
serves that, with two deliberate constraints:

  1. A streak can be repaired once a month. A streak that shatters permanently
     doesn't create urgency, it creates quitting — the user who loses a 40-day
     run on a travel day tends not to come back at all. The freeze is both the
     kinder design and the higher-retention one.

  2. Rewards are granted through an idempotent ledger. Milestones carry a
     stable award_key, so however many times the streak endpoint is hit, day 7
     pays out exactly once.

Earned credits sit on TOP of the existing free allowance in entitlements.py —
this module never changes the daily free ask, it only adds to it. Spend order
is always: free daily first, credits second, so a user never burns something
they earned while a free one was sitting unused.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, date

# ── Reward ladder ───────────────────────────────────────────────────────────
# Day 3 exists because the first week is where users are lost; an early, cheap
# win converts a trial into a habit before the habit has to carry itself.
# After day 90 the ladder repeats every 30 days so long-running users keep
# having something ahead of them.
STREAK_MILESTONES = {
    3:   {"ask": 1,  "compat": 0, "label": "3-day streak"},
    7:   {"ask": 3,  "compat": 0, "label": "1 week"},
    14:  {"ask": 3,  "compat": 0, "label": "2 weeks"},
    21:  {"ask": 3,  "compat": 0, "label": "3 weeks"},
    30:  {"ask": 5,  "compat": 1, "label": "1 month"},
    # 45 and 75 exist to keep the gap between rewards at ~15 days. A 30-day
    # stretch with nothing visible ahead is where habituated users quietly
    # stop — there always has to be a next thing close enough to want.
    45:  {"ask": 3,  "compat": 0, "label": "6 weeks"},
    60:  {"ask": 5,  "compat": 1, "label": "2 months"},
    75:  {"ask": 3,  "compat": 0, "label": "10 weeks"},
    90:  {"ask": 10, "compat": 1, "label": "3 months"},
}
_REPEAT_AFTER = 90          # past here, every +30 days repeats
_REPEAT_EVERY = 30
_REPEAT_REWARD = {"ask": 5, "compat": 1, "label": "another month"}

# Credits are use-it-or-lose-it. Long enough not to feel punitive, short
# enough that banked credits pull someone back rather than sitting forever.
ASK_CREDIT_TTL_DAYS = 60
COMPAT_CREDIT_TTL_DAYS = 90
MAX_ASK_BALANCE = 30        # anti-hoarding ceiling

# Everyone gets one compatibility read per rolling calendar month, streak or
# not — a lapsed user needs a reason to reopen the app, and this is it.
MONTHLY_COMPAT_GRANT = 1


def _local_today(tz_offset: int = 0) -> date:
    """User-local date. tz_offset = minutes east of UTC (same as ask_usage)."""
    return (datetime.now(timezone.utc) + timedelta(minutes=int(tz_offset or 0))).date()


def _d(v) -> date | None:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except Exception:
        return None


def milestone_for(streak: int) -> dict | None:
    """Reward for landing exactly on `streak`, or None."""
    if streak in STREAK_MILESTONES:
        return STREAK_MILESTONES[streak]
    if streak > _REPEAT_AFTER and (streak - _REPEAT_AFTER) % _REPEAT_EVERY == 0:
        return _REPEAT_REWARD
    return None


def next_milestone(streak: int) -> dict:
    """What's ahead — the UI needs '2 days to your next reward'."""
    for day in sorted(STREAK_MILESTONES):
        if day > streak:
            return {"at": day, "in_days": day - streak, **STREAK_MILESTONES[day]}
    nxt = _REPEAT_AFTER + _REPEAT_EVERY
    while nxt <= streak:
        nxt += _REPEAT_EVERY
    return {"at": nxt, "in_days": nxt - streak, **_REPEAT_REWARD}


_UID_CACHE: dict = {}


def _uid(sb, chart_id: str):
    """chart_id -> user_id. Streaks and credits belong to the PERSON, not to
    one of their charts, and the pre-existing user_streaks rows are keyed on
    user_id. Cached because this sits on the hot path of every /home."""
    if not chart_id:
        return None
    if chart_id in _UID_CACHE:
        return _UID_CACHE[chart_id]
    try:
        r = sb.table("charts").select("user_id").eq("id", chart_id).execute()
        uid = (r.data or [{}])[0].get("user_id")
    except Exception as e:
        print(f"[gamification] user lookup failed (non-blocking): {e}")
        uid = None
    if uid:
        if len(_UID_CACHE) > 5000:      # bounded: this lives for the process
            _UID_CACHE.clear()
        _UID_CACHE[chart_id] = uid
    return uid


# ── Ledger ──────────────────────────────────────────────────────────────────

def _grant(sb, user_id, kind: str, delta: int, reason: str,
           award_key: str | None, ttl_days: int | None,
           chart_id: str | None = None) -> bool:
    """Insert a grant. Returns False if the award_key already paid out."""
    if delta <= 0 or not user_id:
        return False
    row = {
        "user_id": user_id, "chart_id": chart_id, "kind": kind,
        "delta": int(delta), "reason": reason, "award_key": award_key,
    }
    if ttl_days:
        row["expires_at"] = (datetime.now(timezone.utc)
                             + timedelta(days=ttl_days)).isoformat()
    try:
        sb.table("reward_ledger").insert(row).execute()
        return True
    except Exception as e:
        # Unique violation on award_key = already granted. That's the
        # idempotency working, not an error.
        if "duplicate" in str(e).lower() or "23505" in str(e):
            return False
        print(f"[gamification] grant failed (non-blocking): {e}")
        return False


def balance(sb, chart_id: str, kind: str) -> int:
    """Unexpired credit balance for a kind ('ask' | 'compat').

    Takes chart_id because every caller has one; resolves to the user so a
    person's credits follow them across their charts."""
    uid = _uid(sb, chart_id)
    if not uid:
        return 0
    try:
        rows = sb.table("reward_ledger").select("delta,expires_at") \
                 .eq("user_id", uid).eq("kind", kind).execute().data or []
    except Exception as e:
        print(f"[gamification] balance read failed (non-blocking): {e}")
        return 0
    now = datetime.now(timezone.utc)
    total = 0
    for r in rows:
        exp = r.get("expires_at")
        if exp:
            try:
                if datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < now:
                    continue        # expired grants stop counting
            except Exception:
                pass
        total += int(r.get("delta") or 0)
    return max(0, total)


def spend(sb, chart_id: str, kind: str, n: int = 1, reason: str = "spend") -> bool:
    """Consume n credits. False if the balance can't cover it."""
    if balance(sb, chart_id, kind) < n:
        return False
    uid = _uid(sb, chart_id)
    if not uid:
        return False
    try:
        sb.table("reward_ledger").insert({
            "user_id": uid, "chart_id": chart_id, "kind": kind,
            "delta": -abs(int(n)), "reason": reason,
        }).execute()
        return True
    except Exception as e:
        print(f"[gamification] spend failed (non-blocking): {e}")
        return False


# ── Streak ──────────────────────────────────────────────────────────────────

def _monthly_compat(sb, user_id, chart_id: str, today: date) -> bool:
    """One free compatibility per calendar month, streak or not."""
    key = f"monthly_compat_{today.strftime('%Y_%m')}"
    return _grant(sb, user_id, "compat", MONTHLY_COMPAT_GRANT, key, key,
                  COMPAT_CREDIT_TTL_DAYS, chart_id)


def touch(sb, chart_id: str, tz_offset: int = 0, user_id=None) -> dict:
    """
    Register activity for today and settle any rewards earned.

    Safe to call on every app open — same-day calls are a no-op and every grant
    is idempotent. Never raises: gamification must not be able to break a
    daily reading.

    Writes the SAME user_streaks row the frontend hook reads, so the existing
    streak widget keeps working while the server becomes the source of truth.
    """
    uid = user_id or _uid(sb, chart_id)
    if not uid:
        return {"ok": False, "reason": "no_user"}
    today = _local_today(tz_offset)

    try:
        got = sb.table("user_streaks").select("*").eq("user_id", uid).execute().data
    except Exception as e:
        print(f"[gamification] streak read failed (non-blocking): {e}")
        return {"ok": False}

    row = (got or [None])[0]
    if not row:
        try:
            sb.table("user_streaks").insert({
                "user_id": uid, "current_streak": 1, "longest_streak": 1,
                "total_days_active": 1, "last_active_date": today.isoformat(),
                "freeze_available": True, "freeze_last_reset": today.isoformat(),
            }).execute()
        except Exception as e:
            print(f"[gamification] streak create failed (non-blocking): {e}")
            return {"ok": False}
        _monthly_compat(sb, uid, chart_id, today)
        return {"ok": True, "streak": 1, "changed": True, "awards": [],
                "freeze_used": False}

    last = _d(row.get("last_active_date"))
    streak = int(row.get("current_streak") or 0)
    longest = int(row.get("longest_streak") or 0)
    total = int(row.get("total_days_active") or 0)
    freeze_ok = bool(row.get("freeze_available", True))
    freeze_reset = _d(row.get("freeze_last_reset"))

    # Freezes refill at the start of each calendar month.
    if not freeze_reset or (freeze_reset.year, freeze_reset.month) != (today.year, today.month):
        freeze_ok = True
        freeze_reset = today

    if last == today:
        _monthly_compat(sb, uid, chart_id, today)
        return {"ok": True, "streak": streak, "changed": False, "awards": [],
                "freeze_used": False}

    gap = (today - last).days if last else None
    freeze_used = False
    if gap == 1:
        streak += 1
    elif gap == 2 and freeze_ok:
        # One missed day, repaired. The streak survives and continues.
        streak += 1
        freeze_ok = False
        freeze_used = True
    else:
        streak = 1

    total += 1
    longest = max(longest, streak)

    upd = {
        "current_streak": streak, "longest_streak": longest,
        "total_days_active": total, "last_active_date": today.isoformat(),
        "freeze_available": freeze_ok,
        "freeze_last_reset": freeze_reset.isoformat() if freeze_reset else today.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if freeze_used:
        upd["freeze_last_used"] = today.isoformat()
    try:
        sb.table("user_streaks").update(upd).eq("user_id", uid).execute()
    except Exception as e:
        print(f"[gamification] streak update failed (non-blocking): {e}")

    awards = []
    ms = milestone_for(streak)
    if ms:
        key = f"streak_{streak}"
        if ms["ask"] and _grant(sb, uid, "ask", ms["ask"], key, key,
                                ASK_CREDIT_TTL_DAYS, chart_id):
            awards.append({"kind": "ask", "amount": ms["ask"], "for": ms["label"]})
        if ms["compat"] and _grant(sb, uid, "compat", ms["compat"], key, key,
                                   COMPAT_CREDIT_TTL_DAYS, chart_id):
            awards.append({"kind": "compat", "amount": ms["compat"], "for": ms["label"]})

    _monthly_compat(sb, uid, chart_id, today)

    return {"ok": True, "streak": streak, "changed": True, "awards": awards,
            "freeze_used": freeze_used}


def state(sb, chart_id: str, tz_offset: int = 0) -> dict:
    """Read-only streak + credit state for the UI. Never raises."""
    uid = _uid(sb, chart_id)
    today = _local_today(tz_offset)
    row = {}
    if uid:
        try:
            got = sb.table("user_streaks").select("*").eq("user_id", uid).execute().data
            row = (got or [None])[0] or {}
        except Exception:
            row = {}

    streak = int(row.get("current_streak") or 0)
    last = _d(row.get("last_active_date"))

    # A streak shown as live when it's already broken is a lie the user will
    # catch. Beyond a freeze's reach, report it as gone.
    at_risk = bool(last and last == (today - timedelta(days=1)))
    if last and (today - last).days > 2:
        streak = 0

    ask_bal = balance(sb, chart_id, "ask")
    return {
        "streak": streak,
        "longest_streak": int(row.get("longest_streak") or 0),
        "total_days_active": int(row.get("total_days_active") or 0),
        "counted_today": last == today,
        "at_risk_today": at_risk,          # "open the app to keep your streak"
        "freeze_available": bool(row.get("freeze_available", True)),
        "next_milestone": next_milestone(streak),
        "ask_credits": min(ask_bal, MAX_ASK_BALANCE),
        "compat_credits": balance(sb, chart_id, "compat"),
    }


# ── Practices ───────────────────────────────────────────────────────────────
# Practice completion is a different, higher-intent act than opening the app.
# Astrology without remedy is diagnosis without treatment, so the ritual is the
# part of the product worth paying people to keep doing — these milestones are
# deliberately richer than the login ladder.
#
# The practice streak stays where it already lives (practice_log, computed by
# _practice_calc_streak in main.py). This only settles the REWARDS for it, so
# there is one ledger and one truth about what a user has earned.
PRACTICE_MILESTONES = {
    3:   {"ask": 1,  "compat": 0, "label": "3 days of practice"},
    7:   {"ask": 3,  "compat": 1, "label": "7 days of practice"},
    14:  {"ask": 3,  "compat": 0, "label": "14 days of practice"},
    21:  {"ask": 5,  "compat": 1, "label": "a full 21-day cycle"},
    40:  {"ask": 8,  "compat": 1, "label": "a 40-day sadhana"},
    90:  {"ask": 15, "compat": 2, "label": "90 days of practice"},
}
_P_REPEAT_AFTER = 90
_P_REPEAT_EVERY = 40        # the classical sadhana cycle, not a round number
_P_REPEAT_REWARD = {"ask": 8, "compat": 1, "label": "another 40-day cycle"}


def practice_milestone_for(streak: int) -> dict | None:
    if streak in PRACTICE_MILESTONES:
        return PRACTICE_MILESTONES[streak]
    if streak > _P_REPEAT_AFTER and (streak - _P_REPEAT_AFTER) % _P_REPEAT_EVERY == 0:
        return _P_REPEAT_REWARD
    return None


def next_practice_milestone(streak: int) -> dict:
    for day in sorted(PRACTICE_MILESTONES):
        if day > streak:
            return {"at": day, "in_days": day - streak, **PRACTICE_MILESTONES[day]}
    nxt = _P_REPEAT_AFTER + _P_REPEAT_EVERY
    while nxt <= streak:
        nxt += _P_REPEAT_EVERY
    return {"at": nxt, "in_days": nxt - streak, **_P_REPEAT_REWARD}


def award_practice(sb, chart_id: str, practice_streak: int) -> list:
    """
    Settle rewards for reaching `practice_streak` days of practice.

    Idempotent per (user, milestone): award_key is 'practice_<n>', so logging
    a second practice on the same day cannot pay twice. Returns the awards
    granted now (empty if this streak length was already settled).
    """
    ms = practice_milestone_for(int(practice_streak or 0))
    if not ms:
        return []
    uid = _uid(sb, chart_id)
    if not uid:
        return []
    key = f"practice_{int(practice_streak)}"
    out = []
    if ms["ask"] and _grant(sb, uid, "ask", ms["ask"], key, key,
                            ASK_CREDIT_TTL_DAYS, chart_id):
        out.append({"kind": "ask", "amount": ms["ask"], "for": ms["label"]})
    if ms["compat"] and _grant(sb, uid, "compat", ms["compat"], key, key,
                               COMPAT_CREDIT_TTL_DAYS, chart_id):
        out.append({"kind": "compat", "amount": ms["compat"], "for": ms["label"]})
    return out


def practice_reward_message(streak: int, awards: list) -> str:
    """
    Message for a completed practice — states only what was actually granted.

    The previous copy promised "a free Deep Dive Location Audit" at day 7 and
    nothing was ever granted. Copy here is generated FROM the awards list, so
    it cannot drift from what the ledger did.
    """
    if awards:
        parts = []
        for a in awards:
            n = a["amount"]
            if a["kind"] == "ask":
                parts.append(f"{n} bonus question{'s' if n != 1 else ''}")
            else:
                parts.append(f"{n} compatibility read{'s' if n != 1 else ''}")
        earned = " and ".join(parts)
        return f"{streak}-day streak — you've earned {earned}."
    if streak >= 3:
        nxt = next_practice_milestone(streak)
        return (f"{streak}-day streak. {nxt['in_days']} more "
                f"{'day' if nxt['in_days'] == 1 else 'days'} to your next reward.")
    return "Practice logged. Every day counts."


def history(sb, chart_id: str, limit: int = 30) -> list:
    """
    Recent ledger entries for a "how did I earn this?" view.

    Grants and spends both appear, newest first, with the reason rendered for
    humans and an `expired` flag so the UI can grey out dead credits rather
    than silently dropping them (a credit that vanishes with no explanation
    reads as a bug).
    """
    uid = _uid(sb, chart_id)
    if not uid:
        return []
    try:
        rows = (sb.table("reward_ledger")
                  .select("kind,delta,reason,expires_at,created_at")
                  .eq("user_id", uid)
                  .order("created_at", desc=True)
                  .limit(int(limit)).execute().data or [])
    except Exception as e:
        print(f"[gamification] history read failed (non-blocking): {e}")
        return []
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        exp = r.get("expires_at")
        expired = False
        if exp:
            try:
                expired = datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < now
            except Exception:
                pass
        out.append({
            "kind": r.get("kind"),
            "delta": int(r.get("delta") or 0),
            "label": _reason_label(r.get("reason") or ""),
            "expires_at": exp,
            "expired": expired,
            "created_at": r.get("created_at"),
        })
    return out


def _reason_label(reason: str) -> str:
    """Ledger reasons are machine keys; give the UI something readable."""
    if reason.startswith("streak_"):
        return f"{reason.split('_')[-1]}-day streak"
    if reason.startswith("practice_"):
        return f"{reason.split('_')[-1]} days of practice"
    if reason.startswith("monthly_compat_"):
        parts = reason.split("_")
        return f"Monthly free reading ({parts[-2]}-{parts[-1]})"
    if reason.startswith("compat_read:"):
        return "Compatibility reading"
    if reason == "ask_question":
        return "Question asked"
    return reason.replace("_", " ").capitalize()
