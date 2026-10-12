"""[work-profile 2026-10-12] What the person actually does — so Business / Career / Money speak to THEIR work, not to "work" in general.

Framed as DKP (desha-kala-patra): WHO (role: running a business, a job, freelance, studying, in transition), WHAT (one line, their words), WHEN (the stage of the work), WHERE (the market).
The chart still decides timing and approach (the engines); this only decides what the move is ABOUT. It never claims the chart predicts which industry succeeds (that study was negative).

Storage: table `work_profiles` (one row per chart; DDL in Antar.world/sql_work_profiles.sql). Fail-open: with no table / no row the pages behave exactly as before.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

TOPICS = ("business", "career", "money")
ROLES = ("running_business", "job", "freelance", "studying", "in_transition")
STAGES = ("idea", "building", "launched", "revenue", "scaling")
_TEXT_MAX = 120

_LABEL = {
    "en": {"role": "What best describes your work right now?", "what": "What is it, in one line?", "stage": "Where is it today?", "market": "Who is it for, and where?",
           "ph_what": "e.g. AI agents for small businesses", "ph_market": "e.g. small shops in the US and LATAM",
           "running_business": "Running a business", "job": "Working a job", "freelance": "Freelance or consulting", "studying": "Studying", "in_transition": "Between things",
           "idea": "An idea", "building": "Building it", "launched": "Launched", "revenue": "Earning revenue", "scaling": "Scaling"},
    "es": {"role": "¿Qué describe mejor tu trabajo ahora?", "what": "¿Qué es, en una línea?", "stage": "¿En qué punto está hoy?", "market": "¿Para quién es y dónde?",
           "ph_what": "p. ej. agentes de IA para pequeños negocios", "ph_market": "p. ej. tiendas pequeñas en EE. UU. y LATAM",
           "running_business": "Dirijo un negocio", "job": "Tengo un empleo", "freelance": "Freelance o consultoría", "studying": "Estudio", "in_transition": "Entre cosas",
           "idea": "Una idea", "building": "Construyéndolo", "launched": "Lanzado", "revenue": "Con ingresos", "scaling": "Escalando"},
}

# (role, stage-or-None, mode) -> (en, es); {what} is the person's own words. mode: open = the topic's window is open, care = hold / steady.
_MOVE = {
    ("running_business", "idea", "open"): ("Talk to three people who would pay for {what} before you build more.", "Habla con tres personas que pagarían por {what} antes de construir más."),
    ("running_business", "idea", "care"): ("Sharpen the one-sentence pitch for {what}; don't commit money yet.", "Afina la frase que explica {what}; no comprometas dinero todavía."),
    ("running_business", "building", "open"): ("Ship the one piece of {what} a customer would touch first.", "Entrega la pieza de {what} que un cliente tocaría primero."),
    ("running_business", "building", "care"): ("Tidy the plan and the numbers for {what}; commit nothing new.", "Ordena el plan y los números de {what}; no te comprometas con nada nuevo."),
    ("running_business", "launched", "open"): ("Put {what} in front of ten more real prospects this week.", "Presenta {what} a diez prospectos reales más esta semana."),
    ("running_business", "launched", "care"): ("Follow up the leads you already have for {what}; don't add new channels.", "Da seguimiento a los contactos que ya tienes para {what}; no abras canales nuevos."),
    ("running_business", "revenue", "open"): ("Sign the next client or raise the price on {what}.", "Cierra el siguiente cliente o sube el precio de {what}."),
    ("running_business", "revenue", "care"): ("Review costs and churn on {what}; protect what is already earning.", "Revisa costos y bajas en {what}; protege lo que ya genera ingresos."),
    ("running_business", "scaling", "open"): ("Hire or delegate the one thing that caps {what}.", "Contrata o delega lo único que limita {what}."),
    ("running_business", "scaling", "care"): ("Hold new hiring; fix the process that breaks first in {what}.", "Pausa nuevas contrataciones; arregla el proceso que falla primero en {what}."),
    ("running_business", None, "open"): ("Pick the one customer conversation for {what} that moves it forward and have it.", "Elige la conversación con un cliente de {what} que más avanza y tenla."),
    ("running_business", None, "care"): ("Use the quiet to tidy numbers and notes for {what} rather than start something new.", "Aprovecha la calma para ordenar números y notas de {what} en vez de empezar algo nuevo."),
    ("job", None, "open"): ("Write down what you have delivered in {what} and ask for the next step.", "Anota lo que has entregado en {what} y pide el siguiente paso."),
    ("job", None, "care"): ("Keep your record clean in {what}; don't force a decision.", "Mantén tu historial limpio en {what}; no fuerces una decisión."),
    ("freelance", None, "open"): ("Pitch two past clients for more {what} work.", "Propón a dos clientes anteriores más trabajo de {what}."),
    ("freelance", None, "care"): ("Finish and invoice the open {what} work; take no new scope.", "Termina y factura el trabajo abierto de {what}; no tomes alcance nuevo."),
    ("studying", None, "open"): ("Apply for the one opening in {what} you've been circling.", "Postula a la oportunidad de {what} que has estado rondando."),
    ("studying", None, "care"): ("Consolidate what you've learned in {what}; hold the big application.", "Consolida lo aprendido en {what}; pospón la postulación grande."),
    ("in_transition", None, "open"): ("Reach out to two people already working in {what}.", "Escribe a dos personas que ya trabajan en {what}."),
    ("in_transition", None, "care"): ("Get clear on the next role in {what}; don't take the first offer.", "Define el siguiente rol en {what}; no aceptes la primera oferta."),
}
_CAREER_FOUNDER = {
    "open": ("Take one visible step as the lead on {what} this week: a talk, a post, or a direct pitch.", "Da un paso visible como líder de {what} esta semana: una charla, una publicación o una propuesta directa."),
    "care": ("Keep your head down on {what}: do one piece of work you would be proud of and show it later.", "Mantén un perfil bajo en {what}: haz una pieza de trabajo de la que te sientas orgulloso y muéstrala después."),
}
_MONEY = {   # money pages talk about the money side of the same work
    "open": ("Review pricing and collections on {what}.", "Revisa precios y cobros de {what}."),
    "care": ("Hold new spending on {what}; re-read the terms before you commit.", "Pausa gastos nuevos en {what}; relee las condiciones antes de comprometerte."),
}


def _clean(v: Any, vocab=None) -> Optional[str]:
    s = str(v or "").strip()
    if not s:
        return None
    if vocab is not None:
        s = s.lower().replace(" ", "_")
        return s if s in vocab else None
    return " ".join(s.split())[:_TEXT_MAX]


def get(sb, chart_id: str) -> Dict[str, Any]:
    """The saved profile merged with what we already know (career_stage on the chart, the latest 'still going' venture). {} when nothing is known. Never raises."""
    out: Dict[str, Any] = {}
    try:
        r = sb.table("work_profiles").select("*").eq("chart_id", chart_id).limit(1).execute().data
        if r:
            out = {k: r[0].get(k) for k in ("role", "what", "stage", "market") if r[0].get(k)}
    except Exception:
        pass
    try:
        if not out.get("role"):
            c = sb.table("charts").select("career_stage,life_work").eq("id", chart_id).limit(1).execute().data
            if c:
                from antar_engine.life_context import get_life_context
                lc = get_life_context(chart_record=c[0]) or {}
                cs = lc.get("career_stage")
                role = {"running_business": "running_business", "job": "job", "studying": "studying", "in_transition": "in_transition"}.get(cs)
                if role:
                    out["role"] = role
    except Exception:
        pass
    try:
        if not out.get("what"):
            v = (sb.table("ventures").select("label,outcome").eq("chart_id", chart_id).execute().data) or []
            going = [x for x in v if (x.get("outcome") or "") in ("still going", "ongoing", "active", "running")]
            if going and going[-1].get("label"):
                out["what"] = _clean(going[-1]["label"])
    except Exception:
        pass
    return out


def save(sb, chart_id: str, user_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + upsert the answered fields only. Returns the merged profile; raises RuntimeError('storage') when the table is missing."""
    row = {"chart_id": chart_id, "user_id": user_id}
    for k, vocab in (("role", ROLES), ("stage", STAGES)):
        v = _clean(fields.get(k), vocab)
        if v:
            row[k] = v
    for k in ("what", "market"):
        v = _clean(fields.get(k))
        if v:
            row[k] = v
    if len(row) <= 2:
        return get(sb, chart_id)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        sb.table("work_profiles").upsert(row, on_conflict="chart_id").execute()
    except Exception as e:
        raise RuntimeError("storage") from e
    return get(sb, chart_id)


