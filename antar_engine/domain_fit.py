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
# [i18n 2026-10-01] Keywords are matched against the RAW question text, which may
# be EN / ES / PT (Antar answers in the question's language). English-only keywords
# silently broke the whole venture guardrail for ES/PT askers — e.g. Andrés asking
# "conseguir los recursos para cerrar este negocio de finca raíz" resolved to
# generic `funding`/`supported` (a soft green-light) instead of `property`/
# `misaligned_approach`. Each domain carries EN + ES + PT triggers. Keep terms
# distinctive (avoid bare common words that would cross domains).
DOMAIN_SPEC = {
    "property": {
        "kw": ("real estate", "property", "land", "plot", "developer", "lease",
               "realty", "flip", "house sale", "sell the land", "apartment",
               "building", "construction",
               # ES
               "finca raíz", "finca raiz", "bienes raíces", "bienes raices",
               "inmueble", "inmobiliari", "propiedad", "terreno", "lote",
               "predio", "apartamento",
               # [finca 2026-10-04] a bare "finca" (farm/rural property) missed the
               # property domain, so no raise-funding guard (Jaime)
               "finca", "hacienda", "parcela",
               # PT
               "imóvel", "imovel", "imóveis", "imoveis", "imobiliári",
               "imobiliari", "propriedade", "terreno", "loteamento",
               "fazenda", "sítio", "chácara", "chacara",
               # Hinglish (romanized Hindi)
               "zameen", "zamin", "makaan", "makan", "jaaydaad", "jaidad",
               "jaydad", "property ki", "plot le"),
        "houses": [4], "karakas": ["Mars", "Saturn"],
        "nature": "slow, owned, long-hold",
    },
    "tech": {
        "kw": ("tech", "software", "app ", "platform", " ai", "a.i", "saas",
               "startup", "digital product", "build a product", "engineering",
               "code ", "web app", "mobile app",
               # ES
               "tecnología", "tecnologia", "plataforma", "aplicación",
               "aplicativo", "inteligencia artificial", "producto digital",
               # PT
               "tecnologia", "plataforma", "aplicativo", "aplicação",
               "inteligência artificial", "produto digital"),
        "houses": [3, 10], "karakas": ["Mercury", "Rahu"],
        "nature": "fast, networked, scalable",
    },
    "hospitality": {
        "kw": ("restaurant", "hospitality", "cafe", "hotel", "food business",
               "catering", "retail", "consumer brand", "salon", "store",
               "service business", "shop",
               # ES
               "restaurante", "cafetería", "cafeteria", "tienda",
               "negocio de comida", "hostelería", "hoteler",
               # PT
               "restaurante", "cafeteria", "loja", "negócio de comida",
               "hotelaria"),
        "houses": [2, 7, 10], "karakas": ["Venus", "Moon"],
        "nature": "public-facing, presence-driven",
    },
    "partnership": {
        "kw": ("co-founder", "cofounder", "business partner", "partnership",
               "joint venture", "equity partner", "take on a partner",
               # ES
               "socio", "cofundador", "co-fundador", "sociedad",
               "empresa conjunta",
               # PT
               "sócio", "socio", "cofundador", "parceria", "parceiro",
               "sociedade",
               # Hinglish
               "saajhedaar", "sajhedaar", "saajhedari", "sajhedari",
               "partner ke saath"),
        "houses": [7], "karakas": ["Venus", "Mercury"],
        "nature": "shared / other-dependent",
    },
    "speculation": {
        "kw": ("speculat", "gamble", "betting", "a bet", "trading", "day trade",
               "stocks", "crypto", "lottery", "options", "forex",
               # ES
               "especula", "apuesta", "apostar", "lotería", "loteria",
               "cripto", "acciones",
               # PT
               "especula", "aposta", "apostar", "loteria", "cripto",
               "ações", "acoes",
               # Hinglish
               "satta", "sattebaazi", "jua", "juaa"),
        "houses": [5], "karakas": ["Rahu", "Ketu", "Mercury"],
        "nature": "high-variance, speculative",
    },
    "career": {
        "kw": ("job", "career", "promotion", "my work", "a role", "position",
               "employment", "my boss", "corporate",
               # ES
               "trabajo", "empleo", "carrera", "puesto", "ascenso", "jefe",
               # PT
               "emprego", "carreira", "cargo", "promoção", "promocao", "chefe",
               # Hinglish
               "naukri", "nokri", "naukari", "job ki", "promotion mil"),
        "houses": [10, 6], "karakas": ["Sun", "Saturn", "Mercury"],
        "nature": "role / structure-driven",
    },
    "funding": {   # generic capital — only used when NO specific asset domain
        "kw": ("funding", "investor", "raise capital", "backer", "venture capital",
               "angel", "fundraise", "capital for",
               # ES
               "financiación", "financiacion", "financiamiento", "inversionista",
               "inversor", "levantar capital", "conseguir recursos",
               "conseguir los recursos", "recursos para", "préstamo", "prestamo",
               "crédito", "credito", "fondos",
               # PT
               "financiamento", "investidor", "captar recursos", "captar capital",
               "empréstimo", "emprestimo", "crédito", "fundos", "recursos para",
               # Hinglish
               "paisa", "paise", "udhaar", "udhar", "karza", "karz",
               "funding chahiye", "paise jutana"),
        "houses": [11, 2, 8], "karakas": ["Jupiter", "Venus"],
        "nature": "gains-timing dependent",
    },
}
# Approach the question implies: fast/leveraged vs slow/owned. A fast approach
# to a slow-shape domain = misaligned_approach. EN + ES + PT.
_FAST_APPROACH = ("flip", "quick", "raise", "investor", "capital", "fund", "sell",
                  "fast", "scale fast", "leverage", "loan", "borrow", "backer",
                  # ES
                  "recursos", "conseguir recursos", "levantar", "captar",
                  "inversionista", "inversor", "financia", "préstamo", "prestamo",
                  "crédito", "credito", "vender", "rápido", "rapido", "cerrar el negocio",
                  "cerrar la operación", "cerrar la operacion", "cerrar este negocio",
                  # PT
                  "captar", "investidor", "financia", "empréstimo", "emprestimo",
                  "vender", "rápido", "rapido", "fechar o negócio", "fechar negócio",
                  # Hinglish
                  "paisa", "paise", "udhaar", "udhar", "karza", "karz", "bech",
                  "bechna", "jaldi", "jutana", "fund chahiye")
