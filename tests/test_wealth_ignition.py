"""
Tests the forward wealth-ignition composer (stored Jaimini Chara × Vimśottari).
Dashas are supplied in the get_dashas_for_chart() row shape — the same stored
rows /predict passes — so the test exercises the real production path.

Ground truth (chart owner's chart): Sri Lagna ~18° Sagittarius; current Chara MD
Taurus with the Capricorn AD running now and Sagittarius AD next (Nov 2026–May
2027, the ignition); Rahu MD begins Aug 2026 and Rahu occupies the 11th →
wealth-favourable → the Sagittarius window is a converged PEAK.
"""
import datetime as _dt

from antar_engine import wealth_ignition as WI

UTC = _dt.timezone.utc
NOW = _dt.datetime(2026, 7, 22, tzinfo=UTC)

CHART = {
    "lagna": {"sign_index": 9, "degree": 24.68},
    "planets": {
        "Sun":     {"sign_index": 7,  "degree": 10.10},
        "Moon":    {"sign_index": 11, "degree": 28.65, "longitude": 358.65},
        "Mars":    {"sign_index": 6,  "degree": 15.0},
        "Mercury": {"sign_index": 6,  "degree": 20.0},
        "Jupiter": {"sign_index": 10, "degree": 15.33},
        "Venus":   {"sign_index": 7,  "degree": 14.98},
        "Saturn":  {"sign_index": 2,  "degree": 12.0},
        "Rahu":    {"sign_index": 7,  "degree": 16.97},
        "Ketu":    {"sign_index": 1,  "degree": 16.97},
    },
}

# --- stored jaimini (Chara) rows: Taurus MD + its 12 antardaśās (6mo each) ---
_AD_SIGNS = ["Gemini", "Taurus", "Aries", "Pisces", "Aquarius", "Capricorn",
             "Sagittarius", "Scorpio", "Libra", "Virgo", "Leo", "Cancer"]


def _jaimini_rows():
    rows = [{"level": "mahadasha", "planet_or_sign": "Taurus",
             "start_date": "2023-11-26", "end_date": "2029-11-26"}]
    d = _dt.date(2023, 11, 26)
    for sign in _AD_SIGNS:
        m = d.month + 6                       # add 6 months
        y = d.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        nxt = _dt.date(y, m, 26)
        rows.append({"level": "antardasha", "planet_or_sign": sign,
                     "start_date": d.isoformat(), "end_date": nxt.isoformat()})
        d = nxt
    return rows


def _vimshottari_rows():
    return [
        {"level": "mahadasha", "planet_or_sign": "Mars",
         "start_date": "2019-08-01", "end_date": "2026-08-01"},
        {"level": "mahadasha", "planet_or_sign": "Rahu",
         "start_date": "2026-08-01", "end_date": "2044-08-01"},
        {"level": "antardasha", "planet_or_sign": "Rahu", "parent_lord": "Rahu",
         "start_date": "2026-08-01", "end_date": "2029-04-01"},
        {"level": "antardasha", "planet_or_sign": "Jupiter", "parent_lord": "Rahu",
         "start_date": "2029-04-01", "end_date": "2031-09-01"},
    ]


DASHAS = {"jaimini": _jaimini_rows(), "vimshottari": _vimshottari_rows()}


def test_wealth_favourability_rules():
    li = WI._lagna_idx(CHART)
    ws = WI._wealth_planet_set(CHART, li, "Jupiter")
    assert WI._lord_is_wealth_favourable("Rahu", CHART, li, ws)[0]     # 11th occupant
    assert WI._lord_is_wealth_favourable("Jupiter", CHART, li, ws)[0]  # dhana karaka
    assert WI._lord_is_wealth_favourable("Saturn", CHART, li, ws)[0]   # 2nd lord


def test_reads_stored_chara_rows_and_flags_sagittarius_peak():
    wi = WI.build_wealth_ignition(CHART, dashas=DASHAS, now=NOW)
    assert wi["available"]
    assert wi["sri_lagna"]["sign"] == "Sagittarius"
    by_sign = {w["sign"]: w for w in wi["windows"]}
    # current + upcoming activations from the STORED rows
    assert by_sign["Capricorn"]["activation"] == "accumulation"
    assert by_sign["Sagittarius"]["activation"] == "ignition"
    p = wi["primary"]
    assert p["sign"] == "Sagittarius"
    assert p["tier"] == "peak"
    assert p["conviction"] == "medium"            # capped, never high
    assert p["vimsottari_md"] == "Rahu"
    assert p["start"].startswith("2026-11")

    block = WI.wealth_ignition_to_context_block(wi)
    assert "FORWARD WEALTH-IGNITION" in block
    assert "Sagittarius" in block and "Rahu" in block


def test_unavailable_without_stored_chara_rows():
    # No jaimini rows -> no forecast (does NOT recompute with a non-prod method).
    wi = WI.build_wealth_ignition(CHART, dashas={"vimshottari": _vimshottari_rows()},
                                  now=NOW)
    assert wi.get("available") is False


def test_life_arc_threading_surfaces_wealth_ignition():
    # /life-arc path: build_forward_cycle must thread `dashas` into the forecast
    # and return it under the "wealth_ignition" key.
    import swisseph as swe
    from antar_engine.life_arc.forward_cycle_engine import build_forward_cycle
    birth_jd = swe.julday(1974, 11, 26, 12.0)
    res = build_forward_cycle(CHART, birth_jd, now=NOW.replace(tzinfo=None),
                              birth_date_str="1974-11-26", language="en",
                              dashas=DASHAS)
    assert "wealth_ignition" in res
    wi = res["wealth_ignition"]
    assert wi.get("available") is True
    assert wi["primary"]["sign"] == "Sagittarius"
    assert wi["primary"]["tier"] == "peak"


if __name__ == "__main__":
    class _MP:  # noqa
        pass
    test_wealth_favourability_rules(); print("PASS favourability")
    test_reads_stored_chara_rows_and_flags_sagittarius_peak(); print("PASS stored-chara peak")
    test_unavailable_without_stored_chara_rows(); print("PASS unavailable-without-rows")
    wi = WI.build_wealth_ignition(CHART, dashas=DASHAS, now=NOW)
    print("\n" + WI.wealth_ignition_to_context_block(wi))
