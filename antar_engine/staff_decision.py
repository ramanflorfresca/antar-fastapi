"""[staff-decision 2026-10-11] "Should I fire someone?" — an explainable lean, not a window.

Owner ruling: a firing question is a decision about HOW, not an event with a date. The answer is one of four leans, and every lean says why:

  coach      they fit the role and take direction -> the problem is likelier expectations than ability
  reassign   right person, wrong seat            -> offer the work their chart is strongest at
  exit       a stretch for the role AND they push for their own authority -> more coaching is unlikely to change it (in writing, with advice)
  document   no reading of the person            -> decide from the record; nothing here says the person is the problem

Two inputs, both deterministic:
  YOUR SIDE  the 6th house = staff, service and workplace conflict. Its lord plus Saturn (the karaka of workers), by dignity and house, say how CLEANLY you
             handle staff conflict: clean / careful / messy. It never changes the lean — it changes the PROCESS (messy = take advice before any exit).
  THEIR SIDE only when the person is a saved employee connection: role fit (when the role is known) and direction-taking, from authority_read.
             exit is only ever reached on evidence (weak fit and not easy to direct); without a reading the lean is "document".

Pure, en + es, no dates, no windows. v1 thresholds, to calibrate on real teams."""
from __future__ import annotations

from typing import List, Optional

from antar_engine import partner_roles as P
from antar_engine.d10_career import SIGN_LORD, SIGNS

_TX = {
    "en": {
        "lean": {"coach": "Coach first", "reassign": "Reassign", "exit": "Exit, in writing", "document": "Document first"},
        "head": "Lean: {lean}.",
        "why_coach": "{who} fits the role and {dir}, so the problem is likelier expectations than ability.",
        "dir_easy": "takes direction well", "dir_scope": "does best with a clear scope", "dir_own": "wants a defined area to own",
        "why_reassign": "{who} looks better suited to other work: strongest in {lanes}. Offer that seat before ending anything.",
        "why_reassign_dir": "{who} pushes for their own authority and the role is a workable fit at best, so a defined area of their own is the better test than more tasks.",
        "why_exit": "The role is a stretch for {who} and they push for their own authority, so more coaching is unlikely to change it.",
        "why_exit_scope": "The role is a stretch for {who} even with a clear scope, so more coaching is unlikely to change it.",
        "why_document": "Nothing here says whether the person or the setup is the problem, so decide from the record, not from timing: what was expected, what happened, and on which dates.",
        "h_clean": "Staff conflict tends to stay clean on your side: you can act once the record exists.",
        "h_careful": "Handle it with care: bring a second person, such as an advisor or HR, into any exit conversation.",
        "h_messy": "Staff conflict tends to turn messy on your side: take advice before any exit and keep every step in writing.",
        "works": "It works if {w}.", "breaks": "It breaks if {b}.",
        "next_coach": "Write three specific things they must change, with a date, and review it in two weeks.",
        "next_reassign": "Write down the work they are strongest at ({lanes}) and offer that seat for a trial period.",
        "next_exit": "Write the record: what was expected, what happened, and on which dates. Take advice, then decide.",
        "basis6": "How you handle staff conflict at work: {lvl}.",
        "lvl_clean": "a strength of yours", "lvl_careful": "something to handle with care", "lvl_messy": "where things tend to turn messy",
        "basis_fit": "{who}'s read: {fit}{dir}.",
        "fit_strong": "a strong fit for the role", "fit_ok": "a workable fit for the role", "fit_weak": "a stretch for the role", "fit_none": "role not specified",
        "fit_dir": ", {dir}",
    },
    "es": {
        "lean": {"coach": "Acompañar primero", "reassign": "Reasignar", "exit": "Salida, por escrito", "document": "Documentar primero"},
        "head": "Inclinación: {lean}.",
        "why_coach": "{who} encaja en el puesto y {dir}, así que el problema es más probablemente de expectativas que de capacidad.",
        "dir_easy": "recibe bien la dirección", "dir_scope": "rinde mejor con un alcance claro", "dir_own": "quiere un área definida que llevar",
        "why_reassign": "{who} parece más indicada o indicado para otro trabajo: es más fuerte en {lanes}. Ofrezcan ese puesto antes de terminar nada.",
        "why_reassign_dir": "{who} busca su propia autoridad y el puesto es, como mucho, un encaje aceptable; un área propia definida es una mejor prueba que más tareas.",
        "why_exit": "El puesto es un reto para {who} y busca su propia autoridad, así que es poco probable que más acompañamiento lo cambie.",
        "why_exit_scope": "El puesto es un reto para {who} incluso con un alcance claro, así que es poco probable que más acompañamiento lo cambie.",
        "why_document": "Nada aquí dice si el problema es la persona o la situación, así que decidan desde el registro y no desde los tiempos: qué se esperaba, qué pasó y en qué fechas.",
        "h_clean": "Los conflictos con el personal tienden a mantenerse limpios de tu lado: puedes actuar cuando exista el registro.",
        "h_careful": "Hazlo con cuidado: lleva a una segunda persona, como un asesor o RR. HH., a cualquier conversación de salida.",
        "h_messy": "Los conflictos con el personal tienden a enredarse de tu lado: pide asesoría antes de cualquier salida y deja cada paso por escrito.",
        "works": "Funciona si {w}.", "breaks": "Se rompe si {b}.",
        "next_coach": "Escribe tres cosas concretas que debe cambiar, con una fecha, y revísenlo en dos semanas.",
        "next_reassign": "Anota el trabajo en el que es más fuerte ({lanes}) y ofrece ese puesto en periodo de prueba.",
        "next_exit": "Escribe el registro: qué se esperaba, qué pasó y en qué fechas. Pide asesoría y luego decide.",
        "basis6": "Cómo manejas los conflictos con el personal en el trabajo: {lvl}.",
        "lvl_clean": "una fortaleza tuya", "lvl_careful": "algo que conviene manejar con cuidado", "lvl_messy": "donde las cosas tienden a complicarse",
        "basis_fit": "Lectura de {who}: {fit}{dir}.",
        "fit_strong": "un encaje fuerte para el puesto", "fit_ok": "un encaje aceptable para el puesto", "fit_weak": "un reto para el puesto", "fit_none": "puesto sin especificar",
        "fit_dir": ", {dir}",
    },
}
_WORKS = {"en": ("the expectations were written down and missed before the decision", "the exit is made in frustration or without a written record"),
          "es": ("las expectativas se escribieron y no se cumplieron antes de decidir", "la salida se hace con frustración o sin un registro escrito")}
