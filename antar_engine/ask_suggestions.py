"""
antar_engine/ask_suggestions.py

Chart-aware Ask landing prompts — the backend RETURNS the suggested prompts,
the frontend only renders them. 4 items total: 2-3 fixed base + 1-2 promoted
chart-derived, so the landing reflects what is LIVE in this user's chart.

Selection (reuses existing committed state — never recomputes, never LLM):
  1. live_signal — today's committed selection (today_signal.read_today_signal:
     the SAME snapshot the Today card showed; cross-surface no-drift).
  2. dasha      — current MD chapter theme (dasha_periods, level 1).
  3. history    — patra_prior.build_patra_tilt top domain (a soft nudge —
     fills a slot only when 1-2 are silent; never overrides them).

Guardrails:
  * Sensitive-domain guard: NEVER promote body/health from a hard transit;
    adverse relationships only when the signal is not high-strength (an open
    door, not a diagnosis). The user can always ask the hard thing themselves.
  * Zero jargon: no planet names, no house numbers — conclusions, not
    calculations. Dasha lords map to plain chapter phrases.
  * Language: en/es/pt served from a static bank (server-side, deterministic).

Fail-open everywhere: any read failing degrades to the fixed base set.
"""
from __future__ import annotations

from typing import Optional

# ── locked label vocabulary (matches the frontend card chips) ───────────────
_LABELS = {
    "en": {"focus": "FOCUS", "career": "CAREER", "finance": "FINANCE",
           "blocks": "BLOCKS", "love": "LOVE", "clarity": "CLARITY",
           "chapter": "THIS CHAPTER"},
    "es": {"focus": "ENFOQUE", "career": "CARRERA", "finance": "FINANZAS",
           "blocks": "BLOQUEOS", "love": "VÍNCULOS", "clarity": "CLARIDAD",
           "chapter": "ESTE CICLO"},
    "pt": {"focus": "FOCO", "career": "CARREIRA", "finance": "FINANÇAS",
           "blocks": "BLOQUEIOS", "love": "RELAÇÕES", "clarity": "CLAREZA",
           "chapter": "ESTE CICLO"},
}

# ── fixed base set (fallback, always available; keep >= 2) ──────────────────
# Order = fill order: FOCUS and BLOCKS are always kept; CAREER/FINANCE yield
# their seat when a promoted prompt already covers that domain.
_BASE = {
    "en": [
        ("focus",   "general", "What does my chart say about this week?"),
        ("blocks",  "general", "What is holding me back in this period?"),
        ("career",  "work",    "How does my work life look in this period?"),
        ("finance", "money",   "How does money look for me right now?"),
    ],
    "es": [
        ("focus",   "general", "¿Qué dice mi carta sobre esta semana?"),
        ("blocks",  "general", "¿Qué me está frenando en esta etapa?"),
        ("career",  "work",    "¿Cómo se ve mi vida laboral en esta etapa?"),
        ("finance", "money",   "¿Cómo se ve mi dinero en este momento?"),
    ],
    "pt": [
        ("focus",   "general", "O que meu mapa diz sobre esta semana?"),
        ("blocks",  "general", "O que está me segurando nesta fase?"),
        ("career",  "work",    "Como está minha vida profissional nesta fase?"),
        ("finance", "money",   "Como está meu dinheiro neste momento?"),
    ],
}

