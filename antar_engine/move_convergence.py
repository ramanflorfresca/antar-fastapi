"""
antar_engine/move_convergence.py

The Desh-Kal-Patra MOVE unifier — one honest "should I move" convergence.

Astrocartography answers only WHERE (the relocation chart / lines = the DESH
leg). The classical Vedic frame is fuller: a move only delivers when the PLACE
(Desh), the TIME (Kal = the running dasha), and the VESSEL (Patra = your chart's
promise + real feasibility) all point the same way. Raw Western astrocartography
over-weights Desh and ignores Kal/Patra — hence "you can't outrun your dasha by
getting on a plane."

This module converges the three legs (each already computed by /places/potential)
into a single conviction read: level + a plain synthesis line + the three leg
reads. It NEVER tells the user to move — it reports how much the frame agrees
that *now* is a real window. Descriptive; jargon-free; localized; never raises.

NAMING: intentionally NOT desh_kal_patra.py — that module is the economic/era
context layer used in kundli reading. This is the relocation-decision frame.
"""
from __future__ import annotations

# Kal — how MOVE-activated the running mahadasha lord is. Rahu/Ketu rule foreign
# lands & relocation; Moon rules change/home; Saturn/Sun root you in place.
_ACTIVATION = {
    "Rahu": "high", "Ketu": "high", "Moon": "high",
    "Mercury": "mod", "Venus": "mod", "Jupiter": "mod", "Mars": "mod",
    "Saturn": "low", "Sun": "low",
}
_FIT_RANK = {"strong": 2, "moderate": 1, "weak": 0}


def _lang(language) -> str:
    b = str(language or "en").split("_")[0].split("-")[0].lower()
    return b if b in ("en", "es", "pt") else "en"


# leg templates ({lord} filled). Kept short — the synthesis line carries the read.
_KAL = {
    "high": {"en": "This is a move-activated chapter — it pulls you toward new ground.",
             "es": "Es un capítulo activado para mudarte — te empuja hacia terreno nuevo.",
             "pt": "É um capítulo ativado para mudança — te puxa para um terreno novo."},
    "mod":  {"en": "The chapter is open to a move without forcing one — it is neutral on place.",
             "es": "El capítulo admite una mudanza sin forzarla — es neutral respecto al lugar.",
             "pt": "O capítulo admite uma mudança sem forçá-la — é neutro quanto ao lugar."},
    "low":  {"en": "This chapter roots you rather than moving you — it asks you to build where you are.",
             "es": "Este capítulo te enraíza en vez de moverte — te pide construir donde estás.",
             "pt": "Este capítulo te enraíza em vez de te mover — pede que construa onde está."},
}
_DESH = {
    "better": {"en": "There is ground that genuinely serves you more than where you live.",
               "es": "Hay un lugar que te sirve genuinamente más que donde vives.",
               "pt": "Há um lugar que te serve genuinamente mais do que onde você vive."},
    "home_ok": {"en": "Where you already are serves you well — no place clearly beats it.",
                "es": "Donde ya estás te sirve bien — ningún lugar lo supera con claridad.",
                "pt": "Onde você já está te serve bem — nenhum lugar o supera com clareza."},
}
_PATRA = {
    "feasible": {"en": "And a realistic move is within reach — you don't have to uproot to tap it.",
                 "es": "Y una mudanza realista está a tu alcance — no hace falta desarraigarte para aprovecharla.",
                 "pt": "E uma mudança realista está ao seu alcance — não precisa se desenraizar para aproveitá-la."},
    "reach":    {"en": "The strongest ground is a bigger reach — treat it as a horizon, not a next step.",
                 "es": "El mejor terreno es un salto mayor — tómalo como un horizonte, no como el siguiente paso.",
                 "pt": "O melhor terreno é um salto maior — encare-o como um horizonte, não o próximo passo."},
}

