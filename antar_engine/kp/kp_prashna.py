"""
kp_prashna.py  —  the KP Prashna (horary) engine behind Ask → Yes / No
=====================================================================

Spec: Antar.world/SPEC_ASK_YESNO_KP_PRASHNA.md

One sincere question → one horary chart → a verdict, a window, and a stored
claim we reconcile later ("did it happen?"). Python decides everything; the
narrator only renders the bundle. Never raises into the caller.

----------------------------------------------------------------------------
AUDITABLE DOCTRINAL CHOICES
----------------------------------------------------------------------------
  SEAT OF JUDGMENT
    KP casts a horary for the place and moment the ASTROLOGER judges it. Antar
    is the astrologer, so the seat is fixed: Edgewater, NJ (ASTROLOGER_SEAT).
    The querent's location is irrelevant to a KP horary — that is what the
    1-249 number is for.

  NUMBER vs MOMENT
    number given (1-249) -> classic KP number horary (kp_horary.cast_horary):
                            the number fixes the ascendant.
    no number            -> moment horary: real Placidus cusps for the seat
                            at the moment of judgment.
    Planets + Ruling Planets are always the MOMENT at the seat.

  VERDICT
    kp_significators.verdict on the horary chart (cuspal sub-lord rule).

  NATAL PROMISE (damper, not a veto)
    The same question type is judged on the natal KP chart. A horary YES that
    the birth chart does not promise is softened to CONDITIONAL. A horary NO is
    never upgraded by the natal chart. Skipped when the birth time is flagged
    needs_reconfirm or birth data is missing.

  HORIZON
    "in the next 30 days", "this month", "today"... is parsed (EN/ES/PT/Hinglish).
    A horary YES whose ruling-planet-confirmed window opens AFTER the horizon
    becomes NOT_NOW ("it comes, later than you asked").

  LEAN (4 states)  yes | not_now | conditional | no
    The FE still receives a strict binary `verdict` (YES only for lean=yes);
    `lean` carries the nuance.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

ASTROLOGER_SEAT = {
    "name": "Edgewater, NJ",
    "lat": 40.8270,
    "lon": -73.9757,
    "tz": "America/New_York",
}

LEANS = ("yes", "not_now", "conditional", "no")

# --------------------------------------------------------------------------
# Question → KP question type.  (keywords, question_type, loss_house)
# Order matters: specific before generic. EN / ES / PT / Hinglish — English-
# only keyword logic is a silent correctness bug for non-English askers.
# --------------------------------------------------------------------------
_QT_RULES = [
    # separation / ending — Bhavat Bhavam on the 7th
    (("divorce", "separat", "break up", "breakup", "split up", "divorc",
      "ruptura", "terminar con", "talaq", "alag ho"), "loss", 7),
    (("marry", "marriage", "wedding", "engaged", "propose", "casar", "boda",
      "matrimonio", "casamento", "shaadi", "shadi", "vivah", "rishta"),
     "marriage", None),
    # a specific person returning / reconciling / reaching out
    (("come back", "comes back", "get back together", "back together",
      "reconcil", "my ex", "text me", "call me", "reach out", "volver",
      "vuelva", "regresar", "voltar", "volte", "wapas", "vapas"), "reunion", None),
    # [kp-romance] a NEW relationship (after reunion: "my girlfriend come back"
    # is a reunion; before job/money so "date" words never fall to gain)
    (("girlfriend", "girl friend", "boyfriend", "boy friend", "a relationship",
      "new relationship", "in a relationship", "relationship with", "dating",
      "go on a date", "fall in love", "find love", "love life", "someone special",
      "soulmate", "soul mate", "crush", "novia", "novio", "pareja", "enamorar",
      "namorada", "namorado", "namoro", "relacionamento", "relación", "relacion",
      "girlfriend", "gf ", "bf ", "pyaar", "pyar", "mohabbat", "ishq",
      "premika", "premi "), "romance", None),
    (("pregnan", "conceiv", "baby", "child", "kids", "fertil", "ivf",
      "embaraz", "bebé", "bebe", "hijo", "gravidez", "grávida", "gravida",
      "filho", "bachcha", "bacha", "santan"), "childbirth", None),
    (("visa", "abroad", "overseas", "foreign", "green card", "h1b", "h-1b",
      "immigra", "emigra", "citizenship", "move abroad", "move overseas",
      "extranjero", "exterior", "videsh", "bahar ja"), "foreign_travel", None),
    (("exam", "admission", "admit", "university", "college", "degree",
      "pass the", "scholarship", "test result", "examen", "universidad",
      "admisión", "admisi", "prova", "vestibular", "faculdade", "pariksha",
      "imtihaan"), "education", None),
    (("promot", "a raise", "pay rise", "salary hike", "hike", "ascens",
      "aumento de sueldo", "aumento de salário", "aumento salarial"),
     "promotion", None),
    (("job", "offer letter", "the offer", "hired", "hire me", "interview",
      "employ", "position", "the role", "trabajo", "empleo", "puesto",
      "emprego", "vaga", "naukri", "naukari"), "job_new", None),
    # [kp-residence] change of residence — after job (a "move to a new job" is
    # a job question), before property ("move to a new house" is a move)
    (("move", "moving", "relocat", "shift house", "shift home", "shift to",
      "shifting", "change my residence", "change residence", "new place to live",
      "settle in", "mudar", "mudanza", "mudarme", "trasladar", "mudança",
      "mudanca", "ghar badal", "ghar badl", "naya ghar", "shift ho"), "residence", None),
    (("house", "home", "property", "apartment", "flat", "plot of land",
      "casa", "propiedad", "piso", "imóvel", "imovel", "apartamento",
      "ghar", "makaan", "zameen", "car", "vehicle", "coche", "carro",
      "gaadi", "gadi"), "property", None),
    (("lawsuit", "litig", "court", "legal case", "the case", "legal", "pleito", "demanda",
      "juicio", "processo", "mukadma", "kesh"), "litigation_win", None),
    (("recover", "heal", "surgery", "health", "cure", "salud", "recuper",
      "saúde", "saude", "theek", "sehat"), "recovery", None),
    (("deal", "contract", "client", "sign the", "signed", "signing", "close the", "closes", "acquisi",
      "trato", "contrato", "cliente", "negócio", "negocio", "sauda"),
     "deal_closes", None),
    (("fund", "investor", "invest", "raise money", "seed", "series a",
      "series b", "round", "loan", "grant", "capital", "money", "payment",
      "paid", "profit", "gain", "financ", "inversi", "dinero", "préstamo",
      "prestamo", "dinheiro", "empréstimo", "emprestimo", "investimento",
      "paisa", "paise", "paisaa", "lakh", "crore"), "gain", None),
    (("lost", "missing", "misplaced", "stolen", "find my", "perdí", "perdi",
      "extravi", "robad", "roubad", "kho gay", "kho gai", "chori"),
     "lost_found", None),
]

# word-START matching: "fund" hits "funding" but "round" never hits "around".
_QT_COMPILED = [
    (re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in keys) + ")"), qt, lh)
    for keys, qt, lh in _QT_RULES
]


# [apple-4.3] betting / games of chance never get a KP verdict — the casino
# surface was retired 2026-10-01. /ask sends them to Explore before Yes/No runs;
# this is the engine-level backstop.
_GAMBLING = re.compile(
    r"(?<!\w)(?:gambl|casino|poker|lotter|lotto|bets?\b|betting|wager|blackjack|"
    r"roulette|jackpot|sports ?book|apuesta|aposta|loter[ií]a|satta|juaa?)", re.I)


def classify_question(question):
    """-> (question_type, loss_house, generic: bool) or (None, None, False)."""
    q = (question or "").lower()
    if _GAMBLING.search(q):
        return None, None, False
    for rx, qt, lh in _QT_COMPILED:
        if rx.search(q):
            return qt, lh, False
    # Everything else is still a KP horary: the 11th — fulfilment of the
    # querent's desire — is the KP generic. Confidence is capped at 1 because
    # the matter was inferred, not named.
    if q.strip():
        return "gain", None, True
    return None, None, False


# --------------------------------------------------------------------------
# Horizon: how far ahead the question looks (days) — None when unstated.
# --------------------------------------------------------------------------
_UNIT_DAYS = {
    "day": 1, "days": 1, "día": 1, "días": 1, "dia": 1, "dias": 1, "din": 1,
    "week": 7, "weeks": 7, "semana": 7, "semanas": 7, "hafte": 7, "hafta": 7,
    "month": 30, "months": 30, "mes": 30, "meses": 30, "mês": 30,
    "mahine": 30, "mahina": 30,
    "year": 365, "years": 365, "año": 365, "años": 365, "ano": 365,
    "anos": 365, "saal": 365,
}
_NUM_UNIT = re.compile(               # [kp-horizon] "60'days" / "60’days" / "60-day"
    r"(\d{1,3})[\s'’‘`\-]*(days?|weeks?|months?|years?|d[ií]as?|semanas?|mes(?:es)?|"
    r"mês|meses|a[nñ]os?|din|hafte|hafta|mahine|mahina|saal)\b", re.I)
_FIXED = [
    (("today", "tonight", "hoy", "hoje", "aaj"), 1),
    (("tomorrow", "mañana", "manana", "amanhã", "amanha", " kal "), 2),
    (("this week", "esta semana", "is hafte", "iss hafte"), 7),
    (("next week", "próxima semana", "proxima semana", "agle hafte"), 14),
    (("this month", "este mes", "este mês", "is mahine", "iss mahine"), 31),
    (("next month", "próximo mes", "proximo mes", "próximo mês",
      "agle mahine"), 62),
    (("this year", "este año", "este ano", "is saal", "iss saal"), 365),
]


def parse_horizon_days(question):
    q = f" {(question or '').lower()} "
    m = _NUM_UNIT.search(q)
    if m:
        unit = m.group(2).lower()
        mult = _UNIT_DAYS.get(unit)
        if mult is None:
            mult = 30 if unit.startswith("mes") else 1
        return max(1, min(int(m.group(1)) * mult, 730))
    for keys, days in _FIXED:
        if any(k in q for k in keys):
            return days
    return None


# --------------------------------------------------------------------------
# Number: request field wins; else "number 74" / "#74" / "número 74" typed in.
# --------------------------------------------------------------------------
_NUM_IN_Q = re.compile(r"(?:(?:number|num|n[uú]mero|pick|#)\D{0,8}|\bno\.\s*)(\d{1,3})", re.I)


def resolve_number(request_number=None, question=""):
    try:
        if request_number is not None and 1 <= int(request_number) <= 249:
            return int(request_number)
    except (TypeError, ValueError):
        pass
    m = _NUM_IN_Q.search(question or "")
    if m and 1 <= int(m.group(1)) <= 249:
        return int(m.group(1))
    return None


# --------------------------------------------------------------------------
# Casting at the seat
# --------------------------------------------------------------------------
def _seat_local(now_utc):
    """-> (naive local datetime at the seat, tz offset hours).

    pytz, not zoneinfo: pytz ships its own tz database, while zoneinfo needs
    system tzdata that slim deploy images may lack — a ZoneInfoNotFoundError
    here would silently push every Yes/No back to the classic engine."""
    import pytz
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    local = now_utc.astimezone(pytz.timezone(ASTROLOGER_SEAT["tz"]))
    off = local.utcoffset().total_seconds() / 3600.0
    return local.replace(tzinfo=None), off


def cast_at_seat(number, now_utc):
    from .kp_horary import cast_horary, ruling_planets
    from .kp_chart import compute_kp_chart
    lat, lon = ASTROLOGER_SEAT["lat"], ASTROLOGER_SEAT["lon"]
    local, off = _seat_local(now_utc)
    if number is not None:
        chart = cast_horary(number, local, lat, lon, off)
        chart["method"] = "kp_number"
        return chart
    chart = compute_kp_chart(local.strftime("%Y-%m-%d"),
                             local.strftime("%H:%M:%S"), lat, lon, tz_offset=off)
    chart["ruling_planets"] = ruling_planets(chart["birth_jd"], lat, lon,
                                             local.weekday())
    chart["method"] = "kp_moment"
    return chart


def _natal_verdict(chart_record, question_type, loss_house):
    """Natal KP verdict for the same matter, or None when it can't be trusted."""
    if not chart_record or chart_record.get("needs_reconfirm") is True:
        return None
    try:
        from .kp_service import _build_chart
        from .kp_significators import verdict
        natal = _build_chart(chart_record)
        if natal is None:
            return None
        return verdict(natal, question_type, loss_house=loss_house).get("verdict")
    except Exception:
        return None


