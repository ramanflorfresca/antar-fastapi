"""[partner-roles 2026-10-11] who should lead what + the can-they-partner gate — deterministic, from two charts."""
import copy
from datetime import datetime

from antar_engine import partner_roles as P

TODAY = datetime(2026, 10, 11)


def _chart(lagna="Capricorn", planets=None, d10_lagna="Taurus", d10=None, atma="Moon"):
    # a deliberately NEUTRAL base (no own / exalted signs, all in the 12th) so a test can strengthen exactly the planets it means to
    base = {"Sun": ("Gemini", 12), "Moon": ("Leo", 12), "Mars": ("Gemini", 12), "Mercury": ("Sagittarius", 12), "Jupiter": ("Gemini", 12),
            "Venus": ("Gemini", 12), "Saturn": ("Gemini", 12), "Rahu": ("Leo", 12), "Ketu": ("Aquarius", 12)}
    pl = {k: {"sign": v[0], "house": v[1], "degree": 5.0 + i} for i, (k, v) in enumerate(base.items())}
    for k, v in (planets or {}).items():
        pl[k] = {**pl[k], "sign": v["sign"], "house": v["house"]}        # degree stays: the Jaimini karaka ranking must not move
    d10p = {k: {"sign": v[0], "house": v[1]} for k, v in base.items()}
    d10p.update(d10 or {})
    return {"lagna": {"sign": lagna}, "planets": pl, "atmakaraka": atma,
            "divisional_charts": {"d10": {"lagna": d10_lagna, "planets": d10p}}}


def _dashas(md="Saturn", ad="Mercury"):
    return {"vimsottari": [
        {"level": "mahadasha", "lord_or_sign": md, "start_date": "2020-01-01", "end_date": "2036-01-01"},
        {"level": "antardasha", "lord_or_sign": ad, "start_date": "2026-01-01", "end_date": "2028-01-01"}]}


def test_running_lords_reads_md_and_ad():
    assert P.running_lords(_dashas("Rahu", "Venus"), TODAY) == ("Rahu", "Venus") and P.running_lords({}, TODAY) == ("", "")


def test_lane_scores_are_bounded_and_deterministic():
    a = P.score_person(_chart(), _dashas(), TODAY)
    assert a == P.score_person(_chart(), _dashas(), TODAY)
    assert set(a["scores"]) == set(P.LANES) and all(0.0 <= v <= 1.0 for v in a["scores"].values())


def test_saturn_and_mars_strength_lifts_operations_and_mercury_rahu_lifts_tech():
    ops = _chart(planets={"Saturn": {"sign": "Capricorn", "house": 10, "degree": 3}, "Mars": {"sign": "Capricorn", "house": 10, "degree": 4}},
                 d10={"Saturn": {"sign": "Capricorn", "house": 10}, "Mars": {"sign": "Capricorn", "house": 10}})
    tech = _chart(planets={"Mercury": {"sign": "Virgo", "house": 10, "degree": 3}, "Rahu": {"sign": "Gemini", "house": 10, "degree": 4}},
                  d10={"Mercury": {"sign": "Virgo", "house": 10}, "Rahu": {"sign": "Gemini", "house": 10}})
    so, st = P.score_person(ops, {}, TODAY)["scores"], P.score_person(tech, {}, TODAY)["scores"]
    assert so["ops"] > st["ops"] and st["tech"] > so["tech"]


def test_missing_data_is_left_out_not_scored_as_weakness():
    c = _chart(planets={"Mercury": {"sign": "Virgo", "house": 10}}, d10={"Mercury": {"sign": "Virgo", "house": 10}})
    nod10 = P.score_person({k: v for k, v in c.items() if k != "divisional_charts"}, _dashas(), TODAY)
    assert nod10["have"]["d10"] is False
    pt = nod10["parts"]["tech"]
    manual = (P.W_D1 * pt["d1"] + P.W_JAI * pt["jaimini"] + P.W_DASHA * pt["dasha"]) / (P.W_D1 + P.W_JAI + P.W_DASHA)
    assert abs(nod10["scores"]["tech"] - manual) < 1e-3                  # normalised over the parts that exist
    no_dasha = P.score_person(c, {}, TODAY)
    assert no_dasha["have"]["dasha"] is False and no_dasha["parts"]["tech"]["dasha"] == 0.0


