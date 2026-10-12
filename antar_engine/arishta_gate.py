"""
antar_engine/arishta_gate.py

The FEAR-OR-REALITY gate for pressure-type questions (debt, legal, status risk).
Classical first step: is the RUNNING dasha chain actually connected to the houses
of trouble (6th obligations/disputes, 8th reversals, 12th loss)? If neither the
Mahadasha nor the Antardasha lord rules or sits in 6/8/12, the stretch is not
pressing on the matter — what the person feels is worry, not an active cycle.

Pure/deterministic. Never raises. A "none" gate describes the CURRENT stretch only;
it never says the matter is impossible later (natal propensity and the next window
are reported separately by the engines).
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGN_LORD, _sign_n_from
from antar_engine.relationships import _house_of

TROUBLE_HOUSES = (6, 8, 12)


def _parse(dasha_str: Optional[str]) -> list:
    parts = [x.strip().title() for x in str(dasha_str or "").replace("–", "-").split("-")]
    return [p for p in parts if p][:2]


def dasha_stack(chart_data: dict, dasha_str: Optional[str], houses=TROUBLE_HOUSES) -> dict:
    """{level: none|one|stack, md, ad, houses_hit[]}.
    A lord is 'connected' if it rules or occupies one of `houses`. level 'stack' =
    BOTH the Mahadasha and Antardasha lords are connected; 'one' = only one."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        lords = _parse(dasha_str)
        if not d1 or not lagna or not lords:
            return {"level": "unknown", "md": False, "ad": False, "houses_hit": []}
        ruled = {h: SIGN_LORD.get(_sign_n_from(lagna, h)) for h in houses}
        flags, hit = [], set()
        for lord in lords:
            rules = [h for h, l in ruled.items() if l == lord]
            sits = _house_of(lord, d1) in houses
            flags.append(bool(rules or sits))
            hit.update(rules)
            if sits:
                hit.add(_house_of(lord, d1))
        md = flags[0]
        ad = flags[1] if len(flags) > 1 else False
        level = "stack" if (md and ad) else "one" if (md or ad) else "none"
        return {"level": level, "md": md, "ad": ad, "houses_hit": sorted(hit)}
    except Exception:
        return {"level": "unknown", "md": False, "ad": False, "houses_hit": []}


def gate_level(chart_data: dict, dasha_str: Optional[str]) -> str:
    return dasha_stack(chart_data, dasha_str)["level"]


def _lang(language) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


_NONE_NOTE = {
    "debt": {
        "en": "Nothing in the current stretch is pressing on your money obligations — what you're feeling reads more as worry than an active squeeze. Stay prudent, but don't borrow trouble.",
        "es": "Nada en la etapa actual presiona tus obligaciones de dinero — lo que sientes se lee más como preocupación que como un apretón activo. Sé prudente, pero no te adelantes al problema.",
        "pt": "Nada na fase atual pressiona suas obrigações de dinheiro — o que você sente se lê mais como preocupação do que como um aperto ativo. Seja prudente, mas não antecipe o problema.",
    },
    "legal": {
        "en": "Nothing in the current stretch is pressing on legal matters — what you're feeling reads more as worry than an active cycle. Keep your paperwork in order, but don't borrow trouble.",
        "es": "Nada en la etapa actual presiona los asuntos legales — lo que sientes se lee más como preocupación que como un ciclo activo. Mantén tus documentos en orden, pero no te adelantes al problema.",
        "pt": "Nada na fase atual pressiona assuntos jurídicos — o que você sente se lê mais como preocupação do que como um ciclo ativo. Mantenha seus documentos em ordem, mas não antecipe o problema.",
    },
}


def gate_note(level: Optional[str], topic: str, language: str = "en") -> str:
    """One sentence for a 'none' gate, else ''. Only fires for a known-none stretch."""
    if level != "none" or topic not in _NONE_NOTE:
        return ""
    return _NONE_NOTE[topic][_lang(language)]