def questions(profile: Dict[str, Any], topic: str, lang: str = "en") -> List[dict]:
    """The questions still worth asking on this topic page (nothing already known, nothing irrelevant). [] when complete. Max 4, all optional."""
    if topic not in TOPICS:
        return []
    L = _LABEL["es" if lang == "es" else "en"]
    qs = []
    if not profile.get("role"):
        qs.append({"key": "role", "type": "chips", "prompt": L["role"], "optional": True, "options": [{"value": r, "label": L[r]} for r in ROLES]})
    if not profile.get("what"):
        qs.append({"key": "what", "type": "text", "prompt": L["what"], "placeholder": L["ph_what"], "optional": True, "max": _TEXT_MAX})
    if profile.get("role") in ("running_business", "freelance", None) and not profile.get("stage") and topic in ("business", "money"):
        qs.append({"key": "stage", "type": "chips", "prompt": L["stage"], "optional": True, "options": [{"value": s, "label": L[s]} for s in STAGES]})
    if not profile.get("market") and topic in ("business", "money"):
        qs.append({"key": "market", "type": "text", "prompt": L["market"], "placeholder": L["ph_market"], "optional": True, "max": _TEXT_MAX})
    return qs


_PROPER = {w.lower(): w for w in (
    "LATAM", "US", "USA", "UK", "EU", "UAE", "MENA", "APAC", "EMEA", "AI", "B2B", "B2C", "SaaS", "SMB", "SMBs",
    "Latin America", "North America", "South America", "Europe", "Asia", "Africa", "India", "Mexico", "Colombia", "Brazil", "Argentina", "Chile", "Peru", "Spain", "Canada",
    "Florida", "Texas", "California", "Miami", "Bogota", "Bogotá", "Medellin", "Medellín", "London", "Dubai", "Singapore", "Australia", "Germany", "France", "Italy", "Portugal")}


