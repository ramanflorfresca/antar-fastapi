"""
antar_engine/deep_read.py

Layer 3 "Day Deep Read" — prose synthesis composed ON TOP of the shipped LK
engine. Computes nothing the engine already computes: reuses lk_trigger,
compose_daily_card, the dasha lookup (passed in), and the live transit math.

Pieces (per COWORK_Day_Deep_Read brief):
  1. echoes_layer_1   — compose_daily_card output, built EXACTLY like
                        home_composer.py so the Today card and the Deep Read
                        never disagree (cross-screen invariant).
  2. house_scan       — 12 deterministic {house, domain, state, note} records.
  3. body_signals     — friction-gated body map (0..5 entries; [] is fine).
  4. themes           — 4..6 grouped themes with aggregate tone.
  5. opening/themes[].paragraph/closing — ONE Claude Sonnet call (cache-gated
                        by the caller; this module only builds + parses).

Strip contract:
  echoes_layer_1 strings   -> source="curated_static" (planet-as-actor kept)
  every LLM-synthesized /   -> source="llm" (full scrub; planet names removed,
  deterministic note          house numbers removed)

English is the source of truth; the caller translates at response time.
"""
from __future__ import annotations
from antar_engine.constants import SONNET_MODEL

import json
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from antar_engine.home_composer import ENERGY_LANG  # planet -> energy phrase (DRY)

# ── Static maps ──────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# House -> plain-English life domain (brief Section 2; no jargon, no house numbers)
DOMAIN_MAP = {
    1: "self & vitality", 2: "money & resources", 3: "effort & peers",
    4: "home & comfort", 5: "creativity & children", 6: "conflicts & routines",
    7: "partnership", 8: "hidden & shared", 9: "luck & father",
    10: "career & authority", 11: "income & allies", 12: "release & private",
}

# Theme key -> constituent houses (brief Section 4, verbatim)
THEME_HOUSES = {
    "foundation": [1, 4, 8],
    "relationships": [3, 7, 11],
    "work": [6, 10],
    "expansion": [5, 9, 11],
    "money": [2, 11],
    "body": [1, 2, 6],
    "inner": [8, 12],
}

THEME_LABEL = {
    "foundation": "Foundation & roots",
    "relationships": "Relationships & allies",
    "work": "Work & responsibility",
    "expansion": "Growth & expansion",
    "money": "Money & resources",
    "body": "Body & energy",
    "inner": "Inner life & release",
}

# House -> body region (canonical kalapurusha mapping; plain English, no jargon)
HOUSE_BODY = {
    1: "the head and overall vitality",
    2: "the face, eyes, and throat",
    3: "the arms, shoulders, and hands",
    4: "the chest and heart",
    5: "the upper abdomen and stomach",
    6: "the gut and digestion",
    7: "the lower back and kidneys",
    8: "the reproductive and eliminative organs",
    9: "the hips and thighs",
    10: "the knees and joints",
    11: "the calves and ankles",
    12: "the feet and sleep",
}

# Planet -> body region (canonical karaka mapping; plain English, no jargon)
PLANET_BODY = {
    "Sun": "the heart and eyes",
    "Moon": "the fluids and stomach",
    "Mars": "the muscles and blood",
    "Mercury": "the skin and nerves",
    "Jupiter": "the liver and weight",
    "Venus": "the kidneys and reproductive system",
    "Saturn": "the bones, teeth, and joints",
    "Rahu": "the nervous system",
    "Ketu": "the nervous system and digestion",
}

BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
DUSHTHANA = {6, 8, 12}

