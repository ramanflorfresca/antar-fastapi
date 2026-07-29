"""
antar_engine/relationships.py

Deterministic relationship / marriage engine — the D-9 (Navamsa) counterpart of
the D-10 career engine. It reads the REAL chart and answers, deterministically:

  • ENTRY + TIMING  — is a partner/marriage promised, and WHEN does it ripen?
  • PARTNER         — what is the spouse like, and how/where are they met?
  • DURABILITY      — is there strain / separation risk, and what relieves it?
  • QUALITY         — the harmony of married/family life.

Method (the owner's spine):
  • Jaimini — Darakaraka (DK, the spouse karaka = lowest-degree planet) and the
    Upapada Lagna (UL, arudha of the 12th = the marriage point) layered over the
    Parashari 7th house / 7th lord.
  • Karaka by gender — Venus is the wife-karaka, Jupiter the husband-karaka; the
    spouse karaka is chosen from the NATIVE's gender (a man's spouse = Venus, a
    woman's = Jupiter).
  • D-9 is the marriage chart — promise is CONFIRMED there, and timing is read by
    running the dasha lord through its D-9 placement (the relationship analog of
    reading the career dasha lord through the D-10).
  • Mangal (Kuja) dosha — Mars on the marriage axis, with classical cancellations.

The LLM only narrates the result; it never invents the astrology. v1 rules are a
principled starting point to calibrate against real charts, not the final word.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from antar_engine.d10_career import (
    SIGNS, SIGN_LORD, _EXALT, _OWN, _DEBIL, _sign_n_from, PLANET_CHAPTER,
)

_MALEFICS = {"Mars", "Saturn", "Sun", "Rahu", "Ketu"}
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_CHARA = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# Spouse nature by the sign of the significator (DK / 7th / D-9 7th). Short,
# plain, present-tense traits — the narrator weaves them, never lists signs.
SIGN_TRAITS = {
    "Aries":       "energetic, independent, direct — quick to act, strong-willed",
    "Taurus":      "steady, loyal, sensual — values comfort, beauty, security",
    "Gemini":      "communicative, witty, youthful — curious and versatile",
    "Cancer":      "nurturing, emotional, home-loving — protective and caring",
    "Leo":         "warm, proud, generous — wants respect, naturally magnetic",
    "Virgo":       "practical, precise, service-minded — health- and detail-aware",
    "Libra":       "charming, fair, refined — partnership-minded and social",
    "Scorpio":     "intense, passionate, private — deeply loyal, all-or-nothing",
    "Sagittarius": "optimistic, free-spirited, honest — philosophical, loves freedom",
    "Capricorn":   "mature, ambitious, dutiful — reserved, dependable, serious",
    "Aquarius":    "unconventional, friendly, independent — humane, forward-looking",
    "Pisces":      "compassionate, dreamy, spiritual — gentle and adaptable",
}

# Where/how the partner is met — from the 7th lord's HOUSE (from lagna).
HOUSE_MEETING = {
    1:  "through your own initiative — someone drawn to who you are",
    2:  "through family, or your financial/social circle",
    3:  "through friends, siblings, or on short travels nearby",
    4:  "through family, home, property, or your home region",
    5:  "through romance, creativity, education, or social occasions",
    6:  "at work, through service, or during a demanding period of life",
    7:  "through open social life, business dealings, or the public sphere",
    8:  "suddenly or unexpectedly — often through a turning point or shared depth",
    9:  "through travel, higher study, mentors, or a foreign connection",
    10: "through work, career, or someone of standing",
    11: "through friends, networks, or a social group",
    12: "in a distant/foreign place, or quietly and privately",
}

# What a house means for the MARRIAGE timeline (dasha lord's D-9 house).
D9_HOUSE_ARENA = {
    1:  "your own self & how you show up in partnership",
    2:  "family life, home, and shared resources",
    3:  "effort, courage, and the near circle",
    4:  "home, roots, and domestic happiness",
    5:  "romance, the heart, and children",
    6:  "friction, service, or obstacles to clear",
    7:  "the partner and the union itself — the marriage axis",
    8:  "depth, transformation, and things hidden or sudden",
    9:  "fortune, dharma, and a wider/foreign horizon",
    10: "public life, status, and the union's standing",
    11: "fulfilment of desire, gains, and social life",
    12: "the private bed-chamber, foreign lands, letting-go",
}


def _dig(planet: str, sign: Optional[str]):
    """Numeric dignity + label."""
    if not sign:
        return 0.0, None
    if _EXALT.get(planet) == sign:
        return 2.0, "exalted"
    if sign in _OWN.get(planet, set()):
        return 1.0, "own sign"
    if _DEBIL.get(planet) == sign:
        return -2.0, "debilitated"
    return 0.0, None


def _spouse_karaka(gender: Optional[str]):
    """Venus = wife-karaka, Jupiter = husband-karaka; chosen from the NATIVE's
    gender (their spouse). Unknown gender → Venus as the general love/marriage
    karaka, flagged so the narrator stays neutral."""
    g = (gender or "").strip().lower()
    if g in ("f", "female", "woman", "w"):
        return "Jupiter", "husband-karaka (Jupiter)"
    if g in ("m", "male", "man"):
        return "Venus", "wife-karaka (Venus)"
    return "Venus", "love/marriage karaka (Venus) — gender unknown"


def _darakaraka(planets: dict) -> Optional[str]:
    """DK = lowest degree-in-sign among the 7 chara karakas (excludes nodes)."""
    best = None
    for p in _CHARA:
        v = planets.get(p) or {}
        d = v.get("degree")
        if d is None:
            continue
        dd = float(d) % 30
        if best is None or dd < best[0]:
            best = (dd, p)
    return best[1] if best else None


def _upapada_sign(lagna_sign: str, planets: dict) -> Optional[str]:
    """Upapada Lagna = arudha of the 12th house. Count the 12th-lord's distance
    from the 12th, project it again from the lord; classical exceptions (lands on
    its own sign or the 7th from it → +10)."""
    if lagna_sign not in SIGNS:
        return None
    h12 = _sign_n_from(lagna_sign, 12)
    lord = SIGN_LORD.get(h12)
    lord_sign = (planets.get(lord) or {}).get("sign")
    if lord_sign not in SIGNS:
        return None
    h12_i, lord_i = SIGNS.index(h12), SIGNS.index(lord_sign)
    d = (lord_i - h12_i) % 12
    ul = (lord_i + d) % 12
    if ul == h12_i or ul == (h12_i + 6) % 12:
        ul = (ul + 10) % 12
    return SIGNS[ul]


def _house_of(planet: str, planets: dict) -> Optional[int]:
    v = planets.get(planet) or {}
    return v.get("house")


def _in_house(planets: dict, h: int) -> list:
    return [p for p, v in planets.items()
            if isinstance(v, dict) and v.get("house") == h]


def _aspects(from_h: Optional[int], to_h: int, planet: str) -> bool:
    """Does `planet` sitting in from_h cast a graha-drishti on to_h?"""
    if not from_h:
        return False
    diff = ((to_h - from_h) % 12) + 1     # 1..12 house-count, inclusive
    asp = {7}
    if planet == "Mars":
        asp |= {4, 8}
    elif planet == "Jupiter":
        asp |= {5, 9}
    elif planet == "Saturn":
        asp |= {3, 10}
    elif planet in ("Rahu", "Ketu"):
        asp |= {5, 9}
    return diff in asp


def _conj_malefics(planet: str, planets: dict) -> list:
    """Malefics sharing the planet's house (whole-sign conjunction)."""
    h = _house_of(planet, planets)
    if not h:
        return []
    return [m for m in _MALEFICS if m != planet and _house_of(m, planets) == h]