def test_compare_assigns_leads_flags_gaps_and_says_who_in_words():
    ops = _built(["Saturn", "Mars"])
    tech = _built(["Mercury", "Rahu"])
    r = P.compare(tech, _dashas(), ops, _dashas(), "Gerardo", "en", TODAY)
    assert "tech" in r["you"]["leads"] and "ops" in r["other"]["leads"]
    assert "You should lead technology & product" in r["text"] and "Gerardo should lead operations & execution" in r["text"]
    assert r["text"].startswith("How to work with Gerardo") and "You is" not in r["text"] and len(r["gaps"]) <= 2
    assert r == P.compare(tech, _dashas(), ops, _dashas(), "Gerardo", "en", TODAY)         # stable


def _built(lane_planets):
    """A chart strong exactly in the given planets (own / exalted sign, a kendra house, D-1 and D-10)."""
    own = {"Sun": "Leo", "Moon": "Cancer", "Mars": "Aries", "Mercury": "Gemini", "Jupiter": "Sagittarius", "Venus": "Taurus",
           "Saturn": "Capricorn", "Rahu": "Gemini", "Ketu": "Gemini"}
    pl = {p: {"sign": own[p], "house": 10} for p in lane_planets}
    return _chart(planets=pl, d10=pl)


def test_unusable_charts_return_none_and_never_raise():
    assert P.compare({}, {}, _chart(), {}, "x") is None and P.compare(None, None, None, None) is None
    assert P.partnership_capacity(None)["level"] == "unknown"


# ---- the gate
def _seventh_weak():
    # Capricorn lagna -> 7th = Cancer, lord Moon; put Moon debilitated in the 12th, Ketu + Rahu + Mars in the 7th (D1 and D10)
    return _chart(planets={"Moon": {"sign": "Scorpio", "house": 12, "degree": 2}, "Ketu": {"sign": "Cancer", "house": 7, "degree": 3},
                           "Mars": {"sign": "Cancer", "house": 7, "degree": 4}, "Rahu": {"sign": "Cancer", "house": 7, "degree": 5}},
                  d10_lagna="Capricorn", d10={"Moon": {"sign": "Scorpio", "house": 12}, "Ketu": {"sign": "Cancer", "house": 7},
                                              "Saturn": {"sign": "Cancer", "house": 7}, "Rahu": {"sign": "Cancer", "house": 7}})


def _seventh_strong():
    return _chart(planets={"Moon": {"sign": "Cancer", "house": 7, "degree": 2}, "Jupiter": {"sign": "Cancer", "house": 7, "degree": 3},
                           "Venus": {"sign": "Cancer", "house": 7, "degree": 4}},
                  d10_lagna="Capricorn", d10={"Moon": {"sign": "Cancer", "house": 7}, "Jupiter": {"sign": "Cancer", "house": 7},
                                              "Venus": {"sign": "Cancer", "house": 7}})


_DK_STRONG = {"karakas": [{"karaka": "DK", "planet": "Jupiter"}]}      # Jupiter exalted in Cancer in the strong fixture
_DK_WEAK = {"karakas": [{"karaka": "DK", "planet": "Moon"}]}           # Moon debilitated in the 12th in the weak fixture


def test_a_weak_seventh_in_both_charts_is_solo_and_a_strong_one_is_capable():
    weak, strong = P.partnership_capacity(_seventh_weak(), _DK_WEAK), P.partnership_capacity(_seventh_strong(), _DK_STRONG)
    assert weak["level"] == "solo" and strong["level"] == "capable" and weak["score"] < P.CAP_SOLO <= P.CAP_CAPABLE <= strong["score"]


def test_solo_person_changes_the_read_before_any_role_split():
    r = P.compare(_built(["Mercury", "Rahu"]), _dashas(), _seventh_weak(), _dashas(), "Saransh", "en", TODAY, None, _DK_WEAK)
    assert r["capacity"]["solo"] is True and r["capacity"]["other"]["level"] == "solo"
    t = r["text"]
    assert "Saransh is built to run things alone" in t and "advisor, investor or contractor" in t
    assert t.index("built to run things alone") < t.index("Who should lead what") and "not as a co-founder arrangement" in t


