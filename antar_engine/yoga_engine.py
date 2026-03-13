"""
antar_engine/yoga_engine.py

Yoga Detection Engine — All Life Domains
──────────────────────────────────────────────────────────────────────
WHAT THIS FILE DOES:
  Detects whether specific planetary combinations (yogas) exist
  in the user's chart for each life question domain.

  A yoga is a combination of:
    - Planet positions (who is where)
    - House lords (who rules which house)
    - Planet strength (exalted / own / debilitated)
    - Mutual relationships (aspect, exchange, conjunction)

WHY THIS MATTERS FOR PREDICTIONS:
  Without yoga detection, predictions are just dasha timing.
  With yoga detection:
    "Do I have billionaire potential?" →
      Dhana yoga present (strong): "The wealth combinations in
      your chart are significant. This is not speculation — the
      2nd and 11th lords are in exchange, and Jupiter sits in a
      kendra from your Moon. This is a wealth chart."

    Dhana yoga absent: "Your chart shows steady, reliable wealth
      building rather than sudden massive accumulation. The path
      to financial security is through [specific dasha] not windfall."

  The yoga answer is FIXED — it never changes regardless of timing.
  The dasha window says WHEN that yoga can manifest.
  Together they give: CAN IT HAPPEN + WHEN.

EACH YOGA RETURNS:
  {
    name:        str    → human-readable name
    present:     bool   → is this combination in the chart?
    strength:    str    → "strong" | "moderate" | "weak" | "absent"
    description: str    → what planets/houses create this
    implication: str    → what this means for the user
    timing_note: str    → which dasha activates this yoga
  }
"""

from __future__ import annotations
from antar_engine.d_charts_calculator import (
    SIGNS, SIGN_INDEX, SIGN_LORDS, OWN_SIGNS,
    EXALTATION, DEBILITATION, NATURAL_BENEFICS, NATURAL_MALEFICS,
    get_house_lord, get_house_sign, is_planet_strong, is_planet_weak,
    get_planets_in_house,
)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _sign_of(planet: str, planets: dict) -> str:
    return planets.get(planet, {}).get("sign", "")

def _strong(planet: str, planets: dict) -> bool:
    s = _sign_of(planet, planets)
    return s in OWN_SIGNS.get(planet, []) or s == EXALTATION.get(planet, "")

def _weak(planet: str, planets: dict) -> bool:
    return _sign_of(planet, planets) == DEBILITATION.get(planet, "")

def _in_sign(planet: str, sign: str, planets: dict) -> bool:
    return _sign_of(planet, planets) == sign

def _jupiter_aspects(sign: str, planets: dict) -> bool:
    """Does Jupiter aspect the given sign? Jupiter aspects 5th, 7th, 9th from itself."""
    jup_sign = _sign_of("Jupiter", planets)
    if not jup_sign:
        return False
    jup_idx  = SIGN_INDEX.get(jup_sign, 0)
    aspects  = {SIGNS[(jup_idx + h - 1) % 12] for h in [5, 7, 9]}
    return sign in aspects or sign == jup_sign

def _saturn_aspects(sign: str, planets: dict) -> bool:
    """Saturn aspects 3rd, 7th, 10th from itself."""
    sat_sign = _sign_of("Saturn", planets)
    if not sat_sign:
        return False
    sat_idx  = SIGN_INDEX.get(sat_sign, 0)
    aspects  = {SIGNS[(sat_idx + h - 1) % 12] for h in [3, 7, 10]}
    return sign in aspects or sign == sat_sign

def _mars_aspects(sign: str, planets: dict) -> bool:
    """Mars aspects 4th, 7th, 8th from itself."""
    mar_sign = _sign_of("Mars", planets)
    if not mar_sign:
        return False
    mar_idx  = SIGN_INDEX.get(mar_sign, 0)
    aspects  = {SIGNS[(mar_idx + h - 1) % 12] for h in [4, 7, 8]}
    return sign in aspects or sign == mar_sign

def _are_in_exchange(p1: str, p2: str, planets: dict) -> bool:
    """Check if two planets are in each other's signs (Parivartana yoga)."""
    p1_sign = _sign_of(p1, planets)
    p2_sign = _sign_of(p2, planets)
    return p1_sign in OWN_SIGNS.get(p2, []) and p2_sign in OWN_SIGNS.get(p1, [])

def _are_conjunct(p1: str, p2: str, planets: dict) -> bool:
    """Check if two planets are in the same sign."""
    return _sign_of(p1, planets) == _sign_of(p2, planets) and _sign_of(p1, planets) != ""