def _combust(planet: str, planets: dict) -> bool:
    """Burnt by the Sun — same sign and within ~8° (a weakened significator)."""
    if planet == "Sun":
        return False
    p = planets.get(planet) or {}
    s = planets.get("Sun") or {}
    if not p or not s or p.get("house") != s.get("house"):
        return False
    pd, sd = p.get("degree"), s.get("degree")
    if pd is None or sd is None:
        return False
    return abs(float(pd) - float(sd)) <= 8.0


def _malefics_on(planets: dict, house: int) -> list:
    """Malefics IN or ASPECTING a house."""
    out = []
    for p in _MALEFICS:
        ph = _house_of(p, planets)
        if ph == house or _aspects(ph, house, p):
            out.append(p)
    return out


def _benefics_on(planets: dict, house: int) -> list:
    out = []
    for p in _BENEFICS:
        ph = _house_of(p, planets)
        if ph == house or _aspects(ph, house, p):
            out.append(p)
    return out


def _mangal_dosha(planets: dict, lagna_sign: str) -> dict:
    """Mars on the marriage axis (1/2/4/7/8/12), from lagna AND from Moon AND
    from Venus (classical triple check). Cancellations: Mars in own/exalted sign,
    Mars conjunct/aspected by Jupiter, Mars in its own houses relative to the
    reference, or in Cancer/Leo (mild)."""
    DOSHA_HOUSES = {1, 2, 4, 7, 8, 12}
    mars = planets.get("Mars") or {}
    mars_sign = mars.get("sign")
    mars_h_lagna = mars.get("house")

    def _house_from(ref_sign, target_sign):
        if ref_sign not in SIGNS or target_sign not in SIGNS:
            return None
        return (SIGNS.index(target_sign) - SIGNS.index(ref_sign)) % 12 + 1

    moon_sign = (planets.get("Moon") or {}).get("sign")
    venus_sign = (planets.get("Venus") or {}).get("sign")
    h_moon = _house_from(moon_sign, mars_sign)
    h_venus = _house_from(venus_sign, mars_sign)

    from_lagna = mars_h_lagna in DOSHA_HOUSES if mars_h_lagna else False
    from_moon = h_moon in DOSHA_HOUSES if h_moon else False
    from_venus = h_venus in DOSHA_HOUSES if h_venus else False
    present = bool(from_lagna or from_moon or from_venus)

    # Cancellations
    cancels = []
    if mars_sign in _OWN.get("Mars", set()) or _EXALT.get("Mars") == mars_sign:
        cancels.append("Mars is in its own or exalted sign")
    if mars_sign in ("Cancer", "Leo", "Aquarius", "Sagittarius"):
        cancels.append("Mars sits in a sign that softens the dosha")
    jup_h = _house_of("Jupiter", planets)
    if jup_h and mars_h_lagna and (jup_h == mars_h_lagna or _aspects(jup_h, mars_h_lagna, "Jupiter")):
        cancels.append("Jupiter conjoins or aspects Mars (a strong relief)")
    cancelled = present and bool(cancels)

    return {
        "present": present, "from_lagna": from_lagna, "from_moon": from_moon,
        "from_venus": from_venus, "cancelled": cancelled, "cancellations": cancels,
        "mars_house": mars_h_lagna, "mars_sign": mars_sign,
    }


