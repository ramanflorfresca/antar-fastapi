"""
antar_engine/domain_fit.py — Domain-Fit Alignment engine.

[domain-fit 2026-09-30] ONE general engine for "is THIS kind of venture a fit
for THIS chart, in THIS season, done THIS way?" — replaces per-combination
overlays (property, speculation, …) with a single domain map + shape/period
scorer. It gates money/venture answers in /ask ABOVE the chart-level strategic
stance: the stance says expand/consolidate for the whole chart; this says
whether the SPECIFIC domain + approach + season align.

HARD BOUNDARY (do not cross): this engine reasons about SHAPE (how a domain fits:
slow/owned vs fast/networked vs speculative), APPROACH-FIT (does the asked
approach match that shape), and TIMING (is the season favourable to act) — it
NEVER predicts vertical success/failure. "Real estate fits you slow-owned, not
flipped, and not this season" — never "real estate will fail / tech will win".
That success-prediction was falsified (business-vertical-timing-study).

Output is an internal-reference directive the narrator translates to plain,
jargon-free language. Fail-open: any error returns a neutral/empty result.
"""
from __future__ import annotations

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
             "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus",
             "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn",
             "Aquarius": "Saturn", "Pisces": "Jupiter"}
EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
         "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra"}
DEBIL = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
         "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
DUSTHANA = {6, 8, 12}
STRONG_HOUSES = {1, 4, 5, 7, 9, 10, 11}   # kendra/trikona/labha/wealth

# Each domain: trigger keywords, the significator houses + karakas, and the
# domain's NATURAL shape (how it inherently works). The chart then tells us how
# THIS person's version of that shape runs.
DOMAIN_SPEC = {
    "property": {
        "kw": ("real estate", "property", "land", "plot", "developer", "lease",
               "realty", "flip", "house sale", "sell the land", "apartment",
               "building", "construction"),
        "houses": [4], "karakas": ["Mars", "Saturn"],
        "nature": "slow, owned, long-hold",
    },
    "tech": {
        "kw": ("tech", "software", "app ", "platform", " ai", "a.i", "saas",
               "startup", "digital product", "build a product", "engineering",
               "code ", "web app", "mobile app"),
        "houses": [3, 10], "karakas": ["Mercury", "Rahu"],
        "nature": "fast, networked, scalable",
    },
    "hospitality": {
        "kw": ("restaurant", "hospitality", "cafe", "hotel", "food business",
               "catering", "retail", "consumer brand", "salon", "store",
               "service business", "shop"),
        "houses": [2, 7, 10], "karakas": ["Venus", "Moon"],
        "nature": "public-facing, presence-driven",
    },
    "partnership": {
        "kw": ("co-founder", "cofounder", "business partner", "partnership",
               "joint venture", "equity partner", "take on a partner"),
        "houses": [7], "karakas": ["Venus", "Mercury"],
        "nature": "shared / other-dependent",
    },
    "speculation": {
        "kw": ("speculat", "gamble", "betting", "a bet", "trading", "day trade",
               "stocks", "crypto", "lottery", "options", "forex"),
        "houses": [5], "karakas": ["Rahu", "Ketu", "Mercury"],
        "nature": "high-variance, speculative",
    },
    "career": {
        "kw": ("job", "career", "promotion", "my work", "a role", "position",
               "employment", "my boss", "corporate"),
        "houses": [10, 6], "karakas": ["Sun", "Saturn", "Mercury"],
        "nature": "role / structure-driven",
    },
    "funding": {   # generic capital — only used when NO specific asset domain
        "kw": ("funding", "investor", "raise capital", "backer", "venture capital",
               "angel", "fundraise", "capital for"),
        "houses": [11, 2, 8], "karakas": ["Jupiter", "Venus"],
        "nature": "gains-timing dependent",
    },
}
# Approach the question implies: fast/leveraged vs slow/owned. A fast approach
# to a slow-shape domain = misaligned_approach.
_FAST_APPROACH = ("flip", "quick", "raise", "investor", "capital", "fund", "sell",
                  "fast", "scale fast", "leverage", "loan", "borrow", "backer")
_SLOW_APPROACH = ("buy and hold", "own", "develop", "build", "long term",
                  "long-term", "hold", "rent out", "construct")