def _fmt_day(iso):
    d = datetime.strptime(iso[:10], "%Y-%m-%d")
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def shown_window(kp):
    """The window the user sees. KP-only: yes / not_now / conditional show the
    horary's ruling-planet-confirmed window; a KP 'no' shows none — the horary
    denies it, and we don't borrow a date from another system."""
    if not kp or not kp.get("available") or kp.get("lean") == "no":
        return None
    return kp.get("window")


def window_label(start, end):
    if not start:
        return None
    try:
        if not end or end[:10] == start[:10]:
            return _fmt_day(start)
        s = datetime.strptime(start[:10], "%Y-%m-%d")
        e = datetime.strptime(end[:10], "%Y-%m-%d")
        if s.year == e.year:
            return f"{s.strftime('%b')} {s.day} – {e.strftime('%b')} {e.day}, {e.year}"
        return f"{_fmt_day(start)} – {_fmt_day(end)}"
    except Exception:
        return f"{start} – {end}"


def combine_lean(horary, natal, window, horizon_days, today):
    """The 4-state lean. Pure function — the rule table lives here."""
    if horary == "no":
        return "no"
    if horary == "conditional":
        return "conditional"
    # horary == "yes"
    if natal == "no":
        return "conditional"
    if horizon_days and window and window.get("ruler_ok") and window.get("start"):
        try:
            opens = datetime.strptime(window["start"][:10], "%Y-%m-%d").date()
            if opens > today + timedelta(days=horizon_days):
                return "not_now"
        except Exception:
            pass
    return "yes"