_SYNTH = {
    "high": {
        "en": "The place, the timing and your chart line up — this reads as a genuine window to make a move.",
        "es": "El lugar, el momento y tu carta se alinean — se lee como una ventana real para mudarte.",
        "pt": "O lugar, o momento e o seu mapa se alinham — lê-se como uma janela real para se mudar.",
    },
    "moderate": {
        "en": "Some of the frame is lit — a move is worth exploring, not urgent; a visit or a base elsewhere may be the honest first step.",
        "es": "Parte del marco está encendida — vale explorar una mudanza, sin prisa; una visita o una base en otro lugar puede ser el primer paso honesto.",
        "pt": "Parte do quadro está acesa — vale explorar uma mudança, sem pressa; uma visita ou uma base em outro lugar pode ser o primeiro passo honesto.",
    },
    "low_dasha": {
        "en": "A place can support you, but with this chapter the move won't do the heavy lifting — you can't outrun your current chapter by moving. Tend where you are; carry the timing with you.",
        "es": "Un lugar puede apoyarte, pero con este capítulo la mudanza no hará el trabajo pesado — no puedes escapar de tu capítulo actual mudándote. Cultiva donde estás; lleva el momento contigo.",
        "pt": "Um lugar pode te apoiar, mas com este capítulo a mudança não fará o trabalho pesado — você não escapa do seu capítulo atual se mudando. Cuide de onde está; leve o tempo com você.",
    },
    "low_home": {
        "en": "The frame doesn't point away — where you are serves you and the chapter roots you. Stay and build; a move isn't the lever right now.",
        "es": "El marco no apunta a irte — donde estás te sirve y el capítulo te enraíza. Quédate y construye; mudarte no es la palanca ahora.",
        "pt": "O quadro não aponta para sair — onde você está te serve e o capítulo te enraíza. Fique e construa; mudar não é a alavanca agora.",
    },
}


# Kal-only "is this a move-activated chapter" read — for surfaces without a city
# ranking (e.g. Ask "should I move?"). The dasha gate + the honest framing +
# "where is a separate Places question". Localized.
_READINESS = {
    "high": {
        "en": "This is a strongly move-activated chapter — it lights up foreign lands and new ground, so the timing genuinely supports a move. Where exactly is a separate question: a place amplifies what this chapter is already doing, it doesn't replace it.",
        "es": "Es un capítulo fuertemente activado para mudarte — enciende las tierras lejanas y el terreno nuevo, así que el momento apoya de verdad una mudanza. Dónde exactamente es otra pregunta: un lugar amplifica lo que este capítulo ya hace, no lo reemplaza.",
        "pt": "É um capítulo fortemente ativado para mudança — acende as terras distantes e o terreno novo, então o momento apoia de verdade uma mudança. Onde exatamente é outra pergunta: um lugar amplifica o que este capítulo já faz, não o substitui.",
    },
    "mod": {
        "en": "This chapter is open to a move without forcing one — it is fairly neutral about place, so relocating can help but isn't fated right now.",
        "es": "Este capítulo admite una mudanza sin forzarla — es bastante neutral respecto al lugar, así que mudarte puede ayudar pero no es algo fijado ahora.",
        "pt": "Este capítulo admite uma mudança sem forçá-la — é bastante neutro quanto ao lugar, então mudar pode ajudar mas não é algo selado agora.",
    },
    "low": {
        "en": "This chapter roots you rather than moving you — it asks you to build where you are. A move now won't do the heavy lifting; you can't outrun your current chapter by relocating.",
        "es": "Este capítulo te enraíza en vez de moverte — te pide construir donde estás. Una mudanza ahora no hará el trabajo pesado; no puedes escapar de tu capítulo actual mudándote.",
        "pt": "Este capítulo te enraíza em vez de te mover — pede que você construa onde está. Uma mudança agora não fará o trabalho pesado; você não escapa do seu capítulo atual se mudando.",
    },
}


# concise verdict fields for the /predict residence-question override (so a move
# question gets a CHAPTER verdict, not the daily transit). band ∈ FAVORABLE|MIXED|WEAK.
_RV_LINE = {
    "high": {"en": "This is a move-activated chapter — the timing genuinely supports a move.",
             "es": "Es un capítulo activado para mudarte — el momento apoya de verdad una mudanza.",
             "pt": "É um capítulo ativado para mudança — o momento apoia de verdade uma mudança."},
    "mod":  {"en": "The chapter is open to a move without forcing one.",
             "es": "El capítulo admite una mudanza sin forzarla.",
             "pt": "O capítulo admite uma mudança sem forçá-la."},
    "low":  {"en": "This chapter roots you — building where you are pays off more than moving now.",
             "es": "Este capítulo te enraíza — construir donde estás rinde más que mudarte ahora.",
             "pt": "Este capítulo te enraíza — construir onde você está rende mais que mudar agora."},
}
_RV_MOVE = {
    "high": {"en": "Line up the move deliberately — use the runway to prepare; the chapter is with you.",
             "es": "Prepara la mudanza con intención — aprovecha el margen para alistarte; el capítulo te acompaña.",
             "pt": "Organize a mudança com intenção — use o tempo para se preparar; o capítulo está com você."},
    "mod":  {"en": "Explore a move without rushing — a visit or a trial base is the honest first step.",
             "es": "Explora una mudanza sin prisa — una visita o una base de prueba es el primer paso honesto.",
             "pt": "Explore uma mudança sem pressa — uma visita ou uma base de teste é o primeiro passo honesto."},
    "low":  {"en": "Hold the relocation — strengthen your current base; you can't outrun your current chapter by moving.",
             "es": "Aplaza la mudanza — fortalece tu base actual; no puedes escapar de tu capítulo actual mudándote.",
             "pt": "Adie a mudança — fortaleça sua base atual; você não escapa do seu capítulo atual se mudando."},
}


