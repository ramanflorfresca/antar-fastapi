"""[positioning 2026-10-12] "How should I position / pitch / brand my <work>?" — answered like a person would, as a short run of chat messages (each <= 5 lines), not one essay.

The engines decide WHAT applies (lane fit, the uphill lanes, the leadership pull, whether recognition lags effort, the season, the next career window, the speculation trap, past ventures that were
hands-on); fixed templates phrase it. No LLM, no invented chart facts, no planet names in the text. If we don't yet know what they build, the first reply is a question (the interview), not a guess.

Returns {"messages": [str...], "next": str, "chips": [{q,title}], "ask_back": None | {key, type, prompt, options?, placeholder?}}.
"""
import re
from typing import Any, Dict, List, Optional

_RX = [
    r"\bpositioning\b", r"\bhow (should |do |can |would |to |could )?(i |we )?position\b", r"\bposition (my|our|the|it|this|a|an)\b", r"\bpitch(ing)?\b", r"\bbrand(ing)?\b", r"go[- ]to[- ]market", r"\bgtm\b", r"how (do|should|can|would) i (sell|market|promote|launch|present|frame|introduce)\b",
    r"what should i lead with", r"how (to|do i) stand out", r"\bmessaging\b", r"how should i (talk|speak) about (my|the|our)",
    r"c[oó]mo (debo |puedo |deber[ií]a )?(posicionar|vender|presentar|promocionar|lanzar|comunicar)", r"posicionamiento", r"\bmarca personal\b",
]
_RXC = [re.compile(x, re.I) for x in _RX]
_WORKY = re.compile(r"\b(platform|product|startup|business|company|app|service|venture|agency|practice|project|brand|plataforma|producto|negocio|empresa|servicio|proyecto)\b", re.I)