# ═════════════════════════════════════════════════════════════════════════════
# PROACTIVE CAUTION — the "tell them BEFORE it matters" layer.
#
# The classical rubric lists natal 6/8/12 factors (Saturn/Mars/Rahu on the trouble
# houses, their lords displaced) on one side and dasha stacks on the other. Scored
# independently they double-count and contradict (Rahu in the 6th is "debt-prone" and
# "debt-free"; Saturn in the 6th both stabilising and jail-prone). So: a natal factor
# counts ONLY WHEN THE RUNNING CHAIN LINKS TO THE SAME HOUSE. Natal pressure with a quiet
# chain is a latent tendency (no caution); a chain connection with no natal pressure is
# a watch at most. Caution needs BOTH to meet.
#
# The chain runs to the pratyantar (weeks-months) and sookshma (days), and the sookshma
# lord is read against its CURRENT transit house — the imminence test.
#
# HONESTY: output is a CAUTION to prepare (above-board conduct, documents, deadlines,
# counsel early) — never a forecast, and it never names jail, arrest, detention or
# deportation. Fear-based output is a product defect.
# ═════════════════════════════════════════════════════════════════════════════
from datetime import date as _date

from antar_engine.relationships import _malefics_on

_HARD = ("Saturn", "Mars", "Rahu", "Ketu")
_LEVEL_NAMES = {"md": ("mahadasha", "md", "1"), "ad": ("antardasha", "ad", "2"),
                "pd": ("pratyantardasha", "pd", "3"), "sd": ("sookshma", "sd", "4")}


def current_chain(dashas: dict, today: Optional[str] = None) -> dict:
    """{md, ad, pd, sd: {lord,start,end}|None} — the running Vimshottari chain."""
    out = {k: None for k in _LEVEL_NAMES}
    try:
        iso = (today or _date.today().isoformat())[:10]
        rows = (dashas or {}).get("vimsottari") or []
        for r in rows:
            if not isinstance(r, dict):
                continue
            lv = str(r.get("level") or "").strip().lower()
            s = str(r.get("start_date") or r.get("start") or "")[:10]
            e = str(r.get("end_date") or r.get("end") or "")[:10]
            lord = str(r.get("lord_or_sign") or r.get("planet_or_sign") or "").title()
            if not (lv and s and e and lord) or not (s <= iso <= e):
                continue
            for k, names in _LEVEL_NAMES.items():
                if lv in names and out[k] is None:
                    out[k] = {"lord": lord, "start": s, "end": e}
    except Exception:
        pass
    return out


def natal_pressure(chart_data: dict) -> dict:
    """{house: [hard planets]} for the trouble houses where Saturn/Mars/Rahu/Ketu sit in
    or aspect the house, OR the house's lord is itself displaced into another trouble house."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        if not d1 or not lagna:
            return {}
        out = {}
        for h in TROUBLE_HOUSES:
            hard = [p for p in _malefics_on(d1, h) if p in _HARD]
            lord = SIGN_LORD.get(_sign_n_from(lagna, h))
            if _house_of(lord, d1) in TROUBLE_HOUSES and _house_of(lord, d1) != h:
                hard = hard + [f"{lord} (lord displaced)"]
            if hard:
                out[h] = hard
        return out
    except Exception:
        return {}


def _connected(chart_data: dict, lord: Optional[str]) -> set:
    """Trouble houses `lord` rules or occupies."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    lagna = (cd.get("lagna") or {}).get("sign")
    if not lord or not lagna:
        return set()
    hs = {h for h in TROUBLE_HOUSES if SIGN_LORD.get(_sign_n_from(lagna, h)) == lord}
    occ = _house_of(lord, d1)
    if occ in TROUBLE_HOUSES:
        hs.add(occ)
    return hs