def kp_prashna(chart_record, question, number=None, now_utc=None):
    """
    Returns {available: True, lean, verdict ('YES'|'NO'), question_type, generic,
             method, number, horizon_days, window {start,end,label,ruler_ok}|None,
             confidence 0-3, natal, drivers, moment_utc, debug}
    or      {available: False, reason}.
    """
    try:
        qt, loss_house, generic = classify_question(question)
        if qt is None:
            return {"available": False, "reason": "question not KP-mappable"}
        if generic:
            # [kp-neutral-fallback] surface topics the classifier is missing (the
            # cast is also stored in prashna_log with generic=true — see
            # scripts/kp_unmapped_report.py)
            print(f"[kp][unmapped] {(question or '')[:120]!r}")
        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        number = resolve_number(number, question)
        horizon = parse_horizon_days(question)

        from .kp_significators import verdict
        from .kp_horary import timed_window
        chart = cast_at_seat(number, now_utc)
        v = verdict(chart, qt, loss_house=loss_house)
        win = timed_window(chart, qt, chart["ruling_planets"],
                           horizon_days=max(540, horizon or 0),
                           loss_house=loss_house)
        natal = _natal_verdict(chart_record, qt, loss_house)
        lean = combine_lean(v["verdict"], natal, win, horizon, now_utc.date())

        conf = int(v.get("confidence") or 0)
        if generic:
            conf = min(conf, 1)          # the matter was inferred, not named
        if natal is not None and (natal == "no") != (v["verdict"] == "no"):
            conf = max(0, conf - 1)      # birth chart disagrees

        window = None
        if win.get("ruler_ok") and win.get("start"):
            w_end = win.get("end")
            clipped = False
            # [kp-horizon] asked "in the next 30 days" → never show a window that
            # runs months past it; cut it at the horizon the person asked about
            if horizon and w_end:
                try:
                    h_end = (now_utc.date() + timedelta(days=horizon)).isoformat()
                    if win["start"][:10] <= h_end < w_end[:10]:
                        w_end, clipped = h_end, True
                except Exception:
                    pass
            window = {"start": win["start"], "end": w_end,
                      "label": window_label(win["start"], w_end),
                      "ruler_ok": True, "clipped_to_horizon": clipped}

        return {
            "available": True,
            "lean": lean,
            "verdict": "YES" if lean == "yes" else "NO",
            "question_type": qt,
            "question": (question or "")[:300],
            "generic": generic,
            "method": chart["method"],
            "number": number,
            "horizon_days": horizon,
            "window": window,
            "confidence": conf,
            "natal": natal,
            "drivers": v.get("drivers") or [],
            "moment_utc": now_utc.isoformat(),
            "debug": {
                "seat": ASTROLOGER_SEAT["name"],
                "horary_verdict": v["verdict"],
                "loss_house": loss_house,
                "csl": v["debug"].get("cuspal_sub_lord"),
                "csl_signifies": v["debug"].get("csl_signifies"),
                "favour_hit": v["debug"].get("favour_hit"),
                "against_hit": v["debug"].get("against_hit"),
                "gate_ok": v["debug"].get("materialization_gate_ok"),
                "rp": chart["ruling_planets"].get("set"),
                "raw_window": win,
            },
        }
    except Exception as e:  # never break the caller
        return {"available": False, "reason": f"kp prashna error: {str(e)[:160]}"}