# lower = slower (for picking the representative actor in a house)
_SLOWNESS = {
    "Saturn": 1, "Rahu": 2, "Ketu": 2, "Jupiter": 3,
    "Mars": 4, "Sun": 5, "Venus": 6, "Mercury": 7, "Moon": 8,
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _cap(s: str) -> str:
    if not s:
        return s
    return s[0].upper() + s[1:]


def _lagna_sign(chart_data: dict) -> str:
    lg = chart_data.get("lagna", {})
    s = lg.get("sign") if isinstance(lg, dict) else None
    return s if s in SIGNS else "Aries"


def _sign_in_house(lagna_sign: str, h: int) -> str:
    try:
        idx = (SIGNS.index(lagna_sign) + (h - 1)) % 12
        return SIGNS[idx]
    except Exception:
        return "Aries"


def _occupants(transits: list) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {}
    for t in (transits or []):
        if not isinstance(t, dict) or "error" in t:
            continue
        p = t.get("planet")
        h = t.get("current_house")
        try:
            h = int(h)
        except Exception:
            continue
        if p and 1 <= h <= 12:
            out.setdefault(h, []).append(p)
    return out


def _rep_occupant(occ: List[str], state: str) -> Optional[str]:
    """The actor whose energy phrase best characterises the house today."""
    if not occ:
        return None
    if state in ("friction", "mixed"):
        mal = [p for p in occ if p in MALEFICS]
        pool = mal or occ
    else:
        ben = [p for p in occ if p in BENEFICS]
        pool = ben or occ
    return sorted(pool, key=lambda p: _SLOWNESS.get(p, 99))[0]


# ── 1. echoes_layer_1 — built EXACTLY like home_composer.py ───────────────────

def compute_echoes_layer_1(chart_data: dict, md_lord: str, today: date,
                           transits: list) -> dict:
    """
    Mirror of the home_composer lkRead block: same LK_CONDITIONS scan, same
    matches_trigger predicate, same compose_daily_card(recent_headlines=[]),
    same local-date anchor. Returned object IS the Today card echo block.
    """
    from antar_engine.lk_conditions import LK_CONDITIONS
    from antar_engine.lk_trigger import matches_trigger
    from antar_engine.composition import compose_daily_card

    dasha = {"md_lord": md_lord}
    fired = []
    for cid, cond in LK_CONDITIONS.items():
        try:
            if matches_trigger(cond["trigger"], chart_data, transits, dasha):
                fired.append({**cond, "id": cid})
        except Exception:
            continue
    # recent_headlines=[] to match home (no 14-day history wired there yet)
    return compose_daily_card(fired, md_lord, [], today)


# ── 2. 12-house scanner ──────────────────────────────────────────────────────

def _house_state(h: int, occ: List[str], natal_planets: dict,
                 lagna_sign: str) -> str:
    from antar_engine.lk_trigger import is_sleeping
    has_ben = any(p in BENEFICS for p in occ)
    has_mal = any(p in MALEFICS for p in occ)
    lord = SIGN_LORD.get(_sign_in_house(lagna_sign, h))
    lord_sleep = bool(lord and is_sleeping(lord, natal_planets))

    if not occ:
        base = "neutral"
    elif h in DUSHTHANA:
        base = "friction" if has_mal else ("mixed" if has_ben else "neutral")
    elif h in KENDRA_TRIKONA:
        if has_ben and not has_mal:
            base = "supportive"
        elif has_ben and has_mal:
            base = "mixed"
        elif has_mal and not has_ben:
            base = "mixed"
        else:
            base = "neutral"
    else:  # 2, 3, 11 — neutral/upachaya
        if has_ben and not has_mal:
            base = "supportive"
        elif has_mal and not has_ben:
            base = "mixed"
        elif has_ben and has_mal:
            base = "mixed"
        else:
            base = "neutral"

    if lord_sleep and base == "supportive":
        base = "mixed"
    return base


def _house_note(h: int, occ: List[str], state: str) -> str:
    domain = DOMAIN_MAP[h]
    rep = _rep_occupant(occ, state)
    energy = ENERGY_LANG.get(rep) if rep else None
    if state == "supportive":
        if energy:
            return f"{_cap(energy)} is flowing easily through {domain} today."
        return f"{_cap(domain)} feels supported and responsive today."
    if state == "friction":
        if energy:
            return f"{_cap(energy)} is meeting resistance around {domain} today."
        return f"{_cap(domain)} is under pressure today — move gently here."
    if state == "mixed":
        if energy:
            return f"{_cap(energy)} is stirring {domain}, but the day pulls both ways."
        return f"{_cap(domain)} is active but unsettled today."
    if energy:
        return f"{_cap(energy)} passes lightly through {domain} today."
    return f"{_cap(domain)} is quiet today — neither pushed nor blocked."


def build_house_scan(chart_data: dict, transits: list, natal_planets: dict,
                     echoes: dict) -> List[dict]:
    lagna_sign = _lagna_sign(chart_data)
    occ_map = _occupants(transits)

    # Bias the headline condition's house to match the echo polarity.
    hl_house = None
    hl_pol = None
    cid = echoes.get("condition_id")
    if cid and cid != "flat_day":
        try:
            from antar_engine.lk_conditions import LK_CONDITIONS
            trig = (LK_CONDITIONS.get(cid) or {}).get("trigger", {})
            hl_house = trig.get("natal_house")
            hl_pol = echoes.get("polarity")
        except Exception:
            pass

    scan = []
    for h in range(1, 13):
        occ = occ_map.get(h, [])
        state = _house_state(h, occ, natal_planets, lagna_sign)
        if hl_house == h:
            if hl_pol == "negative":
                state = "friction"
            elif hl_pol == "positive" and state != "friction":
                state = "supportive"
        scan.append({
            "house": h,
            "domain": DOMAIN_MAP[h],
            "state": state,
            "note": _house_note(h, occ, state),
        })
    return scan


# ── 3. body-mapping module ───────────────────────────────────────────────────

def _lk_weak(planet: str, natal_planets: dict, occ_map: Dict[int, List[str]]) -> bool:
    """LK state weak/sleeping/blocked for a planet today."""
    if not planet:
        return False
    from antar_engine.lk_trigger import is_sleeping
    if is_sleeping(planet, natal_planets):
        return True
    # weak = debilitated natal dignity
    try:
        from antar_engine.antar_ephemeris import _planet_strength
        sign = (natal_planets.get(planet) or {}).get("sign", "")
        if _planet_strength(planet, sign) == "debilitated":
            return True
    except Exception:
        pass
    # blocked = currently transiting a difficult (dushthana) house
    for dh in DUSHTHANA:
        if planet in occ_map.get(dh, []):
            return True
    return False


def build_body_signals(chart_data: dict, transits: list, natal_planets: dict,
                       house_scan: List[dict]) -> List[dict]:
    lagna_sign = _lagna_sign(chart_data)
    occ_map = _occupants(transits)
    out: List[dict] = []
    for rec in house_scan:
        if rec["state"] != "friction":
            continue
        h = rec["house"]
        lord = SIGN_LORD.get(_sign_in_house(lagna_sign, h))
        malefics_here = [p for p in occ_map.get(h, []) if p in MALEFICS]
        # (b): house lord OR a malefic transiting it is weak/sleeping/blocked
        cond_b = _lk_weak(lord, natal_planets, occ_map)
        if not cond_b:
            cond_b = any(_lk_weak(m, natal_planets, occ_map) for m in malefics_here)
        if not cond_b:
            continue
        body = HOUSE_BODY[h]
        out.append({
            "house": h,
            "body_part": body,
            "note": (f"{_cap(body)} may ask for extra care today — "
                     f"rest, water, and a slower pace help."),
        })
        if len(out) >= 5:
            break
    return out


# ── 4. theme grouper ─────────────────────────────────────────────────────────

def build_themes(house_scan: List[dict], polarity: str,
                 lead_keys: Optional[List[str]] = None) -> List[dict]:
    state_by = {r["house"]: r["state"] for r in house_scan}
    note_by = {r["house"]: r["note"] for r in house_scan}

    candidates = []
    for key, houses in THEME_HOUSES.items():
        states = [state_by.get(h, "neutral") for h in houses]
        all_neutral = all(s == "neutral" for s in states)
        if all(s == "supportive" for s in states):
            tone = "supportive"
        elif any(s == "friction" for s in states):
            tone = "friction"
        else:
            tone = "mixed"
        candidates.append({
            "key": key,
            "title": THEME_LABEL[key],
            "houses": houses,
            "tone": tone,
            "notes": [note_by.get(h, "") for h in houses],
            "_all_neutral": all_neutral,
        })

    qualifying = [c for c in candidates if not c["_all_neutral"]]

    neg = (polarity == "negative")
    order = ({"friction": 0, "mixed": 1, "supportive": 2} if neg
             else {"supportive": 0, "mixed": 1, "friction": 2})
    qualifying.sort(key=lambda c: order.get(c["tone"], 1))

    # [one-signal] The committed Today lead theme(s) open the Deep Read —
    # same signal, expanded; never silently replaced.
    lead_keys = [k for k in (lead_keys or []) if k in THEME_HOUSES]
    if lead_keys:
        by_key = {c["key"]: c for c in candidates}
        front = [by_key[k] for k in lead_keys if k in by_key]
        rest = [c for c in qualifying if c["key"] not in set(lead_keys)]
        qualifying = front + rest

    # Enforce a floor of 4: pad with skipped neutral themes if needed.
    if len(qualifying) < 4:
        extras = [c for c in candidates if c["_all_neutral"]
                  and c["key"] not in {q["key"] for q in qualifying}]
        qualifying = qualifying + extras[: (4 - len(qualifying))]
    # [one-signal] Expansion, not re-derivation: cap at 4 when a committed
    # lead exists (lead + up to 3 supporting), else the legacy 6.
    return qualifying[: 4 if lead_keys else 6]


# ── 5. LLM synthesizer wrapper ───────────────────────────────────────────────

# Literal prompt constraints (pasted verbatim from the brief).
_SYNTH_RULES = (
    "Write in plain English. Never use planet Sanskrit names, house numbers, or "
    "Vedic terms. The structured input may contain planet names; in your output, "
    "refer to planets only when they are the actor in a sentence (e.g. 'Mars wants "
    "discharge' is fine, 'Mars is moving in a way that...' is not - use 'conditions "
    "are stirring' instead).\n"
    "Do not introduce signals that aren't in the structured input above. If the "
    "input says house 9 is friction, you write about luck, travel, or authority "
    "being under pressure; you do not invent new content.\n"
    "Each theme paragraph is 2-3 sentences. The opening is one sentence. The "
    "closing is one paragraph (3-4 sentences).\n"
    "Match the texture, do, and don't from the echoes_layer_1 block. Your synthesis "
    "must be consistent with what the user already saw on the Today card - never "
    "contradict it.\n"
    "No gendered framing. Use 'close people' or 'allies' or 'supportive people', "
    "never 'close men' or 'close women'.\n"
    "No occupation-specific guesses. If the input doesn't say what the user does, "
    "don't guess.\n"
    "When a committed_today block is present in the structured input, it is what "
    "the user already saw on the Today card. Your opening sentence must surface "
    "the SAME lead theme as committed_today.headline - expand it, never replace "
    "it. Nothing you write may contradict committed_today.body_text; the body "
    "theme paragraph must open from that state."
)


def _echo_block(echoes: dict) -> dict:
    return {
        "polarity": echoes.get("polarity"),
        "headline": echoes.get("headline"),
        "gist": echoes.get("gist"),
        "cause": echoes.get("cause"),
        "use": echoes.get("use"),
        "do": echoes.get("do"),
        "dont": echoes.get("dont"),
    }


# [one-signal] Static system block — byte-stable across calls and charts so
# the KV-cache split applies (rules above, "## LIVE DATA" below; same pattern
# as call_llm_claude).
_SYNTH_STATIC = (
    "You are writing the daily Deep Read for a life-navigation app. You are "
    "given a structured day-reading below the ## LIVE DATA marker. Synthesize "
    "it into plain prose.\n\n"
    "RULES:\n" + _SYNTH_RULES
    + "\n\nReturn ONLY valid JSON, no preamble, no code fence, exactly:\n"
    "{\"opening\": \"<one sentence>\", "
    "\"themes\": [{\"key\": \"<theme key>\", \"paragraph\": \"<2-3 sentences>\"}], "
    "\"closing\": \"<one paragraph, 3-4 sentences>\"}\n"
    "Provide exactly one themes entry for each key listed in "
    "theme_keys_in_order, in that order."
)


def _build_synth_live(echoes: dict, themes: List[dict],
                      body_signals: List[dict], house_scan: List[dict],
                      committed: Optional[dict] = None) -> str:
    structured = {
        "echoes_layer_1": _echo_block(echoes),
        "house_scan": [{"domain": r["domain"], "state": r["state"], "note": r["note"]}
                       for r in house_scan],
        "themes": [{"key": t["key"], "title": t["title"], "tone": t["tone"],
                    "notes": t["notes"]} for t in themes],
        "body_signals": [{"note": b["note"]} for b in body_signals],
        "theme_keys_in_order": [t["key"] for t in themes],
    }
    if committed:
        structured["committed_today"] = {
            "headline": committed.get("headline") or "",
            "lead_domains": committed.get("highlight_domains") or [],
            "direction": committed.get("direction") or "",
            "body_text": committed.get("body_text") or "",
        }
    return "## LIVE DATA\n" + json.dumps(structured, ensure_ascii=False, indent=2)


def _extract_json(raw: str) -> dict:
    if not raw:
        return {}
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1:]
    a = s.find("{")
    b = s.rfind("}")
    if a != -1 and b != -1 and b > a:
        s = s[a:b + 1]
    try:
        return json.loads(s)
    except Exception:
        return {}