def residence_verdict(dasha_lord: str | None, best_year=None, language: str = "en") -> dict:
    """A CHAPTER-level verdict package for an Ask move/relocation question — to
    override the generic daily verdict. Returns (never raises):
      {available, band: FAVORABLE|MIXED|WEAK, activation, line, the_move,
       secondary_note, window_range}."""
    try:
        L = _lang(language)
        lord = (dasha_lord or "").strip().title()
        if not lord:
            return {"available": False}
        act = _ACTIVATION.get(lord, "mod")
        band = {"high": "FAVORABLE", "mod": "MIXED", "low": "WEAK"}[act]
        yr = str(best_year).strip() if best_year else ""
        if yr:
            dr = {"en": f"around {yr}", "es": f"alrededor de {yr}", "pt": f"por volta de {yr}"}[L]
        else:
            dr = {"en": "over the next few years", "es": "en los próximos años",
                  "pt": "nos próximos anos"}[L]
        return {"available": True, "band": band, "activation": act,
                "line": _RV_LINE[act][L], "the_move": _RV_MOVE[act][L],
                "secondary_note": move_readiness(lord, language).get("note"),
                "window_range": dr}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def move_readiness(dasha_lord: str | None, language: str = "en") -> dict:
    """Kal-only move read (no city ranking): is this a move-activated chapter?
    For Ask 'should I move?'. Returns (never raises):
      {available, level: high|moderate|low, activation, lord, note}."""
    try:
        L = _lang(language)
        lord = (dasha_lord or "").strip().title()
        if not lord:
            return {"available": False}
        act = _ACTIVATION.get(lord, "mod")
        return {"available": True,
                "level": {"high": "high", "mod": "moderate", "low": "low"}[act],
                "activation": act, "lord": lord,
                "note": _READINESS[act][L].format(lord=lord)}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def move_convergence(dasha_lord: str | None, home_fit: str | None,
                     best_fit: str | None, bigger_fit: str | None,
                     has_promise: bool, language: str = "en") -> dict:
    """Converge Desh (place) x Kal (dasha) x Patra (promise/feasibility) into one
    'is now a real window to move' read. Returns (never raises):
      {available, level: high|moderate|low, line, legs:{kal,desh,patra}}
    """
    try:
        L = _lang(language)
        lord = (dasha_lord or "").strip().title()
        act = _ACTIVATION.get(lord, "mod")           # Kal
        home_r = _FIT_RANK.get((home_fit or "").lower(), 1)
        best_r = max(_FIT_RANK.get((best_fit or "").lower(), 0),
                     _FIT_RANK.get((bigger_fit or "").lower(), 0))
        desh_better = best_r > home_r                # a place beats home
        patra_feasible = _FIT_RANK.get((best_fit or "").lower(), 0) >= 1  # a within-reach pick exists
        bigger_only = (not patra_feasible) and _FIT_RANK.get((bigger_fit or "").lower(), 0) >= 1

        # ── level (Kal gates the whole read — the Vedic honesty) ──────────────
        if act == "low":
            level = "low"
            synth = _SYNTH["low_dasha"][L]
        elif desh_better and (patra_feasible or bigger_only) and act == "high":
            level = "high"
            synth = _SYNTH["high"][L]
        elif desh_better and (act in ("high", "mod")):
            level = "moderate"
            synth = _SYNTH["moderate"][L]
        else:
            level = "low"
            synth = _SYNTH["low_home"][L]

        legs = {
            "kal": (_KAL[act][L].format(lord=lord or "your dasha")),
            "desh": (_DESH["better"][L] if desh_better else _DESH["home_ok"][L]),
            "patra": (_PATRA["feasible"][L] if patra_feasible
                      else _PATRA["reach"][L] if bigger_only else None),
        }
        return {"available": True, "level": level, "line": synth, "legs": legs}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