# --------------------------------------------------------------------------
# Narration + calibration helpers
# --------------------------------------------------------------------------
_LEAN_PLAIN = {
    "yes": "it comes through",
    "not_now": "it comes, but later than the time you asked about",
    "conditional": "it can come through, but only if a condition clears first",
    "no": "the deciding factor does not back it right now",
}


def narrator_block(kp, question: str = ""):
    """Reconciled internal reasoning for the why/actions LLM call. Jargon-free:
    no planets, houses, signs, sub-lords — the narrator must not echo any."""
    lean = kp.get("lean")
    w = kp.get("window") or {}
    parts = [
        "Internal reasoning (reconciled, authoritative): a horary reading of THIS "
        f"question says {_LEAN_PLAIN.get(lean, 'unclear')}.",
        f"Strength of the read: {kp.get('confidence', 0)} of 3.",
    ]
    if kp.get("generic"):
        parts.append("The matter was not recognised as a specific topic. Speak about "
                     "the outcome the person asked about, in their own words — never "
                     "assume it is about money, work or love unless they said so.")
    if kp.get("natal") == "no" and lean == "conditional":
        parts.append("The person's wider life pattern does not strongly promise this "
                     "matter, so the path to it needs a different route or more effort.")
    if w.get("label"):
        _role = {"conditional": "the window in which the condition can clear",
                 "not_now": "when it opens"}.get(lean, "when it comes")
        parts.append(f"AUTHORITATIVE TIMING ({_role}): {w['label']} — never state "
                     "any other date, month, or window.")
    else:
        parts.append("No confirmed window — do not invent one.")
    if lean in ("no", "not_now", "conditional"):
        parts.append("Never say a flat 'no' and stop: name what would change the "
                     "outcome, and what to do meanwhile.")
    # [kp-conditions] the SPECIFIC condition — the why must name it, never a
    # generic "one hurdle" / "one piece falls into place"
    try:
        from .kp_conditions import explain
        ex = explain(kp, "en", question or kp.get("question") or "")
        if ex.get("condition"):
            parts.append("SPECIFIC CONDITION (authoritative — the why MUST name this in "
                         "plain words, never a vague 'one hurdle' or 'one piece'): "
                         + ex["condition"])
    except Exception:
        pass
    return " ".join(parts)