# ── live-signal prompt bank: (domain, direction) → label_key, text ──────────
# Gentle phrasings only — an open door, not a diagnosis.
_LIVE = {
    "en": {
        ("money", "positive"):         ("finance", "How long does this money window stay open?"),
        ("money", "adverse"):          ("finance", "Why does money feel tight right now?"),
        ("work", "positive"):          ("career",  "How long does this good stretch at work last?"),
        ("work", "adverse"):           ("career",  "Why does work feel stuck right now?"),
        ("relationships", "positive"): ("love",    "What is opening up in my relationships right now?"),
        ("relationships", "adverse"):  ("love",    "Why do my relationships feel strained right now?"),
        ("mind", "positive"):          ("clarity", "How long does this clarity last?"),
        ("mind", "adverse"):           ("clarity", "Why does my mind feel scattered right now?"),
    },
    "es": {
        ("money", "positive"):         ("finance", "¿Cuánto dura esta ventana de dinero?"),
        ("money", "adverse"):          ("finance", "¿Por qué el dinero se siente apretado ahora?"),
        ("work", "positive"):          ("career",  "¿Cuánto dura este buen tramo en el trabajo?"),
        ("work", "adverse"):           ("career",  "¿Por qué el trabajo se siente estancado ahora?"),
        ("relationships", "positive"): ("love",    "¿Qué se está abriendo en mis relaciones ahora?"),
        ("relationships", "adverse"):  ("love",    "¿Por qué mis relaciones se sienten tensas ahora?"),
        ("mind", "positive"):          ("clarity", "¿Cuánto dura esta claridad?"),
        ("mind", "adverse"):           ("clarity", "¿Por qué mi mente se siente dispersa ahora?"),
    },
    "pt": {
        ("money", "positive"):         ("finance", "Quanto tempo dura esta janela de dinheiro?"),
        ("money", "adverse"):          ("finance", "Por que o dinheiro parece apertado agora?"),
        ("work", "positive"):          ("career",  "Quanto tempo dura este bom trecho no trabalho?"),
        ("work", "adverse"):           ("career",  "Por que o trabalho parece travado agora?"),
        ("relationships", "positive"): ("love",    "O que está se abrindo nas minhas relações agora?"),
        ("relationships", "adverse"):  ("love",    "Por que minhas relações parecem tensas agora?"),
        ("mind", "positive"):          ("clarity", "Quanto tempo dura esta clareza?"),
        ("mind", "adverse"):           ("clarity", "Por que minha mente parece dispersa agora?"),
    },
}

# ── dasha chapter themes: MD lord → plain chapter phrase (NO planet names) ──
_DASHA = {
    "en": {
        "saturn":  "What is this building phase about for me?",
        "jupiter": "What is this growth chapter bringing me?",
        "rahu":    "What is this ambitious, restless chapter about?",
        "ketu":    "What is this letting-go chapter asking of me?",
        "venus":   "What is this chapter of connection and comfort about?",
        "sun":     "What does this chapter of visibility mean for me?",
        "moon":    "What is this emotionally deep chapter about?",
        "mars":    "What is this chapter's drive pointing me towards?",
        "mercury": "What is this chapter of learning and connection about?",
    },
    "es": {
        "saturn":  "¿De qué trata esta fase de construcción para mí?",
        "jupiter": "¿Qué me trae este capítulo de crecimiento?",
        "rahu":    "¿De qué trata este capítulo ambicioso e inquieto?",
        "ketu":    "¿Qué me pide este capítulo de soltar?",
        "venus":   "¿De qué trata este capítulo de conexión y disfrute?",
        "sun":     "¿Qué significa para mí este capítulo de visibilidad?",
        "moon":    "¿De qué trata este capítulo emocionalmente profundo?",
        "mars":    "¿Hacia dónde me empuja el impulso de este capítulo?",
        "mercury": "¿De qué trata este capítulo de aprendizaje y conexión?",
    },
    "pt": {
        "saturn":  "Do que trata esta fase de construção para mim?",
        "jupiter": "O que este capítulo de crescimento está me trazendo?",
        "rahu":    "Do que trata este capítulo ambicioso e inquieto?",
        "ketu":    "O que este capítulo de desapego está pedindo de mim?",
        "venus":   "Do que trata este capítulo de conexão e prazer?",
        "sun":     "O que este capítulo de visibilidade significa para mim?",
        "moon":    "Do que trata este capítulo emocionalmente profundo?",
        "mars":    "Para onde o impulso deste capítulo me empurra?",
        "mercury": "Do que trata este capítulo de aprendizado e conexão?",
    },
}

# history nudge reuses the POSITIVE live phrasing for the tilted domain.
_HISTORY_DOMAINS = ("money", "work", "relationships", "mind")  # body excluded

# base label_key covered by a promoted domain → that base card yields its seat
_BASE_YIELDS = {"money": "finance", "work": "career"}


def _norm_lang(language: Optional[str]) -> str:
    lang = (language or "en").split("-")[0].lower()
    return lang if lang in ("en", "es", "pt") else "en"


def _base_prompts(lang: str) -> list:
    return [
        {"label": _LABELS[lang][k], "text": t, "domain": d, "source": "base"}
        for k, d, t in _BASE[lang]
    ]