def tidy(text: Any) -> str:
    """The person's own words, made safe to sit INSIDE a sentence: a capitalised first word is lower-cased ('Small shops in latam' -> 'small shops in LATAM'), known acronyms / countries /
    regions get their proper form (latam -> LATAM, us -> US, mexico -> Mexico). Anything else they typed (brand names, 'iPhone', all-caps shouting) is left exactly as written."""
    t = " ".join(str(text or "").split())
    if not t:
        return ""
    letters = [c for c in t if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(t) > 6:
        return t                                              # all caps: leave it
    words = t.split(" ")
    out, i = [], 0
    while i < len(words):
        w = words[i]
        core = w.strip(".,;:!?()\"'")
        pre, post = w[:len(w) - len(w.lstrip(".,;:!?()\"'"))], w[len(w.rstrip(".,;:!?()\"'")):]
        two = (" ".join(x.strip(".,;:!?()\"'") for x in words[i:i + 2])).lower() if i + 1 < len(words) else ""
        if two in _PROPER:                                    # two-word names: 'latin america', 'north america'
            out.append(pre + _PROPER[two] + (words[i + 1][len(words[i + 1].rstrip(".,;:!?()\"'")):]))
            i += 2
            continue
        if core.lower() in _PROPER and (core.islower() or core.istitle() or core.isupper()):
            out.append(pre + _PROPER[core.lower()] + post)
        elif i == 0 and core[:1].isupper() and core[1:].islower() and not any(
                x.strip(".,;:!?()\"'")[:1].isupper() and x.strip(".,;:!?()\"'").lower() not in _PROPER for x in words[1:]):
            out.append(pre + core[:1].lower() + core[1:] + post)         # only when nothing else is capitalised ("Acme Studio" is a name: kept)
        else:
            out.append(w)
        i += 1
    return " ".join(out)


_FALLBACK_NAME = {"en": {"running_business": "your business", "freelance": "your freelance work", "job": "your work", "studying": "your studies", "in_transition": "your next step"},
                  "es": {"running_business": "tu negocio", "freelance": "tu trabajo freelance", "job": "tu trabajo", "studying": "tus estudios", "in_transition": "tu siguiente paso"}}


def short_name(what: str, role: str, lang: str = "en") -> str:
    """The person's own words when they are short enough to sit inside a sentence; otherwise 'your business' / 'your work' (a venture label like
    'Tech platform for AI agents/employees for small business in LATAM/USA' reads badly mid-sentence)."""
    w = " ".join(str(what or "").split())
    if 0 < len(w) <= 38 and "/" not in w:
        return tidy(w)
    return _FALLBACK_NAME["es" if lang == "es" else "en"].get(role, "your work")


def personalise_move(topic: str, tone: str, profile: Dict[str, Any], lang: str = "en") -> Optional[str]:
    """One move that is about THEIR work. Needs at least the one-line `what`; mode follows the engine's tone (open vs care/steady). None → keep the generic move."""
    what = (profile or {}).get("what")
    if topic not in TOPICS or not what:
        return None
    mode = "open" if tone == "open" else "care"
    i = 1 if lang == "es" else 0
    role = profile.get("role") or "running_business"
    what = short_name(what, role, lang)
    if topic == "money":
        return _MONEY[mode][i].format(what=what)
    if topic == "career" and role == "running_business":      # Career is about YOU in it (authority, visibility), not the numbers: Business already covers those
        return _CAREER_FOUNDER[mode][i].format(what=what)
    key = (role, profile.get("stage") if role == "running_business" else None, mode)
    tpl = _MOVE.get(key) or _MOVE.get((role, None, mode))
    return tpl[i].format(what=what) if tpl else None


def fit_for(sb, chart_id: str, profile: Dict[str, Any], lang: str = "en") -> Optional[dict]:
    """The chart's fit read (best / uphill lanes always; the tier for THEIR work once they have said what it is). None when the chart has no career ranking."""
    try:
        from antar_engine import d10_career, work_fit
        c = (sb.table("charts").select("chart_data").eq("id", chart_id).limit(1).execute().data) or []
        if not c:
            return None
        cd = c[0].get("chart_data")
        if isinstance(cd, str):
            import json as _json
            cd = _json.loads(cd)
        ranked = (d10_career.analyze_career(cd or {}) or {}).get("careers") or []
        return work_fit.fit(ranked, (profile or {}).get("what") or "", lang)
    except Exception:
        return None