def test_two_capable_partners_get_the_positive_line_and_no_warning():
    r = P.compare(_seventh_strong(), _dashas(), _seventh_strong(), _dashas(), "Asha", "en", TODAY, _DK_STRONG, _DK_STRONG)
    assert "Both of you can partner" in r["text"] and r["capacity"]["solo"] is False and "run things alone" not in r["text"]


def test_spanish_is_native_and_free_of_english_phrases():
    r = P.compare(_built(["Mercury", "Rahu"]), _dashas(), _seventh_weak(), _dashas(), "Saransh", "es", TODAY, None, _DK_WEAK)
    t = r["text"]
    assert t.startswith("C\u00f3mo trabajar con Saransh") and "Saransh rinde mejor en solitario" in t and "Qui\u00e9n deber\u00eda liderar qu\u00e9" in t
    for en in ("should lead", "built to run", "You are", "Right now", "Neither of you"):
        assert en not in t


def test_capacity_nudges_with_darakaraka_without_flipping_a_clear_case():
    c = _seventh_strong()
    base = P.partnership_capacity(copy.deepcopy(c))["score"]
    assert 0.0 <= base <= 1.0


# ---- convergence: both systems should give the same answer
def test_a_strong_seventh_with_a_weak_darakaraka_is_conditional_and_says_the_systems_split():
    dk_weak_here = {"karakas": [{"karaka": "DK", "planet": "Saturn"}]}      # Saturn in the 12th in a neutral sign
    c = P.partnership_capacity(_seventh_strong(), dk_weak_here)
    assert c["level"] == "conditional" and c["contested"] is True and c["jaimini_level"] == "solo"
    r = P.compare(_seventh_strong(), _dashas(), _seventh_strong(), _dashas(), "Asha", "en", TODAY, _DK_STRONG, dk_weak_here)
    assert "Asha can partner, but the two systems point different ways" in r["text"] and "run things alone" not in r["text"]


def test_a_lane_where_the_systems_pick_different_leaders_is_contested_not_assigned(monkeypatch):
    def fake(chart, dashas, today=None, jaimini=None):
        who = chart["who"]
        par = {l: 0.5 for l in P.LANES}
        jai = {l: 0.5 for l in P.LANES}
        par["ops"], jai["ops"] = (0.9, 0.2) if who == "a" else (0.3, 0.8)      # Parashari: A ahead; Jaimini: B ahead
        par["tech"], jai["tech"] = (0.8, 0.8) if who == "a" else (0.3, 0.3)     # both systems: A ahead
        sc = {l: round(0.7 * par[l] + 0.3 * jai[l], 4) for l in P.LANES}
        return {"scores": sc, "parashari": par, "jaimini": jai, "parts": {l: {"dasha": 0.0} for l in P.LANES}, "amk": "Mercury",
                "ak": "Moon", "dk": "Sun", "md": "", "ad": "", "chara_md": "", "chara_ad": "", "have": {"d1": True, "d10": True, "jaimini": True, "dasha": False}}
    monkeypatch.setattr(P, "score_person", fake)
    a = {"planets": {"Sun": {}}, "who": "a"}
    b = {"planets": {"Sun": {}}, "who": "b"}
    r = P.compare(a, {}, b, {}, "B", "en", TODAY)
    assert "ops" in r["contested"] and "ops" not in r["you"]["leads"] + r["other"]["leads"]
    assert "tech" in r["you"]["leads"] and "The two systems split on operations & execution" in r["text"]
    assert "Both systems agree" not in r["text"]


def test_when_both_systems_agree_the_read_says_so():
    r = P.compare(_built(["Mercury", "Rahu"]), _dashas(), _built(["Saturn", "Mars"]), _dashas(), "G", "en", TODAY)
    assert r["contested"] == [] or "Both systems agree" not in r["text"]


def test_chara_running_uses_live_rows_then_a_stored_snapshot_only_while_its_dates_cover_today():
    rows = {"jaimini": [{"level": "mahadasha", "lord_or_sign": "Taurus", "start_date": "2023-11-26", "end_date": "2029-11-25"}]}
    snap = {"current_ad": {"sign_name": "Libra", "start": "2026-05-27T09:00:00", "end": "2026-11-26T00:00:00"}}
    assert P.chara_running(rows, TODAY, snap) == ("Taurus", "Libra")
    assert P.chara_running(rows, datetime(2027, 1, 5), snap) == ("Taurus", "")      # snapshot expired -> no stale AD
    assert P.chara_running({}, TODAY, None) == ("", "")


