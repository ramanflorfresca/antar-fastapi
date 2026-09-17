"""
antar_engine/career_change.py

Deterministic CAREER / BUSINESS-CHANGE engine — the WHEN of a pivot. Answers:
  • TIMING — when a career change, job move, business pivot, or a shift in
    direction is likely, via the shared multi-system convergence with the
    Lal-Kitab varshphal weighted HEAVILY (owner: most accurate yearly). The
    signature the owner named: Ketu in transit / the varshphal 10th, plus the
    10th (career), 7th (business/partnership), 3rd (own initiative / new
    direction), 6th (job/service), 11th (gains/network), 8th (sudden upheaval).
  • NATURE — CHOSEN (a venture you initiate, a step up, a new field) vs FORCED
    (a role ending, a restructure, being pushed out), and WHICH kind of change
    (own business vs a new job vs a status shift), from the activating lords.

This is a WHEN + NATURE reading only — descriptive timing, never a magnitude or
outcome claim (validate-first: business-vertical/when-to-build success is a
falsified study; we do NOT predict whether the change succeeds). Karakas: Ketu
(detachment/the pull away from the current path — primary), Rahu (ambition/new
& unconventional field), Saturn (restructure/karma/permanence), Sun (status/
authority), Mercury (commerce/business). LLM narrates only. v1.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGN_LORD, _sign_n_from
from antar_engine.relationships import _house_of
from antar_engine.domain_timing import domain_convergence

CAREER_CHANGE_SPEC = {
    "noun": "a career change",
    "houses": [10, 3, 7, 6, 11, 8],
    "activator_houses": [10, 3, 7, 6],
    "karakas": ["Ketu", "Rahu", "Saturn", "Sun", "Mercury"],
    "varsh_houses": [10, 6],       # LK varshphal 10th/6th lit = a change-of-work year
    "malefic_varsh": True,         # a malefic/node (esp. Ketu) in the varshphal 10th = the churn
    "varsh_weight": 1.8,           # LK varshphal weighted heavily (owner directive)
    "transit_grahas": ["Saturn", "Ketu", "Rahu", "Jupiter", "Mars"],
    "transit_houses": [10, 3, 7, 6, 1],
    "chara_weight": 1.0,
    "min_score": 2.0,
}


def _career_change_nature(chart_data, lords) -> list:
    """Which KIND of change — own venture vs new job vs status shift vs a break —
    from the lords activating the window. Mirrors residence's _residence_nature."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    lagna = ((cd.get("lagna") or {}).get("sign"))
    if not lagna:
        return []
    tenth_lord = SIGN_LORD.get(_sign_n_from(lagna, 10))
    third_lord = SIGN_LORD.get(_sign_n_from(lagna, 3))
    seventh_lord = SIGN_LORD.get(_sign_n_from(lagna, 7))
    sixth_lord = SIGN_LORD.get(_sign_n_from(lagna, 6))
    eleventh_lord = SIGN_LORD.get(_sign_n_from(lagna, 11))
    out, seen = [], set()

    def _push(t):
        if t and t not in seen:
            seen.add(t); out.append(t)

    for lord in lords:
        if not lord:
            continue
        h = _house_of(lord, d1)
        if lord == "Ketu" or h == 8:
            _push("a break from your current line of work — dissatisfaction pulling "
                  "you toward something new")
        if lord == "Rahu" or lord == eleventh_lord or h == 11:
            _push("a leap into a new, bigger or unconventional field")
        if lord == third_lord or h == 3:
            _push("striking out on your own — a new venture, a side path, or self-effort")
        if lord == seventh_lord or h == 7:
            _push("a shift toward business, partnership or self-employment")
        if lord == sixth_lord or h == 6:
            _push("a change of job or service — a new employer or role")
        if lord == "Saturn" or lord == tenth_lord:
            _push("a structural restructure of your career — earned and gradual, not sudden")
        if lord == "Sun":
            _push("a change in status or authority — a repositioning at the top")
    return out[:2]