def _live_candidate(signal: Optional[dict], lang: str) -> Optional[dict]:
    """Priority 1 — today's committed signal, sensitive-domain guarded."""
    if not isinstance(signal, dict):
        return None
    domains = [d for d in (signal.get("highlight_domains") or []) if d]
    direction = (signal.get("direction") or "").strip().lower()
    strength = (signal.get("strength") or "").strip().lower()
    if not domains or direction in ("", "quiet"):
        return None  # honest quiet day — nothing to surface, no manufactured drama
    if direction == "mixed":
        direction = "positive"  # surface the opportunity side, never the ambush
    if direction not in ("positive", "adverse"):
        return None
    for d in domains:
        # Sensitive-domain guard: body/health is never promoted from a transit;
        # adverse relationships only when the signal is not high-strength.
        if d == "body":
            continue
        if d == "relationships" and direction == "adverse" and strength == "high":
            continue
        hit = _LIVE[lang].get((d, direction))
        if hit:
            label_key, text = hit
            return {"label": _LABELS[lang][label_key], "text": text,
                    "domain": d, "source": "live_signal"}
    return None


def _dasha_candidate(md_lord: Optional[str], lang: str) -> Optional[dict]:
    """Priority 2 — current MD chapter theme (plain language, no planet name)."""
    lord = (md_lord or "").strip().lower()
    for key, text in _DASHA[lang].items():
        if lord.startswith(key[:4]) and lord:  # 'sat', 'jupi', 'merc'... robust to casing/truncation
            return {"label": _LABELS[lang]["chapter"], "text": text,
                    "domain": "cycle", "source": "dasha"}
    return None


def _history_candidate(tilt: Optional[dict], lang: str) -> Optional[dict]:
    """Priority 3 — the patra-prior top domain. A soft nudge that fills a
    slot only when priorities 1-2 are silent; body is never suggested."""
    if not isinstance(tilt, dict) or not tilt:
        return None
    ranked = sorted(tilt, key=tilt.get, reverse=True)
    for d in ranked:
        if d in _HISTORY_DOMAINS:
            label_key, text = _LIVE[lang][(d, "positive")]
            return {"label": _LABELS[lang][label_key], "text": text,
                    "domain": d, "source": "history"}
    return None


def build_suggested_prompts(chart_id: str, sb, language: str = "en") -> list:
    """4 prompts: up to 2 promoted (live signal > dasha > history) + base
    fill. Always returns exactly 4; on ANY failure returns the base set."""
    lang = _norm_lang(language)
    try:
        promoted: list = []

        # 1. live signal — the committed Today selection (UTC date, then the
        #    day before: the commit is keyed on the user's LOCAL date).
        signal = None
        try:
            from datetime import date, timedelta
            from antar_engine.today_signal import read_today_signal
            signal = read_today_signal(sb, chart_id, date.today().isoformat())
            if signal is None:
                signal = read_today_signal(
                    sb, chart_id, (date.today() - timedelta(days=1)).isoformat())
        except Exception:
            signal = None
        live = _live_candidate(signal, lang)
        if live:
            promoted.append(live)

        # 2. dasha chapter theme
        try:
            from datetime import date
            _t = date.today().isoformat()
            r = sb.table("dasha_periods") \
                .select("planet_or_sign") \
                .eq("chart_id", chart_id).eq("system", "vimsottari") \
                .eq("level", 1).lte("start_date", _t).gte("end_date", _t) \
                .limit(1).execute()
            md_lord = (r.data[0].get("planet_or_sign") if r.data else "") or ""
        except Exception:
            md_lord = ""
        if len(promoted) < 2:
            dasha = _dasha_candidate(md_lord, lang)
            if dasha:
                promoted.append(dasha)

        # 3. history nudge — only if 1-2 left an open slot
        if len(promoted) < 2:
            try:
                from antar_engine.patra_prior import build_patra_tilt
                tilt = build_patra_tilt(chart_id, sb)
            except Exception:
                tilt = {}
            hist = _history_candidate(tilt, lang)
            if hist and hist["domain"] not in {p["domain"] for p in promoted}:
                promoted.append(hist)

        promoted = promoted[:2]

        # base fill: FOCUS + BLOCKS always; CAREER/FINANCE yield their seat
        # when a promoted prompt already covers that domain.
        covered = {p["domain"] for p in promoted}
        yielded = {_BASE_YIELDS[d] for d in covered if d in _BASE_YIELDS}
        base = [b for b in _base_prompts(lang)
                if b["label"] != ""  # guard
                and _label_key(b, lang) not in yielded]
        out = promoted + base
        return out[:4] if len(out) >= 4 else (out + _base_prompts(lang))[:4]
    except Exception as e:
        print(f"[ask-suggestions] degraded to base set: {e}")
        return _base_prompts(lang)[:4]


def _label_key(prompt: dict, lang: str) -> str:
    """Reverse-lookup a base prompt's label key from its rendered label."""
    inv = {v: k for k, v in _LABELS[lang].items()}
    return inv.get(prompt.get("label", ""), "")
