"""[divorced-marriage 2026-10-11] "Will my marriage improve?" asked by someone who is DIVORCED or SEPARATED.

The old answer treated it as one question and mixed two engines: the new-union window ("not until Nov 2027") leaked into a read that also talked
about "rebuilding", while "Will my ex come back?" on the same chart said a reconnection window was OPEN NOW. A divorced reader is asking two things:

  1. can the bond with the former spouse be REBUILT   -> the RECONCILIATION event engine (the one the ex-question uses)
  2. is a NEW partnership coming                      -> the MARRIAGE event engine (the one "will I get married?" uses)

This composes one answer naming both, from the engines' own verdict + window, so it can never disagree with either question asked alone. It makes no
claim about what the other person feels or will do (the chart shows the reader's timing and what supports it) and never says the marriage is over
or can't be saved. Deterministic; en / es / pt. The move comes separately (answer_polish -> ask_basis.existing_union_move: decide rebuild / closure / new start)."""
from __future__ import annotations

from datetime import date, datetime
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


def compose(rebuild_ee: Optional[dict], new_ee: Optional[dict], marital_status: str, language: str = "en",
            today: Optional[date] = None) -> Optional[dict]:
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
        read = "\n".join([tx["open"].format(status=tx[ms]), tx["re_h"].format(them=them) + a, tx["new_h"] + b, tx["close"]])
        pick = r if r["state"] != "none" else n
        timing = f"{my(pick['start'])} – {my(pick['end'])}" if pick["state"] != "none" else None
        return {"read": read, "timing": timing, "rebuild_state": r["state"], "new_state": n["state"]}
    except Exception:
        return None