def career_change_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                         today: Optional[str] = None) -> dict:
    """When a career/business change is likely — multi-system convergence
    (varshphal-heavy). Returns {available, windows[], best, summary, nature}.
    Descriptive WHEN + NATURE only; no magnitude/outcome claim."""
    res = domain_convergence(chart_data, dashas, CAREER_CHANGE_SPEC,
                             birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    for w in res.get("windows", []):
        parts = [x.strip() for x in w["label"].replace("–", "-").split("-")]
        nat = _career_change_nature(chart_data, parts)
        # FORCED / SUDDEN change — a hard graha (Ketu/Saturn/Mars) pressing the 10th,
        # or anything striking the 8th, reads as a role ending, a restructure, or
        # being pushed out rather than a chosen pivot.
        hits = w.get("transit_hits") or []
        forced = any((g in ("Ketu", "Saturn", "Mars") and h == 10) or h == 8 for g, h in hits)
        if forced:
            nat = ["a forced or sudden change — a role ending, a restructure, or being "
                   "pushed off the current path"] + nat
        w["nature"] = nat[:2]
        w["forced"] = bool(forced)
    best = res.get("best")
    if best:
        nat = best.get("nature") or []
        res["summary"] = (f"The most likely window for a career change is around "
                          f"{best.get('year', best['start'][:4])} — {len(best['systems'])} "
                          f"systems agree" + (f", pointing to {nat[0]}." if nat else "."))
        res["nature"] = nat
    else:
        res["summary"] = ("No sharply-converging career-change window ahead — no structural "
                          "pivot flagged. Your current path stays steady.")
        res["nature"] = []
    return res


def career_change_verdict(cc_result: dict, language: str = "en") -> dict:
    """Localized chapter verdict for a career/business-change question — a WHEN +
    NATURE read, never a success/outcome claim (validate-first). Returns
    {available, line, the_move, window_range, has_window}. Band is intentionally
    omitted: this is timing, not a good/bad verdict."""
    lang = (language or "en").split("-")[0]
    if not isinstance(cc_result, dict) or not cc_result.get("available"):
        return {"available": False}
    best = cc_result.get("best")
    nat = (cc_result.get("nature") or [None])[0]

    if best:
        year = best.get("year") or (best.get("start") or "")[:4]
        forced = bool(best.get("forced"))
        wr = {"en": f"around {year}", "es": f"alrededor de {year}",
              "pt": f"por volta de {year}"}.get(lang, f"around {year}")
        if lang == "es":
            line = f"El momento más probable para un cambio de carrera es {wr}."
            if nat:
                line += f" La señal apunta a {nat}."
            move = ("Prepara el terreno ahora — habilidades, red de contactos, ahorros; "
                    "no fuerces la salida antes de tiempo. La ventana se abre "
                    f"{wr}.")
        elif lang == "pt":
            line = f"O momento mais provável para uma mudança de carreira é {wr}."
            if nat:
                line += f" O sinal aponta para {nat}."
            move = ("Prepare o terreno agora — habilidades, rede de contatos, reservas; "
                    "não force a saída cedo demais. A janela se abre "
                    f"{wr}.")
        else:
            line = f"The most likely window for a career change is {wr}."
            if nat:
                line += f" The signal points to {nat}."
            move = ("Lay the groundwork now — skills, network, a runway of savings; don't "
                    f"force the exit early. The window opens {wr}.")
        return {"available": True, "line": line, "the_move": move,
                "window_range": wr, "has_window": True}

    # No converging window — an honest "steady for now" answer.
    if lang == "es":
        line = ("No hay una ventana clara de cambio de carrera por delante — tu camino "
                "actual se lee estable por ahora.")
        move = ("No hay presión estructural para cambiar. Consolida donde estás; "
                "reevalúa cuando se abra una ventana.")
    elif lang == "pt":
        line = ("Não há uma janela clara de mudança de carreira à frente — seu caminho "
                "atual se lê estável por enquanto.")
        move = ("Não há pressão estrutural para mudar. Consolide onde está; "
                "reavalie quando uma janela se abrir.")
    else:
        line = ("No clear career-change window is flagging ahead — your current path "
                "reads steady for now.")
        move = ("There's no structural pressure to switch. Consolidate where you are; "
                "reassess when a window opens.")
    return {"available": True, "line": line, "the_move": move,
            "window_range": None, "has_window": False}