def analyze_relationship(chart_data: dict, gender: Optional[str] = None) -> dict:
    """Full single-chart relationship reading. Returns
    {available, promise{}, partner{}, durability{}, quality{}, mangal{},
     factors{}, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        dv = cd.get("divisional_charts") or {}
        d9 = (dv.get("d9") or {})
        d9_pl = d9.get("planets") or {}
        d9_lagna = d9.get("lagna")
        if not d1 or not lagna:
            return {"available": False}

        karaka, karaka_note = _spouse_karaka(gender)
        dk = _darakaraka(d1)
        ul_sign = _upapada_sign(lagna, d1)
        seventh_sign = _sign_n_from(lagna, 7)
        seventh_lord = SIGN_LORD.get(seventh_sign)
        seventh_lord_h = _house_of(seventh_lord, d1)
        in_7 = _in_house(d1, 7)

        factors = {
            "spouse_karaka": karaka, "karaka_note": karaka_note,
            "darakaraka": dk, "upapada_sign": ul_sign,
            "seventh_sign": seventh_sign, "seventh_lord": seventh_lord,
            "seventh_lord_house": seventh_lord_h, "planets_in_7th": in_7,
            "d9_lagna": d9_lagna,
        }

        # ── PROMISE ──────────────────────────────────────────────────────────
        # Convergence of the marriage significators. Each contributes; strong +
        # confirmed-in-D9 + benefic = a bright promise, afflicted = a guarded one.
        p_score = 0.0
        p_reasons = []
        drivers = []

        def _add(cond, w, why):
            nonlocal p_score
            if cond:
                p_score += w
                p_reasons.append(why)

        # 7th lord — the axle of partnership
        sl_dig, sl_lab = _dig(seventh_lord, (d1.get(seventh_lord) or {}).get("sign"))
        _add(seventh_lord_h not in (6, 8, 12), 1.5,
             "the lord of partnership is well-placed (not in a difficult house)")
        _add(sl_dig > 0, 1.0, f"the partnership lord is {sl_lab or 'dignified'}")
        _add(sl_dig < 0, -1.5, "the partnership lord is weak (debilitated)")
        drivers.append({"factor": "7th lord", "planet": seventh_lord,
                        "house": seventh_lord_h, "dignity": sl_lab})

        # spouse karaka (gendered)
        k_dig, k_lab = _dig(karaka, (d1.get(karaka) or {}).get("sign"))
        k_h = _house_of(karaka, d1)
        _add(k_dig >= 0, 1.0, "the marriage significator is sound")
        _add(k_dig < 0, -1.0, "the marriage significator is under strain")
        _add(k_h not in (6, 8, 12), 0.5, "the marriage significator is well-placed")
        drivers.append({"factor": karaka_note, "planet": karaka,
                        "house": k_h, "dignity": k_lab})

        # Darakaraka (Jaimini spouse karaka)
        if dk:
            dk_dig, dk_lab = _dig(dk, (d1.get(dk) or {}).get("sign"))
            _add(dk_dig >= 0, 0.8, "the Jaimini spouse-indicator is sound")
            drivers.append({"factor": "Darakaraka", "planet": dk, "dignity": dk_lab})

        # Upapada Lagna + its lord + 2nd-from-UL (sustenance of marriage)
        if ul_sign:
            ul_lord = SIGN_LORD.get(ul_sign)
            ul_lord_dig, _ = _dig(ul_lord, (d1.get(ul_lord) or {}).get("sign"))
            ul_malefics = _malefics_on(d1, (SIGNS.index(ul_sign) % 12) + 1) if ul_sign in SIGNS else []
            _add(ul_lord_dig >= 0, 0.8, "the marriage-point lord is sound")
            # 2nd from UL — the sustenance/longevity of the marriage
            ul_i = SIGNS.index(ul_sign)
            second_from_ul = SIGNS[(ul_i + 1) % 12]
            sfu_lord = SIGN_LORD.get(second_from_ul)
            sfu_dig, _ = _dig(sfu_lord, (d1.get(sfu_lord) or {}).get("sign"))
            _add(sfu_dig >= 0, 0.6, "the sustenance of the marriage is supported")
            factors["second_from_upapada"] = second_from_ul

        # benefic vs malefic pressure on the 7th
        mal7 = _malefics_on(d1, 7)
        ben7 = _benefics_on(d1, 7)
        _add(len(ben7) > 0, 0.6, "benefics support the house of partnership")
        _add(len(mal7) >= 2, -1.0, "the house of partnership is under malefic pressure")
        factors["malefics_on_7th"] = mal7
        factors["benefics_on_7th"] = ben7

        # D-9 confirmation — spouse karaka + 7th-from-D9-lagna condition
        d9_confirms = False
        if d9_pl:
            k_d9_sign = (d9_pl.get(karaka) or {}).get("sign")
            k_d9_dig, _ = _dig(karaka, k_d9_sign)
            d9_7th_sign = _sign_n_from(d9_lagna, 7) if d9_lagna else None
            d9_7th_lord = SIGN_LORD.get(d9_7th_sign) if d9_7th_sign else None
            d9_7th_lord_dig = 0.0
            if d9_7th_lord:
                d9_7th_lord_dig, _ = _dig(d9_7th_lord, (d9_pl.get(d9_7th_lord) or {}).get("sign"))
            d9_confirms = (k_d9_dig >= 0) and (d9_7th_lord_dig >= 0)
            _add(d9_confirms, 1.2, "the navamsa (marriage chart) confirms the promise")
            _add(k_d9_dig < 0, -0.8, "the marriage significator is weak in the navamsa")
        factors["d9_confirms"] = d9_confirms

        # promise band — a DIAL, never a dead no
        if p_score >= 4.5:
            band = "strong"
        elif p_score >= 2.5:
            band = "moderate"
        elif p_score >= 1.0:
            band = "workable"
        else:
            band = "guarded"
        promise = {"score": round(p_score, 2), "band": band, "reasons": p_reasons,
                   "drivers": drivers}

        # ── PARTNER DESCRIPTION ──────────────────────────────────────────────
        dk_sign = (d1.get(dk) or {}).get("sign") if dk else None
        d9_7th_sign = _sign_n_from(d9_lagna, 7) if d9_lagna else None
        partner = {
            "from_darakaraka": {"sign": dk_sign, "traits": SIGN_TRAITS.get(dk_sign)},
            "from_7th_sign": {"sign": seventh_sign, "traits": SIGN_TRAITS.get(seventh_sign)},
            "from_d9_7th": {"sign": d9_7th_sign, "traits": SIGN_TRAITS.get(d9_7th_sign)},
            "how_met": HOUSE_MEETING.get(seventh_lord_h) if seventh_lord_h else None,
        }

        # ── DURABILITY / SEPARATION RISK ─────────────────────────────────────
        # Beyond dignity: the classic separation signatures — Ketu (dissolution)
        # on the love axis, the marriage karaka afflicted by conjunction/combustion
        # (Raman: Venus+Rahu, combust; Rishipal: Venus debil + Mars), Rahu turning
        # the union unconventional, and the 7th under malefic pressure.
        risk = 0.0
        risk_flags = []
        ketu_h = _house_of("Ketu", d1)
        rahu_h = _house_of("Rahu", d1)
        if ketu_h in (5, 7):
            risk += 1.6
            risk_flags.append("a strong pull toward detachment on your love axis (Ketu in the 5th/7th)")
        if rahu_h == 7:
            risk += 1.2
            risk_flags.append("an unconventional or turbulent quality to the union (Rahu on the 7th)")
        k_conj = _conj_malefics(karaka, d1)
        if k_conj:
            risk += 0.8 * len(k_conj)
            risk_flags.append(f"the marriage significator sits with {', '.join(k_conj)} (affliction)")
        if _combust(karaka, d1):
            risk += 0.8
            risk_flags.append("the marriage significator is combust — burnt close to the Sun")
        sl_conj = _conj_malefics(seventh_lord, d1)
        if sl_conj:
            risk += 0.6 * len(sl_conj)
            risk_flags.append(f"the partnership lord sits with {', '.join(sl_conj)}")
        if len(mal7) >= 1:
            risk += len(mal7) * 0.7
            risk_flags.append(f"malefic pressure on the partnership house ({', '.join(mal7)})")
        if seventh_lord_h in (6, 8, 12):
            risk += 1.2
            risk_flags.append("the partnership lord sits in a house of friction/loss")
        k_dig_now, _ = _dig(karaka, (d1.get(karaka) or {}).get("sign"))
        if k_dig_now < 0:
            risk += 1.0
            risk_flags.append("the marriage significator is weakened (debilitated)")
        # benefic relief
        relief = []
        if "Jupiter" in ben7 or "Venus" in ben7:
            risk -= 1.0
            relief.append("Jupiter/Venus grace on the 7th eases the strain")
        durability = {
            "risk_score": round(max(0.0, risk), 2),
            "level": ("elevated" if risk >= 3.0 else "some" if risk >= 1.2 else "low"),
            "flags": risk_flags, "relief": relief,
        }

        # ── QUALITY / FAMILY LIFE (2nd + 4th + benefics) ─────────────────────
        second_lord = SIGN_LORD.get(_sign_n_from(lagna, 2))
        fourth_lord = SIGN_LORD.get(_sign_n_from(lagna, 4))
        q = 0.0
        for hl in (second_lord, fourth_lord):
            hd, _ = _dig(hl, (d1.get(hl) or {}).get("sign"))
            q += 0.5 if hd >= 0 else -0.5
        q += 0.4 * len(_benefics_on(d1, 4)) - 0.4 * len(_malefics_on(d1, 4))
        quality = {
            "score": round(q, 2),
            "level": ("harmonious" if q >= 1.0 else "mixed" if q >= -0.5 else "needs work"),
        }

        mangal = _mangal_dosha(d1, lagna)

        summary = (
            f"Marriage promise is {band}. "
            + (f"The partner tends {SIGN_TRAITS.get(dk_sign)}, "
               f"met {HOUSE_MEETING.get(seventh_lord_h)}. " if dk_sign and seventh_lord_h else "")
            + f"Durability risk is {durability['level']}; family harmony looks {quality['level']}."
            + (" Mangal dosha is present"
               + (" but cancelled." if mangal["cancelled"] else ".")
               if mangal["present"] else "")
        )

        return {"available": True, "promise": promise, "partner": partner,
                "durability": durability, "quality": quality, "mangal": mangal,
                "factors": factors, "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


# ═══════════════════════════════════════════════════════════════════════════
# RELATIONSHIP TIMING — dasha lord read through the D-9 (marriage chart)
# ───────────────────────────────────────────────────────────────────────────
# When does a partner enter / when is the union lit? A mahadasha activates
# marriage when its lord is a marriage significator (7th lord, spouse karaka,
# Darakaraka, UL lord, a planet in the 7th, or the 2nd/11th lord) — and HOW it
# plays is read from where that lord sits in the D-9. Mirrors career_timeline.

def _marriage_activation(lord, sig):
    """How strongly a dasha lord lights up marriage, given the significator set."""
    s, why = 0.0, []
    if lord == sig["seventh_lord"]:
        s += 2.0; why.append("rules your house of partnership")
    if lord == sig["karaka"]:
        s += 2.0; why.append("is your marriage significator")
    if lord == sig["dk"]:
        s += 1.8; why.append("is your Jaimini spouse-indicator")
    if lord == sig["ul_lord"]:
        s += 1.5; why.append("rules your marriage-point")
    if lord in sig["in_7"]:
        s += 1.5; why.append("sits in your house of partnership")
    if lord in (sig["second_lord"], sig["eleventh_lord"]):
        s += 1.0; why.append("rules a house of family/fulfilment")
    return s, why


def relationship_timeline(chart_data: dict, dashas: dict, gender: Optional[str] = None,
                          today: Optional[str] = None) -> dict:
    """Marriage/partnership CHAPTERS by mahadasha, each scored for how much it
    lights up the union and read through the dasha lord's D-9 placement. Returns
    {available, chapters[], current, best_window, summary}. Never raises."""
    try:
        from datetime import date
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        dv = cd.get("divisional_charts") or {}
        d9_pl = ((dv.get("d9") or {}).get("planets") or {})
        if not d1 or not lagna:
            return {"available": False}

        karaka, _ = _spouse_karaka(gender)
        ul_sign = _upapada_sign(lagna, d1)
        sig = {
            "seventh_lord": SIGN_LORD.get(_sign_n_from(lagna, 7)),
            "karaka": karaka,
            "dk": _darakaraka(d1),
            "ul_lord": SIGN_LORD.get(ul_sign) if ul_sign else None,
            "in_7": _in_house(d1, 7),
            "second_lord": SIGN_LORD.get(_sign_n_from(lagna, 2)),
            "eleventh_lord": SIGN_LORD.get(_sign_n_from(lagna, 11)),
        }

        # [separation timing] which dasha lords, when they run, ELEVATE strain over
        # a marriage — the afflicted marriage karaka's own period (Rishipal divorced
        # in his debilitated-Venus dasha), Ketu on the love axis, Rahu on the 7th,
        # the 6/8/12 lords (conflict/loss/parting), and any malefic pressing the 7th.
        k_sign = (d1.get(karaka) or {}).get("sign")
        k_afflicted = (_dig(karaka, k_sign)[0] < 0 or bool(_conj_malefics(karaka, d1))
                       or _combust(karaka, d1))
        strain_src = {}
        if k_afflicted:
            strain_src[karaka] = "your marriage significator is under strain in this period"
        ketu_h, rahu_h = _house_of("Ketu", d1), _house_of("Rahu", d1)
        if ketu_h in (5, 7):
            strain_src["Ketu"] = "detachment pulls on the relationship"
        if rahu_h == 7 or "Rahu" in _conj_malefics(karaka, d1):
            strain_src["Rahu"] = "a disruptive influence on the union"
        for hn, why in ((6, "conflict"), (8, "upheaval"), (12, "distance/loss")):
            hl = SIGN_LORD.get(_sign_n_from(lagna, hn))
            if hl:
                strain_src.setdefault(hl, f"a period of {why} for partnership")
        for m in _malefics_on(d1, 7):
            strain_src.setdefault(m, "pressure on the partnership house")

        vim = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
        raw = []
        for p in vim if isinstance(vim, list) else []:
            if not isinstance(p, dict):
                continue
            lord = str(p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord") or "").title()
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            lvl = str(p.get("level") or p.get("type") or "").lower()
            dur = float(p.get("duration_years") or p.get("duration") or 0) or 0.0
            if lord and s and e:
                raw.append({"lord": lord, "start": s, "end": e, "level": lvl, "dur": dur})
        mds = [r for r in raw if r["level"] in ("mahadasha", "maha", "md")]
        if not mds:
            mds = [r for r in raw if r["dur"] >= 5.0]
        if not mds:
            return {"available": False}
        mds.sort(key=lambda x: x["start"])

        today = today or date.today().isoformat()
        birth_year = int(mds[0]["start"][:4])
        cur_idx = None
        for i, m in enumerate(mds):
            if m["start"] <= today <= m["end"]:
                cur_idx = i
                break

        chapters = []
        for i, m in enumerate(mds):
            start_year, end_year = int(m["start"][:4]), int(m["end"][:4])
            if end_year < birth_year + 16:      # marriageable window onward
                continue
            if cur_idx is not None and i > cur_idx + 2:
                continue
            lord = m["lord"]
            act, why = _marriage_activation(lord, sig)
            is_activator = bool(why)
            d9h = (d9_pl.get(lord) or {}).get("house")
            d9s = (d9_pl.get(lord) or {}).get("sign")

            # [strain] separation risk for THIS period: a strain-source lord, and/
            # or a partnership-activator running through a D-9 friction house — the
            # union is stirred but through a broken channel (Raman divorced 2014 in
            # his Moon period: Moon = his 7th lord, sitting in the D-9 8th).
            strain, strain_why = 0.0, []
            if lord in strain_src:
                strain += 1.0; strain_why.append(strain_src[lord])
            if d9h in (6, 8, 12):
                if is_activator:
                    # a partnership-activator (esp. the 7th lord) working through a
                    # navamsa dusthana is a prime separation trigger — Raman's 2014
                    # divorce was exactly his 7th lord (Moon) in the D-9 8th.
                    strain += 1.5
                    strain_why.append("partnership is stirred through a friction channel")
                else:
                    strain += 0.5
            if lord == karaka and k_afflicted:
                strain += 0.5
                strain_why.append("the marriage significator itself is afflicted")

            # D-9 read: on the marriage axis (1/7) or 5/11 (romance/fulfilment)
            # sharpens the ENTRY window; 6/8/12 warns of friction/delay.
            d9_note = ""
            if d9h in (1, 7):
                act += 1.0; d9_note = "on the marriage axis in the navamsa (sharp)"
            elif d9h in (5, 11):
                act += 0.6; d9_note = "touching romance/fulfilment in the navamsa"
            elif d9h in (6, 8, 12):
                act -= 0.6; d9_note = "in a friction house in the navamsa (delay/strain)"
            dig, _lab = _dig(lord, (d1.get(lord) or {}).get("sign"))
            tone = ("bright" if act >= 2.0 and dig >= 0
                    else "possible" if act >= 1.5
                    else "quiet" if act < 1.0
                    else "workable")
            phase = ("current" if i == cur_idx
                     else "next" if cur_idx is not None and i == cur_idx + 1
                     else "past" if (cur_idx is not None and i < cur_idx) or m["end"] < today
                     else "future")
            chapters.append({
                "lord": lord, "phase": phase,
                "years": f"{start_year}–{end_year}",
                "age": f"{max(0, start_year - birth_year)}–{end_year - birth_year}",
                "activation": round(act, 2), "why": why,
                "strain": round(strain, 2), "strain_why": strain_why,
                "d9_house": d9h, "d9_sign": d9s, "d9_arena": D9_HOUSE_ARENA.get(d9h, ""),
                "d9_note": d9_note, "tone": tone,
                "nature": PLANET_CHAPTER.get(lord, ""),
            })

        current = next((c for c in chapters if c["phase"] == "current"), None)
        # best upcoming window = highest activation among current/next/future
        upcoming = [c for c in chapters if c["phase"] in ("current", "next", "future")]
        best = max(upcoming, key=lambda c: c["activation"], default=None)
        best_window = best if best and best["activation"] >= 1.5 else None
        # strain window = the peak-strain chapter in view (past included, so a
        # separation that already happened is explained, not just forecast).
        _stw = max(chapters, key=lambda c: c["strain"], default=None)
        strain_window = _stw if _stw and _stw["strain"] >= 1.5 else None

        if current:
            lit = "a live window for partnership" if current["activation"] >= 1.5 else "a quieter phase for partnership"
            summary = (f"You are in your {current['lord']} period ({current['years']}) — "
                       f"{lit}.")
            if best_window and best_window is not current:
                summary += (f" The strongest window ahead is your {best_window['lord']} "
                            f"period ({best_window['years']}).")
            elif best_window is current:
                summary += " This is your strongest window in view."
        else:
            summary = ""

        return {"available": True, "chapters": chapters, "current": current,
                "best_window": best_window, "strain_window": strain_window,
                "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
