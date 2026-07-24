"""
Validates the Sri Lagna primitive against a real Capricorn-lagna chart (the
module owner's own chart).

- The Chara Mahādaśā is checked via the existing production `compute_jaimini_dashas`
  (verified against Parasara Light) — current MD = Taurus (Nov 2023–Nov 2029).
- Antardaśās themselves are NOT recomputed here: production reads the stored
  `system='jaimini'` rows. This test feeds `sri_lagna_activation_windows` the
  Chara sub-sign windows directly (the shape those stored rows normalise to) and
  checks the Sri Lagna activation tags.

Ground truth: Sri Lagna ~18° Sagittarius (lord Jupiter); the Sagittarius
sub-period is the ignition, Capricorn is accumulation (2nd from SL).
"""
from datetime import date

from antar_engine.jaimini import compute_jaimini_dashas, get_current_dasha
from antar_engine.sri_lagna import sri_lagna, sri_lagna_activation_windows

LAGNA_IDX = 9
PLANET_SIGN = {"Sun": 7, "Moon": 11, "Mars": 6, "Mercury": 6, "Jupiter": 10,
               "Venus": 7, "Saturn": 2, "Rahu": 7, "Ketu": 1}
BIRTH = date(1974, 11, 26)
AS_OF = date(2026, 7, 22)

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

# Chara sub-sign windows (as the stored jaimini AD rows normalise to).
_WINDOWS = [
    {"sign": "Capricorn",   "sign_index": 9, "start_date": date(2026, 5, 26), "end_date": date(2026, 11, 26)},
    {"sign": "Sagittarius", "sign_index": 8, "start_date": date(2026, 11, 26), "end_date": date(2027, 5, 26)},
    {"sign": "Scorpio",     "sign_index": 7, "start_date": date(2027, 5, 26), "end_date": date(2027, 11, 26)},
    {"sign": "Libra",       "sign_index": 6, "start_date": date(2027, 11, 26), "end_date": date(2028, 5, 26)},
    {"sign": "Leo",         "sign_index": 4, "start_date": date(2028, 11, 26), "end_date": date(2029, 5, 26)},
]


def test_current_chara_md_is_taurus():
    mds = compute_jaimini_dashas(LAGNA_IDX, PLANET_SIGN, BIRTH)
    cur = get_current_dasha(mds, AS_OF)
    assert cur["sign"] == "Taurus"
    assert cur["start_date"] == date(2023, 11, 26)
    assert cur["end_date"] == date(2029, 11, 26)


def test_sri_lagna_is_sagittarius():
    sl = sri_lagna(CHART)
    assert sl["available"]
    assert sl["sign"] == "Sagittarius"
    assert sl["lord"] == "Jupiter"
    assert 17.0 <= sl["degree"] <= 19.5


def test_activation_tags():
    wins = sri_lagna_activation_windows(CHART, _WINDOWS, as_of=AS_OF)
    by_sign = {w["sign"]: w for w in wins}
    assert by_sign["Capricorn"]["activation"] == "accumulation"     # 2nd from SL
    assert by_sign["Sagittarius"]["activation"] == "ignition"       # SL itself
    assert by_sign["Libra"]["activation"] == "gains"                # 11th from SL
    assert by_sign["Leo"]["activation"] == "fortune"                # trine from SL
    assert "Scorpio" not in by_sign                                 # 12th from SL — not a wealth house
    assert by_sign["Sagittarius"]["strength"] == 1.0


if __name__ == "__main__":
    test_current_chara_md_is_taurus(); print("PASS md=Taurus")
    test_sri_lagna_is_sagittarius();  print("PASS sri_lagna=Sagittarius")
    test_activation_tags();           print("PASS activation tags")
