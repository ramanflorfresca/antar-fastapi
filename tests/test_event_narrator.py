"""
tests/test_event_narrator.py — deterministic verdict + narrator binding.

Verdict logic is pure python (no ephemeris) — fully testable here via the stub
runner. Each founder-doctrine branch is asserted explicitly so the
Python-authoritative verdict (prereq c1) can't drift silently.

Run via the sandbox stub: python /tmp/run_tests.py  (module auto-discovered)
or: cd ~/antarai && source venv311/bin/activate && python -m pytest tests/test_event_narrator.py -q
"""

from datetime import date

from antar_engine.event_narrator import (
    compute_event_verdict, build_reading_sequence_prompt,
)


# ── window fixture ───────────────────────────────────────────────────────────
# [2026-09-28] These tests used to hard-code start="2026-03-01"/end="2026-09-01"
# and assert the literal label "Mar 2026 – Sep 2026". _clamp_start_today()
# presents an already-running window forward from today, so once real time
# passed the start date the label collapsed onto the end month ("Sep 2026") and
# the assertions began failing on a calendar date rather than on a code change.
# Derive the window from today instead: it is always genuinely ahead of now, so
# the clamp never applies and the label is always a two-month range.

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _future_window(start_in=2, span=6):
    """(start_iso, end_iso, expected_label) for a window opening `start_in`
    months from now and running for `span` months.

    The expected label is spelled out here rather than obtained from
    _fmt_window(), so the assertion still exercises the formatter instead of
    comparing it against itself.
    """
    today = date.today()
    first = today.year * 12 + today.month - 1 + start_in
    sy, sm0 = divmod(first, 12)
    ey, em0 = divmod(first + span, 12)
    return (f"{sy:04d}-{sm0 + 1:02d}-01", f"{ey:04d}-{em0 + 1:02d}-01",
            f"{_MONTHS[sm0 + 1]} {sy} – {_MONTHS[em0 + 1]} {ey}")


# ── minimal board builder: only the fields the verdict reads ─────────────────

def _board(*, event="funding", event_houses=(11, 2, 8, 6),
           dasha_promise=False, chara_karaka=None, chara_occ_houses=(),
           divisional_strong=False, yogas=(), dt="none", gate=False,
           pd=None, ad=None, forming=(), varsh_window=None):
    karakas = []
    if chara_karaka is not None:
        abbr = {"funding": "AmK", "career": "AmK", "marriage": "DK",
                "general": "AmK"}.get(event, "AmK")
        karakas = [{"abbr": abbr, "planet": "Venus", "sign": "Taurus",
                    "house_from_md_lagna": chara_karaka, "dignity": "neutral"}]
    rotated = {h: {"sign": "Aries", "lord": "Mars",
                   "occupants": (["Sun"] if h in chara_occ_houses else [])}
               for h in range(1, 13)}
    varga = {"funding": "d10", "career": "d10", "marriage": "d9"}.get(event, "d10")
    # event-house lord 'Jupiter' strong in the varga when divisional_strong
    divs = {varga: {"Jupiter": {"dignity": "exalted" if divisional_strong else "neutral"},
                    "Venus": {"dignity": "neutral"}}}
    houses = {h: {"lord": "Jupiter"} for h in range(1, 13)}
    return {
        "generated": {"concern": event, "event": event,
                      "event_houses": list(event_houses)},
        "promise_vs_trigger": {"dasha_promise": dasha_promise},
        "vimshottari": {"md": {"lord": "Saturn",
                               "profile": {"house_from_lagna": 6, "dignity": "neutral",
                                           "owns_houses": [1, 2], "house_tags": ["dusthana"]}},
                        "ad": ad or {"lord": "Mars"},
                        "pd": pd},
        "chara": {"md_sign": {"sign": "Cancer"}, "karakas": karakas,
                  "rotated_houses": rotated},
        "divisionals": divs,
        "houses_from_lagna": houses,
        "yogas_present": [{"name": y} for y in yogas],
        "double_transit": {"classical_verdict": dt, "forming_windows": list(forming)},
        "varshphal": {"gate_open": gate, "event_house_hits": (["Venus"] if gate else []),
                      "window": varsh_window},
    }