_T = {
    "en": {
        "ask_role": "Before I answer: what best describes your work right now?", "ask_what": "And what is it, in one line? (e.g. AI agents for small businesses)",
        "ask_stage": "Where is it today?", "ask_market": "Who is it for, and where?",
        "roles": {"running_business": "Running a business", "job": "Working a job", "freelance": "Freelance or consulting", "studying": "Studying", "in_transition": "Between things"},
        "stages": {"idea": "An idea", "building": "Building it", "launched": "Launched", "revenue": "Earning revenue", "scaling": "Scaling"},
        "intro": "Straight answer on positioning {w}: {core}.",
        "core_lane": "lead with {short}, and put your own judgment behind it",
        "core_voice_spec": "lead with {short}, and be the specialist people come to",
        "lane_noun": {"technology & innovation": "what it actually does: work done for the customer, not advice about it", "science & research": "the depth of your analysis",
                      "networks / community / humanitarian": "the community and relationships around it", "law & diplomacy": "trust and clear terms",
                      "communication & media": "your voice and your story", "arts & design": "the craft and the experience", "finance & banking": "clarity about money",
                      "default": "your strongest skill"},
        "why": "Why: your strongest lane is {a}{b}.", "why_b": ", then {b}", "why_rahu": " Your career chart carries the part that rules systems, other people's money and AI in its 8th house.",
        "lead_h": "Lead with:", "avoid_h": "Avoid:",
        "L_voice_lead": "You as the expert voice behind it, not only the founder.", "L_voice_spec": "You as the specialist people come to; let others carry the volume.",
        "L_proof": "One paying customer as proof before any big claim. Recognition arrives slower than effort for you right now.",
        "L_network": "Growth through partners and communities, not cold volume.", "L_lane": "{noun_cap}.",
        "A_scatter": "Selling it to everyone. Pick one kind of customer first.", "A_ops": "Done-for-you service work, delivery or daily logistics. Hands-on operations run uphill for your chart{past}.",
        "A_past": ", like your {p}", "A_spec": "Quick bets and fast-money framing. Price for the long run.",
        "season": "This stretch of your life favours {lead_for} (to {until}). Watch out for {waste}.", "window": " Your next career window: {w}.",
        "market": "You named {m}. Pick one for your first ten customers so the proof stays clean.", "market_ask": "Who is it for, and where? Tell me and I'll sharpen this.",
        "close": "This is a fit read, not a guarantee. The market and the customer are yours.",
        "next_default": "This week: write one sentence on who it is for and what it replaces, and say it to one real prospect.",
        "chip_market": ("Which market should I start with?", "Which market first?"), "chip_partner": ("Who should I partner with?", "Who to partner with"), "chip_fit": ("Does this type of work fit my chart?", "Does this fit my chart?"),
        "seasons": {"Rahu": ("reach, scale and being seen as the authority", "chasing every opening at once"), "Saturn": ("structure, patience and long-haul credibility", "rushing before the foundation holds"),
                    "Jupiter": ("teaching, trust and advice people can act on", "promising more than you can deliver"), "Mercury": ("deals, conversations and fast learning", "talking more than shipping"),
                    "Venus": ("relationships and polish", "waiting for perfect"), "Mars": ("speed and direct action", "forcing outcomes"), "Sun": ("stepping into the lead", "going it alone"),
                    "Moon": ("steady, caring service", "reacting to every mood"), "Ketu": ("focus, refining and letting go", "scattering your effort")},
        "gen_work": "your work",
    },
    "es": {
        "ask_role": "Antes de responder: ¿qué describe mejor tu trabajo ahora?", "ask_what": "¿Y qué es, en una línea? (p. ej. agentes de IA para pequeños negocios)",
        "ask_stage": "¿En qué punto está hoy?", "ask_market": "¿Para quién es y dónde?",
        "roles": {"running_business": "Dirijo un negocio", "job": "Tengo un empleo", "freelance": "Freelance o consultoría", "studying": "Estudio", "in_transition": "Entre cosas"},
        "stages": {"idea": "Una idea", "building": "Construyéndolo", "launched": "Lanzado", "revenue": "Con ingresos", "scaling": "Escalando"},
        "intro": "Respuesta directa sobre cómo posicionar {w}: {core}.",
        "core_lane": "empieza por {short} y pon tu propio criterio detrás",
        "core_voice_spec": "empieza por {short} y sé el especialista al que acuden",
        "lane_noun": {"technology & innovation": "lo que hace de verdad: trabajo hecho para el cliente, no consejos sobre él", "science & research": "la profundidad de tu análisis",
                      "networks / community / humanitarian": "la comunidad y las relaciones a su alrededor", "law & diplomacy": "la confianza y las condiciones claras",
                      "communication & media": "tu voz y tu historia", "arts & design": "el oficio y la experiencia", "finance & banking": "la claridad sobre el dinero",
                      "default": "tu mayor fortaleza"},
        "why": "Por qué: tu área más fuerte es {a}{b}.", "why_b": ", luego {b}", "why_rahu": " Tu carta de carrera tiene lo que rige los sistemas, el dinero de otros y la IA en su casa 8.",
        "lead_h": "Empieza por:", "avoid_h": "Evita:",
        "L_voice_lead": "Tú como la voz experta detrás, no solo como fundador.", "L_voice_spec": "Tú como el especialista al que acuden; deja que otros lleven el volumen.",
        "L_proof": "Un cliente que pague como prueba antes de cualquier gran afirmación. El reconocimiento te llega más lento que el esfuerzo ahora.",
        "L_network": "Crecer con socios y comunidades, no con volumen en frío.", "L_lane": "{noun_cap}.",
        "A_scatter": "Venderlo a todo el mundo. Elige primero un tipo de cliente.", "A_ops": "Servicio hecho para el cliente, reparto o logística diaria. Las operaciones manuales van cuesta arriba para tu carta{past}.",
        "A_past": ", como {p}", "A_spec": "Apuestas rápidas y dinero fácil. Fija precios pensando a largo plazo.",
        "season": "Esta etapa de tu vida favorece {lead_for} (hasta {until}). Cuidado con {waste}.", "window": " Tu próxima ventana de carrera: {w}.",
        "market": "Mencionaste {m}. Elige uno para tus primeros diez clientes y que la prueba quede limpia.", "market_ask": "¿Para quién es y dónde? Cuéntamelo y afino esto.",
        "close": "Es una lectura de encaje, no una garantía. El mercado y el cliente son tuyos.",
        "next_default": "Esta semana: escribe una frase sobre para quién es y qué reemplaza, y díselo a un prospecto real.",
        "chip_market": ("¿Con qué mercado debería empezar?", "¿Qué mercado primero?"), "chip_partner": ("¿Con quién debería asociarme?", "Con quién asociarme"), "chip_fit": ("¿Este tipo de trabajo encaja con mi carta?", "¿Encaja con mi carta?"),
        "seasons": {"Rahu": ("alcance, escala y que te vean como la autoridad", "perseguir todas las oportunidades a la vez"), "Saturn": ("estructura, paciencia y credibilidad a largo plazo", "correr antes de que la base aguante"),
                    "Jupiter": ("enseñar, confianza y consejos accionables", "prometer más de lo que puedes cumplir"), "Mercury": ("tratos, conversaciones y aprender rápido", "hablar más que entregar"),
                    "Venus": ("relaciones y pulido", "esperar la perfección"), "Mars": ("velocidad y acción directa", "forzar resultados"), "Sun": ("dar un paso al frente", "hacerlo todo solo"),
                    "Moon": ("servicio constante y cuidadoso", "reaccionar a cada estado de ánimo"), "Ketu": ("enfoque, afinar y soltar", "dispersar tu esfuerzo")},
        "gen_work": "tu trabajo",
    },
}


def is_positioning_q(q: Any) -> bool:
    s = str(q or "")
    if not s.strip() or len(s) > 400:
        return False
    return any(r.search(s) for r in _RXC) and bool(_WORKY.search(s) or re.search(r"\b(my|our|mi|mis|nuestro)\b", s, re.I))