def calibration_marker(kp, tajik_verdict, engine, moment_iso):
    """Machine marker for user_correlations.correlation_key (never shown)."""
    w = (kp or {}).get("window") or {}
    return (f"[YN;engine={engine};kp={(kp or {}).get('lean', '')};"
            f"kpv={((kp or {}).get('debug') or {}).get('horary_verdict', '')};"
            f"kpc={(kp or {}).get('confidence', '')};nat={(kp or {}).get('natal') or ''};"
            f"tajik={tajik_verdict or ''};qt={(kp or {}).get('question_type', '')};"
            f"num={(kp or {}).get('number') or ''};method={(kp or {}).get('method', '')};"
            f"hz={(kp or {}).get('horizon_days') or ''};"
            f"win={w.get('start') or ''}..{w.get('end') or ''};moment={moment_iso}]")


def verify_after(kp, now_utc=None):
    """When to ask "did it happen?": the asked horizon, else the window's end,
    else 30 days. Clamped to 1..120 days."""
    now_utc = now_utc or datetime.now(timezone.utc)
    days = 30
    if kp and kp.get("horizon_days"):
        days = kp["horizon_days"]
    elif kp and (kp.get("window") or {}).get("end"):
        try:
            end = datetime.strptime(kp["window"]["end"][:10], "%Y-%m-%d").date()
            days = (end - now_utc.date()).days + 1
        except Exception:
            pass
    days = max(1, min(int(days), 120))
    return now_utc + timedelta(days=days)


