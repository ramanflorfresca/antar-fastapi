"""Unit tests for the AK x D-10 shadow features (no ephemeris needed)."""
from antar_engine.profession import ak_d10_shadow as s


def _lons(**over):
    base = {"Sun": 10.0, "Moon": 40.0, "Mars": 70.0, "Mercury": 100.0,
            "Jupiter": 130.0, "Venus": 160.0, "Saturn": 190.0}
    base.update(over)
    return base


def test_ak_is_highest_degree_within_sign_not_absolute_longitude():
    # Saturn is furthest round the zodiac (350 deg = 20 deg into Pisces), but
    # Sun at 29.5 deg in Aries has the higher in-sign degree, so Sun is the AK.
    l = _lons(Sun=29.5, Saturn=350.0)
    assert s.atmakaraka(l) == "Sun"
    assert s.atmakaraka_absolute_longitude(l) == "Saturn"


def test_d10_sign_matches_calculator_convention():
    # Sun at 29.9 Aries (odd sign): count starts at Aries, 10th portion -> Capricorn.
    f = s.ak_d10_features(_lons(Sun=29.9))
    assert f["ak"] == "Sun" and f["ak_d10_sign"] == "Capricorn"
    # Mars AK at 29.9 Taurus (even sign): count starts at the 9th sign (Capricorn),
    # 10th portion -> Capricorn + 9 = Libra.
    f = s.ak_d10_features(_lons(Mars=59.9))
    assert f["ak"] == "Mars" and f["ak_d10_sign"] == "Libra"


def test_dignity_and_dispositor():
    f = s.ak_d10_features(_lons(Mars=29.9 + 270))  # 299.9 = Aquarius 29.9, odd sign
    assert f["ak"] == "Mars"
    assert f["ak_d10_dispositor"] == s.SIGN_LORDS[f["ak_d10_sign"]]


def test_groups_for_slugs_multi_slug():
    assert s.groups_for_slugs("painter+musician") == {"ARTS"}
    assert s.groups_for_slugs("military-personnel+politician") == {"SPORT_MIL", "SUN_CLASS"}
    assert s.groups_for_slugs("miscelaneous") == set()


def test_fisher_known_values():
    assert s.fisher_one_sided(5, 0, 0, 5) < 0.01
    assert abs(s.fisher_one_sided(1, 1, 1, 1) - 5 / 6) < 1e-9
    assert s.fisher_one_sided(0, 5, 5, 0) == 1.0


def test_prereg_hash_is_stable():
    assert s.prereg_hash() == s.prereg_hash() and len(s.prereg_hash()) == 16
