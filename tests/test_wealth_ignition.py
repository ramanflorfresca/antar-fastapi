"""
Tests the forward wealth-ignition composer (Jaimini × Vimśottari). The
Vimśottari side is injected (a known Rahu-MD-from-Aug-2026 timeline) so the
assertion is deterministic and independent of exact birth time.

Ground truth (chart owner's chart): Sri Lagna ~18° Sagittarius; the Sagittarius
Chara sub-period (Nov 2026–May 2027) is the ignition; Rahu MD begins Aug 2026
and Rahu occupies the 11th → wealth-favourable → the window is a converged PEAK.
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


def _fake_vims(chart_data, birth_jd):
    def d(y, m, day):
        return _dt.datetime(y, m, day, tzinfo=UTC)
    return {
        "mahadashas": [
            {"lord": "Mars", "start_datetime": d(2019, 8, 1), "end_datetime": d(2026, 8, 1)},
            {"lord": "Rahu", "start_datetime": d(2026, 8, 1), "end_datetime": d(2044, 8, 1)},
        ],
        "antardashas": [
            {"lord": "Rahu", "parent_lord": "Rahu",
             "start_datetime": d(2026, 8, 1), "end_datetime": d(2029, 4, 1)},
            {"lord": "Jupiter", "parent_lord": "Rahu",
             "start_datetime": d(2029, 4, 1), "end_datetime": d(2031, 9, 1)},
        ],
    }


def test_wealth_favourability_rules():
    li = WI._lagna_idx(CHART)
    ws = WI._wealth_planet_set(CHART, li, "Jupiter")
    # Rahu occupies the 11th (Scorpio) -> favourable
    assert WI._lord_is_wealth_favourable("Rahu", CHART, li, ws)[0]
    # Jupiter is a dhana karaka + Sri Lagna lord -> favourable
    assert WI._lord_is_wealth_favourable("Jupiter", CHART, li, ws)[0]
    # Saturn is the 2nd lord (Aquarius) -> favourable
    assert WI._lord_is_wealth_favourable("Saturn", CHART, li, ws)[0]


def test_primary_window_is_sagittarius_peak(monkeypatch):
    monkeypatch.setattr(WI.vimsottari, "calculate_vimsottari_from_chart", _fake_vims)
    wi = WI.build_wealth_ignition(CHART, birth_jd=2442000.0,
                                  birth_date_str="1974-11-26", now=NOW)
    assert wi["available"]
    assert wi["sri_lagna"]["sign"] == "Sagittarius"
    p = wi["primary"]
    assert p["sign"] == "Sagittarius"
    assert p["activation"] == "ignition"
    assert p["tier"] == "peak"
    assert p["conviction"] == "medium"       # capped, never high
    assert p["vimsottari_md"] == "Rahu"
    assert p["start"].startswith("2026-11")

    block = WI.wealth_ignition_to_context_block(wi)
    assert "FORWARD WEALTH-IGNITION" in block
    assert "Sagittarius" in block and "Rahu" in block


if __name__ == "__main__":
    class _MP:
        def setattr(self, obj, name, val): setattr(obj, name, val)
    test_wealth_favourability_rules()
    print("PASS test_wealth_favourability_rules")
    test_primary_window_is_sagittarius_peak(_MP())
    print("PASS test_primary_window_is_sagittarius_peak")
    WI.vimsottari.calculate_vimsottari_from_chart = _fake_vims
    wi = WI.build_wealth_ignition(CHART, 2442000.0, "1974-11-26", now=NOW)
    print("\n" + WI.wealth_ignition_to_context_block(wi))