def _fallback_opening(echoes: dict, committed: Optional[dict] = None) -> str:
    chl = ((committed or {}).get("headline") or "").strip()
    if chl:
        return chl if chl.endswith(".") else chl + "."
    hl = (echoes.get("headline") or "").strip()
    if hl:
        return hl if hl.endswith(".") else hl + "."
    return "A day to move with awareness — some areas open, others ask for patience."


def _fallback_closing(echoes: dict) -> str:
    do = (echoes.get("do") or "").strip()
    dont = (echoes.get("dont") or "").strip()
    parts = ["Take the day in order rather than all at once."]
    if do:
        parts.append(do)
    if dont:
        parts.append(dont)
    parts.append("Small, steady choices carry further today than big ones.")
    return " ".join(parts)


def _fallback_paragraph(theme: dict) -> str:
    notes = [n for n in (theme.get("notes") or []) if n]
    if notes:
        return " ".join(notes[:2])
    return f"{theme.get('title', 'This area')} is steady today — keep your usual rhythm."


def _fallback_synth(echoes: dict, themes: List[dict],
                    body_signals: List[dict],
                    committed: Optional[dict] = None) -> dict:
    return {
        "opening": _fallback_opening(echoes, committed),
        "themes": [{"key": t["key"], "title": t["title"], "tone": t["tone"],
                    "paragraph": _fallback_paragraph(t)} for t in themes],
        "closing": _fallback_closing(echoes),
    }


