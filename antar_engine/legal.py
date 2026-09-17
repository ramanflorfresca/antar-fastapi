"""
antar_engine/legal.py

Deterministic LEGAL / disputes engine. Answers, from the real chart:
  • PROPENSITY — how prone to disputes/litigation (6/8/12 affliction, Mars/Saturn/
    Rahu pressure on the self).
  • WIN vs LOSE — your side (lagna + 6th = victory over adversaries, 11th = the
    gain, Jupiter = dharma/your advocate) against the opponent (7th).
  • TIMING — when a legal matter is likely to flare / resolve, via the shared
    multi-system convergence (Vimśottarī AD of 6/8/12 lords or Saturn/Mars/Rahu +
    transits + Chara + Lal-Kitab varshphal 6th/8th).

Classical spine: 6th = the case, disputes, enemies, debts (also victory-over-
enemies for YOU); 7th = the opposing party / open conflict; 8th = reversals,
penalties, hidden dealings; 12th = loss, confinement, legal costs, defeat.
Karakas: Saturn (law, judgment, delay), Mars (conflict), Rahu (manipulation),
Mercury (documents/arguments); Jupiter = protection / a favourable judgment.
LLM narrates only. v1 — calibrate against real outcomes.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import (
    _dig, _house_of, _in_house, _malefics_on, _benefics_on, _aspects)
from antar_engine.domain_timing import domain_convergence

# What a legal matter is likely ABOUT, from the house an activating lord rules/
# occupies (the arena) and the planet's own nature (the flavour).
_HOUSE_CAUSE = {
    2:  "money, family assets, or savings",
    3:  "siblings, neighbours, or a contract/communication",
    4:  "property, land, home, or vehicles",
    6:  "debts, loans, enemies, or a service/employment dispute",
    7:  "a partnership, business deal, spouse, or an open opponent",
    8:  "inheritance, other people's money, insurance, tax, or hidden dealings",
    12: "losses, expenses, a foreign matter, or confinement",
}
_PLANET_CAUSE = {
    "Saturn":  "institutions or banks, labour, land, or a long-drawn matter",
    "Mars":    "property, aggression, a sibling, or an accident",
    "Rahu":    "fraud, manipulation, tax/regulation, or a foreign angle",
    "Mercury": "a contract, documents, or communication",
    "Venus":   "a marriage, a woman, or a partnership",
    "Ketu":    "something hidden, tax, or a secret",
    "Jupiter": "finance, an advisor, or a matter of principle",
    "Sun":     "authority, government, or status/ego",
    "Moon":    "family, the public, or property",
}


def _legal_cause(chart_data: dict, lords) -> list:
    """The likely SUBJECT of a legal matter, from the houses the activating lords
    rule/occupy + their planetary nature. Ordered, de-duplicated, top few."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    lagna = ((cd.get("lagna") or {}).get("sign"))
    if not lagna:
        return []
    seen, out = set(), []

    def _push(txt):
        if txt and txt not in seen:
            seen.add(txt)
            out.append(txt)

    for lord in lords:
        if not lord:
            continue
        for h in (6, 7, 8, 2, 4, 12, 3):
            if SIGN_LORD.get(_sign_n_from(lagna, h)) == lord:
                _push(_HOUSE_CAUSE.get(h))
        oh = (d1.get(lord) or {}).get("house")
        if oh in _HOUSE_CAUSE:
            _push(_HOUSE_CAUSE.get(oh))
        _push(_PLANET_CAUSE.get(lord))
    return out[:3]


LEGAL_SPEC = {
    "noun": "legal matters",
    "houses": [6, 7, 8, 12],
    "activator_houses": [6, 8, 12],
    "karakas": ["Saturn", "Mars", "Rahu", "Mercury"],
    "varsh_houses": [6, 8],
    "transit_grahas": ["Saturn", "Mars", "Rahu", "Ketu"],
    "transit_houses": [1, 6, 7, 8],
    "malefic_varsh": True,
    "varsh_weight": 1.6,   # LK varshphal is the most accurate yearly layer — weight it up
    "min_score": 2.0,
}