def _dignity(planet, sign):
    if not sign:
        return "neutral"
    if EXALT.get(planet) == sign:
        return "exalted"
    if DEBIL.get(planet) == sign:
        return "debilitated"
    if SIGN_LORD.get(sign) == planet:
        return "own"
    return "neutral"


def _resolve_domain(question, concern):
    ql = (question or "").lower()
    c = (concern or "").lower()
    # specific asset/venture domains win over generic funding/career
    order = ["property", "tech", "hospitality", "partnership", "speculation",
             "career", "funding"]
    hit = None
    for d in order:
        if any(k in ql for k in DOMAIN_SPEC[d]["kw"]):
            hit = d
            break
    if not hit:
        # fall back to the concern router's domain
        cmap = {"funding": "funding", "income": "funding", "wealth": "funding",
                "career": "career", "business": "tech", "venture": "tech",
                "speculation": "speculation"}
        hit = cmap.get(c)
    # is the question ALSO about raising money for that domain?
    raising = any(k in ql for k in ("raise", "investor", "capital", "fund",
                                    "backer", "loan"))
    return hit, raising


def assess_domain_fit(chart_data, dashas, question, concern, running_lords=None):
    """Return a dict: {available, domain, nature, shape, alignment, period_fit,
    reasons[], directive}. alignment in aligned|caution|misaligned_approach|
    neutral. directive is '' when not applicable."""
    out = {"available": False, "domain": None, "shape": "", "alignment": "neutral",
           "period_fit": "neutral", "reasons": [], "directive": ""}
    try:
        domain, raising = _resolve_domain(question, concern)
        if not domain:
            return out
        cd = chart_data or {}
        planets = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        if not planets or lagna not in SIGNS:
            return out
        li = SIGNS.index(lagna)
        spec = DOMAIN_SPEC[domain]

        def sign_of_house(h):
            return SIGNS[(li + h - 1) % 12]

        def house_of(planet):
            v = planets.get(planet)
            return v.get("house") if isinstance(v, dict) else None

        def sign_of(planet):
            v = planets.get(planet)
            return v.get("sign") if isinstance(v, dict) else None

        reasons = []
        support, afflict = 0, 0
        # --- primary house condition ---
        for h in spec["houses"]:
            hs = sign_of_house(h)
            lord = SIGN_LORD[hs]
            lh = house_of(lord)
            # lord placement
            if lh in STRONG_HOUSES:
                support += 1
            elif lh in DUSTHANA:
                afflict += 1
            # lord dignity
            dg = _dignity(lord, sign_of(lord))
            if dg in ("exalted", "own"):
                support += 1
            elif dg == "debilitated":
                afflict += 1
            # occupants
            occ = [p for p, v in planets.items()
                   if isinstance(v, dict) and v.get("house") == h]
            for p in occ:
                if _dignity(p, sign_of(p)) == "debilitated":
                    afflict += 1
                elif _dignity(p, sign_of(p)) in ("exalted", "own"):
                    support += 1
        # --- karaka condition ---
        for k in spec["karakas"]:
            dg = _dignity(k, sign_of(k))
            if dg in ("exalted", "own"):
                support += 1
            elif dg == "debilitated":
                afflict += 1
            if house_of(k) in DUSTHANA:
                afflict += 1
            elif house_of(k) in STRONG_HOUSES:
                support += 1

        # --- SHAPE: what dominant influence runs this domain for THIS chart ---
        # Saturn ruling or sitting in the primary house => slow/owned shape.
        shape = spec["nature"]
        prim = spec["houses"][0]
        prim_lord = SIGN_LORD[sign_of_house(prim)]
        prim_occ = [p for p, v in planets.items()
                    if isinstance(v, dict) and v.get("house") == prim]
        saturn_runs = (prim_lord == "Saturn" or "Saturn" in prim_occ)
        merc_rahu_runs = (prim_lord in ("Mercury",) or
                          {"Mercury", "Rahu"} & set(prim_occ))
        if domain == "property" and saturn_runs:
            shape = "slow, owned, long-hold (built/kept, never flipped)"
            reasons.append("property is a patient, owned domain for them, not a quick flip")
        elif saturn_runs:
            shape = spec["nature"] + " — but worked slowly/patiently"
        elif merc_rahu_runs and domain in ("tech", "career"):
            shape = "fast, networked, your-insight-driven"

        # --- APPROACH fit: fast/leveraged ask vs a slow-shape domain ---
        ql = (question or "").lower()
        asked_fast = raising or any(k in ql for k in _FAST_APPROACH)
        asked_slow = any(k in ql for k in _SLOW_APPROACH)
        slow_shape = ("slow" in shape or "owned" in shape or domain == "property")
        approach_mismatch = (asked_fast and not asked_slow and slow_shape)

        # --- period fit ---
        run = {str(x).title() for x in (running_lords or set())}
        karaka_running = bool(run & set(spec["karakas"]))
        lords_running = any(SIGN_LORD[sign_of_house(h)] in run for h in spec["houses"])
        # Guru-Chandala haze: Rahu with/ in Jupiter's sign AND Rahu is running
        rahu_sign = sign_of("Rahu")
        guru_chandala = (rahu_sign in ("Sagittarius", "Pisces")
                         or house_of("Rahu") == house_of("Jupiter"))
        illusion = guru_chandala and "Rahu" in run
        if illusion:
            out["period_fit"] = "caution"
            reasons.append("they're in a hazy / non-closure period for acting on this")
        elif karaka_running or lords_running:
            out["period_fit"] = "favorable"

        # --- alignment verdict ---
        # Guardrail, not an oracle: we flag misalignment / caution and give SHAPE,
        # and offer only a SOFT "supported" (fits-your-shape, proceed-with-discipline)
        # — never a confident "this domain will work" green-light (that ranking was
        # falsified and is where the scorer is noisiest).
        net = support - afflict
        if domain == "speculation":
            # speculation is never green-lit (safety; the KP speculation gate is closed)
            alignment = "caution"
            if house_of("Ketu") == 5 or house_of("Rahu") == 5:
                reasons.append("speculation is a standing leak for them (their chart's own pattern)")
            else:
                reasons.append("speculation is high-variance and not something to lean on")
        elif approach_mismatch:
            alignment = "misaligned_approach"
        elif afflict >= 2 and afflict > support:
            alignment = "caution"
        elif net >= 2 and not approach_mismatch:
            alignment = "supported"
        else:
            alignment = "neutral"

        out.update({"available": True, "domain": domain, "shape": shape,
                    "alignment": alignment, "reasons": reasons})
        out["directive"] = _directive(domain, shape, alignment, out["period_fit"],
                                      reasons, raising)
        return out
    except Exception:
        return out