def _transit_house(chart_data: dict, planet: str, on: Optional[str] = None) -> Optional[int]:
    """House (from lagna) a planet transits today, or None if unavailable."""
    try:
        from antar_engine.double_transit import SIGN_INDEX, sidereal_sign_indices
        lag = (chart_data.get("lagna") or {})
        li = lag.get("sign_index")
        li = li % 12 if isinstance(li, int) else SIGN_INDEX.get(lag.get("sign"))
        if li is None:
            return None
        day = _date.fromisoformat((on or _date.today().isoformat())[:10])
        si = sidereal_sign_indices(day, (planet,)).get(planet)
        return None if si is None else (si - li) % 12 + 1
    except Exception:
        return None


def legal_caution(chart_data: dict, dashas: dict, today: Optional[str] = None,
                  transit_house_fn=None) -> dict:
    """Proactive caution read. Returns {tier: none|watch|caution|high, imminent, trigger,
    linked_houses[], window{start,end}|None}. Never raises.
    'caution' = MD+AD both link AND a natal-pressured house is among the linked houses (or the
    pratyantar links with a hard-planet trigger); 'high' = MD+AD+PD all link with the natal meet;
    'watch' = a chain link without the natal meet."""
    quiet = {"tier": "none", "imminent": False, "trigger": False, "linked_houses": [], "window": None}
    try:
        chain = current_chain(dashas, today)
        if not (chain["md"] and chain["ad"]):
            return quiet
        conn = {k: (_connected(chart_data, v["lord"]) if v else set()) for k, v in chain.items()}
        nat = natal_pressure(chart_data)
        chain_houses = set().union(*conn.values())
        if not chain_houses:
            return quiet
        linked = sorted(h for h in nat if h in chain_houses)
        md_ad = bool(conn["md"] and conn["ad"])
        pd_on = bool(conn["pd"])
        trigger = any((chain[k] or {}).get("lord") in _HARD for k in ("ad", "pd", "sd"))
        if md_ad and linked and pd_on:
            tier = "high"
        elif linked and (md_ad or (pd_on and trigger and (conn["md"] or conn["ad"]))):
            tier = "caution"
        else:
            tier = "watch"
        imminent = False
        if tier in ("caution", "high"):
            fn = transit_house_fn or (lambda p: _transit_house(chart_data, p, today))
            probe = (chain["sd"] or chain["pd"] or {}).get("lord")
            imminent = bool(probe and fn(probe) in TROUBLE_HOUSES)
        win = chain["pd"] or chain["ad"]
        return {"tier": tier, "imminent": imminent, "trigger": trigger, "linked_houses": linked,
                "window": ({"start": win["start"], "end": win["end"]} if win else None)}
    except Exception:
        return quiet


_CAUTION = {
    "en": "A word of caution before it matters: the present stretch is one to be careful in around legal and official matters. Keep everything above-board, read and keep copies of what you sign, meet every deadline, and bring in qualified counsel early rather than late. This is a caution to prepare, not a forecast.",
    "es": "Una palabra de precaución antes de que importe: la etapa actual pide cuidado en asuntos legales y oficiales. Mantén todo en regla, lee y conserva copia de lo que firmas, cumple cada plazo y consulta a un profesional calificado pronto, no tarde. Es una precaución para prepararte, no un pronóstico.",
    "pt": "Uma palavra de cautela antes que importe: a fase atual pede cuidado em assuntos legais e oficiais. Mantenha tudo em ordem, leia e guarde cópia do que assina, cumpra todos os prazos e procure um profissional qualificado cedo, não tarde. É uma cautela para se preparar, não uma previsão.",
}
_CAUTION_NOW = {
    "en": " The next few weeks especially — double-check anything with legal weight before you act on it.",
    "es": " Las próximas semanas en especial — revisa dos veces cualquier cosa con peso legal antes de actuar.",
    "pt": " As próximas semanas em especial — confira duas vezes qualquer coisa com peso legal antes de agir.",
}


def caution_note(caution: Optional[dict], language: str = "en") -> str:
    """The proactive heads-up sentence(s), or '' unless tier is caution/high."""
    if not caution or caution.get("tier") not in ("caution", "high"):
        return ""
    L = _lang(language)
    return _CAUTION[L] + (_CAUTION_NOW[L] if caution.get("imminent") else "")