# ── the six verdict branches ─────────────────────────────────────────────────

def test_supported_when_gate_promise_and_dt_fires():
    start, end, label = _future_window()
    b = _board(dasha_promise=True, gate=True, dt="fires",
               pd={"lord": "Venus", "start": start, "end": end})
    v = compute_event_verdict(b)
    assert v["verdict"] == "supported"
    assert v["tone"] == "positive"
    assert v["window"]["label"] == label
    assert v["window"]["kind"] == "active_sub_period"


def test_active_window_is_presented_forward_from_today():
    """A sub-period that already began is shown from today, never from its real
    start — the behaviour _clamp_start_today() exists for. Pinned here because
    it is what silently broke the three hard-coded-window tests above."""
    started = f"{date.today().year - 1:04d}-01-01"
    _, end, _ = _future_window()
    v = compute_event_verdict(_board(dasha_promise=True, gate=True, dt="fires",
                                     pd={"lord": "Venus", "start": started,
                                         "end": end}))
    today = date.today()
    assert v["window"]["label"].startswith(f"{_MONTHS[today.month]} {today.year}")
    # the raw period is preserved even though the label is clamped
    assert v["window"]["start"] == started


def test_supported_likely_when_dt_moon_only():
    v = compute_event_verdict(_board(dasha_promise=True, gate=True, dt="likely",
                                     ad={"lord": "Mars", "start": "2025-01-01",
                                         "end": "2027-01-01"}))
    assert v["verdict"] == "supported_likely"
    assert v["tone"] == "positive"
    # falls back to AD window when no PD
    assert v["window"]["kind"] == "active_period"


def test_hard_gate_mode_demotes_moon_only_to_building():
    b = _board(dasha_promise=True, gate=True, dt="likely",
               forming=[{"start": "2027-04-01", "end": "2027-08-01"}])
    v = compute_event_verdict(b, dt_mode="hard_gate")
    assert v["verdict"] == "promised_building"
    assert v["window"]["kind"] == "trigger_forms"
    assert v["window"]["label"] == "Apr 2027 – Aug 2027"


def test_promised_building_when_gate_promise_no_trigger():
    b = _board(dasha_promise=True, gate=True, dt="none",
               forming=[{"start": "2028-01-01", "end": "2028-05-01"}])
    v = compute_event_verdict(b)
    assert v["verdict"] == "promised_building"
    assert v["tone"] == "negative"
    assert v["window"]["kind"] == "trigger_forms"


def test_promised_not_this_year_when_gate_closed_but_promise():
    b = _board(dasha_promise=True, gate=False, dt="fires",
               varsh_window={"start": "2025-06-10", "end": "2026-06-10"})
    v = compute_event_verdict(b)
    assert v["verdict"] == "promised_not_this_year"
    assert v["tone"] == "negative"
    # gate closed overrides even a firing DT — doctrine: varshphal gates the year
    assert v["window"]["kind"] == "next_year_review"


def test_weak_noise_when_dt_without_promise():
    v = compute_event_verdict(_board(dasha_promise=False, gate=True, dt="fires"))
    assert v["verdict"] == "weak_noise"
    assert v["window"] is None


def test_not_supported_when_nothing():
    v = compute_event_verdict(_board())
    assert v["verdict"] == "not_supported"
    assert v["tone"] == "negative"


# ── promise can come from chara alone ────────────────────────────────────────

def test_chara_support_alone_satisfies_promise():
    # no dasha promise, but the event karaka sits in the 11th from period lagna
    b = _board(dasha_promise=False, chara_karaka=11, gate=True, dt="fires")
    v = compute_event_verdict(b)
    assert v["layers"]["chara_support"] is True
    assert v["verdict"] == "supported"


def test_chara_support_via_rotated_occupant():
    b = _board(dasha_promise=False, chara_occ_houses=(11,), gate=True, dt="fires")
    v = compute_event_verdict(b)
    assert v["layers"]["chara_support"] is True


