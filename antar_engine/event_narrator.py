"""
antar_engine/event_narrator.py — Event Prediction Engine v2, PHASE 2.

Two responsibilities, both downstream of event_evidence.build_whole_board:

  1. compute_event_verdict(board)  — DETERMINISTIC, Python-authoritative.
     Reads the whole-board facts and produces the verdict DIRECTION, confidence
     (layer-agreement count), timing window, and strain modifiers. The narrator
     never decides direction or dates — it only phrases this (prereq c1/c2).

  2. build_reading_sequence_prompt(board, verdict, language) — the KN Rao
     reading-sequence INSTRUCTION bound to the pinned facts + pinned verdict +
     pinned window, with two-tone output rules and the month-level window
     discipline already used by ask_consultation.consultation_prompt_block.

DOCTRINE (founder spec, [[project-timing-paddhati-doctrine]] + event spec):
  * Varshphal GATES the year (binary). Gate closed → not-this-year, full stop,
    however strong the dasha arc is.
  * Promise = Vimshottari dasha-lord connection OR Chara support (MD-sign-as-
    lagna karaka in a supportive house). Chara also types supported-vs-strained
    (2/11 supportive, 6/8/12 strained — EVENT-RELATIVE: 8th funding-positive,
    marriage-strain).
  * Double Transit is the TRIGGER. promise without DT = "coming, not yet";
    DT without promise = noise; both (under an open gate) = it fires.
  * Confidence = how many independent layers agree (dasha / chara / divisional /
    yoga / DT / varshphal).
  * DT Moon+Lagna is a CONFIDENCE-WEIGHTER by default (Moon-only = "likely"),
    switchable to a hard gate (dt_mode="hard_gate").

No verdict text, no dates invented here beyond what the board's windows already
contain. Internal module — output_strips owns the final user-facing scrub
(rule 12: no Sanskrit / planet names / house numbers reach the frontend).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

# Event-relative dusthana polarity: houses normally 'strained' (6/8/12) that are
# actually POSITIVE for a given event (counted from the relevant lagna).
_POSITIVE_DUSTHANA = {
    "funding":    {8, 12},   # 8 = other-people's-money (equity), 12 = investment
    "career":     {6},       # 6 = service/employment
    "relocation": {12},      # 12 = foreign settling
    "litigation": {6},       # 6 = the dispute itself (your side of it)
    "marriage":   set(),
    "health":     set(),
    "general":    set(),
}

# Which divisional confirms each event, and the karaka that carries it.
_EVENT_VARGA = {
    "funding": "d10", "career": "d10", "marriage": "d9",
    "relocation": "d4", "health": "d1", "litigation": "d1", "general": "d10",
}
_EVENT_KARAKA = {           # 7-scheme abbrs (founder ruling R4)
    "marriage": "DK", "career": "AmK", "funding": "AmK", "general": "AmK",
}

_DUSTHANA = {6, 8, 12}
_SUPPORTIVE = {2, 11}

# Event-engine verdict → the client-facing /ask verdict enum (YES/LIKELY/
# NOT_YET/NO). The narrator phrases prose; THIS is the authoritative direction.
CLIENT_VERDICT = {
    "supported":              "YES",
    "supported_likely":       "LIKELY",
    "promised_building":      "NOT_YET",
    "promised_not_this_year": "NOT_YET",
    "weak_noise":             "NO",
    "not_supported":          "NO",
}

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _d(s) -> Optional[date]:
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _fmt_window(s, e) -> Optional[str]:
    """Month-level window string (never day-level — window-discipline rule)."""
    sd, ed = _d(s), _d(e)
    if not sd or not ed:
        return None
    if (sd.year, sd.month) == (ed.year, ed.month):
        return f"{_MONTHS[sd.month]} {sd.year}"
    return f"{_MONTHS[sd.month]} {sd.year} – {_MONTHS[ed.month]} {ed.year}"


# ── verdict ──────────────────────────────────────────────────────────────────

def compute_event_verdict(board: dict, dt_mode: str = "weighter") -> dict:
    """
    Deterministic verdict from the whole board. dt_mode:
      "weighter"  (default) — Moon-only DT ("likely") counts as a soft trigger.
      "hard_gate"           — only Moon+Lagna DT ("fires") counts as a trigger.

    Returns a fully transparent structure: the verdict direction, confidence,
    the per-layer booleans that produced it (so the logic is auditable), the
    timing window, and event-relative strain modifiers.
    """
    gen = board.get("generated", {})
    event = gen.get("event", "general")
    event_houses = gen.get("event_houses", [])
    pvt = board.get("promise_vs_trigger", {})
    vim = board.get("vimshottari", {})
    chara = board.get("chara", {})
    varsh = board.get("varshphal", {})
    dtb = board.get("double_transit", {})

    # ── layer 1: dasha promise (Vimshottari) ──────────────────────────────
    dasha_promise = bool(pvt.get("dasha_promise"))

    # ── layer 2: chara support + strain typing (MD-sign-as-lagna karaka) ──
    chara_support, strain_modifiers, chara_karaka_house = _chara_read(
        chara, event, event_houses)

    # ── layer 3: divisional confirm (event varga shows the significator) ──
    divisional_confirm = _divisional_confirm(board, event)

    # ── layer 4: yoga confirm (any relevant yoga fired) ───────────────────
    yoga_confirm = bool(board.get("yogas_present"))

    # ── layer 5: Double Transit trigger ───────────────────────────────────
    dt_verdict = (dtb.get("classical_verdict") or "none").lower()
    trigger_strong = dt_verdict == "fires"
    trigger_soft = dt_verdict == "likely"
    dt_trigger_any = dt_verdict in ("fires", "likely")
    if dt_mode == "hard_gate":
        trigger_active = trigger_strong
    else:
        trigger_active = trigger_strong or trigger_soft

    # ── layer 6: varshphal year gate (binary) ─────────────────────────────
    gate_open = bool(varsh.get("gate_open"))

    promise = dasha_promise or chara_support

    # ── verdict synthesis (deterministic) ─────────────────────────────────
    if not gate_open:
        if promise:
            verdict, headline_kind = "promised_not_this_year", "negative"
        else:
            verdict, headline_kind = "not_supported", "negative"
    else:  # gate open
        if promise and trigger_strong:
            verdict, headline_kind = "supported", "positive"
        elif promise and trigger_soft and dt_mode != "hard_gate":
            # Moon-only DT counts as a soft yes ONLY under the confidence-weighter;
            # under hard_gate it is demoted to building (no Lagna confirmation).
            verdict, headline_kind = "supported_likely", "positive"
        elif promise and not trigger_active:
            verdict, headline_kind = "promised_building", "negative"
        elif (not promise) and dt_trigger_any:
            verdict, headline_kind = "weak_noise", "negative"
        else:
            verdict, headline_kind = "not_supported", "negative"

    # ── confidence = layer-agreement count ────────────────────────────────
    layers = {
        "dasha_promise": dasha_promise,
        "chara_support": chara_support,
        "divisional_confirm": divisional_confirm,
        "yoga_confirm": yoga_confirm,
        "double_transit": dt_trigger_any,
        "varshphal_gate": gate_open,
    }
    agree = sum(1 for v in layers.values() if v)
    confidence = "high" if agree >= 4 else "medium" if agree >= 2 else "low"

    window = _select_window(verdict, board)

    return {
        "verdict": verdict,
        "tone": headline_kind,
        "confidence": confidence,
        "layers_agreeing": agree,
        "layers": layers,
        "dt_mode": dt_mode,
        "dt_verdict": dt_verdict,
        "window": window,
        "strain_modifiers": strain_modifiers,
        "chara_karaka_house": chara_karaka_house,
        "event": event,
        "event_houses": event_houses,
        "rule": "varshphal gates the year; promise (dasha|chara) + Double "
                "Transit fires it; promise without DT = building; DT without "
                "promise = noise. Confidence = layer agreement.",
    }


def _chara_read(chara: dict, event: str, event_houses: list):
    """Chara support + event-relative strain from the MD-rotated karaka."""
    karakas = chara.get("karakas") or []
    want = _EVENT_KARAKA.get(event, "AmK")
    pos_dust = _POSITIVE_DUSTHANA.get(event, set())
    strain = []
    support = False
    karaka_house = None

    k = next((x for x in karakas if x.get("abbr") == want), None)
    if k:
        karaka_house = k.get("house_from_md_lagna")
        if karaka_house in _SUPPORTIVE or karaka_house in event_houses:
            support = True
        if karaka_house in _DUSTHANA and karaka_house not in pos_dust:
            strain.append(f"{want} in house {karaka_house} from the period lagna "
                          f"(a straining placement for {event})")

    # also: does the chara MD or AD sign land on an event house from MD-lagna?
    rot = chara.get("rotated_houses") or {}
    for h in event_houses:
        cell = rot.get(h) or rot.get(str(h))
        if cell and cell.get("occupants"):
            support = True
            break

    return support, strain, karaka_house


def _divisional_confirm(board: dict, event: str) -> bool:
    """Event-house lord OR event karaka strong (own/exalted) in the event varga."""
    varga = _EVENT_VARGA.get(event, "d10")
    divs = board.get("divisionals", {})
    chart = divs.get(varga) or {}
    houses = board.get("houses_from_lagna", {})
    egen = board.get("generated", {}).get("event_houses", [])
    strong = {"own", "exalted"}

    # event-house lord dignity in the varga
    if egen:
        first = egen[0]
        lord = (houses.get(first) or houses.get(str(first)) or {}).get("lord")
        if lord and (chart.get(lord) or {}).get("dignity") in strong:
            return True

    # event karaka dignity in the varga
    want = _EVENT_KARAKA.get(event, "AmK")
    k = next((x for x in (board.get("chara", {}).get("karakas") or [])
              if x.get("abbr") == want), None)
    if k and (chart.get(k.get("planet")) or {}).get("dignity") in strong:
        return True
    return False


def _select_window(verdict: str, board: dict) -> Optional[dict]:
    """Pin the timing window from the engine (never invented)."""
    vim = board.get("vimshottari", {})
    dtb = board.get("double_transit", {})

    if verdict in ("supported", "supported_likely"):
        # tightest current connecting period: PD if present, else AD
        pd = vim.get("pd")
        if pd and pd.get("start") and pd.get("end"):
            lbl = _fmt_window(pd["start"], pd["end"])
            if lbl:
                return {"kind": "active_sub_period", "label": lbl,
                        "start": pd["start"], "end": pd["end"]}
        ad = vim.get("ad")
        if ad and ad.get("start") and ad.get("end"):
            lbl = _fmt_window(ad["start"], ad["end"])
            if lbl:
                return {"kind": "active_period", "label": lbl,
                        "start": ad["start"], "end": ad["end"]}

    if verdict == "promised_building":
        # next time the Double Transit FORMS on the targets
        fw = dtb.get("forming_windows") or []
        if fw:
            w = fw[0]
            lbl = _fmt_window(w.get("start"), w.get("end"))
            if lbl:
                return {"kind": "trigger_forms", "label": lbl,
                        "start": w.get("start"), "end": w.get("end")}

    if verdict == "promised_not_this_year":
        # the arc exists; the next eligible varshphal year opens at next birthday
        vw = (board.get("varshphal") or {}).get("window") or {}
        if vw.get("end"):
            return {"kind": "next_year_review", "label": _fmt_window(vw["end"], vw["end"]),
                    "start": vw["end"], "end": vw["end"]}
    return None


# ── narrator prompt (KN Rao reading sequence, bound to pinned facts) ─────────

_VERDICT_FRAMING = {
    "supported":            "YES — supported and triggered this year.",
    "supported_likely":     "LEANS YES — supported, trigger forming (Moon-frame only).",
    "promised_building":    "NOT YET — the potential is real but the trigger has not formed.",
    "promised_not_this_year": "NOT THIS YEAR — the potential exists but this year's gate is closed.",
    "weak_noise":           "NO STRONG SIGNAL — a passing trigger with no underlying promise.",
    "not_supported":        "NOT SUPPORTED — this is a building/preparation phase.",
}


def build_reading_sequence_prompt(board: dict, verdict: dict,
                                  language: str = "en") -> str:
    """
    The narrator instruction. Claude READS the combination in KN Rao's order and
    phrases the PINNED verdict + PINNED window — it never recomputes a position,
    flips the direction, or invents a date. Facts are pre-resolved in `board`.
    """
    gen = board.get("generated", {})
    v = verdict
    win = v.get("window")
    lines = []

    lines.append("=== EVENT READING — deterministic facts. Do NOT alter the "
                 "verdict direction, the confidence, or the window. Interpret; "
                 "never calculate. ===")
    lines.append(f"QUESTION DOMAIN: {gen.get('concern')} (event type: {gen.get('event')})")
    lines.append(f"PYTHON VERDICT (authoritative): {v['verdict']} — "
                 f"{_VERDICT_FRAMING.get(v['verdict'], '')}")
    lines.append(f"CONFIDENCE: {v['confidence']} ({v['layers_agreeing']} of 6 "
                 "layers agree)")
    if win and win.get("label"):
        lines.append(f"WINDOW (use verbatim, month-level ONLY): {win['label']} "
                     f"[{win['kind']}]")
    else:
        lines.append("WINDOW: none — frame as a building/preparation phase; "
                     "do NOT invent dates.")

    # the board facts, in the order they must be read
    lines.append("")
    lines.append("READ THE BOARD IN THIS ORDER (KN Rao):")

    md = (board.get("vimshottari") or {}).get("md") or {}
    ad = (board.get("vimshottari") or {}).get("ad") or {}
    prof = md.get("profile") or {}
    lines.append(f"1. RUNNING PERIOD (the promise): main period lord {md.get('lord')} "
                 f"in house {prof.get('house_from_lagna')} "
                 f"({', '.join(prof.get('house_tags') or []) or 'no special tag'}), "
                 f"dignity {prof.get('dignity')}, owns houses "
                 f"{prof.get('owns_houses')}; sub-period {ad.get('lord')}. "
                 f"Dasha connects the target area: "
                 f"{board.get('promise_vs_trigger', {}).get('dasha_promise')}.")

    chara = board.get("chara") or {}
    lines.append(f"2. CHARA CROSS-CHECK: period sign {(chara.get('md_sign') or {}).get('sign')} "
                 f"as lagna; key indicator house = {v.get('chara_karaka_house')}; "
                 f"support={v['layers']['chara_support']}.")

    lines.append(f"3. DIVISIONAL CONFIRM ({_EVENT_VARGA.get(gen.get('event'),'d10')}): "
                 f"significator strong = {v['layers']['divisional_confirm']}.")

    yp = board.get("yogas_present") or []
    lines.append(f"4. YOGAS: {', '.join(y.get('name','') for y in yp) if yp else 'none firing'}.")

    dtb = board.get("double_transit") or {}
    lines.append(f"5. DOUBLE TRANSIT (the trigger): {dtb.get('classical_verdict')} "
                 f"(mode: {v.get('dt_mode')}). This is what turns 'promised' into "
                 "'happening'.")

    varsh = board.get("varshphal") or {}
    lines.append(f"6. YEAR GATE (varshphal): {'OPEN' if varsh.get('gate_open') else 'CLOSED'}"
                 + (f" — {', '.join(varsh.get('event_house_hits') or [])} active this year"
                    if varsh.get('gate_open') else "") + ".")

    if v.get("strain_modifiers"):
        lines.append("STRAIN MODIFIERS (name honestly, do not catastrophize): "
                     + "; ".join(v["strain_modifiers"]) + ".")

    # two-tone output contract
    lines.append("")
    if v["tone"] == "positive":
        lines.append("OUTPUT TONE — POSITIVE: confirm it happens, give the window "
                     "plainly, then ONE concrete way to use it. Confident, dated, "
                     "actionable. No hedging.")
    else:
        lines.append("OUTPUT TONE — CARRY THE USER: never a bare 'no'. Name what "
                     "is missing (the trigger / the year gate), give the next "
                     "opening if the board has one, and ONE concrete preparation "
                     "step for the building phase. Patient, not deflating.")

    # window discipline (mirrors ask_consultation.consultation_prompt_block v2)
    lines.append("WINDOW DISCIPLINE: month-level only. Never stretch ('through the "
                 "end of the year'), never narrow to specific days, never count "
                 "days remaining, never use scarcity pressure. If the window is "
                 "open now, advise calm, concrete use of it.")
    lines.append("LANGUAGE: respect the language parameter. Use everyday, "
                 "experiential language — NO planet names, house numbers, signs, "
                 "or Sanskrit terms in the answer (the energy-translation layer "
                 "and output strips enforce this; write as if speaking to a "
                 "friend about their life, not their chart).")
    lines.append("=== END EVENT READING ===")
    return "\n".join(lines)


# ── orchestrator (one call for the /ask wiring) ─────────────────────────────

def run_event_engine(chart_data, jaimini_data, dashas, birth_date, concern,
                     *, dt_mode: str = "weighter",
                     current_date: Optional[date] = None) -> Optional[dict]:
    """
    Build whole board → deterministic verdict → narrator prompt in one call,
    for the /ask wiring (Phase 2b). Returns a dict
      {board, verdict, narrator_prompt, client_verdict, timing_label}
    or None on failure (caller falls back to the legacy convergence path).
    """
    from antar_engine.event_evidence import build_whole_board
    board = build_whole_board(chart_data, jaimini_data, dashas, birth_date,
                              concern, current_date=current_date)
    verdict = compute_event_verdict(board, dt_mode=dt_mode)
    prompt = build_reading_sequence_prompt(board, verdict)
    win = verdict.get("window") or {}
    return {
        "board": board,
        "verdict": verdict,
        "narrator_prompt": prompt,
        "client_verdict": CLIENT_VERDICT.get(verdict["verdict"], "NOT_YET"),
        "timing_label": win.get("label"),
    }
