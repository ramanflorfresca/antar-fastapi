"""[authority-read 2026-10-11] Employee / boss / advisor connections: AUTHORITY AND FIT, not a lane split.

A cofounder pair splits lanes between equals (partner_roles). A reporting line asks something else, and each of the three asks it differently:

  employee  (someone reporting to me)  — is this person right for the role, how do they take direction, how should I manage them
  boss      (my manager)               — what do they value, how do they lead, how do I work with them
  advisor   (mentor / consultant)      — what to use them for, what NOT to rely on them for

Built from the SAME six-lane scoring as partner_roles (D-1 + D-10 + Jaimini AmK/AK + Vimshottari/Chara timing; stored karakas, live Chara period),
reduced to the other person's strongest lanes, their thin lanes, an authority STYLE and — for an employee — a direction-taking read and, when the
role is known, a fit against it. Both systems must agree on their top lane or it is reported as contested. Deterministic, no LLM (the connection
card phrases it). v1 thresholds, to calibrate on real reporting lines. en + es."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from antar_engine import partner_roles as P

KINDS = ("employee", "boss", "advisor")
_ALIAS = {"employee": "employee", "boss": "boss", "boss-or-manager": "boss", "manager": "boss", "advisor": "advisor", "mentor": "advisor"}

# the role the reader is hiring for / the other person holds -> the lanes it draws on
ROLE_LANES = {"sales": ("sales",), "marketing": ("creative", "sales"), "social": ("creative",), "operations": ("ops",),
              "finance": ("finance",), "cfo": ("finance",), "ceo": ("vision",), "engineering": ("tech",), "people": ("ops", "creative"),
              "legal": ("ops", "finance"), "managerial": ("vision", "ops")}

_NAME = {"en": P._NAME["en"], "es": P._NAME["es"]}
_STYLE = {
    "en": {"structured": "structured and process-driven", "decisive": "decisive and hands-on", "guiding": "guiding and big-picture",
           "fast": "fast-moving and changeable"},
    "es": {"structured": "estructurado y orientado al proceso", "decisive": "decidido y de mano firme", "guiding": "orientador y de visión amplia",
           "fast": "ágil y cambiante"},
}
# how to work with each authority style (a plain instruction, not a trait)
_HOW = {
    "en": {"structured": "bring written plans and dates; they trust what is documented", "decisive": "come with a recommendation, not a menu of options",
           "guiding": "ask for their view on direction and keep the details to yourself", "fast": "confirm decisions in writing — they can change their mind"},
    "es": {"structured": "lleva planes y fechas por escrito; confía en lo documentado", "decisive": "llega con una recomendación, no con un menú de opciones",
           "guiding": "pide su visión de la dirección y resuelve tú los detalles", "fast": "confirma las decisiones por escrito: pueden cambiar de opinión"},
}
_TX = {
    "en": {
        "t_employee": "How to manage {b}", "t_boss": "How to work with {b}", "t_advisor": "How to use {b}",
        "strong": "{b} is strongest in {lanes}.", "thin": "Thinnest in {lanes}.",
        "fit_strong": "For the {role} role that is a strong fit.", "fit_ok": "For the {role} role it is a workable fit, not their strongest ground.",
        "fit_weak": "For the {role} role it is a stretch: it sits among their thinner lanes.",
        "style": "Their authority style is {style}: {how}.",
        "dir_easy": "They take direction well: set the goal and review the result.",
        "dir_scope": "They do best with a clear scope: say exactly what they own and what needs your sign-off.",
        "dir_own": "They push for their own authority: give them a lane they fully own, in writing, rather than tasks.",
        "value": "They value {lanes}: lead with it when you ask for something.",
        "add": "You add where they are thin: {lanes}. Offer that, not a copy of what they already do.",
        "use": "Use {b} for {lanes}.", "not": "Do not lean on {b} for {lanes}.",
        "dep": "Keep the relationship advisory: they are not built to carry execution for you.",
        "contested": "The two systems point to different strongest lanes for them, so treat their strongest area as open.",
        "now": "Right now {b} is switched on for {lanes}.",
        "close": "This is a read of fit and style; confirm roles and expectations in writing.",
    },
    "es": {
        "t_employee": "Cómo dirigir a {b}", "t_boss": "Cómo trabajar con {b}", "t_advisor": "Cómo aprovechar a {b}",
        "strong": "{b} es más fuerte en {lanes}.", "thin": "Más débil en {lanes}.",
        "fit_strong": "Para el puesto de {role} es un encaje fuerte.", "fit_ok": "Para el puesto de {role} es un encaje aceptable, no su terreno más fuerte.",
        "fit_weak": "Para el puesto de {role} es un reto: queda entre sus áreas más débiles.",
        "style": "Su estilo de autoridad es {style}: {how}.",
        "dir_easy": "Recibe bien la dirección: fija la meta y revisa el resultado.",
        "dir_scope": "Rinde mejor con un alcance claro: di exactamente qué le toca y qué necesita tu aprobación.",
        "dir_own": "Busca su propia autoridad: dale un área que lleve por completo, por escrito, en lugar de tareas sueltas.",
        "value": "Valora {lanes}: empieza por ahí cuando pidas algo.",
        "add": "Tú aportas donde son más débiles: {lanes}. Ofrece eso, no una copia de lo que ya hacen.",
        "use": "Aprovecha a {b} para {lanes}.", "not": "No te apoyes en {b} para {lanes}.",
        "dep": "Mantengan la relación como asesoría: no están hechos para cargar la ejecución por ti.",
        "contested": "Los dos sistemas señalan áreas más fuertes distintas para esa persona, así que trata su área más fuerte como abierta.",
        "now": "Ahora mismo {b} está activado para {lanes}.",
        "close": "Es una lectura de encaje y estilo; confirmen los roles y expectativas por escrito.",
    },
}
ROLE_ES = {"sales": "ventas", "marketing": "marketing", "social": "redes sociales", "operations": "operaciones", "finance": "finanzas",
           "cfo": "dirección financiera", "ceo": "dirección general", "engineering": "ingeniería", "people": "personas",
           "legal": "legal", "managerial": "gestión"}


def _strengths_of(chart: dict, planets: tuple) -> float:
    pl, d10 = (chart or {}).get("planets") or {}, P._d10(chart)["planets"]
    vals = []
    for p in planets:
        a, b = pl.get(p) or {}, d10.get(p) or {}
        s1 = P._strength(p, a["sign"], a.get("house")) if a.get("sign") else None
        s10 = P._strength(p, b["sign"], b.get("house")) if b.get("sign") else s1
        if s1 is not None:
            vals.append((s1 + (s10 if s10 is not None else s1)) / 2)
    return sum(vals) / len(vals) if vals else 0.5


def authority_style(chart: dict, amk: Optional[str] = None) -> str:
    """structured (Saturn) | decisive (Sun, Mars) | guiding (Jupiter) | fast (Rahu, Mercury) — the highest, the career karaka's style +0.1."""
    sc = {"structured": _strengths_of(chart, ("Saturn",)), "decisive": _strengths_of(chart, ("Sun", "Mars")),
          "guiding": _strengths_of(chart, ("Jupiter",)), "fast": _strengths_of(chart, ("Rahu", "Mercury"))}
    bump = {"Saturn": "structured", "Sun": "decisive", "Mars": "decisive", "Jupiter": "guiding", "Rahu": "fast", "Mercury": "fast"}.get(amk or "")
    if bump:
        sc[bump] += 0.1
    return max(sc, key=lambda k: sc[k])


