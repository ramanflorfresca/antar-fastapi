"""[divorced-marriage 2026-10-11] "Will my marriage improve?" asked by someone who is DIVORCED or SEPARATED.

The old answer treated it as one question and mixed two engines: the new-union window ("not until Nov 2027") leaked into a read that also talked
about "rebuilding", while "Will my ex come back?" on the same chart said a reconnection window was OPEN NOW. A divorced reader is asking two things:

  1. can the bond with the former spouse be REBUILT   -> the RECONCILIATION event engine (the one the ex-question uses)
  2. is a NEW partnership coming                      -> the MARRIAGE event engine (the one "will I get married?" uses)

This composes one answer naming both, from the engines' own verdict + window, so it can never disagree with either question asked alone. It makes no
claim about what the other person feels or will do (the chart shows the reader's timing and what supports it) and never says the marriage is over
or can't be saved. Deterministic; en / es / pt. The move comes separately (answer_polish -> ask_basis.existing_union_move: decide rebuild / closure / new start)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from antar_engine import decision_i18n as I18

_TX = {
    "en": {
        "open": "You're {status}, so there are two separate questions here, and the timing answers them differently.",
        "re_h": "Rebuilding with {them}: ", "new_h": "A new partnership: ",
        "now": "a window is open now, through {end}.", "soon": "the supportive window opens {start} – {end}; until then it is groundwork, not a reconnection.",
        "no_re": "the timing shows no supported window in the next two years — put your effort into what you can decide yourself.",
        "now_n": "a window is open now, through {end}.", "soon_n": "the next supportive window is {start} – {end}; before it, build the ground rather than the commitment.",
        "no_n": "the timing shows no supported window in the next two years.",
        "close": "The timing shows what supports you; it cannot show what the other person will do.",
        "k_lasts": "Because you're {status}, the question of whether your marriage lasts becomes whether the bond with {them} can be rebuilt.",
        "k_patch": "This is about {them}, so here is the timing for that.",
        "k_year": "Looking at the next twelve months:",
        "k_year_in": "a window opens {start} – {end}, inside the next twelve months.",
        "k_year_out": "nothing opens this year — the next supportive window is {start} – {end}.",
        "k_year_none": "the timing shows no supported window in the next two years.",
        "k_year_re": "Separately, rebuilding with {them}: ",
        "k_wm": "You're deciding between waiting on {them} and building something new — here is what the timing supports for each.",
        "d_wait": "Waiting has a reason only inside the rebuilding window above: make one clear attempt there, then decide.",
        "d_move": "The timing supports moving forward more than waiting: put your effort into what you are building, not into a reply.",
        "d_none": "Neither window opens in the next two years, so decide on what you want, not on a date.",
        "d_both": "Both are possible and the earlier one is {first}; choose by what you want, not by the date.",
        "sep_re": "Separately, a new partnership: ",
        "divorced": "divorced", "separated": "separated", "them_d": "your former spouse", "them_s": "your spouse",
    },
    "es": {
        "open": "Estás {status}, así que aquí hay dos preguntas distintas, y los tiempos las responden de forma diferente.",
        "re_h": "Reconstruir el vínculo con {them}: ", "new_h": "Una nueva pareja: ",
        "now": "hay una ventana abierta ahora, hasta {end}.", "soon": "la ventana favorable se abre {start} – {end}; hasta entonces es preparar el terreno, no una reconexión.",
        "no_re": "los tiempos no muestran una ventana favorable en los próximos dos años: pon tu esfuerzo en lo que tú puedes decidir.",
        "now_n": "hay una ventana abierta ahora, hasta {end}.", "soon_n": "la próxima ventana favorable es {start} – {end}; antes de ella, construye el terreno y no el compromiso.",
        "no_n": "los tiempos no muestran una ventana favorable en los próximos dos años.",
        "close": "Los tiempos muestran qué te respalda; no pueden mostrar lo que hará la otra persona.",
        "k_lasts": "Como estás {status}, la pregunta de si tu matrimonio dura se convierte en si el vínculo con {them} puede reconstruirse.",
        "k_patch": "Esto es sobre {them}, así que aquí está el momento para eso.",
        "k_year": "Mirando los próximos doce meses:",
        "k_year_in": "se abre una ventana {start} – {end}, dentro de los próximos doce meses.",
        "k_year_out": "este año no se abre nada: la próxima ventana favorable es {start} – {end}.",
        "k_year_none": "los tiempos no muestran una ventana favorable en los próximos dos años.",
        "k_year_re": "Por separado, reconstruir el vínculo con {them}: ",
        "k_wm": "Estás decidiendo entre esperar a {them} y construir algo nuevo: esto es lo que los tiempos respaldan en cada caso.",
        "d_wait": "Esperar solo tiene sentido dentro de la ventana de reconstrucción de arriba: haz un intento claro ahí y luego decide.",
        "d_move": "Los tiempos respaldan más avanzar que esperar: pon tu esfuerzo en lo que estás construyendo, no en una respuesta.",
        "d_none": "Ninguna ventana se abre en los próximos dos años, así que decide por lo que quieres, no por una fecha.",
        "d_both": "Ambas son posibles y la más cercana es {first}; elige por lo que quieres, no por la fecha.",
        "sep_re": "Por separado, una nueva pareja: ",
        "divorced": "divorciado o divorciada", "separated": "separado o separada", "them_d": "tu ex pareja", "them_s": "tu pareja",
    },
    "pt": {
        "open": "Você está {status}, então aqui há duas perguntas diferentes, e o momento as responde de formas diferentes.",
        "re_h": "Reconstruir o vínculo com {them}: ", "new_h": "Um novo relacionamento: ",
        "now": "há uma janela aberta agora, até {end}.", "soon": "a janela favorável abre {start} – {end}; até lá é preparar o terreno, não uma reaproximação.",
        "no_re": "o momento não mostra uma janela favorável nos próximos dois anos: ponha seu esforço no que você mesmo pode decidir.",
        "now_n": "há uma janela aberta agora, até {end}.", "soon_n": "a próxima janela favorável é {start} – {end}; antes dela, construa o terreno e não o compromisso.",
        "no_n": "o momento não mostra uma janela favorável nos próximos dois anos.",
        "close": "O momento mostra o que o sustenta; não pode mostrar o que a outra pessoa vai fazer.",
        "k_lasts": "Como você está {status}, a pergunta de se o seu casamento dura vira a pergunta de se o vínculo com {them} pode ser reconstruído.",
        "k_patch": "Isto é sobre {them}, então aqui está o momento para isso.",
        "k_year": "Olhando os próximos doze meses:",
        "k_year_in": "uma janela abre {start} – {end}, dentro dos próximos doze meses.",
        "k_year_out": "nada abre este ano — a próxima janela favorável é {start} – {end}.",
        "k_year_none": "o momento não mostra uma janela favorável nos próximos dois anos.",
        "k_year_re": "Separadamente, reconstruir o vínculo com {them}: ",
        "k_wm": "Você está decidindo entre esperar por {them} e construir algo novo — veja o que o momento sustenta em cada caso.",
        "d_wait": "Esperar só faz sentido dentro da janela de reconstrução acima: faça uma tentativa clara ali e depois decida.",
        "d_move": "O momento sustenta mais seguir em frente do que esperar: ponha seu esforço no que está construindo, não numa resposta.",
        "d_none": "Nenhuma janela abre nos próximos dois anos, então decida pelo que você quer, não por uma data.",
        "d_both": "Ambas são possíveis e a mais próxima é {first}; escolha pelo que quer, não pela data.",
        "sep_re": "Separadamente, um novo relacionamento: ",
        "divorced": "divorciado ou divorciada", "separated": "separado ou separada", "them_d": "seu ex-cônjuge", "them_s": "seu cônjuge",
    },
}


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _state(ee: Optional[dict], today: date) -> dict:
    """{state: open_now | upcoming | none, start, end} from an event-engine result (client verdict + window)."""
    try:
        v = (ee or {}).get("verdict") or {}
        win = v.get("window") or {}
        s, e = _d(win.get("start")), _d(win.get("end"))
        client = (ee or {}).get("client_verdict")
        if client in ("YES", "LIKELY") and s and e and e >= today:
            return {"state": "open_now" if s <= today else "upcoming", "start": max(s, today), "end": e}      # never show a start in the past
        if client == "NOT_YET" and s and e and e >= today:
            return {"state": "upcoming", "start": s, "end": e}
        if client in ("YES", "LIKELY") and s and e and e < today:
            return {"state": "none", "start": None, "end": None}
    except Exception:
        pass
    return {"state": "none", "start": None, "end": None}


_K_PATCH = re.compile(r"(?i)\b(patch\s+up|get\s+back\s+together|back\s+together|reconcil\w*|make\s+up|rebuild|reunit\w*|reunion|volver\s+con|volver\s+a\s+estar|reconcili\w*|voltar\s+com|voltar\s+a\s+ficar)\b")
_K_WAIT = re.compile(r"(?i)\b(wait\s+(?:for|on)\b[^?]{0,30}\bor\b|or\s+move\s+on|move\s+on\s+or|should\s+i\s+(?:wait|move\s+on|let\s+go)|esperar[^?]{0,30}\bo\b[^?]{0,20}\bseguir|seguir\s+adelante\s+o|esperar[^?]{0,30}\bou\b[^?]{0,20}\bseguir)\b")
_K_YEAR = re.compile(r"(?i)\b(this\s+year|within\s+(?:the\s+)?(?:next\s+)?(?:12|twelve)\s+months|este\s+a[ñn]o|este\s+ano|next\s+12\s+months)\b")
_K_LASTS = re.compile(r"(?i)\b(last|survive|work\s+out|make\s+it|durar\w*|dura|funcionar\w*|sobreviv\w*)\b")


def question_kind(question: str) -> str:
    """'wait_or_move' | 'patch' | 'year' | 'lasts' | 'both' - which of the two questions a divorced / separated
    reader is really asking, so the answer leads with it instead of returning the same block for all of them."""
    q = question or ""
    if _K_WAIT.search(q):
        return "wait_or_move"
    if _K_PATCH.search(q):
        return "patch"
    if _K_YEAR.search(q):
        return "year"
    if _K_LASTS.search(q):
        return "lasts"
    return "both"


def compose(rebuild_ee: Optional[dict], new_ee: Optional[dict], marital_status: str, language: str = "en",
            today: Optional[date] = None, question: str = "") -> Optional[dict]:
    """{read, timing, rebuild_state, new_state} or None (single / widowed reader, unknown language, no engine result at all)."""
    try:
        ms = (marital_status or "").lower().strip()
        if language not in _TX or ms not in ("divorced", "separated") or (rebuild_ee is None and new_ee is None):
            return None
        tx = _TX[language]
        today = today or datetime.utcnow().date()
        r, n = _state(rebuild_ee, today), _state(new_ee, today)
        my = lambda d: I18.month_year(d, language)
        them = tx["them_d" if ms == "divorced" else "them_s"]

        def line(st, now_k, soon_k, none_k):
            if st["state"] == "open_now":
                return tx[now_k].format(end=my(st["end"]))
            if st["state"] == "upcoming":
                return tx[soon_k].format(start=my(st["start"]), end=my(st["end"]))
            return tx[none_k]
        a = line(r, "now", "soon", "no_re")
        b = line(n, "now_n", "soon_n", "no_n")
        kind = question_kind(question)
        status = tx[ms]
        rebuild_l = tx["re_h"].format(them=them) + a
        new_l = tx["new_h"] + b
        pick = r if r["state"] != "none" else n
        if kind == "patch":
            parts = [tx["k_patch"].format(them=them), rebuild_l] + ([tx["sep_re"] + b] if n["state"] != "none" else []) + [tx["close"]]
            pick = r if r["state"] != "none" else n
        elif kind == "lasts":
            parts = [tx["k_lasts"].format(status=status, them=them), rebuild_l, tx["close"]]
            pick = r if r["state"] != "none" else n
        elif kind == "year":
            horizon = today + timedelta(days=365)
            if n["state"] == "open_now":
                yl = tx["now_n"].format(end=my(n["end"]))
            elif n["state"] == "upcoming" and n["start"] <= horizon:
                yl = tx["k_year_in"].format(start=my(n["start"]), end=my(n["end"]))
            elif n["state"] == "upcoming":
                yl = tx["k_year_out"].format(start=my(n["start"]), end=my(n["end"]))
            else:
                yl = tx["k_year_none"]
            parts = [tx["k_year"], tx["new_h"] + yl] + ([tx["k_year_re"].format(them=them) + a] if r["state"] != "none" else []) + [tx["close"]]
            pick = n if n["state"] != "none" else r
        elif kind == "wait_or_move":
            soon = lambda st: st["state"] == "open_now" or (st["state"] == "upcoming" and st["start"] <= today + timedelta(days=183))
            if r["state"] != "none" and soon(r):
                d = tx["d_wait"]
            elif r["state"] == "none" and n["state"] != "none":
                d = tx["d_move"]
            elif r["state"] == "none" and n["state"] == "none":
                d = tx["d_none"]
            else:
                first = min((x for x in (r, n) if x["state"] != "none"), key=lambda x: x["start"])
                d = tx["d_both"].format(first=f"{my(first['start'])} – {my(first['end'])}")
            parts = [tx["k_wm"].format(them=them), rebuild_l, new_l, d, tx["close"]]
            live = [x for x in (r, n) if x["state"] != "none"]
            pick = min(live, key=lambda x: x["start"]) if live else r
        else:
            parts = [tx["open"].format(status=status), rebuild_l, new_l, tx["close"]]
        read = "\n".join(parts)
        timing = f"{my(pick['start'])} – {my(pick['end'])}" if pick["state"] != "none" else None
        return {"read": read, "timing": timing, "rebuild_state": r["state"], "new_state": n["state"], "kind": kind}
    except Exception:
        return None