# ── event-relative strain (8th funding-positive, marriage-strain) ───────────

def test_eighth_house_karaka_no_strain_for_funding():
    v = compute_event_verdict(_board(event="funding", event_houses=(11, 2, 8, 6),
                                     chara_karaka=8, gate=True, dt="fires"))
    assert v["strain_modifiers"] == []          # 8th is positive for funding


def test_eighth_house_karaka_is_strain_for_marriage():
    v = compute_event_verdict(_board(event="marriage", event_houses=(7, 2),
                                     chara_karaka=8, gate=True, dt="fires"))
    assert any("house 8" in s for s in v["strain_modifiers"])


# ── confidence = layer agreement ─────────────────────────────────────────────

def test_confidence_counts_layers():
    high = compute_event_verdict(_board(dasha_promise=True, chara_karaka=11,
                                        divisional_strong=True, yogas=("Dhana Yoga",),
                                        dt="fires", gate=True))
    assert high["confidence"] == "high" and high["layers_agreeing"] >= 4
    low = compute_event_verdict(_board())
    assert low["confidence"] == "low" and low["layers_agreeing"] <= 1


# ── narrator prompt: pins verdict/window, never leaks invent-license ─────────

def test_narrator_prompt_pins_verdict_and_window():
    start, end, label = _future_window()
    b = _board(dasha_promise=True, gate=True, dt="fires",
               pd={"lord": "Venus", "start": start, "end": end})
    v = compute_event_verdict(b)
    p = build_reading_sequence_prompt(b, v)
    assert "PYTHON VERDICT (authoritative): supported" in p
    assert label in p
    assert "Interpret; never calculate" in p
    assert "WINDOW DISCIPLINE: month-level only" in p
    assert "NO planet names, house numbers" in p
    # positive tone selected
    assert "OUTPUT TONE — POSITIVE" in p


def test_narrator_prompt_negative_carries_user():
    b = _board(dasha_promise=True, gate=True, dt="none",
               forming=[{"start": "2028-01-01", "end": "2028-05-01"}])
    v = compute_event_verdict(b)
    p = build_reading_sequence_prompt(b, v)
    assert "CARRY THE USER" in p
    assert "never a bare 'no'" in p
    assert "Apr" not in p or "trigger_forms" in p  # window is the forming one


def test_run_event_engine_orchestrator_shape():
    """run_event_engine glues board→verdict→client_verdict→timing for /ask
    wiring. Monkeypatch build_whole_board so no ephemeris is needed."""
    import antar_engine.event_evidence as ev
    start, end, label = _future_window()
    canned = _board(dasha_promise=True, gate=True, dt="fires",
                    pd={"lord": "Venus", "start": start, "end": end})
    orig = ev.build_whole_board
    ev.build_whole_board = lambda *a, **k: canned
    try:
        from antar_engine.event_narrator import run_event_engine
        out = run_event_engine({}, {}, {}, "1990-01-01", "funding")
    finally:
        ev.build_whole_board = orig
    assert out["verdict"]["verdict"] == "supported"
    assert out["client_verdict"] == "YES"
    assert out["timing_label"] == label
    assert "PYTHON VERDICT (authoritative): supported" in out["narrator_prompt"]


def test_client_verdict_map_covers_all_verdicts():
    from antar_engine.event_narrator import CLIENT_VERDICT
    for vk in ("supported", "supported_likely", "promised_building",
               "promised_not_this_year", "weak_noise", "not_supported"):
        assert CLIENT_VERDICT[vk] in ("YES", "LIKELY", "NOT_YET", "NO")


def test_narrator_prompt_reads_kn_rao_order():
    b = _board(dasha_promise=True, gate=True, dt="fires")
    p = build_reading_sequence_prompt(b, compute_event_verdict(b))
    for marker in ("1. RUNNING PERIOD", "2. CHARA CROSS-CHECK",
                   "3. DIVISIONAL CONFIRM", "4. YOGAS",
                   "5. DOUBLE TRANSIT", "6. YEAR GATE"):
        assert marker in p