_PLANET_ES = {"Sun": "el Sol", "Moon": "la Luna", "Mars": "Marte", "Mercury": "Mercurio", "Jupiter": "Júpiter", "Venus": "Venus", "Saturn": "Saturno"}


def handling(chart: dict) -> Optional[dict]:
    """How cleanly the reader handles staff conflict, from the 6th-house lord and Saturn: {level, lord, house, sign, notes}. None without a usable chart."""
    try:
        planets = (chart or {}).get("planets") or {}
        lg = ((chart or {}).get("lagna") or {})
        lagna = lg.get("sign") if isinstance(lg, dict) else lg
        if lagna not in SIGNS or not planets:
            return None
        lord = SIGN_LORD[SIGNS[(SIGNS.index(lagna) + 5) % 12]]
        pl = planets.get(lord) or {}
        if not pl.get("sign"):
            return None
        s_lord = P._strength(lord, pl["sign"], pl.get("house"))
        sat = planets.get("Saturn") or {}
        s_sat = P._strength("Saturn", sat["sign"], sat.get("house")) if sat.get("sign") else s_lord
        score = (s_lord + s_sat) / 2
        level = "clean" if score >= 0.55 else "careful" if score >= 0.40 else "messy"
        from antar_engine.ask_basis import _dignity
        notes = [n for n in _dignity(lord, pl["sign"], planets) if n]
        if level == "clean" and any(n == "debilitated" or n.startswith("combust") for n in notes):
            level = "careful"                     # a weakened 6th lord never reads "clean"
        return {"level": level, "lord": lord, "house": pl.get("house"), "sign": pl["sign"], "notes": notes, "score": round(score, 3)}
    except Exception:
        return None


def lean_for(er: Optional[dict]) -> str:
    """coach | reassign | exit | document, from an authority_read of an employee connection (None -> document)."""
    if not isinstance(er, dict) or er.get("kind") != "hierarchy":
        return "document"
    fit, d = er.get("fit"), er.get("direction")
    if fit == "strong":
        return "coach"
    if fit == "ok":
        return "coach" if d in ("easy", "scope") else "reassign"
    if fit == "weak":
        return "reassign" if d == "easy" else "exit"
    # no role named: we cannot say they are a poor fit, so never an exit and never "better suited to other work" — only a clear scope (coach) or,
    # for someone who wants their own authority, a defined area of their own (reassign, worded as that)
    return "coach" if d in ("easy", "scope") else "reassign" if d == "own" else "document"


def compose(chart: dict, er: Optional[dict], name: str = "", language: str = "en") -> Optional[dict]:
    """{lean, read, next, basis, handling}. Never raises; None only when the language has no template."""
    try:
        lang = language if language in _TX else None
        if not lang:
            return None
        tx = _TX[lang]
        who = (name or "").strip() or ("la persona" if lang == "es" else "the person")
        lean = lean_for(er)
        h = handling(chart)
        nm = P._NAME[lang]
        o = (er or {}).get("other") or {}
        lanes = ", ".join(nm[l] for l in o.get("strengths", [])[:2])
        d = (er or {}).get("direction")
        fit = (er or {}).get("fit")
        if lean == "coach":
            why = tx["why_coach"].format(who=who, dir=tx["dir_" + (d if d in ("easy", "scope", "own") else "easy")])
            nxt = tx["next_coach"]
        elif lean == "reassign":
            why = (tx["why_reassign_dir"] if (d == "own" and fit in ("ok", None)) else tx["why_reassign"]).format(who=who, lanes=lanes or "?")
            nxt = tx["next_reassign"].format(lanes=lanes or "?")
        elif lean == "exit":
            why = (tx["why_exit_scope"] if d == "scope" else tx["why_exit"]).format(who=who)
            nxt = tx["next_exit"]
        else:
            why, nxt = tx["why_document"], None
        parts = [tx["head"].format(lean=tx["lean"][lean]), why]
        if h:
            parts.append(tx["h_" + h["level"]])
        w, b = _WORKS[lang]
        parts += [tx["works"].format(w=w), tx["breaks"].format(b=b)]
        basis = []
        if h:
            basis.append(tx["basis6"].format(lvl=tx["lvl_" + h["level"]]))      # plain: no house number, no planet name
        if er and lean != "document":
            fit_t = tx["fit_" + (fit if fit in ("strong", "ok", "weak") else "none")]
            dir_t = tx["fit_dir"].format(dir=tx["dir_" + d]) if d in ("easy", "scope", "own") else ""
            basis.append(tx["basis_fit"].format(who=who, fit=fit_t, dir=dir_t))
        return {"lean": lean, "read": " ".join(parts), "next": nxt, "basis": " ".join(basis), "handling": (h or {}).get("level")}
    except Exception as e:
        print(f"[staff-decision] failed: {type(e).__name__}: {e}")
        return None
