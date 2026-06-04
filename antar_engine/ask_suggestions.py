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
        ("focus",   "general", "What should I prioritize this week?"),
        ("blocks",  "general", "What's blocking me right now?"),
        ("career",  "work",    "Where is my work life heading?"),
        ("finance", "money",   "How does money look for me right now?"),
    ],
    "es": [
        ("focus",   "general", "¿Qué debería priorizar esta semana?"),
        ("blocks",  "general", "¿Qué me está bloqueando ahora mismo?"),
        ("career",  "work",    "¿Hacia dónde va mi vida laboral?"),
        ("finance", "money",   "¿Cómo se ve mi dinero en este momento?"),
    ],
    "pt": [
        ("focus",   "general", "O que devo priorizar esta semana?"),
        ("blocks",  "general", "O que está me bloqueando agora?"),
        ("career",  "work",    "Para onde vai minha vida profissional?"),
        ("finance", "money",   "Como está meu dinheiro neste momento?"),
    ],
}

# ── live-signal prompt bank: (domain, direction) → label_key, text ──────────
# Gentle phrasings only — an open door, not a diagnosis.
_LIVE = {
    "en": {
        ("money", "positive"):         ("finance", "Where can I make the most of this money window?"),
        ("money", "adverse"):          ("finance", "Why does money feel tight right now?"),
        ("work", "positive"):          ("career",  "What should I push forward at work right now?"),
        ("work", "adverse"):           ("career",  "Why does work feel stuck right now?"),
        ("relationships", "positive"): ("love",    "What's opening up in my relationships right now?"),
        ("relationships", "adverse"):  ("love",    "Why do my relationships feel strained right now?"),
        ("mind", "positive"):          ("clarity", "How do I use this clarity while it's here?"),
        ("mind", "adverse"):           ("clarity", "Why does my mind feel scattered right now?"),
    },
    "es": {
        ("money", "positive"):         ("finance", "¿Cómo aprovecho esta ventana de dinero?"),
        ("money", "adverse"):          ("finance", "¿Por qué el dinero se siente apretado ahora?"),
        ("work", "positive"):          ("career",  "¿Qué debería impulsar en el trabajo ahora mismo?"),
        ("work", "adverse"):           ("career",  "¿Por qué el trabajo se siente estancado ahora?"),
        ("relationships", "positive"): ("love",    "¿Qué se está abriendo en mis relaciones ahora?"),
        ("relationships", "adverse"):  ("love",    "¿Por qué mis relaciones se sienten tensas ahora?"),
        ("mind", "positive"):          ("clarity", "¿Cómo uso esta claridad mientras está aquí?"),
        ("mind", "adverse"):           ("clarity", "¿Por qué mi mente se siente dispersa ahora?"),
    },
    "pt": {
        ("money", "positive"):         ("finance", "Como aproveito esta janela de dinheiro?"),
        ("money", "adverse"):          ("finance", "Por que o dinheiro parece apertado agora?"),
        ("work", "positive"):          ("career",  "O que devo impulsionar no trabalho agora?"),
        ("work", "adverse"):           ("career",  "Por que o trabalho parece travado agora?"),
        ("relationships", "positive"): ("love",    "O que está se abrindo nas minhas relações agora?"),
        ("relationships", "adverse"):  ("love",    "Por que minhas relações parecem tensas agora?"),
        ("mind", "positive"):          ("clarity", "Como uso esta clareza enquanto ela está aqui?"),
        ("mind", "adverse"):           ("clarity", "Por que minha mente parece dispersa agora?"),
    },
}

# ── dasha chapter themes: MD lord → plain chapter phrase (NO planet names) ──
_DASHA = {
    "en": {
        "saturn":  "How do I make the most of this building phase?",
        "jupiter": "How do I make the most of this growth chapter?",
        "rahu":    "How do I channel this ambitious, restless chapter?",
        "ketu":    "What is this letting-go chapter asking of me?",
        "venus":   "How do I make the most of this chapter of connection and comfort?",
        "sun":     "How do I step into the visibility this chapter offers?",
        "moon":    "How do I work with this emotionally deep chapter?",
        "mars":    "Where should I direct this chapter's drive?",
        "mercury": "How do I use this chapter of learning and connection?",
    },
    "es": {
        "saturn":  "¿Cómo aprovecho esta fase de construcción?",
        "jupiter": "¿Cómo aprovecho este capítulo de crecimiento?",
        "rahu":    "¿Cómo canalizo este capítulo ambicioso e inquieto?",
        "ketu":    "¿Qué me pide este capítulo de soltar?",
        "venus":   "¿Cómo aprovecho este capítulo de conexión y disfrute?",
        "sun":     "¿Cómo asumo la visibilidad que ofrece este capítulo?",
        "moon":    "¿Cómo trabajo con este capítulo emocionalmente profundo?",
        "mars":    "¿Hacia dónde dirijo el impulso de este capítulo?",
        "mercury": "¿Cómo uso este capítulo de aprendizaje y conexión?",
    },
    "pt": {
        "saturn":  "Como aproveito esta fase de construção?",
        "jupiter": "Como aproveito este capítulo de crescimento?",
        "rahu":    "Como canalizo este capítulo ambicioso e inquieto?",
        "ketu":    "O que este capítulo de desapego está pedindo de mim?",
        "venus":   "Como aproveito este capítulo de conexão e prazer?",
        "sun":     "Como assumo a visibilidade que este capítulo oferece?",
        "moon":    "Como trabalho com este capítulo emocionalmente profundo?",
        "mars":    "Para onde direciono o impulso deste capítulo?",
        "mercury": "Como uso este capítulo de aprendizado e conexão?",
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