def _yoga_strength(conditions: list[bool]) -> str:
    """Given a list of supporting conditions, return overall strength."""
    score = sum(conditions)
    if score >= len(conditions) * 0.75: return "strong"
    if score >= len(conditions) * 0.5:  return "moderate"
    if score > 0:                       return "weak"
    return "absent"


# ══════════════════════════════════════════════════════════════════════════════
# WEALTH & BILLIONAIRE YOGAS
# ══════════════════════════════════════════════════════════════════════════════

def detect_wealth_yogas(
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    """
    Detects all wealth combinations.
    Used for: "Do I have billionaire potential?", "When does wealth peak?"
    "Will I be rich?", "Should I invest?", "What is my earning potential?"

    Key charts: D-1 (Rashi), D-2 (Hora)
    Key houses: 2 (accumulated wealth), 9 (fortune/luck), 11 (income/gains)
    Key planets: Jupiter (expansion), Venus (luxury), Moon (flow)
    """
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    d2         = d_charts.get("D2", {})
    yogas      = []

    lord_2  = get_house_lord(lagna_sign, 2)
    lord_9  = get_house_lord(lagna_sign, 9)
    lord_11 = get_house_lord(lagna_sign, 11)
    sign_2  = get_house_sign(lagna_sign, 2)
    sign_9  = get_house_sign(lagna_sign, 9)
    sign_11 = get_house_sign(lagna_sign, 11)
    sign_1  = lagna_sign

    # ── 1. Dhana Yoga — core wealth combination ───────────────────
    # 2nd and 11th lords in relationship (conjunction, exchange, mutual aspect)
    l2_in_11   = _in_sign(lord_2, sign_11, planets)
    l11_in_2   = _in_sign(lord_11, sign_2, planets)
    l2_l11_conj = _are_conjunct(lord_2, lord_11, planets)
    exchange   = _are_in_exchange(lord_2, lord_11, planets)
    dhana_present = l2_in_11 or l11_in_2 or l2_l11_conj or exchange

    yogas.append({
        "name":        "Dhana Yoga — Wealth Combination",
        "present":     dhana_present,
        "strength":    _yoga_strength([l2_in_11, l11_in_2, l2_l11_conj or exchange, _strong(lord_2, planets), _strong(lord_11, planets)]),
        "description": f"2nd lord ({lord_2}) and 11th lord ({lord_11}) relationship",
        "implication": (
            "This is a genuine wealth chart. The income and accumulation houses are connected. "
            "Wealth builds significantly during the dashas of these lords."
            if dhana_present else
            "Classic Dhana Yoga is not present. Wealth comes through consistent effort "
            "rather than automatic combinations. The right dasha timing matters more."
        ),
        "timing_note": f"Peak activation during {lord_2} or {lord_11} mahadasha",
    })

    # ── 2. Raj Yoga — power + wealth ─────────────────────────────
    # Kendra lord + Trikona lord connected
    kendra_lords  = {get_house_lord(lagna_sign, h) for h in [1, 4, 7, 10]}
    trikona_lords = {get_house_lord(lagna_sign, h) for h in [1, 5, 9]}
    raj_planets   = kendra_lords & trikona_lords
    extra_raj     = []
    for kl in kendra_lords:
        for tl in trikona_lords:
            if kl != tl and (_are_conjunct(kl, tl, planets) or _are_in_exchange(kl, tl, planets)):
                extra_raj.append(f"{kl}+{tl}")
    raj_present = len(raj_planets) > 0 or len(extra_raj) > 0

    yogas.append({
        "name":        "Raj Yoga — Power & Prominence",
        "present":     raj_present,
        "strength":    "strong" if len(raj_planets) > 1 or len(extra_raj) > 1 else "moderate" if raj_present else "absent",
        "description": (
            f"Single-planet Raj Yogas: {', '.join(raj_planets)}. "
            f"Exchange/conjunction Raj Yogas: {', '.join(extra_raj)}"
        ) if raj_present else "No Kendra-Trikona lord connection",
        "implication": (
            "Raj Yoga gives rise to prominence, recognition, and authority alongside wealth. "
            "This person is built to lead, not just accumulate. Peak during Raj Yoga planet dashas."
            if raj_present else
            "Raj Yoga absent. Success comes through the right field and timing, "
            "not automatic authority or recognition."
        ),
        "timing_note": f"Activated during {', '.join(list(raj_planets)[:2])} dashas" if raj_planets else "",
    })

    # ── 3. Gaja Kesari Yoga — Jupiter + Moon ─────────────────────
    moon_sign = _sign_of("Moon", planets)
    moon_idx  = SIGN_INDEX.get(moon_sign, 0)
    kendra_from_moon = {SIGNS[(moon_idx + h - 1) % 12] for h in [1, 4, 7, 10]}
    jup_sign  = _sign_of("Jupiter", planets)
    gaja_kesari = jup_sign in kendra_from_moon

    yogas.append({
        "name":        "Gaja Kesari Yoga — Wisdom & Prosperity",
        "present":     gaja_kesari,
        "strength":    "strong" if gaja_kesari and _strong("Jupiter", planets) else "moderate" if gaja_kesari else "absent",
        "description": f"Jupiter ({jup_sign}) in kendra from Moon ({moon_sign})",
        "implication": (
            "Gaja Kesari brings social reputation, wise decisions, and lasting prosperity. "
            "This person is respected and financially supported by their reputation."
            if gaja_kesari else
            "Gaja Kesari not present. Jupiter's wisdom and Moon's public reputation "
            "operate more independently."
        ),
        "timing_note": "Most powerful during Jupiter dasha",
    })

    # ── 4. Lakshmi Yoga — sustained abundance ────────────────────
    lord9_strong  = _strong(lord_9, planets)
    venus_strong  = _strong("Venus", planets)
    lord9_in_kendra_or_trikona = _sign_of(lord_9, planets) in {
        get_house_sign(lagna_sign, h) for h in [1, 4, 5, 7, 9, 10]
    }
    lakshmi = lord9_strong and venus_strong

    yogas.append({
        "name":        "Lakshmi Yoga — Sustained Abundance",
        "present":     lakshmi,
        "strength":    "strong" if lakshmi else ("partial" if lord9_strong or venus_strong else "absent"),
        "description": f"9th lord ({lord_9}) strong + Venus strong",
        "implication": (
            "Lakshmi Yoga gives consistent, graceful prosperity — not sudden but sustained. "
            "Wealth comes with beauty, harmony, and divine support."
            if lakshmi else
            f"Lakshmi Yoga partially present. "
            f"{'9th lord is strong — fortune exists.' if lord9_strong else ''}"
            f"{'Venus is strong — aesthetic prosperity possible.' if venus_strong else ''}"
        ),
        "timing_note": "Venus dasha + 9th lord dasha = peak prosperity periods",
    })

    # ── 5. Billionaire check — Kubera + Rahu factor ───────────────
    rahu_sign   = _sign_of("Rahu", planets)
    rahu_in_11  = rahu_sign == sign_11
    rahu_in_2   = rahu_sign == sign_2
    sun_strong  = _strong("Sun", planets)
    rahu_strong = rahu_in_11 or rahu_in_2
    all_present = [dhana_present, raj_present, gaja_kesari, rahu_strong, sun_strong]
    billionaire_score = sum(all_present)

    yogas.append({
        "name":        "Ultra-Wealth Potential (Billionaire Assessment)",
        "present":     billionaire_score >= 3,
        "strength":    (
            "very strong" if billionaire_score >= 4 else
            "strong"      if billionaire_score == 3 else
            "moderate"    if billionaire_score == 2 else
            "limited"
        ),
        "description": (
            f"{billionaire_score}/5 ultra-wealth indicators present: "
            f"Dhana:{dhana_present}, Raj:{raj_present}, GajaKesari:{gaja_kesari}, "
            f"Rahu-wealth:{rahu_strong}, Sun-authority:{sun_strong}"
        ),
        "implication": (
            "The chart carries the combinations seen in ultra-high-net-worth individuals. "
            "This is not guaranteed — timing, effort, and the right field are still required. "
            "But the potential is genuinely there."
            if billionaire_score >= 3 else
            f"The chart shows {['limited','modest','solid','strong'][min(billionaire_score,3)]} "
            "wealth potential. Genuine prosperity is possible through the right dasha timing "
            "and aligned career path. Ultra-wealth requires additional effort beyond the chart."
        ),
        "timing_note": "Jupiter + Rahu dasha conjunction is the most powerful wealth-creation window",
    })

    # ── 6. D-2 Hora confirmation ──────────────────────────────────
    d2_lagna_sign = d2.get("Lagna", {}).get("sign", "") if d2 else ""
    d2_benefic    = d2_lagna_sign in ["Cancer", "Leo"]  # Moon hora or Sun hora lagna
    d2_jupiter    = d2.get("Jupiter", {}).get("strength", "") in ("exalted", "own") if d2 else False
    d2_venus      = d2.get("Venus",   {}).get("strength", "") in ("exalted", "own") if d2 else False

    yogas.append({
        "name":        "D-2 Hora — Wealth Chart Confirmation",
        "present":     d2_benefic or d2_jupiter or d2_venus,
        "strength":    "strong" if (d2_jupiter or d2_venus) else "moderate" if d2_benefic else "absent",
        "description": f"D-2 Hora lagna: {d2_lagna_sign or 'uncalculated'}",
        "implication": (
            "The dedicated wealth chart confirms financial dharma. "
            "Money flows naturally when aligned with purpose."
            if (d2_benefic or d2_jupiter or d2_venus) else
            "D-2 Hora chart shows wealth requires more effort to accumulate. "
            "Discipline and strategy matter more than luck."
        ),
        "timing_note": "D-2 analysis refines the type and flow of wealth",
    })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
# LEGAL YOGAS
# ══════════════════════════════════════════════════════════════════════════════

def detect_legal_yogas(
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    """
    Legal victory, case timing, and resolution analysis.
    Used for: "Will I win?", "When does my case resolve?",
              "Should I settle or fight?", "Legal trouble timing"

    Key chart: D-6 (Shashthamsha) — the dedicated enemy/legal/disease chart
    Key houses: 6 (enemies/legal), 7 (opponents in court), 12 (losses)
    Key planets: Mars (fighting), Saturn (delays), Jupiter (justice), Rahu (surprise)
    """
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    d6         = d_charts.get("D6", {})
    yogas      = []

    lord_6   = get_house_lord(lagna_sign, 6)
    lord_7   = get_house_lord(lagna_sign, 7)
    lord_12  = get_house_lord(lagna_sign, 12)
    sign_6   = get_house_sign(lagna_sign, 6)
    sign_12  = get_house_sign(lagna_sign, 12)

    # ── 1. Victory yoga — 6th > 12th ─────────────────────────────
    l6_strong  = _strong(lord_6, planets)
    l12_strong = _strong(lord_12, planets)
    l6_weak    = _weak(lord_6, planets)
    l12_weak   = _weak(lord_12, planets)

    yogas.append({
        "name":        "Victory in Conflict",
        "present":     (l6_strong and not l12_strong) or l12_weak,
        "strength":    (
            "strong"   if l6_strong and l12_weak else
            "moderate" if l6_strong else
            "weak"     if not l6_weak else
            "absent"
        ),
        "description": f"6th lord ({lord_6}): {'strong' if l6_strong else 'weak' if l6_weak else 'neutral'} | 12th lord ({lord_12}): {'strong' if l12_strong else 'weak' if l12_weak else 'neutral'}",
        "implication": (
            "The chart strongly supports victory over opponents. "
            "Fight the case — don't settle unless the timing is very wrong."
            if l6_strong and not l12_strong else
            "The case is winnable but requires the right dasha timing and strong legal representation. "
            "Do not approach this casually."
            if not l6_weak else
            "The chart shows challenges in this legal area. "
            "Settlement or strategic withdrawal may serve better than prolonged fighting. "
            "Get excellent legal advice before proceeding."
        ),
        "timing_note": f"Fight hardest during {lord_6} dasha/antardasha",
    })

    # ── 2. Mars strength — fighting spirit ───────────────────────
    mars_in_6       = _in_sign("Mars", sign_6, planets)
    mars_strong     = _strong("Mars", planets)
    mars_aspects_6  = _mars_aspects(sign_6, planets)

    yogas.append({
        "name":        "Mars — Fighting Strength",
        "present":     mars_in_6 or mars_strong or mars_aspects_6,
        "strength":    "strong" if mars_in_6 and mars_strong else "moderate" if mars_in_6 or mars_strong else "weak" if mars_aspects_6 else "absent",
        "description": f"Mars in {_sign_of('Mars', planets)} {'— in 6th house' if mars_in_6 else '— aspecting 6th' if mars_aspects_6 else ''}",
        "implication": (
            "Strong Mars gives exceptional fighting spirit in legal matters. "
            "You will not back down. Persistence wins this case."
            if mars_in_6 or mars_strong else
            "Mars energy is available but not dominant. "
            "Focused effort and good legal strategy matter more than brute persistence."
        ),
        "timing_note": "Mars antardasha = most active fighting period",
    })

    # ── 3. Jupiter's justice ──────────────────────────────────────
    jup_aspects_6 = _jupiter_aspects(sign_6, planets)
    jup_aspects_7 = _jupiter_aspects(get_house_sign(lagna_sign, 7), planets)
    jup_helps     = jup_aspects_6 or jup_aspects_7 or _strong("Jupiter", planets)

    yogas.append({
        "name":        "Jupiter — Legal Protection & Justice",
        "present":     jup_helps,
        "strength":    "strong" if _strong("Jupiter", planets) and jup_aspects_6 else "moderate" if jup_helps else "absent",
        "description": f"Jupiter in {_sign_of('Jupiter', planets)} — aspects 6th: {jup_aspects_6}, aspects 7th: {jup_aspects_7}",
        "implication": (
            "Jupiter's protective energy is active in your legal house. "
            "Justice tends to prevail. A wise, ethical judge or advisor supports the outcome."
            if jup_helps else
            "Jupiter is not directly protecting the legal house. "
            "Seek an experienced, ethical lawyer. The legal outcome depends heavily on quality of representation."
        ),
        "timing_note": "Jupiter dasha/antardasha = most favorable period for legal resolution",
    })

    # ── 4. Saturn — delay indicator ───────────────────────────────
    sat_in_6       = _in_sign("Saturn", sign_6, planets)
    sat_aspects_6  = _saturn_aspects(sign_6, planets)
    sat_involvement = sat_in_6 or sat_aspects_6

    yogas.append({
        "name":        "Saturn — Delay or Discipline",
        "present":     sat_involvement,
        "strength":    "moderate",
        "description": f"Saturn in {_sign_of('Saturn', planets)} — {'in 6th house' if sat_in_6 else 'aspecting 6th' if sat_aspects_6 else 'not in 6th'}",
        "implication": (
            "Saturn in the legal house brings delays — the case will take longer than expected. "
            "BUT Saturn is good in the 6th: it eventually defeats enemies through persistence. "
            "Patience is not optional here, it is the strategy."
            if sat_in_6 else
            "Saturn aspects the legal area, suggesting systematic, disciplined approach wins. "
            "Rushing this case or taking shortcuts will backfire."
            if sat_aspects_6 else
            "Saturn is not directly involved in the legal house. "
            "Delays are less likely — the case may resolve in the expected timeframe."
        ),
        "timing_note": "Saturn transiting the 6th or its lord = case becomes most active",
    })

    # ── 5. D-6 Shashthamsha — dedicated legal chart ───────────────
    d6_lagna_sign  = d6.get("Lagna", {}).get("sign", "") if d6 else ""
    d6_lagna_lord  = SIGN_LORDS.get(d6_lagna_sign, "") if d6_lagna_sign else ""
    d6_ll_strong   = is_planet_strong(d6_lagna_lord, d6) if d6 else False
    d6_mars_strong = is_planet_strong("Mars", d6) if d6 else False
    d6_sat_weak    = is_planet_weak("Saturn", d6) if d6 else False

    yogas.append({
        "name":        "D-6 Shashthamsha — Legal Destiny Chart",
        "present":     d6_ll_strong or d6_mars_strong,
        "strength":    "strong" if (d6_ll_strong and d6_mars_strong) else "moderate" if (d6_ll_strong or d6_mars_strong) else "weak",
        "description": f"D-6 lagna {d6_lagna_sign}, lagna lord {d6_lagna_lord}: {'strong' if d6_ll_strong else 'weak'}, Mars: {'strong' if d6_mars_strong else 'standard'}",
        "implication": (
            "The dedicated legal chart confirms fighting strength. "
            "Your chart is built to handle and overcome legal challenges."
            if (d6_ll_strong or d6_mars_strong) else
            "D-6 shows legal matters are genuinely challenging in this chart. "
            "Strategy, not stubbornness, is the path forward."
        ),
        "timing_note": "D-6 refines the nature and outcome of legal/health challenges",
    })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & RECOVERY YOGAS
# ══════════════════════════════════════════════════════════════════════════════

def detect_health_yogas(
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    """
    Health constitution, recovery, and vitality analysis.
    Used for: "Will I recover?", "What is my health weakness?",
              "When will I feel better?", "Should I have surgery now?"

    Key chart: D-6 (enemy/disease), D-3 (courage, vitality)
    Key houses: 1 (constitution), 6 (disease), 8 (chronic/sudden), 12 (hospitalisation)
    Key planets: Moon (mind), Sun (vitality), Saturn (chronic), Mars (surgery/acute)
    """
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    d6         = d_charts.get("D6", {})
    yogas      = []

    lord_1  = get_house_lord(lagna_sign, 1)   # lagna lord = constitution
    lord_6  = get_house_lord(lagna_sign, 6)   # disease house
    lord_8  = get_house_lord(lagna_sign, 8)   # chronic/hidden illness
    sign_1  = lagna_sign
    sign_6  = get_house_sign(lagna_sign, 6)
    sign_8  = get_house_sign(lagna_sign, 8)

    # ── 1. Constitutional strength ────────────────────────────────
    ll_strong  = _strong(lord_1, planets)
    ll_weak    = _weak(lord_1, planets)
    sun_strong = _strong("Sun", planets)

    yogas.append({
        "name":        "Constitutional Strength",
        "present":     ll_strong or sun_strong,
        "strength":    "strong" if ll_strong and sun_strong else "moderate" if ll_strong or sun_strong else "weak" if not ll_weak else "limited",
        "description": f"Lagna lord ({lord_1}): {'strong' if ll_strong else 'weak' if ll_weak else 'moderate'}, Sun: {'strong' if sun_strong else 'standard'}",
        "implication": (
            "Strong constitution. The body has genuine recovery power. "
            "Illness tends to be acute rather than chronic — you bounce back."
            if ll_strong else
            "The constitution needs support and care. "
            "Preventive health practices matter more than for most people. "
            "Recovery is possible but requires conscious effort."
            if ll_weak else
            "Moderate constitutional strength. Health responds well to lifestyle choices."
        ),
        "timing_note": f"{lord_1} dasha periods are your strongest health windows",
    })

    # ── 2. Moon — mental and emotional health ────────────────────
    moon_strong = _strong("Moon", planets)
    moon_weak   = _weak("Moon", planets)
    moon_in_6   = _in_sign("Moon", sign_6, planets)
    moon_in_8   = _in_sign("Moon", sign_8, planets)

    yogas.append({
        "name":        "Moon — Mind-Body Connection",
        "present":     not (moon_weak or moon_in_6 or moon_in_8),
        "strength":    "strong" if moon_strong else "weak" if (moon_weak or moon_in_6) else "moderate",
        "description": f"Moon in {_sign_of('Moon', planets)} {'— in disease house' if moon_in_6 else '— in transformation house' if moon_in_8 else ''}",
        "implication": (
            "Strong Moon supports emotional resilience and mental health. "
            "Mind-body connection works in your favor during healing."
            if moon_strong and not moon_in_6 else
            "Moon in the disease house suggests emotional factors contribute to physical health. "
            "Mental and emotional health is a key part of any physical healing."
            if moon_in_6 else
            "Moon is functional. Emotional wellbeing supports but doesn't dominate health outcomes."
        ),
        "timing_note": "Moon dasha/antardasha — watch emotional health carefully",
    })

    # ── 3. Jupiter healing grace ──────────────────────────────────
    jup_aspects_1 = _jupiter_aspects(sign_1, planets)
    jup_strong    = _strong("Jupiter", planets)

    yogas.append({
        "name":        "Jupiter — Healing Protection",
        "present":     jup_aspects_1 or jup_strong,
        "strength":    "strong" if jup_strong and jup_aspects_1 else "moderate" if jup_aspects_1 or jup_strong else "absent",
        "description": f"Jupiter in {_sign_of('Jupiter', planets)} {'— aspecting lagna' if jup_aspects_1 else ''}",
        "implication": (
            "Jupiter provides genuine healing protection. "
            "Recovery is supported by wisdom, good doctors, and faith. "
            "Jupiter dasha is the best window for healing."
            if jup_aspects_1 or jup_strong else
            "Jupiter's protective influence on the body is limited. "
            "Medical care, nutrition, and lifestyle matter more than natural protection."
        ),
        "timing_note": "Jupiter transit over lagna or Moon = best healing period",
    })

    # ── 4. Saturn / Rahu — chronic illness indicators ─────────────
    sat_in_1   = _in_sign("Saturn", sign_1, planets)
    sat_in_6   = _in_sign("Saturn", sign_6, planets)
    rahu_in_1  = _in_sign("Rahu", sign_1, planets)
    rahu_in_6  = _in_sign("Rahu", sign_6, planets)
    chronic_risk = sat_in_1 or rahu_in_1

    yogas.append({
        "name":        "Chronic Condition Risk",
        "present":     chronic_risk,
        "strength":    "moderate" if chronic_risk else "absent",
        "description": f"Saturn in lagna: {sat_in_1}, Rahu in lagna: {rahu_in_1}",
        "implication": (
            "Saturn or Rahu in the first house suggests tendency toward chronic conditions "
            "or health issues that require long-term management rather than quick fixes. "
            "Prevention and consistent routine are more effective than reactive treatment."
            if chronic_risk else
            "No strong chronic illness indicators in the lagna. "
            "Health issues are more likely to be acute and resolvable rather than long-term."
        ),
        "timing_note": "Saturn periods require extra health vigilance",
    })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
# MARRIAGE YOGAS
# ══════════════════════════════════════════════════════════════════════════════

def detect_marriage_yogas(
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    """
    Marriage timing, partner quality, and relationship longevity.
    Used for: "When will I get married?", "Will my marriage last?",
              "What kind of partner will I attract?", "Is divorce in my chart?"

    Key chart: D-9 (Navamsa) — THE marriage chart
    Key houses: 7 (partner), 2 (family), 11 (gains/social)
    Key planets: Venus (love), Jupiter (wisdom/expansion), Moon (emotion)
    """
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    d9         = d_charts.get("D9", {})
    yogas      = []

    lord_7   = get_house_lord(lagna_sign, 7)
    sign_7   = get_house_sign(lagna_sign, 7)

    # ── 1. Venus strength ─────────────────────────────────────────
    venus_strong = _strong("Venus", planets)
    venus_weak   = _weak("Venus", planets)
    venus_in_7   = _in_sign("Venus", sign_7, planets)

    yogas.append({
        "name":        "Venus — Love & Partnership Energy",
        "present":     venus_strong or venus_in_7,
        "strength":    "strong" if venus_strong and venus_in_7 else "moderate" if venus_strong or venus_in_7 else "weak" if venus_weak else "neutral",
        "description": f"Venus in {_sign_of('Venus', planets)} {'— exalted/own sign' if venus_strong else '— debilitated' if venus_weak else ''}",
        "implication": (
            "Strong Venus gives a natural gift for love, beauty, and relationships. "
            "Marriage is fulfilling and the partner is likely attractive and harmonious."
            if venus_strong else
            "Venus in the 7th brings relationship focus directly. "
            "Partnership is a central life theme."
            if venus_in_7 else
            "Venus needs conscious cultivation. Relationships require effort and awareness."
            if venus_weak else
            "Venus is functional. Love life depends more on timing than automatic compatibility."
        ),
        "timing_note": "Venus mahadasha and antardasha are primary marriage windows",
    })

    # ── 2. 7th lord strength ──────────────────────────────────────
    l7_strong = _strong(lord_7, planets)
    l7_weak   = _weak(lord_7, planets)
    l7_in_7   = _in_sign(lord_7, sign_7, planets)   # 7th lord in own house

    yogas.append({
        "name":        "7th Lord — Partnership Destiny",
        "present":     l7_strong or l7_in_7,
        "strength":    "strong" if l7_strong else "weak" if l7_weak else "moderate",
        "description": f"7th lord ({lord_7}) in {_sign_of(lord_7, planets)} {'— strong' if l7_strong else '— debilitated' if l7_weak else ''}",
        "implication": (
            "Strong 7th lord indicates the partner and marriage itself will be strong, "
            "supportive, and long-lasting."
            if l7_strong else
            "7th lord under pressure suggests the partner or the relationship itself may face challenges. "
            "Marriage requires conscious work and the right timing to succeed."
            if l7_weak else
            "7th lord is functional. Partnership quality depends on both people's effort."
        ),
        "timing_note": f"{lord_7} dasha = relationship arrives or transforms",
    })

    # ── 3. Jupiter's blessing ─────────────────────────────────────
    jup_aspects_7 = _jupiter_aspects(sign_7, planets)
    jup_strong    = _strong("Jupiter", planets)

    yogas.append({
        "name":        "Jupiter — Marriage Blessing",
        "present":     jup_aspects_7 or jup_strong,
        "strength":    "strong" if jup_strong and jup_aspects_7 else "moderate" if jup_aspects_7 or jup_strong else "absent",
        "description": f"Jupiter {'aspects 7th house' if jup_aspects_7 else 'does not aspect 7th house'}",
        "implication": (
            "Jupiter blesses the partnership house. Marriage brings growth, wisdom, and abundance. "
            "The partner is likely wise, generous, or spiritually inclined."
            if jup_aspects_7 else
            "Jupiter does not directly bless the 7th. "
            "Marriage is meaningful but not automatically expansive — growth requires conscious effort."
        ),
        "timing_note": "Jupiter transit over 7th lord or Venus = marriage timing window",
    })

    # ── 4. D-9 Navamsa confirmation ───────────────────────────────
    d9_lagna_sign = d9.get("Lagna", {}).get("sign", "") if d9 else ""
    d9_lagna_lord = SIGN_LORDS.get(d9_lagna_sign, "") if d9_lagna_sign else ""
    d9_ll_strong  = is_planet_strong(d9_lagna_lord, d9) if d9 else False
    d9_venus_str  = d9.get("Venus", {}).get("strength", "") if d9 else ""
    d9_venus_good = d9_venus_str in ("exalted", "own") if d9_venus_str else False

    yogas.append({
        "name":        "D-9 Navamsa — Soul-Level Marriage Chart",
        "present":     d9_ll_strong or d9_venus_good,
        "strength":    "strong" if d9_ll_strong and d9_venus_good else "moderate" if d9_ll_strong or d9_venus_good else "weak",
        "description": f"Navamsa lagna: {d9_lagna_sign}, lagna lord: {d9_lagna_lord} ({'strong' if d9_ll_strong else 'weak'}), Venus in Navamsa: {d9_venus_str}",
        "implication": (
            "The soul-level marriage chart is strong. "
            "The marriage is karmically supported — deep compatibility and long-term fulfillment possible."
            if d9_ll_strong or d9_venus_good else
            "The Navamsa shows marriage requires conscious work at the soul level. "
            "The right partner triggers growth, but it's not effortless."
        ),
        "timing_note": "D-9 quality defines the depth of the marriage, not just its timing",
    })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
# CHILDREN YOGAS
# ══════════════════════════════════════════════════════════════════════════════

def detect_children_yogas(
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    planets    = chart_data["planets"]
    lagna_sign = chart_data["lagna"]["sign"]
    d7         = d_charts.get("D7", {})
    yogas      = []

    lord_5  = get_house_lord(lagna_sign, 5)
    sign_5  = get_house_sign(lagna_sign, 5)

    # Jupiter as putrakaraka
    jup_strong    = _strong("Jupiter", planets)
    jup_in_5      = _in_sign("Jupiter", sign_5, planets)
    jup_aspects_5 = _jupiter_aspects(sign_5, planets)
    l5_strong     = _strong(lord_5, planets)
    l5_weak       = _weak(lord_5, planets)

    yogas.append({
        "name":        "Putra Yoga — Children Blessing",
        "present":     jup_strong or jup_in_5 or jup_aspects_5 or l5_strong,
        "strength":    "strong" if (jup_strong and l5_strong) else "moderate" if (jup_strong or l5_strong) else "weak" if l5_weak else "neutral",
        "description": f"Jupiter: {_sign_of('Jupiter', planets)} ({'strong' if jup_strong else 'standard'}), 5th lord ({lord_5}): {'strong' if l5_strong else 'weak' if l5_weak else 'neutral'}",
        "implication": (
            "Strong children combinations. Parenthood is well-supported by the chart. "
            "Jupiter dasha is the primary fertility window."
            if (jup_strong or l5_strong) else
            "Children are possible but the chart suggests some challenges or delays. "
            "Jupiter transit timing and medical support may help."
        ),
        "timing_note": f"Jupiter or {lord_5} dasha = primary conception window",
    })

    d7_lagna_sign = d7.get("Lagna", {}).get("sign", "") if d7 else ""
    d7_ll         = SIGN_LORDS.get(d7_lagna_sign, "") if d7_lagna_sign else ""
    d7_ll_strong  = is_planet_strong(d7_ll, d7) if d7 else False

    yogas.append({
        "name":        "D-7 Saptamsha — Children Destiny Chart",
        "present":     d7_ll_strong,
        "strength":    "strong" if d7_ll_strong else "moderate",
        "description": f"D-7 lagna: {d7_lagna_sign}, lagna lord {d7_ll}: {'strong' if d7_ll_strong else 'standard'}",
        "implication": (
            "The dedicated children chart is strong. Parenthood is karmically supported."
            if d7_ll_strong else
            "D-7 is moderate. Children timing and circumstances depend heavily on dasha windows."
        ),
        "timing_note": "D-7 confirms the quality of parenting karma",
    })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN ROUTER — returns the right detector
# ══════════════════════════════════════════════════════════════════════════════

DOMAIN_DETECTORS = {
    "wealth":       detect_wealth_yogas,
    "billionaire":  detect_wealth_yogas,
    "funding":      detect_wealth_yogas,
    "property":     detect_wealth_yogas,
    "legal":        detect_legal_yogas,
    "health":       detect_health_yogas,
    "marriage":     detect_marriage_yogas,
    "children":     detect_children_yogas,
}

def detect_yogas_for_question(
    domain: str,
    chart_data: dict,
    d_charts: dict,
) -> list[dict]:
    """
    Main entry point. Pass the domain and charts.
    Returns list of yoga dicts for the LLM context block.
    """
    detector = DOMAIN_DETECTORS.get(domain)
    if not detector:
        return []
    return detector(chart_data, d_charts)