# ── no-invention gate (polarity-aware) ───────────────────────────────────────

_ADVERSE_CUES = re.compile(
    r"(?i)\b(strain|strained|worr\w+|pressure|trouble\w*|loss|lose|losing|"
    r"difficult\w*|hard|tension|conflict\w*|fragile|drain\w*|stress\w*|"
    r"struggl\w*|risk\w*|guard|protect|careful|caution\w*|avoid|setback\w*|"
    r"friction|discomfort|expense|cost\w*)\b"
)


def _grounding_ok(synth: dict, house_scan: list):
    """(ok, offending). Reject an ADVERSE claim about a life-area whose computed
    house state is NOT friction/mixed — that contradicts the house_scan the
    Today card also reads. Neutral/positive mentions are fine (all 12 houses are
    in the model's input); only manufactured strain is caught."""
    from antar_engine.today_narration import _AREA_MENTIONS
    from antar_engine.life_areas import AREA_HOUSE
    state_by = {r.get("house"): r.get("state") for r in (house_scan or [])}
    texts = [synth.get("opening", ""), synth.get("closing", "")]
    texts += [t.get("paragraph", "") for t in (synth.get("themes") or [])]
    blob = " ".join(t for t in texts if t)
    offending = []
    for sent in re.split(r"(?<=[.!?])\s+", blob):
        if not _ADVERSE_CUES.search(sent):
            continue
        for rx, area in _AREA_MENTIONS:
            if rx.search(sent):
                st = state_by.get(AREA_HOUSE.get(area))
                if st not in ("friction", "mixed"):
                    offending.append((area, st or "neutral"))
    return (not offending, offending)


