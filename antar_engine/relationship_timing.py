"""
antar_engine/relationship_timing.py

LAYER 3 of the relationship reading — WHEN does what activate, and is this an ending or a fight?

  • Season of the running periods (main + sub, with the inner period as the floor): is this even a breakup?
      ending   — the main and sub period lords are BOTH lords of different strain houses (6th / 8th / 12th)
      friction — a live partnership period beside a strain period (the 7th-lord main period with a 6th-lord sub-period is a
                 fight, not a final break), or a strain sub-period alone
      opening  — a period lord is tied to the 7th house, the 7th lord, Venus or the Darakaraka with no strain lord running
      quiet    — the periods are not built around partnership; neither a fight nor a reunion is the theme
  • The next stretch that genuinely supports partnership: the next sub-period (or inner period inside a year) whose lord is
    CONNECTED to the 7th house, its lord, Venus or the Darakaraka - occupies, rules, conjoins, exchanges (aspect is weak). Connection,
    not friendship: how two planets feel about each other does not wire them together.
  • Week-scale: NOT the sookshma period (days-to-hours long and moved by a four-minute birth-time error; it also mixes a period lord
    with a transit, two different clocks). Moon / Venus / Jupiter transits over the 7th house, the 7th lord's natal sign and the
    Darakaraka's natal sign are the honest instrument below the inner period.

Everything here times THE READER's own move (when a conversation is best supported); it never dates what another person will do.
Pure + fail-open. v1, classical defaults, UNVALIDATED against dated outcomes. Reuses people_pointer / relationships helpers.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.people_pointer import _connected, _running
from antar_engine.relationships import _darakaraka, _sign_aspects

_STRAIN = {6, 8, 12}


def _lordships(lagna: str) -> dict:
    out: dict = {}
    for h in range(1, 13):
        lord = SIGN_LORD.get(_sign_n_from(lagna, h))
        if lord:
            out.setdefault(lord, set()).add(h)
    return out


def _role(planet: Optional[str], planets: dict, lagna: str, lord_of: dict) -> dict:
    if not planet:
        return {"planet": None, "houses": set(), "strain": set(), "placed": None, "conn": [], "strong": False}
    houses = set(lord_of.get(planet, set()))
    conn = _connected(planet, planets, lagna)
    return {"planet": planet, "houses": houses, "strain": houses & _STRAIN,
            "placed": (planets.get(planet) or {}).get("house"),
            "conn": conn, "strong": any(not c.startswith("looks at") for c in conn)}


def _tied7(r: dict) -> bool:
    return any(c in ("rules the house of partnership", "sits in the house of partnership") for c in r["conn"])


def _core(r: dict) -> bool:
    """The 7th house itself, or the period lord IS Venus / the Darakaraka. Conjunctions and exchanges are the weaker, wider net."""
    return _tied7(r) or any(c in ("is the planet of love itself", "is the partner-significator") for c in r["conn"])


def _sign_gap(a: Optional[str], b: Optional[str]) -> Optional[int]:
    if a in SIGNS and b in SIGNS:
        return (SIGNS.index(b) - SIGNS.index(a)) % 12 + 1
    return None


def classify_season(planets: dict, lagna: str, running: dict) -> dict:
    lord_of = _lordships(lagna)
    md, ad, pd = (_role(running.get(k), planets, lagna, lord_of) for k in ("md", "ad", "pd"))
    reasons = []
    gap = _sign_gap((planets.get(md["planet"]) or {}).get("sign"), (planets.get(ad["planet"]) or {}).get("sign")) if md["planet"] and ad["planet"] else None
    ad_from_md_dusthana = gap in _STRAIN
    both_strain = bool(md["strain"] and ad["strain"] and md["strain"] != ad["strain"])
    partner_live_md = bool(md["conn"])
    # the 7th house itself in play: the period lord RULES it or SITS in it
    tied7, core = _tied7, _core
    if both_strain and not (tied7(md) or tied7(ad)):
        reasons.append("the main and sub period both belong to different houses of strain or loss, and neither is the partnership house's own")
        season = "ending"
    elif both_strain:
        reasons.append("two strain houses are running, but one of the periods is the partnership house's own: a fight, not a final break")
        season = "friction"
    elif (md["strain"] or ad["strain"]) and ad_from_md_dusthana and not (md["strong"] or ad["strong"]):
        reasons.append("a strain period with the sub-period in a house of loss from it, and nothing tying either to partnership")
        season = "ending"
    elif (tied7(md) and ad["strain"]) or (tied7(ad) and md["strain"]):
        reasons.append("the partnership house is in play beside a period of strain: a fight inside a bond that is still live, not a final break")
        season = "friction"
    elif core(md) or core(ad):
        reasons.append("the running period is tied to partnership")
        season = "opening"
    else:
        # strain with no tie to the partnership house, or only a conjunction, is a hard stretch / a quiet one, not a statement about the bond
        season = "quiet"
    return {"season": season, "reasons": reasons,
            "md": md["planet"], "ad": ad["planet"], "pd": pd["planet"],
            "md_connected": md["strong"], "ad_connected": ad["strong"], "pd_connected": pd["strong"]}


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def next_supported_stretch(planets: dict, lagna: str, dashas: dict, today: date, years: int = 3) -> dict:
    """First sub-period (within `years`) and first inner period (within 12 months) whose lord is CONNECTED to partnership and is
    not a strain lord. Start is clipped to today for a period already running."""
    lord_of = _lordships(lagna)
    rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
    out: dict = {"ad": None, "pd": None}
    for level, key, horizon in (("antardasha", "ad", today + timedelta(days=365 * years)),
                                ("pratyantardasha", "pd", today + timedelta(days=365))):
        best = None
        for r in rows:
            if not isinstance(r, dict) or str(r.get("level") or r.get("type") or "").lower() != level:
                continue
            s, e = _d(r.get("start_date") or r.get("start")), _d(r.get("end_date") or r.get("end"))
            if not s or not e or e < today or s > horizon:
                continue
            lord = str(r.get("lord_or_sign") or r.get("planet_or_sign") or r.get("lord") or "").title()
            role = _role(lord, planets, lagna, lord_of)
            if role["strain"] or not _core(role):
                continue
            cand = {"lord": lord, "start": max(s, today), "end": e, "why": role["conn"][0]}
            if best is None or cand["start"] < best["start"]:
                best = cand
        out[key] = best
    return out


# ── week scale: Moon / Venus / Jupiter over the partnership points ───────────────
def _targets(planets: dict, lagna: str) -> dict:
    seventh = _sign_n_from(lagna, 7)
    lord7 = SIGN_LORD.get(seventh)
    dk = _darakaraka(planets)
    t = {"the partnership house": seventh}
    if lord7 and (planets.get(lord7) or {}).get("sign") in SIGNS:
        t["the partnership lord"] = planets[lord7]["sign"]
    if dk and (planets.get(dk) or {}).get("sign") in SIGNS:
        t["the partner-significator"] = planets[dk]["sign"]
    return t


def _touch(planet: str, sign_now: str, target_sign: str) -> bool:
    return sign_now == target_sign or _sign_aspects(sign_now, target_sign, planet)


def _sidereal_sign(planet: str, jd: float) -> Optional[str]:
    from antar_engine.antar_ephemeris import planet_longitude, lahiri_ayanamsa
    lon = (planet_longitude(planet, jd) - lahiri_ayanamsa(jd)) % 360
    return SIGNS[int(lon // 30) % 12]


def _jd(dt: datetime) -> float:
    return 2440587.5 + dt.timestamp() / 86400.0


def transit_windows(planets: dict, lagna: str, now: Optional[datetime] = None, sign_fn=None) -> dict:
    """{planet: {'now': bool, 'next': (start, end) | None}} for Moon (next 21 days), Venus (150 days), Jupiter (1 year)."""
    sign_fn = sign_fn or _sidereal_sign
    now = now or datetime.utcnow()
    tg = _targets(planets, lagna)
    spec = {"Moon": (21, 0.25), "Venus": (150, 1.0), "Jupiter": (365, 5.0)}
    out: dict = {}
    for p, (span, step) in spec.items():
        hits, t = [], 0.0
        while t <= span:
            when = now + timedelta(days=t)
            sg = sign_fn(p, _jd(when))
            touching = [name for name, ts in tg.items() if sg and _touch(p, sg, ts)]
            hits.append((when, bool(touching), touching))
            t += step
        nowflag = hits[0][1]
        nxt, i = None, 0
        while i < len(hits):
            if hits[i][1] and (i == 0 or not hits[i - 1][1]):
                j = i
                while j + 1 < len(hits) and hits[j + 1][1]:
                    j += 1
                if i > 0:                                           # the next ENTRY, not the one already under way
                    nxt = (hits[i][0].date(), hits[j][0].date(), hits[i][2][0])
                    break
                i = j
            i += 1
        out[p] = {"now": nowflag, "next": nxt}
    return out


_SEASON_TXT = {
    "ending": ("THE RUNNING PERIODS DESCRIBE AN ENDING SEASON, NOT A FIGHT. The main and sub period belong to different houses of strain "
               "or loss. Say so kindly and plainly: do not hold out a reunion date, and put the weight on closure and on what the reader "
               "wants next."),
    "friction": ("THE RUNNING PERIODS DESCRIBE FRICTION, NOT A FINAL BREAK. A strain period is running; the bond itself is not what "
                 "has ended. Frame it as a hard stretch to work through with a direct conversation."),
    "opening": "THE RUNNING PERIODS ARE TIED TO PARTNERSHIP. This is a live season for the bond: a serious conversation is supported.",
    "quiet": ("THE RUNNING PERIODS ARE NOT BUILT AROUND PARTNERSHIP. Neither a fight nor a reunion is this stretch's theme: do not read "
              "silence or a spark as more than that, and verify the premise before treating a rough patch as a breakup."),
}


_SEASON_TXT_PARTNERED = {
    "ending": ("THE RUNNING PERIODS ARE A HEAVY, TESTING STRETCH FOR THE SHARED LIFE. This reader is PARTNERED: this is a season to protect the "
               "relationship through, NOT an ending and NOT a prediction about the marriage. Never say it is ending, never mention closure or a "
               "reunion. Name the pressure plainly and give one protective step the two of them can take."),
    "friction": ("THE RUNNING PERIODS DESCRIBE FRICTION INSIDE A LIVE BOND. This reader is PARTNERED: frame it as a hard stretch to work "
                 "through together with a direct, calm conversation - not a break."),
}


def _my(d: date) -> str:
    return d.strftime("%b %Y")


def _dm(d: date) -> str:
    return d.strftime("%b %-d")


def analyze_season(chart_data: dict, dashas: Optional[dict] = None, today: Optional[date] = None,
                   now: Optional[datetime] = None, sign_fn=None, with_transits: bool = True, partnered: bool = False) -> dict:
    """{available, season, reasons, stack, next_stretch, transits, facts[]}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        planets, lagna = cd.get("planets") or {}, (cd.get("lagna") or {}).get("sign")
        if not planets or lagna not in SIGNS:
            return {"available": False}
        running = _running(dashas or {})
        if not running.get("md"):
            return {"available": False}
        today = today or date.today()
        s = classify_season(planets, lagna, running)
        nxt = next_supported_stretch(planets, lagna, dashas or {}, today)
        facts = [(_SEASON_TXT_PARTNERED.get(s["season"]) if partnered else None) or _SEASON_TXT[s["season"]]]
        ad, pd = nxt.get("ad"), nxt.get("pd")
        if ad:
            facts.append(f"The next sub-period genuinely tied to partnership runs {_my(ad['start'])} – {_my(ad['end'])}"
                         + (" (it is already under way)" if ad["start"] <= today else "")
                         + ": that is when a serious step is best supported. It times THE READER's move, not another person's reply.")
        else:
            facts.append("No sub-period in the next three years is genuinely tied to partnership: do not offer a supported window; put the "
                         "weight on what the reader can decide themselves.")
        if pd and (not ad or pd["start"] != ad["start"]):
            facts.append(f"Inside the coming year, the inner period tied to partnership runs {_dm(pd['start'])} – {_dm(pd['end'])}; this "
                         "inner period is the finest timing to state.")
        tr = None
        if with_transits:
            try:
                tr = transit_windows(planets, lagna, now, sign_fn)
                bits = []
                if tr["Moon"]["next"]:
                    a, b, _w = tr["Moon"]["next"]
                    bits.append(f"calm days to START a direct conversation: {_dm(a)}" + (f" – {_dm(b)}" if b != a else ""))
                if tr["Venus"]["now"]:
                    bits.append("this is a warmer month for reconnecting")
                elif tr["Venus"]["next"]:
                    a, b, _w = tr["Venus"]["next"]
                    bits.append(f"a warmer stretch for reconnecting: {_dm(a)} – {_dm(b)}")
                if tr["Jupiter"]["now"]:
                    bits.append("the slow, supportive pass is under way this year")
                elif tr["Jupiter"]["next"]:
                    a, b, _w = tr["Jupiter"]["next"]
                    bits.append(f"the slow, supportive pass opens {_my(a)} – {_my(b)}")
                if bits:
                    facts.append("WEEK-SCALE (from slow and fast movers passing the partnership points; the reader's own timing, never a "
                                 "prediction of any reply): " + "; ".join(bits) + ".")
            except Exception:
                tr = None
        facts.append("TIMING RULES: state nothing finer than the inner period or these transit windows; never promise a date for what another "
                     "person will do or when they will make contact.")
        return {"available": True, "season": s["season"], "reasons": s["reasons"], "stack": {k: s[k] for k in ("md", "ad", "pd")},
                "next_stretch": nxt, "transits": tr, "facts": facts}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