def direction_level(chart: dict) -> str:
    """easy | scope | own — how someone takes direction (discipline + learning vs wanting their own authority)."""
    d = (0.45 * _strengths_of(chart, ("Saturn",)) + 0.25 * _strengths_of(chart, ("Mercury",))
         + 0.30 * (1 - _strengths_of(chart, ("Sun", "Mars"))))
    return "easy" if d >= 0.50 else "scope" if d >= 0.38 else "own"


def compare(kind: str, chart_a: dict, dashas_a: dict, chart_b: dict, dashas_b: dict, name_b: str = "", lang: str = "en",
            today: Optional[datetime] = None, jaimini_a: Optional[dict] = None, jaimini_b: Optional[dict] = None,
            role: Optional[str] = None) -> Optional[dict]:
    """The authority-and-fit read for a reporting line. None when the type is not one of the three or a chart is unusable. Never raises."""
    try:
        kind = _ALIAS.get((kind or "").lower())
        lang = lang if lang in _TX else "en"
        if kind not in KINDS or not ((chart_a or {}).get("planets") and (chart_b or {}).get("planets")):
            return None
        tx, nm = _TX[lang], _NAME[lang]
        a, b = P.score_person(chart_a, dashas_a, today, jaimini_a), P.score_person(chart_b, dashas_b, today, jaimini_b)
        order_b = [l for l, _ in sorted(b["scores"].items(), key=lambda kv: -kv[1])]
        order_a = [l for l, _ in sorted(a["scores"].items(), key=lambda kv: -kv[1])]
        top_b, thin_b = order_b[:2], order_b[-2:]
        join = lambda xs: (", ".join(xs[:-1]) + (" y " if lang == "es" else " and ") + xs[-1]) if len(xs) > 1 else "".join(xs)
        lanes = lambda ls: join([nm[l] for l in ls])
        who = (name_b or "").strip() or ("la otra persona" if lang == "es" else "the other person")
        # both systems should name the same strongest lane for them — a REAL disagreement is each system's top lane sitting outside the other's
        # top three (comparing only the single top lane flags nearly everyone: the two systems rarely order the first two identically)
        rank = lambda sysname: [l for l, _ in sorted(((l, b[sysname][l]) for l in P.LANES if b[sysname].get(l) is not None), key=lambda kv: -kv[1])]
        pr, jr = rank("parashari"), rank("jaimini")
        contested = bool(pr and jr and pr[0] not in jr[:3] and jr[0] not in pr[:3])
        style_b = authority_style(chart_b, b["amk"])
        lines = [tx["t_" + kind].format(b=who), "", tx["strong"].format(b=who, lanes=lanes(top_b)) + " " + tx["thin"].format(lanes=lanes(thin_b))]
        out = {"version": "authority-read-1", "kind": "hierarchy", "type": kind, "language": lang,
               "other": {"strengths": top_b, "thin": thin_b, "style": style_b, "scores": b["scores"], "amk": b["amk"], "ak": b["ak"]},
               "you": {"strengths": order_a[:2], "scores": a["scores"]}, "contested_top": contested, "role": role or None}
        if kind == "employee":
            if role in ROLE_LANES:
                rl = ROLE_LANES[role]
                rank = min(order_b.index(l) for l in rl)
                level = "strong" if rank < 2 else "weak" if rank >= 4 else "ok"
                rn = role if lang == "en" else ROLE_ES.get(role, role)
                lines.append(tx["fit_" + level].format(role=rn))
                out["fit"] = level
            d = direction_level(chart_b)
            out["direction"] = d
            lines.append(tx["dir_" + {"easy": "easy", "scope": "scope", "own": "own"}[d]])
            lines.append(tx["style"].format(style=_STYLE[lang][style_b], how=_HOW[lang][style_b]))
        elif kind == "boss":
            lines.append(tx["value"].format(lanes=lanes(top_b[:1])))
            lines.append(tx["style"].format(style=_STYLE[lang][style_b], how=_HOW[lang][style_b]))
            add = [l for l in order_a[:3] if l in thin_b or l not in top_b][:2]
            if add:
                lines.append(tx["add"].format(lanes=lanes(add)))
                out["you"]["add"] = add
        else:  # advisor
            lines.append(tx["use"].format(b=who, lanes=lanes(top_b)))
            lines.append(tx["not"].format(b=who, lanes=lanes(thin_b)))
            lines.append(tx["dep"])
        if contested:
            lines.append(tx["contested"])
        parts_b = sorted(b["parts"].items(), key=lambda kv: -kv[1]["dasha"])
        now = [l for l, v in parts_b if v["dasha"] > 0][:2]
        if now:
            lines.append(tx["now"].format(b=who, lanes=lanes(now)))
        lines.append(tx["close"])
        out["text"] = "\n".join(lines)
        return out
    except Exception as e:
        print(f"[authority-read] failed: {type(e).__name__}: {e}")
        return None
