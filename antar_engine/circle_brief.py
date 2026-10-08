"""
antar_engine/circle_brief.py - the Founders' brief: "Our reading" for cofounder and business pairs.

What a person would ask an astrologer about themselves and a cofounder: how each of us works, who should
lead what, when to be careful, what not to do, how to balance it. Built ONLY from engines we already ship and
trust to DESCRIBE (never to predict):
  * the plain-language strengths / cautions from the chart (chart_identity's de-jargoned yogas);
  * career_mode (builds and owns, or works best inside a structure);
  * domain_fit's pace (fast and networked vs slow and long-hold);
  * the pair's dated windows (circle_overlap: both open / either needs care);
  * the chapter each person is in and when it changes (chart_identity).

HARD BOUNDARY (the closed business-vertical / timing studies): this NEVER says funding will come, a venture
will work, a sector will pay or a date will be lucky. It describes how two people tend to work, who covers
what, and when to be careful, and it says so in the response. Nothing is invented: a person with no flagged
caution simply has none ("nothing flagged"), not a manufactured weak point.

Lenses: cofounder, business (the wording of the balance line and the last don't differ). Roles (driver /
anchor / steady) are deterministic from pace + the strength labels; thresholds are written down below.
All strings en / es / pt / hinglish (Hindi falls back to English). Pure functions; no DB, no LLM.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from antar_engine import circle_copy as CC
from antar_engine import topic_copy as C

LENSES = ("cofounder", "business")
DRIVER_STEMS = {"Ruchaka", "Raj", "Chandra-Mangala"}
ANCHOR_STEMS = {"Sasa", "Hamsa", "Gajakesari", "Amala"}
# Only cautions about HOW someone decides are shown to a partner. Anything about a person's inner or
# emotional life (e.g. "emotional support can feel thin") is theirs alone and never leaves their own chart.
WATCH_SHOWN = {"Grahan", "Guru-Chandala"}
PACE_FAST_MIN, PACE_SLOW_MAX = 2, -1       # tech-net minus property-net: >=2 fast, <=-1 slow, else steady
SHIFT_HORIZON_DAYS = 800                    # a chapter change further out than ~2 years is not "now"
MAX_CAREFUL = 3

NOTE = {
    "en": "This describes how you each tend to work and when to be careful. It does not predict funding or whether the venture will succeed.",
    "es": "Esto describe cómo suelen trabajar cada uno y cuándo tener cuidado. No predice financiamiento ni si el proyecto tendrá éxito.",
    "pt": "Isto descreve como cada um costuma trabalhar e quando ter cuidado. Não prevê financiamento nem se o negócio terá sucesso.",
    "hinglish": "Ye batata hai ki aap dono aam taur par kaise kaam karte hain aur kab savdhaan rehna hai. Ye funding ya venture ki safalta ki bhavishyavaani nahin karta.",
}
ROLE_LABEL = {
    "en": {"driver": "The driver", "anchor": "The anchor", "steady": "The steady hand"},
    "es": {"driver": "Quien impulsa", "anchor": "Quien ancla", "steady": "La mano firme"},
    "pt": {"driver": "Quem impulsiona", "anchor": "Quem ancora", "steady": "A mão firme"},
    "hinglish": {"driver": "Aage badhane wala", "anchor": "Sambhalne wala", "steady": "Sthir haath"},
}
ROLE_LINE = {
    "en": {"driver": "Sets the pace, starts things and takes the bets.",
           "anchor": "Tests the bets, holds the long view and keeps commitments steady.",
           "steady": "Moves at an even pace and can lean either way as the work needs."},
    "es": {"driver": "Marca el ritmo, empieza las cosas y asume las apuestas.",
           "anchor": "Pone a prueba las apuestas, sostiene la visión a largo plazo y mantiene firmes los compromisos.",
           "steady": "Avanza a un ritmo parejo y puede inclinarse hacia un lado u otro según lo pida el trabajo."},
    "pt": {"driver": "Define o ritmo, começa as coisas e assume as apostas.",
           "anchor": "Testa as apostas, mantém a visão de longo prazo e dá firmeza aos compromissos.",
           "steady": "Anda num ritmo parelho e pode pender para um lado ou outro conforme o trabalho pede."},
    "hinglish": {"driver": "Raftaar tay karta hai, cheezein shuru karta hai aur daanv lagata hai.",
                 "anchor": "Daanv ko parakhta hai, lambi nazar rakhta hai aur commitments ko sthir rakhta hai.",
                 "steady": "Barabar raftaar se chalta hai aur kaam ke hisaab se kisi bhi taraf jhuk sakta hai."},
}
PACE_LINE = {
    "en": {"fast": "Tends to move fast and think in terms of scale.", "slow": "Tends to build slowly and for the long hold.",
           "steady": "Tends to move at a steady, even pace."},
    "es": {"fast": "Suele moverse rápido y pensar en escala.", "slow": "Suele construir despacio y para el largo plazo.",
           "steady": "Suele avanzar a un ritmo parejo."},
    "pt": {"fast": "Costuma agir rápido e pensar em escala.", "slow": "Costuma construir devagar e para o longo prazo.",
           "steady": "Costuma andar num ritmo parelho."},
    "hinglish": {"fast": "Aam taur par tez chalta hai aur bade scale mein sochta hai.", "slow": "Aam taur par dheere aur lambe samay ke liye banata hai.",
                 "steady": "Aam taur par barabar raftaar se chalta hai."},
}
MODE_LINE = {
    "en": {"owns": "Leans towards building and owning, not just working inside someone else's structure.",
           "structure": "Works best with a clear structure and a defined mandate."},
    "es": {"owns": "Se inclina por construir y ser dueño, no solo trabajar dentro de la estructura de otro.",
           "structure": "Trabaja mejor con una estructura clara y un mandato definido."},
    "pt": {"owns": "Inclina-se a construir e ser dono, e não só trabalhar dentro da estrutura de outro.",
           "structure": "Trabalha melhor com uma estrutura clara e um mandato definido."},
    "hinglish": {"owns": "Banane aur malik banne ki taraf jhukta hai, sirf kisi aur ke dhaanche mein kaam karne ki nahin.",
                 "structure": "Saaf dhaanche aur tay zimmedaari ke saath sabse achha kaam karta hai."},
}
NOTHING_FLAGGED = {
    "en": "Nothing flagged in the chart.", "es": "No hay nada señalado en la carta.",
    "pt": "Nada sinalizado no mapa.", "hinglish": "Chart mein kuch flag nahin hua.",
}
BALANCE = {
    "split": {
        "en": "{driver} sets the pace and takes the bets; {anchor} tests them and holds the long view. Let {driver} propose and {anchor} sign off on anything large or hard to undo.",
        "es": "{driver} marca el ritmo y asume las apuestas; {anchor} las pone a prueba y sostiene la visión a largo plazo. Que {driver} proponga y {anchor} dé el visto bueno a todo lo grande o difícil de deshacer.",
        "pt": "{driver} define o ritmo e assume as apostas; {anchor} as testa e mantém a visão de longo prazo. Que {driver} proponha e {anchor} aprove tudo o que for grande ou difícil de desfazer.",
        "hinglish": "{driver} raftaar tay karta hai aur daanv lagata hai; {anchor} use parakhta hai aur lambi nazar rakhta hai. {driver} prastav rakhe aur {anchor} har bade ya palatne mushkil faisle par mohar lagaye.",
    },
    "two_drivers": {
        "en": "You both lean towards leading. Agree up front who has the final say in each area, or you will each push at once.",
        "es": "Los dos se inclinan por liderar. Acuerden desde el principio quién tiene la última palabra en cada área, o los dos empujarán a la vez.",
        "pt": "Os dois se inclinam a liderar. Combinem desde o início quem tem a palavra final em cada área, ou os dois vão empurrar ao mesmo tempo.",
        "hinglish": "Aap dono netritva ki taraf jhukte hain. Shuru mein hi tay karein ki har area mein antim faisla kiska hoga, nahin to dono ek saath dhakelenge.",
    },
    "two_anchors": {
        "en": "You both lean towards caution. Agree who goes first on each new step, or things may wait on each other.",
        "es": "Los dos se inclinan por la cautela. Acuerden quién da el primer paso en cada novedad, o las cosas pueden quedar esperándose.",
        "pt": "Os dois se inclinam à cautela. Combinem quem dá o primeiro passo em cada novidade, ou as coisas podem ficar esperando uma pela outra.",
        "hinglish": "Aap dono savdhaani ki taraf jhukte hain. Har naye kadam par tay karein ki pehla kadam kaun uthayega, nahin to kaam ek doosre ka intezaar karega.",
    },
    "even": {
        "en": "Your styles are close enough that the split is yours to choose. Write down who owns what.",
        "es": "Sus estilos se parecen lo bastante como para que el reparto sea suyo. Escriban quién se encarga de qué.",
        "pt": "Os estilos de vocês são parecidos o bastante para a divisão ser de vocês. Escrevam quem fica com o quê.",
        "hinglish": "Aapke tareeke itne milte-julte hain ki baantna aap par hai. Likh lein ki kaun kya sambhalega.",
    },
}
LENS_TAIL = {
    "cofounder": {
        "en": "Decide equity and who holds which decision, in writing, before the next big step.",
        "es": "Decidan por escrito la participación y quién toma cada decisión, antes del próximo paso grande.",
        "pt": "Decidam por escrito a participação e quem toma cada decisão, antes do próximo passo grande.",
        "hinglish": "Agle bade kadam se pehle equity aur kaun sa faisla kiska hai, likhit mein tay karein.",
    },
    "business": {
        "en": "Keep the money terms and who signs in writing.",
        "es": "Dejen por escrito las condiciones de dinero y quién firma.",
        "pt": "Deixem por escrito as condições de dinheiro e quem assina.",
        "hinglish": "Paise ki sharten aur kaun sign karega, likhit mein rakhein.",
    },
}
DONT = {
    "careful": {
        "en": "Don't sign or commit big money during {ranges}.",
        "es": "No firmen ni comprometan mucho dinero durante {ranges}.",
        "pt": "Não assinem nem comprometam muito dinheiro durante {ranges}.",
        "hinglish": "{ranges} ke dauran bada paisa sign ya commit na karein.",
    },
    "careful_none": {
        "en": "Don't sign or commit big money while either of you is in a careful stretch. Check the Windows tab first.",
        "es": "No firmen ni comprometan mucho dinero mientras alguno esté en un tramo de cuidado. Revisen primero la pestaña de ventanas.",
        "pt": "Não assinem nem comprometam muito dinheiro enquanto um dos dois estiver num trecho de cuidado. Vejam antes a aba de janelas.",
        "hinglish": "Jab tak aap mein se koi savdhaani wale stretch mein ho, bada paisa sign ya commit na karein. Pehle Windows tab dekhein.",
    },
    "heat": {
        "en": "Don't decide big things in the heat of the moment. Wait a day.",
        "es": "No decidan cosas grandes en caliente. Esperen un día.",
        "pt": "Não decidam coisas grandes no calor do momento. Esperem um dia.",
        "hinglish": "Bade faisle gusse ya jald-baazi mein na lein. Ek din ruk jaayein.",
    },
    "titles": {
        "en": "Don't split by title. Name who has the final say on each area, and put decisions in writing.",
        "es": "No se repartan por cargo. Nombren quién tiene la última palabra en cada área y dejen las decisiones por escrito.",
        "pt": "Não dividam por cargo. Nomeiem quem tem a palavra final em cada área e deixem as decisões por escrito.",
        "hinglish": "Pad ke hisaab se na baantein. Tay karein ki har area mein antim faisla kiska hai, aur faisle likhit mein rakhein.",
    },
}
TIMING_LINE = {
    "open": {
        "en": "Your best shared window for {topic}: {range}.",
        "es": "Su mejor ventana compartida para {topic}: {range}.",
        "pt": "A melhor janela compartilhada de vocês para {topic}: {range}.",
        "hinglish": "{topic} ke liye aap dono ki sabse achhi shared window: {range}.",
    },
    "none": {
        "en": "Your charts don't share an open window to raise or sign in the periods we can date. If you have to move, do it outside the careful stretches.",
        "es": "Sus cartas no comparten una ventana abierta para levantar fondos o firmar en los periodos que podemos fechar. Si tienen que moverse, háganlo fuera de los tramos de cuidado.",
        "pt": "Os mapas de vocês não compartilham uma janela aberta para captar ou assinar nos períodos que conseguimos datar. Se precisarem agir, façam isso fora dos trechos de cuidado.",
        "hinglish": "Jin samayon ko hum date kar sakte hain unmein aap dono ke charts ki funding ya sign karne ke liye koi common khuli window nahin hai. Agar karna hi pade to savdhaani wale stretch ke baahar karein.",
    },
}
SHIFT = {
    "en": "{name} moves into a season of {to} on {on}.",
    "es": "{name} entra en una etapa de {to} el {on}.",
    "pt": "{name} entra numa fase de {to} em {on}.",
    "hinglish": "{name} {on} ko {to} ke daur mein pravesh karta hai.",
}
TEXTS = (NOTE, ROLE_LABEL, ROLE_LINE, PACE_LINE, MODE_LINE, NOTHING_FLAGGED, BALANCE["split"], BALANCE["two_drivers"],
         BALANCE["two_anchors"], BALANCE["even"], LENS_TAIL["cofounder"], LENS_TAIL["business"], DONT["careful"],
         DONT["careful_none"], DONT["heat"], DONT["titles"], TIMING_LINE["open"], TIMING_LINE["none"], SHIFT)


def lens_for(relation: Optional[str]) -> Optional[str]:
    """What the other person is to the viewer -> a brief lens, or None (no brief for other relations yet)."""
    return {"cofounder": "cofounder", "business": "business"}.get(str(relation or ""))


def _stem(name) -> str:
    from antar_engine.yogas import _yoga_stem
    return _yoga_stem(name)


def _pace(cd: dict, dashas: dict) -> str:
    try:
        from antar_engine.domain_fit import fit_all_domains
        fits = fit_all_domains(cd, dashas)
        diff = fits["tech"]["net"] - fits["property"]["net"]
        return "fast" if diff >= PACE_FAST_MIN else "slow" if diff <= PACE_SLOW_MAX else "steady"
    except Exception:
        return "steady"


def _owns(cd: dict) -> Optional[bool]:
    try:
        from antar_engine.career_mode import career_mode
        m = career_mode(cd)
        return bool(m.get("ownership") == "owned" and m.get("mode") in ("venture", "business"))
    except Exception:
        return None


def role_of(pace: str, stems: List[str]) -> str:
    drv = (2 if pace == "fast" else 0) + sum(1 for s in stems if s in DRIVER_STEMS)
    anc = (2 if pace == "slow" else 0) + sum(1 for s in stems if s in ANCHOR_STEMS)
    return "driver" if drv > anc else "anchor" if anc > drv else "steady"


def _fit_parts(cd: dict, dashas: dict, lang: str, today: date) -> dict:
    """temperament, partnership lean (with plain reasons) and the running season, from circle_fit."""
    from antar_engine import circle_fit as F
    t = F.temperament(cd)
    out = {"temperament": {"trait": t["trait"]} if t else None, "partnership": None, "season": None}   # the star name is never shown
    try:
        pl = F.partnership_lean(cd)
        out["partnership"] = {"lean": pl["lean"], "label": CC.pick(F.LEAN_LABEL[pl["lean"]], lang),
                              "reasons": [CC.pick(F.REASON[k], lang) for k in pl["reasons"]][:3]}
        se = F.season_at(cd, (dashas or {}).get("vimsottari"), today)
        if se:
            out["season"] = {"theme": se["theme"], "label": CC.pick(F.THEME_LABEL, lang)[se["theme"]], "heavy": se["heavy"],
                             "ends": se["ends"].isoformat(), "ends_label": C.day_label_y(se["ends"], lang)}
    except Exception:
        pass
    return out


def profile(cd: dict, dashas: dict, name: str, lang: str = "en", today: Optional[date] = None) -> dict:
    """One person's working profile. `strong_at` / `watch_for` are [{title, effect}] ( `effect` is English and is
    translated by the route; titles are localized); `watch_for` is [] when nothing is flagged."""
    from antar_engine.yogas import plain_yoga
    lang = CC.lang_of(lang)
    stems, strong, watch = [], [], []
    for y in (cd or {}).get("yogas") or []:
        if not (isinstance(y, dict) and y.get("name")):
            continue
        p = plain_yoga(y["name"], lang)
        stems.append(_stem(y["name"]))
        row = {"title": p["title"], "effect": p["effect_en"] or y.get("effect", ""), "_s": y.get("strength", "")}
        if p["kind"] == "strength":
            strong.append(row)
        elif _stem(y["name"]) in WATCH_SHOWN:
            watch.append(row)
    rank = {"strong": 0, "moderate": 1, "weak": 2}
    for lst in (strong, watch):
        lst.sort(key=lambda r: rank.get(str(r["_s"]).lower(), 3))
    pace = _pace(cd, dashas)
    role = role_of(pace, stems)
    owns = _owns(cd)
    how = [CC.pick(PACE_LINE, lang)[pace]]
    if owns is not None:
        how.append(CC.pick(MODE_LINE, lang)["owns" if owns else "structure"])
    shift = None
    try:
        from antar_engine.chart_identity import build_chart_identity
        cp = (build_chart_identity(cd, (dashas or {}).get("vimsottari"), name=name, today=today, language=lang) or {}).get("current_period") or {}
        on = cp.get("next_shift_on")
        if on and cp.get("next_shift_to"):
            d = date.fromisoformat(str(on)[:10])
            if 0 <= (d - (today or date.today())).days <= SHIFT_HORIZON_DAYS:
                shift = {"on": d.isoformat(), "label": C.day_label_y(d, lang), "to": cp["next_shift_to"]}
    except Exception:
        shift = None
    strip = lambda rows: [{"title": r["title"], "effect": r["effect"]} for r in rows]
    fit = _fit_parts(cd, dashas, lang, today or date.today())
    return {"first_name": name, "role": role, "role_label": CC.pick(ROLE_LABEL, lang)[role],
            "temperament": fit["temperament"], "partnership": fit["partnership"], "season": fit["season"],
            "role_line": CC.pick(ROLE_LINE, lang)[role], "pace": pace, "how_you_work": how,
            "strong_at": strip(strong[:3]), "watch_for": strip(watch[:2]),
            "watch_for_none": CC.pick(NOTHING_FLAGGED, lang) if not watch else None, "shift": shift}


def balance(a: dict, b: dict, lens: str, lang: str = "en") -> dict:
    """The split line for two profiles (any order) + the lens-specific tail."""
    lang = CC.lang_of(lang)
    ra, rb = a["role"], b["role"]
    if {ra, rb} == {"driver", "anchor"}:
        d, n = (a, b) if ra == "driver" else (b, a)
        kind, line = "split", CC.pick(BALANCE["split"], lang).format(driver=d["first_name"], anchor=n["first_name"])
    elif ra == rb == "driver":
        kind, line = "two_drivers", CC.pick(BALANCE["two_drivers"], lang)
    elif ra == rb == "anchor":
        kind, line = "two_anchors", CC.pick(BALANCE["two_anchors"], lang)
    else:
        kind, line = "even", CC.pick(BALANCE["even"], lang)
    return {"kind": kind, "line": line, "tail": CC.pick(LENS_TAIL[lens], lang)}


def _range(w: dict, lang: str, today: Optional[date]) -> str:
    from antar_engine.circle_overlap import _range as rng
    return rng(date.fromisoformat(w["start"]), date.fromisoformat(w["end"]), lang, today)


def timing(topics: List[dict], lens: str, lang: str = "en", today: Optional[date] = None) -> dict:
    """From the pair page's topics: the shared open windows and the careful stretches for money / business
    (+ career for cofounders), earliest first. No overlap -> the plain 'none' line."""
    lang = CC.lang_of(lang)
    want = {"money", "business"} | ({"career"} if lens == "cofounder" else set())
    open_, care = [], []
    for tp in topics or []:
        if tp.get("topic") not in want:
            continue
        for kind, bucket in (("best", open_), ("care", care)):
            for w in tp.get(kind) or []:
                bucket.append({"topic": tp["topic"], "label": tp["label"], "start": w["start"], "end": w["end"],
                               "range": w["label"], "days": w["days"]})
    open_.sort(key=lambda w: w["start"]); care.sort(key=lambda w: w["start"])
    if open_:
        w = open_[0]
        line = CC.pick(TIMING_LINE["open"], lang).format(topic=w["label"].lower(), range=w["range"])
    else:
        line = CC.pick(TIMING_LINE["none"], lang)
    return {"line": line, "shared_open": open_[:MAX_CAREFUL], "careful": care[:MAX_CAREFUL]}


def donts(careful: List[dict], profiles: List[dict], lang: str = "en") -> List[str]:
    lang = CC.lang_of(lang)
    out = []
    if careful:
        ranges = "; ".join(f"{w['range']} ({w['label'].lower()})" for w in careful[:MAX_CAREFUL])
        out.append(CC.pick(DONT["careful"], lang).format(ranges=ranges))
    else:
        out.append(CC.pick(DONT["careful_none"], lang))
    if any(p["watch_for"] for p in profiles) or any(p["role"] == "driver" for p in profiles):
        out.append(CC.pick(DONT["heat"], lang))
    out.append(CC.pick(DONT["titles"], lang))
    return out[:3]


def build(me: dict, other: dict, lens: str, topics: List[dict], fit: Optional[dict], moves: Optional[list],
          lang: str = "en", today: Optional[date] = None, phase: Optional[dict] = None) -> dict:
    """The whole brief from two profiles + the pair page's topics. `me` first. Pure."""
    from antar_engine import circle_fit as F
    lang = CC.lang_of(lang)
    leans = [{"first_name": p["first_name"], "lean": (p.get("partnership") or {}).get("lean", "either")} for p in (me, other)]
    verdict = F.verdict(leans[0], leans[1], {me["role"], other["role"]} == {"driver", "anchor"}, lang)
    tm = timing(topics, lens, lang, today)
    shifts = [{"first_name": p["first_name"], **p["shift"],
               "line": CC.pick(SHIFT, lang).format(name=p["first_name"], to=p["shift"]["to"], on=p["shift"]["label"])}
              for p in (me, other) if p.get("shift")]
    return {"lens": lens, "verdict": verdict, "phase": phase, "fit": fit, "people": [me, other], "balance": balance(me, other, lens, lang),
            "timing": dict(tm, shifts=shifts), "donts": donts(tm["careful"], [me, other], lang),
            "moves": moves or [], "note": CC.pick(NOTE, lang)}