async def synthesize(claude_client, echoes: dict, themes: List[dict],
                     body_signals: List[dict], house_scan: List[dict],
                     committed: Optional[dict] = None) -> dict:
    if claude_client is None:
        return _fallback_synth(echoes, themes, body_signals, committed)
    live = _build_synth_live(echoes, themes, body_signals, house_scan, committed)
    _MAX_ATTEMPTS = 2
    for _attempt in range(_MAX_ATTEMPTS):
        try:
            import time as _time_dr
            _t0 = _time_dr.monotonic()
            resp = await claude_client.messages.create(
                model=SONNET_MODEL,
                max_tokens=1000,
                temperature=0.4,
                system=[
                    {"type": "text", "text": _SYNTH_STATIC,
                     "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": live},
                ],
                messages=[{"role": "user", "content": "Write the Deep Read JSON now."}],
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
            try:
                _u = resp.usage
                print(f"[deep_read] synth {_time_dr.monotonic() - _t0:.2f}s "
                      f"in={getattr(_u, 'input_tokens', 0)} "
                      f"out={getattr(_u, 'output_tokens', 0)} "
                      f"cache_hit={getattr(_u, 'cache_read_input_tokens', 0) or 0} "
                      f"cache_write={getattr(_u, 'cache_creation_input_tokens', 0) or 0}")
            except Exception:
                pass
            raw = resp.content[0].text.strip()
            data = _extract_json(raw)
            opening = (data.get("opening") or "").strip() or _fallback_opening(echoes, committed)
            closing = (data.get("closing") or "").strip() or _fallback_closing(echoes)
            pmap = {}
            for d in (data.get("themes") or []):
                if isinstance(d, dict) and d.get("key"):
                    pmap[d["key"]] = (d.get("paragraph") or "").strip()
            out_themes = []
            for t in themes:
                para = pmap.get(t["key"]) or _fallback_paragraph(t)
                out_themes.append({"key": t["key"], "title": t["title"],
                                   "tone": t["tone"], "paragraph": para})
            result = {"opening": opening, "themes": out_themes, "closing": closing}
            _ok, _bad = _grounding_ok(result, house_scan)
            if _ok:
                return result
            print(f"[deep_read] no-invention gate rejected {_bad} (attempt "
                  f"{_attempt + 1}/{_MAX_ATTEMPTS}); "
                  f"{'retrying' if _attempt + 1 < _MAX_ATTEMPTS else 'using grounded fallback'}")
        except Exception as e:
            print(f"[deep_read] synth failed (fallback): {e}")
            return _fallback_synth(echoes, themes, body_signals, committed)
    # every attempt manufactured strain about a fine area -> grounded synth.
    return _fallback_synth(echoes, themes, body_signals, committed)


# ── orchestrator ─────────────────────────────────────────────────────────────

async def build_deep_read(chart_id: str, chart_row: dict, chart_data: dict,
                          lk_data: dict, md_lord: str, tz_offset: int,
                          today_str: str, claude_client=None,
                          committed: Optional[dict] = None) -> dict:
    """English-source Deep Read payload (unstripped, untranslated)."""
    from antar_engine.transits_engine import calculate_current_transits
    from antar_engine.lk_trigger import _natal_planets

    now_local = datetime.utcnow()  # date already fixed by caller via today_str
    try:
        local_date = date.fromisoformat(today_str[:10])
    except Exception:
        local_date = now_local.date()

    transits = (calculate_current_transits(chart_data) or {}).get("current_transits", [])
    natal_planets = _natal_planets(chart_data)

    echoes = compute_echoes_layer_1(chart_data, md_lord, local_date, transits)
    house_scan = build_house_scan(chart_data, transits, natal_planets, echoes)
    body_signals = build_body_signals(chart_data, transits, natal_planets, house_scan)
    polarity = echoes.get("polarity", "flat")

    # [one-signal] The committed Today selection (today_signal) is canon:
    # its lead theme(s) open the Deep Read, and its BODY state is the single
    # source for body narration — never re-derived into a contradiction.
    _lead_keys: List[str] = []
    if committed:
        try:
            from antar_engine.today_signal import DOMAIN_TO_THEME
            _lead_keys = [DOMAIN_TO_THEME[d]
                          for d in (committed.get("highlight_domains") or [])
                          if d in DOMAIN_TO_THEME]
        except Exception:
            _lead_keys = []

    themes = build_themes(house_scan, polarity, lead_keys=_lead_keys)

    if committed and (committed.get("body_text") or "").strip():
        _btxt = committed["body_text"].strip()
        _bstate = committed.get("body_state") or "even"
        for _t in themes:
            if _t["key"] == "body":
                if _bstate in ("even", "high"):
                    _t["tone"] = "supportive" if _bstate == "high" else "mixed"
                    _t["notes"] = [_btxt]
                else:
                    _t["tone"] = "friction"
                    _t["notes"] = [_btxt] + [n for n in _t["notes"] if n][:2]
        if _bstate in ("even", "high"):
            # Today told the user energy is fine — care-notes derived from a
            # different model must not contradict that on the same day.
            body_signals = []

    synth = await synthesize(claude_client, echoes, themes, body_signals,
                             house_scan, committed)

    return {
        "chart_id": chart_id,
        "language": "en",
        "date": today_str,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "opening": synth["opening"],
        "themes": synth["themes"],
        "closing": synth["closing"],
        "body_signals": body_signals,   # [] not null when empty
        "house_scan": house_scan,       # exactly 12
        "echoes_layer_1": echoes,
        "_committed_fp": ({"domains": list(committed.get("highlight_domains") or []),
                           "direction": committed.get("direction")}
                          if committed else None),
    }


# ── strip contract ───────────────────────────────────────────────────────────

def strip_deep_read_payload(payload: dict, language: str = "en") -> dict:
    """
    echoes_layer_1 -> source='curated_static' (planet-as-actor kept, Path B).
    Everything LLM-synthesized -> source='llm' (full scrub: planet names and
    house numbers removed).
    """
    from antar_engine.output_strips import apply_user_facing_strips as _apply

    def _llm(s):
        if isinstance(s, str):
            return _apply(s, language=language, field_type="plain",
                          source="llm", depth="user")
        return s

    def _curated(node):
        if isinstance(node, dict):
            return {k: _curated(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_curated(x) for x in node]
        if isinstance(node, str):
            return _apply(node, language=language, field_type="plain",
                          source="curated_static", depth="user")
        return node

    out = dict(payload)
    out["opening"] = _llm(payload.get("opening"))
    out["closing"] = _llm(payload.get("closing"))
    out["themes"] = [
        {**t, "title": _llm(t.get("title")), "paragraph": _llm(t.get("paragraph"))}
        for t in (payload.get("themes") or [])
    ]
    out["house_scan"] = [
        {**h, "note": _llm(h.get("note"))}
        for h in (payload.get("house_scan") or [])
    ]
    out["body_signals"] = [
        {**b, "note": _llm(b.get("note"))}
        for b in (payload.get("body_signals") or [])
    ]
    out["echoes_layer_1"] = _curated(payload.get("echoes_layer_1"))
    return out
