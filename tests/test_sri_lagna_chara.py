"""
Validates the Sri Lagna × K.N. Rao Chara antardaśā primitive against a real
Capricorn-lagna chart (the module owner's own chart). Ground truth comes from
the chart owner's software:
    Current Chara MD  : Taurus (Nov 2023 – Nov 2029)
    AD active Jul 2026: Capricorn
    AD active Nov 2026: Sagittarius
    Sri Lagna         : ~18° Sagittarius, lord Jupiter
Expected activations: Sagittarius AD = 'ignition', Capricorn AD = 'accumulation'.
"""
from datetime import date

from antar_engine.jaimini import (
    compute_jaimini_dashas, get_current_dasha, compute_jaimini_antardashas,
)
from antar_engine.sri_lagna import sri_lagna, sri_lagna_activation_windows

# Capricorn lagna chart (sidereal). Degrees are exact where known.
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


def _ad_on(ads, day):
    return next((a for a in ads if a["start_date"] <= day < a["end_date"]), None)


def test_current_chara_md_is_taurus():
    mds = compute_jaimini_dashas(LAGNA_IDX, PLANET_SIGN, BIRTH)
    cur = get_current_dasha(mds, AS_OF)
    assert cur["sign"] == "Taurus", cur["sign"]
    assert cur["start_date"] == date(2023, 11, 26)
    assert cur["end_date"] == date(2029, 11, 26)


def test_antardasha_sequence_matches_ground_truth():
    mds = compute_jaimini_dashas(LAGNA_IDX, PLANET_SIGN, BIRTH)
    cur = get_current_dasha(mds, AS_OF)
    ads = compute_jaimini_antardashas(cur, LAGNA_IDX)
    assert len(ads) == 12
    assert _ad_on(ads, date(2026, 7, 22))["sign"] == "Capricorn"
    assert _ad_on(ads, date(2026, 12, 1))["sign"] == "Sagittarius"
    # last AD ends exactly on the MD end
    assert ads[-1]["end_date"] == cur["end_date"]


def test_sri_lagna_is_sagittarius():
    sl = sri_lagna(CHART)
    assert sl["available"]
    assert sl["sign"] == "Sagittarius", sl["sign"]
    assert sl["lord"] == "Jupiter"
    assert 17.0 <= sl["degree"] <= 19.5, sl["degree"]


def test_activation_windows_flag_ignition_and_accumulation():
    mds = compute_jaimini_dashas(LAGNA_IDX, PLANET_SIGN, BIRTH)
    cur = get_current_dasha(mds, AS_OF)
    ads = compute_jaimini_antardashas(cur, LAGNA_IDX)
    wins = sri_lagna_activation_windows(CHART, ads, as_of=AS_OF)
    by_sign = {w["sign"]: w for w in wins}
    # Forward set from Jul 2026 (Aquarius 'lord' window already passed, excluded).
    assert by_sign["Capricorn"]["activation"] == "accumulation"
    assert by_sign["Sagittarius"]["activation"] == "ignition"
    assert by_sign["Libra"]["activation"] == "gains"          # 11th from SL
    assert by_sign["Leo"]["activation"] == "fortune"          # trine from SL
    # The ignition window is the strongest and lands in the Rahu MD era.
    ign = by_sign["Sagittarius"]
    assert ign["strength"] == 1.0
    assert ign["start_date"].year == 2026 and ign["start_date"].month >= 11


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    # Human-readable dump
    mds = compute_jaimini_dashas(LAGNA_IDX, PLANET_SIGN, BIRTH)
    cur = get_current_dasha(mds, AS_OF)
    ads = compute_jaimini_antardashas(cur, LAGNA_IDX)
    print(f"\nSri Lagna: {sri_lagna(CHART)['sign']} "
          f"{sri_lagna(CHART)['degree']}°  lord={sri_lagna(CHART)['lord']}")
    print("Forward Sri-Lagna activation windows:")
    for w in sri_lagna_activation_windows(CHART, ads, as_of=AS_OF):
        print(f"  {w['start_date']} -> {w['end_date']}  {w['sign']:12} "
              f"{w['activation']:12} (strength {w['strength']}, "
              f"{w['house_from_sri_lagna']}th from SL)")