def _directive(domain, shape, alignment, period_fit, reasons, raising):
    """Internal-reference block the narrator translates. Never predicts success."""
    why = "; ".join(reasons)
    head = ("\n\nDOMAIN FIT (internal reference — GATE the venture answer by this; "
            "translate to plain language; this is about SHAPE, APPROACH and TIMING, "
            "NOT whether it will succeed — never promise or deny an outcome): "
            "the question is about %s. " % domain)
    if alignment == "misaligned_approach":
        body = ("This domain fits them only as %s — the fast/leveraged approach they "
                "are asking about fights their chart%s. Do NOT coach raising capital, "
                "finding an investor, or forcing a quick close for THIS. Tell them "
                "plainly the approach is the problem, the aligned approach is %s, and "
                "steer their money/energy toward their actual lane instead." %
                (shape, (" (" + why + ")" if why else ""), shape))
    elif alignment == "caution":
        body = ("Treat this domain with CAUTION for them%s. Don't encourage pushing "
                "hard or raising for it; frame it honestly and protect them." %
                ((" — " + why) if why else ""))
    elif alignment == "supported":
        body = ("This domain fits their shape (as %s) — you may support it, framed as "
                "'proceed with focus and discipline', NOT as a promise it will "
                "succeed. The outcome is theirs to earn." % shape)
    else:
        body = ("Give a measured read; no strong push either way; outcome is theirs.")
    if period_fit == "caution":
        body += (" NOTE the TIMING: this is not the season to launch/raise/close for "
                 "this — advise prepare-and-wait for a cleaner window.")
    return head + body