def ask_back(profile: Dict[str, Any], lang: str = "en") -> Optional[dict]:
    """The next interview question (role, then what) — None once both are known. Stage and market are offered after the answer, never required."""
    t = _T["es" if lang == "es" else "en"]
    if not profile.get("role"):
        return {"key": "role", "type": "chips", "prompt": t["ask_role"], "optional": True, "options": [{"value": k, "label": v} for k, v in t["roles"].items()]}
    if not profile.get("what"):
        return {"key": "what", "type": "text", "prompt": t["ask_what"], "optional": False, "placeholder": t["ask_what"].split("(")[-1].rstrip(")").replace("e.g. ", "").replace("p. ej. ", ""), "max": 120}
    return None


def _short(what: str, lang: str) -> str:
    from antar_engine.work_profile import short_name
    return short_name(what, "running_business", lang)


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _recognition_lags(chart: dict) -> bool:
    """The D-1 10th lord is debilitated or combust: recognition arrives slower than effort."""
    try:
        from antar_engine.ask_basis import _SIGNS, _LORD, _dignity
        planets = chart.get("planets") or {}
        lagna = (chart.get("lagna") or {}).get("sign")
        lord = _LORD[_SIGNS[(_SIGNS.index(lagna) + 9) % 12]]
        pl = planets.get(lord) or {}
        return bool(pl.get("sign")) and any(n == "debilitated" or n.startswith("combust") for n in _dignity(lord, pl["sign"], planets))
    except Exception:
        return False


def compose(chart: dict, fit: Optional[dict], profile: Dict[str, Any], *, md: str = "", until: str = "", window: str = "", leadership: str = "",
            past_hands_on: Optional[List[str]] = None, lang: str = "en") -> Optional[dict]:
    """Needs the lane fit (work_fit.fit output) and the profile's `what`. None when either is missing."""
    lang = "es" if lang == "es" else "en"
    t = _T[lang]
    what = (profile or {}).get("what")
    if not fit or not fit.get("best") or not what:
        return None
    w = _short(what, lang)
    best = fit["best"]
    from antar_engine import work_fit as _WF
    # lane nouns are keyed by the ENGLISH field name; es fit labels are mapped back
    en_of = {v: k for k, v in _WF._ES_FIELD.items()}
    key0 = en_of.get(best[0], best[0])
    noun = t["lane_noun"].get(key0, t["lane_noun"]["default"])
    spec = "specialist" in (leadership or "").lower() or "individual" in (leadership or "").lower()
    short = noun.split(":")[0] if key0 == "technology & innovation" or key0 == "technology & innovation" else noun
    core = t["core_voice_spec" if spec else "core_lane"].format(short=short)
    msgs = [t["intro"].format(w=w, core=core)]
    why = t["why"].format(a=best[0], b=(t["why_b"].format(b=best[1]) if len(best) > 1 else ""))
    d10r = ((((chart.get("divisional_charts") or {}).get("d10") or {}).get("planets") or {}).get("Rahu") or {}).get("house")
    if key0 == "technology & innovation" and d10r == 8:
        why += t["why_rahu"]
    msgs.append(why)
    lead = [t["L_lane"].format(noun_cap=_cap(noun))]
    lead.append(t["L_voice_spec"] if spec else t["L_voice_lead"])
    if _recognition_lags(chart):
        lead.append(t["L_proof"])
    elif any("network" in b.lower() or "red" in b.lower() for b in best):
        lead.append(t["L_network"])
    msgs.append(t["lead_h"] + "\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(lead[:3], 1)))
    avoid = []
    if "executive" in (leadership or "").lower() or "leader" in (leadership or "").lower():
        avoid.append(t["A_scatter"])
    if fit.get("uphill"):
        p = (past_hands_on or [None])[0]
        avoid.append(t["A_ops"].format(past=(t["A_past"].format(p=p) if p else "")))
    rahu_h = ((chart.get("planets") or {}).get("Rahu") or {}).get("house")
    if rahu_h in (5, 8, 11):
        avoid.append(t["A_spec"])
    if avoid:
        msgs.append(t["avoid_h"] + "\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(avoid[:3], 1)))
    lead_for, waste = t["seasons"].get(md, (None, None))
    if lead_for:
        s = t["season"].format(lead_for=lead_for, until=until or "the next shift", waste=waste)
        if window:
            s += t["window"].format(w=window)
        msgs.append(s)
    from antar_engine.work_profile import tidy as _tidy
    msgs.append(t["market"].format(m=_tidy(profile["market"])) if profile.get("market") else t["market_ask"])
    nxt = None
    try:
        from antar_engine.work_profile import personalise_move
        nxt = personalise_move("business", "open", dict(profile, role=profile.get("role") or "running_business"), lang)
    except Exception:
        nxt = None
    nxt = nxt or t["next_default"]
    msgs.append(t["close"])
    chips = [{"q": t[k][0], "title": t[k][1]} for k in (("chip_market", "chip_partner", "chip_fit") if not profile.get("market") else ("chip_partner", "chip_fit"))]
    return {"messages": [m for m in msgs if m], "next": nxt, "chips": chips, "ask_back": None}


def interview(profile: Dict[str, Any], lang: str = "en") -> Optional[dict]:
    q = ask_back(profile or {}, lang)
    if not q:
        return None
    return {"messages": [q["prompt"]], "next": None, "chips": [], "ask_back": q}