def analyze_legal(chart_data: dict) -> dict:
    """Return {available, propensity{}, outcome{}, factors{}, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}

        lagna_lord = SIGN_LORD.get(lagna)
        sixth = _sign_n_from(lagna, 6)
        sixth_lord = SIGN_LORD.get(sixth)
        seventh = _sign_n_from(lagna, 7)
        seventh_lord = SIGN_LORD.get(seventh)
        eleventh_lord = SIGN_LORD.get(_sign_n_from(lagna, 11))

        def _dg(p):
            return _dig(p, (d1.get(p) or {}).get("sign"))[0]

        # ── PROPENSITY for disputes/litigation ───────────────────────────────
        prop, pflags = 0.0, []
        for h, nm in ((6, "disputes/enemies"), (8, "sudden reversals"), (12, "loss/entanglement")):
            m = _malefics_on(d1, h)
            if m:
                prop += 0.5 * len(m)
                pflags.append(f"malefic pressure on your house of {nm} ({', '.join(m)})")
        # Mars/Saturn/Rahu striking the self (lagna) — a combative/entangled life
        for p in ("Mars", "Saturn", "Rahu"):
            ph = _house_of(p, d1)
            if ph == 1 or (ph and _aspects(ph, 1, p)):
                prop += 0.4
                pflags.append(f"{p} presses your ascendant (a combative streak)")
        propensity = {
            "score": round(prop, 2),
            "level": ("high" if prop >= 2.5 else "some" if prop >= 1.0 else "low"),
            "flags": pflags,
        }

        # ── WIN vs LOSE — your side against the opponent ──────────────────────
        # YOU = lagna (self) + 6th (victory over adversaries) + 11th (the gain);
        # OPPONENT = 7th. Jupiter graces (aspects lagna/6/10) = dharma on your side.
        self_s, opp_s, drivers = 0.0, 0.0, []
        self_s += _dg(lagna_lord) + _dg(sixth_lord)
        if _dg(eleventh_lord) >= 0:
            self_s += 0.5
        jup_h = _house_of("Jupiter", d1)
        jup_grace = jup_h and any(_aspects(jup_h, h, "Jupiter") or jup_h == h for h in (1, 6, 10))
        if jup_grace:
            self_s += 1.2
            drivers.append("Jupiter's grace protects you (a favourable, dharmic hand)")
        # benefic support to your ascendant
        if _benefics_on(d1, 1):
            self_s += 0.4
        opp_s += _dg(seventh_lord)
        # malefics strengthening the opponent's 7th
        if len(_malefics_on(d1, 7)) >= 2:
            opp_s += 0.6
        # the 6th (your fighting house) stronger than the 7th (opponent) → you prevail
        lean = self_s - opp_s
        outcome = {
            "self_strength": round(self_s, 2), "opponent_strength": round(opp_s, 2),
            "lean": ("favourable" if lean >= 1.0 else "unfavourable" if lean <= -1.0 else "contested"),
            "jupiter_protection": bool(jup_grace), "drivers": drivers,
        }

        # likely SUBJECT of disputes — from the 6/8/12 lords and what sits there
        _cause_lords = [SIGN_LORD.get(_sign_n_from(lagna, h)) for h in (6, 8, 12)]
        _cause_lords += _in_house(d1, 6) + _in_house(d1, 8)
        likely_causes = _legal_cause(cd, _cause_lords)

        factors = {
            "sixth_sign": sixth, "sixth_lord": sixth_lord,
            "seventh_sign": seventh, "seventh_lord": seventh_lord,
            "lagna_lord": lagna_lord, "malefics_in_6": _in_house(d1, 6),
        }

        summary = (f"Propensity for disputes is {propensity['level']}; if a legal "
                   f"matter arises, the chart leans {outcome['lean']}"
                   + (" — Jupiter's protection is a real asset." if jup_grace else ".")
                   + (f" Disputes tend to involve {likely_causes[0]}." if likely_causes else ""))

        return {"available": True, "propensity": propensity, "outcome": outcome,
                "likely_causes": likely_causes, "factors": factors, "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def legal_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                 today: Optional[str] = None) -> dict:
    """When a legal matter is likely to flare/resolve — multi-system convergence.
    Returns {available, windows[], best, summary}."""
    res = domain_convergence(chart_data, dashas, LEGAL_SPEC, birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    # attach the likely CAUSE to each window from its activating lords (MD–AD)
    for w in res.get("windows", []):
        parts = [x.strip() for x in w["label"].replace("–", "-").split("-")]
        w["cause"] = _legal_cause(chart_data, parts)
    best = res.get("best")
    if best:
        cause = best.get("cause") or []
        res["summary"] = (f"The most legally-charged window is around {best.get('year', best['start'][:4])} "
                          f"— {len(best['systems'])} systems flag it"
                          + (f", likely about {cause[0]}." if cause else "."))
        res["cause"] = cause
    else:
        res["summary"] = "No sharply-converging legal window ahead — no structural flare flagged."
        res["cause"] = []
    return res


# ── chapter-verdict package for the Ask /predict legal override ──────────────
# Honest by design: NEVER claims a guaranteed win. The chart shows a LEAN and
# the charged window; preparation + counsel convert a lean into a result. band ∈
# MIXED|WEAK (never FAVORABLE — "you'll win" is not ours to promise).
def _leg_lang(language: str) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_LEG_LINE = {
    "favourable": {
        "en": "The chart leans in your favour on this matter — but the outcome isn't fated; strong preparation is what turns a lean into a result.",
        "es": "La carta se inclina a tu favor en este asunto — pero el resultado no está sellado; la buena preparación es lo que convierte una inclinación en un resultado.",
        "pt": "O mapa pende a seu favor neste assunto — mas o resultado não está selado; boa preparação é o que transforma uma inclinação em resultado.",
    },
    "contested": {
        "en": "This reads as genuinely contested — the chart doesn't decide it; how well you prepare and who you retain does.",
        "es": "Esto se lee como genuinamente disputado — la carta no lo decide; lo decide qué tan bien te prepares y a quién contrates.",
        "pt": "Isto se lê como genuinamente disputado — o mapa não decide; quem decide é o quanto você se prepara e quem você contrata.",
    },
    "unfavourable": {
        "en": "The chart leans against you here — treat a fair settlement or airtight preparation as the smart play, not a gamble on winning.",
        "es": "La carta se inclina en tu contra aquí — trata un acuerdo justo o una preparación impecable como la jugada inteligente, no una apuesta por ganar.",
        "pt": "O mapa pende contra você aqui — trate um acordo justo ou uma preparação impecável como a jogada inteligente, não uma aposta em vencer.",
    },
}
_LEG_MOVE = {
    "en": "Get thorough documentation and a qualified lawyer now — the matter is most charged {win}.",
    "es": "Consigue documentación exhaustiva y un abogado calificado ahora — el asunto está más candente {win}.",
    "pt": "Reúna documentação completa e um advogado qualificado agora — o assunto está mais aceso {win}.",
}
_LEG_JUP = {
    "en": " Jupiter's protection is a genuine asset here.",
    "es": " La protección de Júpiter es un activo real aquí.",
    "pt": " A proteção de Júpiter é um trunfo real aqui.",
}
_LEG_DISCLAIM = {
    "en": "This is not legal advice — a qualified lawyer should handle the actual case.",
    "es": "Esto no es asesoría legal — un abogado calificado debe manejar el caso real.",
    "pt": "Isto não é aconselhamento jurídico — um advogado qualificado deve conduzir o caso real.",
}


def legal_verdict(lean: str, jupiter_protection: bool, best_year, language: str = "en") -> dict:
    """CHAPTER-level legal verdict for the Ask /predict override. Returns
    (never raises): {available, band, line, the_move, secondary_note, window_range}."""
    try:
        L = _leg_lang(language)
        lean = lean if lean in _LEG_LINE else "contested"
        band = "WEAK" if lean == "unfavourable" else "MIXED"
        yr = str(best_year).strip() if best_year else ""
        if yr:
            win = {"en": f"around {yr}", "es": f"alrededor de {yr}", "pt": f"por volta de {yr}"}[L]
        else:
            win = {"en": "in the period ahead", "es": "en el periodo que viene", "pt": "no período à frente"}[L]
        line = _LEG_LINE[lean][L] + (_LEG_JUP[L] if jupiter_protection else "")
        return {"available": True, "band": band, "line": line,
                "the_move": _LEG_MOVE[L].format(win=win),
                "secondary_note": _LEG_DISCLAIM[L], "window_range": win}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