_SLOW_APPROACH = ("buy and hold", "own", "develop", "build", "long term",
                  "long-term", "hold", "rent out", "construct",
                  # ES
                  "comprar y mantener", "largo plazo", "construir", "alquilar",
                  "mantener", "conservar",
                  # PT
                  "comprar e manter", "longo prazo", "construir", "alugar", "manter",
                  # Hinglish
                  "rakhna", "banana", "kiraye pe", "lambe samay", "lamba")


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
    # is the question ALSO about raising money for that domain? EN + ES + PT + Hinglish.
    raising = any(k in ql for k in (
        "raise", "investor", "capital", "fund", "backer", "loan",
        # ES
        "recursos", "inversionista", "inversor", "financia", "préstamo",
        "prestamo", "crédito", "credito", "levantar capital", "conseguir recursos",
        # PT
        "captar", "investidor", "financiamento", "empréstimo", "emprestimo",
        # Hinglish
        "paisa", "paise", "udhaar", "udhar", "karza", "karz", "funding"))
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
                    "alignment": alignment, "reasons": reasons,
                    # raw shape score (no approach penalty) so callers like the
                    # Aligned-Path engine can RANK which domains fit this chart best.
                    "support": support, "afflict": afflict, "net": support - afflict})
        out["directive"] = _directive(domain, shape, alignment, out["period_fit"],
                                      reasons, raising)
        # plain_read: a jargon-free, USER-FACING sentence for the veto case. The
        # narrator normally translates `directive` itself; plain_read is the
        # deterministic fallback the fail-closed/voice-gate path drops in when the
        # LLM read is unavailable — so a vetoed answer never collapses back to the
        # domain-blind "money comes through backers, timing supports it" template.
        out["plain_read"] = _plain_read(domain, shape, alignment, out["period_fit"])
        return out
    except Exception:
        return out


# Domain → a plain, jargon-free noun phrase (no planets/houses/Sanskrit).
_DOMAIN_PHRASE = {
    "property": "property", "tech": "tech", "hospitality": "a public-facing business",
    "partnership": "a partnership", "speculation": "speculation",
    "career": "your work", "funding": "raising outside money",
}


def _plain_read(domain, shape, alignment, period_fit):
    """One honest, jargon-free sentence for the deterministic fail-closed path.
    Only meaningful for the veto alignments (misaligned_approach / caution);
    empty otherwise so the normal narrator/body logic stays in charge."""
    dp = _DOMAIN_PHRASE.get(domain, "this")
    if alignment == "misaligned_approach":
        s = ("This isn't the approach to back here. For you, %s works %s — not raised "
             "against or rushed to a close. So don't chase investors or a quick close "
             "for this one; put that same drive into the lane you're actually built to "
             "run." % (dp, shape))
        if period_fit == "caution":
            s += " And this isn't the clean season to force it — prepare now, move when it clears."
        return s
    if alignment == "caution":
        s = ("Go carefully with %s right now — it's not the thing to push hard on or "
             "raise money for. Protect what you already have first." % dp)
        if period_fit == "caution":
            s += " This isn't the season to force it; wait for a cleaner window."
        return s
    return ""


# Venture domains worth ranking for "what you're built for" (funding is generic
# capital, not a venture; speculation is a trap, never an edge — both excluded).
_EDGE_DOMAINS = ("tech", "property", "hospitality", "partnership", "career")


def fit_all_domains(chart_data, dashas, running_lords=None):
    """Score every venture domain for THIS chart with a NEUTRAL probe (the domain's
    own name, no approach words) so `net` reflects pure shape-fit, not the approach
    penalty. Returns {domain: result}. Used by the Aligned-Path engine to rank the
    person's natural edge and name the domain-level trap. Fail-open → {}."""
    out = {}
    try:
        for d in _EDGE_DOMAINS:
            probe = DOMAIN_SPEC[d]["kw"][0]  # neutral keyword, no fast/slow verbs
            r = assess_domain_fit(chart_data, dashas, probe, d, running_lords=running_lords)
            if r.get("available"):
                out[d] = r
    except Exception:
        pass
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