_MARK = re.compile(r"(\w+)=([^;\]]*)")


def _parse_marker(s):
    s = str(s or "")
    if "[YN;" not in s:
        return None
    return dict(_MARK.findall(s[s.index("[YN;"):]))


def score_yesno_calibration(sb):
    """Head-to-head on reconciled Yes/No questions: KP lean vs the classic
    (Tajik) verdict against what actually happened. Report only — it never
    opens a gate. Directional: KP yes→happened; KP no/not_now→did not happen;
    KP conditional is reported separately (no directional claim)."""
    try:
        rows = (sb.table("user_correlations")
                .select("correlation_key,feedback_status")
                .eq("concern", "yesno").execute().data) or []
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}

    kp = {"n": 0, "hits": 0}
    tj = {"n": 0, "hits": 0}
    by_lean, conditional, answered = {}, 0, 0
    for r in rows:
        status = str(r.get("feedback_status") or "").lower()
        if status not in ("yes", "no"):
            continue
        m = _parse_marker(r.get("correlation_key"))
        if not m:
            continue
        answered += 1
        happened = status == "yes"
        lean = m.get("kp") or ""
        d = by_lean.setdefault(lean or "none", {"happened": 0, "did_not": 0})
        d["happened" if happened else "did_not"] += 1
        if lean in ("yes", "no", "not_now"):
            kp["n"] += 1
            kp["hits"] += int((lean == "yes") == happened)
        elif lean == "conditional":
            conditional += 1
        tv = (m.get("tajik") or "").upper()
        if tv in ("YES", "NO"):
            tj["n"] += 1
            tj["hits"] += int((tv == "YES") == happened)

    def _rate(x):
        return round(x["hits"] / x["n"], 3) if x["n"] else None

    kp["hit_rate"], tj["hit_rate"] = _rate(kp), _rate(tj)
    return {
        "available": True,
        "answered": answered,
        "kp": kp,
        "classic": tj,
        "kp_conditional": conditional,
        "by_kp_lean": by_lean,
        "kp_ready": bool(kp["n"] >= 30 and (kp["hit_rate"] or 0) >= 0.70),
        "note": "Calibration only. kp_ready is advisory (n>=30, >=70%); "
                "flipping ASK_YESNO_ENGINE is the owner's call.",
    }