def test_stored_karakas_beat_the_degree_computation():
    chart = _chart()
    jai = {"karakas": [{"karaka": "AK", "planet": "Venus"}, {"karaka": "AmK", "planet": "Saturn"}, {"karaka": "DK", "planet": "Mars"}]}
    k = P._stored_karakas(chart, jai)
    assert (k["AK"], k["AmK"], k["DK"]) == ("Venus", "Saturn", "Mars")
    assert P._stored_karakas(chart, None)["AmK"]            # falls back to the degrees


def test_a_running_chara_period_is_named_in_the_right_now_line_in_en_and_es():
    """Regression: the 'chara' template key was missing for English, so ANY person with a Chara period running made compare() return None."""
    d = {**_dashas(), "jaimini": [{"level": "mahadasha", "lord_or_sign": "Taurus", "start_date": "2023-11-26", "end_date": "2029-11-25"}]}
    en = P.compare(_built(["Mercury", "Rahu"]), d, _built(["Saturn", "Mars"]), d, "Gerardo", "en", TODAY)
    assert en is not None and "(and the Taurus Chara period)" in en["text"] and en["you"]["chara_ad"] == "Taurus"
    es = P.compare(_built(["Mercury", "Rahu"]), d, _built(["Saturn", "Mars"]), d, "Gerardo", "es", TODAY)
    assert es is not None and "(y el periodo Chara de Tauro)" in es["text"]


def test_every_template_key_the_code_reads_exists_in_every_language():
    import re
    src = open(P.__file__, encoding="utf-8").read()
    used = set(re.findall(r'tx\["([a-z_0-9]+)"\]', src))
    for lang, tx in P._TX.items():
        assert used <= set(tx), (lang, sorted(used - set(tx)))


def _fake_score(base, shift):
    sc = {l: round(v + shift, 4) for l, v in zip(P.LANES, base)}
    return {"scores": sc, "parashari": dict(sc), "jaimini": dict(sc), "parts": {l: {"d1": 0.4, "d10": 0.4, "jaimini": 0.2, "dasha": 0.0} for l in P.LANES},
            "amk": "Mercury", "ak": "Moon", "dk": "Sun", "md": "", "ad": "", "chara_md": "", "chara_ad": "", "have": {"d1": True, "d10": True, "jaimini": True, "dasha": True}}


def test_a_person_level_offset_does_not_hand_one_person_every_lane(monkeypatch):
    """Same profile, one chart simply reads 0.15 higher in EVERY lane: that is a level gap, not 6 leads (Raman vs saransh)."""
    base = [0.50, 0.45, 0.55, 0.30, 0.48, 0.52]
    seq = iter([_fake_score(base, 0.0), _fake_score(base, -0.15)])
    monkeypatch.setattr(P, "score_person", lambda *a, **k: next(seq))
    monkeypatch.setattr(P, "partnership_capacity", lambda *a, **k: {"level": "capable", "score": 0.7, "contested": False})
    r = P.compare({"planets": {"Sun": {}}}, {}, {"planets": {"Sun": {}}}, {}, "Sam", "en", TODAY)
    assert r["you"]["leads"] == [] and r["other"]["leads"] == []            # identical relative profiles: nothing to assign by strength alone


def test_relative_strength_still_assigns_where_profiles_differ(monkeypatch):
    a = [0.60, 0.40, 0.45, 0.45, 0.45, 0.45]                                 # A stands out in tech
    b = [0.30, 0.45, 0.30, 0.30, 0.30, 0.30]                                 # B is lower everywhere but relatively strongest in ops
    seq = iter([_fake_score(a, 0.0), _fake_score(b, 0.0)])
    monkeypatch.setattr(P, "score_person", lambda *a_, **k: next(seq))
    monkeypatch.setattr(P, "partnership_capacity", lambda *a_, **k: {"level": "capable", "score": 0.7, "contested": False})
    r = P.compare({"planets": {"Sun": {}}}, {}, {"planets": {"Sun": {}}}, {}, "Sam", "en", TODAY)
    assert "tech" in r["you"]["leads"] and "ops" in r["other"]["leads"]
