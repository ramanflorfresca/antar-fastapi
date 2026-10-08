"""Compatibility engine: relationship types, gating, and classical-source fixes.

Covers the 2026-10 audit: spouse/sibling types, per-type dasha specs (no
separation penalty outside romantic/spouse), per-type wording, marriage-only
kutas gated to romantic/spouse, Tara/Bhakoot truth tables, nakshatra spelling,
mutual Graha Maitri, strict API type validation, and role on reopen.
"""
import copy

import pytest

from antar_engine import Compatibility as C
from antar_engine import compatibility_layers as CL
from antar_engine import compatibility_reasons as R
from antar_engine import compatibility_templates as T

NEW_TYPES = ("spouse", "sibling", "parent", "child", "advisor")
FAMILY_TYPES = ("parent", "child", "sibling", "advisor")


# ── helpers ──────────────────────────────────────────────────────────────────

def _chart(moon_sign="Aries", nak="Ashwini", lagna="Aries"):
    planets = {}
    for i, p in enumerate(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]):
        planets[p] = {"sign": C.SIGNS[(i * 3) % 12], "house": (i % 12) + 1, "longitude": i * 31.0,
                      "nakshatra": "Rohini"}
    planets["Moon"] = {"sign": moon_sign, "house": 1, "longitude": C.SIGNS.index(moon_sign) * 30 + 5.0,
                       "nakshatra": nak}
    return {"planets": planets, "lagna": {"sign": lagna}, "current_dasha": "Jupiter-Venus"}


def _raw(chart_a, chart_b, reason):
    return C.calculate_compatibility(chart_a, chart_b, "A", "B", compatibility_type=reason)


# ── A. reasons / aliases / strict resolver ───────────────────────────────────

def test_all_new_types_registered():
    for t in NEW_TYPES:
        assert t in R.VALID_REASONS
        assert t in R.REASON_WEIGHTS
        assert sum(R.REASON_WEIGHTS[t].values()) == 100
        assert R.REASON_DEFINITIONS[t]["needs_role"] is False


@pytest.mark.parametrize("raw,expected", [
    ("husband", "spouse"), ("wife", "spouse"), ("spouse", "spouse"),
    ("married", "spouse"), ("marriage", "spouse"),
    ("brother", "sibling"), ("sister", "sibling"), ("sibling", "sibling"),
    ("mentor", "advisor"), ("guide", "advisor"), ("advisor", "advisor"),
    ("son", "son"), ("daughter", "daughter"),
    ("mother", "mother"), ("father", "father"),
    ("partner", "romantic"), ("romantic", "romantic"), ("dating", "romantic"),
    ("Co-Founder", "cofounder"), ("boss", "boss-or-manager"),
])
def test_alias_mapping(raw, expected):
    assert R.resolve_reason(raw) == expected
    assert R.normalize_reason(raw, None) == expected


@pytest.mark.parametrize("raw", ["", None, "   ", "frenemy", "cofunder", "xyz"])
def test_unknown_type_is_none_for_strict_resolver(raw):
    assert R.resolve_reason(raw) is None


def test_lenient_normalizer_still_defaults_for_stored_legacy_values():
    assert R.normalize_reason("frenemy", None, default="romantic") == "romantic"


def test_reasons_directory_lists_new_types_in_every_language():
    for lang in ("en", "es", "pt"):
        keys = [r["key"] for r in R.reasons_directory(lang)["reasons"]]
        assert set(R.VALID_REASONS) == set(keys)
        by_key = {r["key"]: r for r in R.reasons_directory(lang)["reasons"]}
        for t in NEW_TYPES:
            assert by_key[t]["label"] and by_key[t]["question"] and by_key[t]["sublabel"]
    es = {r["key"]: r for r in R.reasons_directory("es")["reasons"]}
    assert es["spouse"]["label"] != R.REASON_DEFINITIONS["spouse"]["label"]


def test_start_endpoint_rejects_unknown_type_with_422():
    from fastapi.testclient import TestClient
    import main
    client = TestClient(main.app, raise_server_exceptions=False)
    r = client.post("/api/v1/compatibility/start",
                    json={"chart_id_a": "x", "chart_id_b": "y", "compat_type": "frenemy"})
    assert r.status_code == 422, r.text
    r = client.post("/api/v1/compatibility/start",
                    json={"chart_id_a": "x", "chart_id_b": "y", "compatibility_type": "nonsense"})
    assert r.status_code == 422, r.text


def test_omitted_type_keeps_the_cofounder_default():
    import main
    req = main.CompatibilityStartRequest(chart_id_a="a")
    assert "compat_type" not in req.model_fields_set and "compatibility_type" not in req.model_fields_set
    assert req.compatibility_type == "cofounder"


# ── B. forward-dasha specs ───────────────────────────────────────────────────

def test_dasha_specs_for_new_types():
    import main
    S = main._FWD_REL_SPEC
    assert S["parent"]["pos"] == [4, 9, 10, 2] and {"Moon", "Sun", "Jupiter"} <= set(S["parent"]["good"])
    assert {"Rahu", "Ketu"} <= set(S["parent"]["bad"]) and "Saturn" in S["parent"]["mild_bad"]
    assert S["child"]["pos"] == [5, 9, 11, 2] and {"Jupiter", "Moon", "Sun", "Venus"} <= set(S["child"]["good"])
    assert S["sibling"]["pos"] == [3, 11, 2, 9] and {"Mars", "Mercury", "Jupiter"} <= set(S["sibling"]["good"])
    assert S["spouse"]["pos"] == [7, 2, 5, 11] and {"Venus", "Jupiter", "Moon"} <= set(S["spouse"]["good"])
    assert S["advisor"]["pos"] == [9, 5, 2, 10] and {"Jupiter", "Mercury", "Sun"} <= set(S["advisor"]["good"])


def test_separation_penalty_only_for_romantic_and_spouse():
    import main
    on = {k for k, v in main._FWD_REL_SPEC.items() if v["sep"]}
    assert on <= {"romantic", "spouse", "marriage"}, on
    for t in ("parent", "child", "sibling", "friend", "advisor", "business", "cofounder",
              "family", "employee", "boss-or-manager"):
        assert main._FWD_REL_SPEC[t]["sep"] is False, t
    assert main._FWD_REL_SPEC["spouse"]["sep"] and main._FWD_REL_SPEC["romantic"]["sep"]


def _dashas(lords):
    rows = []
    year = 2026
    for lord in lords:
        rows.append({"level": "mahadasha", "planet_or_sign": lord,
                     "start_date": f"{year}-01-01", "end_date": f"{year + 2}-12-31"})
        year += 3
    return {"vimsottari": rows}


def test_forward_dasha_no_separation_penalty_for_family(monkeypatch):
    """A natal rupture signature / strain window that would cut a spouse read must
    NOT touch a parent/child/sibling read."""
    import main
    from antar_engine import relationships as rel
    monkeypatch.setattr(rel, "separation_timing",
                        lambda *a, **k: {"windows": [{"start": "2027-06-01", "score": 5.0}]})
    monkeypatch.setattr(rel, "analyze_relationship",
                        lambda *a, **k: {"durability": {"level": "elevated"}})
    ca = _chart(lagna="Aries")
    cb = _chart(lagna="Leo")
    d = _dashas(["Jupiter", "Moon"])
    out = {t: main._forward_dasha_support(ca, d, cb, d, t, "1980-01-01", "1982-01-01")
           for t in ("spouse", "parent", "child", "sibling", "advisor")}
    assert all(o["available"] for o in out.values())
    assert out["spouse"]["separation_flag"] is True
    for t in ("parent", "child", "sibling", "advisor"):
        assert out[t]["separation_flag"] is False
        assert not any("strain window" in w or "rupture" in w for w in out[t]["watch_points"]), t
    assert out["spouse"]["score"] < out["parent"]["score"]


def test_forward_dasha_uses_the_type_houses():
    """Same dashas, different houses: a lord ruling the 5th supports a child read but
    not a sibling read."""
    import main
    # Aries lagna: Sun rules 5, Mars rules 1/8, Mercury rules 3/6, Jupiter 9/12
    ca = _chart(lagna="Aries")
    for p in ca["planets"].values():
        p["house"] = 12      # park every planet away from the houses we test
    cb = copy.deepcopy(ca)
    d = _dashas(["Sun", "Sun"])
    child = main._forward_dasha_support(ca, d, cb, d, "child", "", "")
    sibling = main._forward_dasha_support(ca, d, cb, d, "sibling", "", "")
    assert child["score"] > sibling["score"]


def test_marriage_key_is_the_spouse_spec():
    import main
    ca, cb = _chart(), _chart(lagna="Libra")
    d = _dashas(["Venus", "Jupiter"])
    a = main._forward_dasha_support(ca, d, cb, d, "marriage", "", "")
    b = main._forward_dasha_support(ca, d, cb, d, "spouse", "", "")
    assert a["score"] == b["score"]


# ── C. templates ─────────────────────────────────────────────────────────────

def test_every_type_has_its_own_non_fallback_wording():
    covered = set(T.reasons_with_templates())
    for r in R.VALID_REASONS:
        assert r in covered, f"{r} has no authored templates"


def test_family_wording_is_not_business_wording():
    biz_h = {T._HEADLINES["business"][b] for b in T.BADGES}
    biz_d = {T._DETAILS["business"][b] for b in T.BADGES}
    for r in NEW_TYPES:
        for b in T.BADGES:
            h, d = T.v2_overall(r, b, "Asha", "Ravi")
            assert h and d and h not in biz_h and d not in biz_d, (r, b)
            assert "builder" not in h.lower() and "partnership" not in h.lower() or r == "spouse", (r, b, h)
            for layer in T.LAYER_ORDER:
                line = T.get_line(r, layer, b, None, "Asha", "Ravi")
                assert line and line != T._GENERIC[layer][b].format(b_name="Ravi"), (r, layer, b)
    for r in ("parent", "child", "sibling"):
        text = " ".join(T.get_line(r, l, b, None, "A", "B") for l in T.LAYER_ORDER for b in T.BADGES)
        text += " ".join(T.v2_overall(r, b, "A", "B")[0] for b in T.BADGES)
        for word in ("builders", "partnership", "venture", "business", "dasha", "nakshatra"):
            assert word not in text.lower(), (r, word)


# ── D. gating of marriage-only kutas ─────────────────────────────────────────

def _score(reason, ca, cb, role=None):
    raw = _raw(ca, cb, reason)
    return CL.compose_compat_v2(raw, ca, cb, reason, role)


def _same_nadi_pair():
    # Ashwini + Ardra are both Adi; Ashwini + Bharani differ
    a = _chart("Aries", "Ashwini")
    same = _chart("Gemini", "Ardra")
    diff = _chart("Gemini", "Bharani")
    assert C.NAKSHATRA_NADI["Ashwini"] == C.NAKSHATRA_NADI["Ardra"] != C.NAKSHATRA_NADI["Bharani"]
    return a, same, diff


@pytest.mark.parametrize("reason", ["parent", "child", "sibling", "advisor", "business",
                                    "cofounder", "friend", "family"])
def test_nadi_does_not_change_non_marriage_scores(reason):
    a, same, diff = _same_nadi_pair()
    # keep Moon SIGN identical in both so Bhakoot / Graha Maitri don't move either
    diff["planets"]["Moon"]["sign"] = same["planets"]["Moon"]["sign"]
    assert _score(reason, a, same)["score"] == _score(reason, a, diff)["score"]


@pytest.mark.parametrize("reason", ["romantic", "spouse"])
def test_nadi_changes_marriage_scores(reason):
    a, same, diff = _same_nadi_pair()
    diff["planets"]["Moon"]["sign"] = same["planets"]["Moon"]["sign"]
    assert _score(reason, a, same)["score"] != _score(reason, a, diff)["score"]


def test_bhakoot_and_yoni_gated_too():
    a = _chart("Aries", "Ashwini")
    # 6/8 Moon signs (Scorpio) = bhakoot dosha; same sign (Aries) = none
    bad = _chart("Virgo", "Hasta")
    ok = _chart("Virgo", "Hasta")
    ok["planets"]["Moon"]["sign"] = "Aries"
    # lifepath for a parent read must be dasha-only: identical for any Bhakoot outcome
    r_bad = {l["layer_key"]: l["score"] for l in _score("parent", a, bad)["layers"]}
    bad2 = copy.deepcopy(bad)
    bad2["planets"]["Moon"]["sign"] = "Libra"       # different bhakoot relation
    r_bad2 = {l["layer_key"]: l["score"] for l in _score("parent", a, bad2)["layers"]}
    assert r_bad["lifepath"] == r_bad2["lifepath"]
    # yoni: chemistry for a mentor read ignores the Moon nakshatra animal
    ya = {l["layer_key"]: l["score"] for l in _score("advisor", a, _chart("Aries", "Hasta"))["layers"]}
    yb = {l["layer_key"]: l["score"] for l in _score("advisor", a, _chart("Aries", "Shatabhisha"))["layers"]}
    assert ya["chemistry"] == yb["chemistry"]


def test_sources_for_reason_gate():
    for r in R.VALID_REASONS:
        srcs = R.sources_for_reason(r)
        names = {n for layer in srcs.values() for n, _ in layer}
        if r in ("romantic", "spouse"):
            assert {"yoni", "bhakoot", "nadi_dosha"} <= names, r
        else:
            assert not (names & {"yoni", "bhakoot", "nadi_dosha"}), r
        for layer, lst in srcs.items():
            assert abs(sum(w for _, w in lst) - 1.0) < 0.01, (r, layer)
        comm = {n for n, _ in srcs["communication"]}
        assert "graha_maitri" not in comm, r          # no double count
        assert "graha_maitri" in {n for n, _ in srcs["soul"]}, r


def test_zero_weight_layers_never_surface_in_highlights():
    # a pair engineered so chemistry is strongly high/low while weight is 0
    a = _chart("Aries", "Ashwini")
    b = _chart("Aries", "Ashwini")
    for reason in ("parent", "child", "sibling", "advisor", "family", "employee"):
        res = _score(reason, a, b, "managerial" if reason == "employee" else None)
        zero = [l for l in res["layers"] if l["weight_in_this_reason"] == 0]
        assert zero and all(l["applicable"] is False for l in zero), reason
        zero_text = {l["detail"] for l in zero}
        assert not (zero_text & set(res["watch_points"] + res["catalysts"])), reason


def test_highlights_ranked_by_weight():
    a, b = _chart("Aries", "Ashwini"), _chart("Aries", "Ashwini")
    res = _score("romantic", a, b)
    w = {l["detail"]: l["weight_in_this_reason"] for l in res["layers"]}
    cat = [w[c] for c in res["catalysts"]]
    assert cat == sorted(cat, reverse=True)


# ── E. source fixes ──────────────────────────────────────────────────────────

def test_tara_truth_table_both_directions():
    assert set(C.GOOD_TARAS) == {2, 4, 6, 8, 9}
    assert set(C.BAD_TARAS) == {3, 5, 7}
    assert set(C.NEUTRAL_TARAS) == {1}
    assert set(C.GOOD_TARAS) | set(C.BAD_TARAS) | set(C.NEUTRAL_TARAS) == set(range(1, 10))
    for t in range(1, 10):
        pts = C._tara_points(t)
        assert pts == (1.5 if t in C.GOOD_TARAS else 0.0 if t in C.BAD_TARAS else 0.75), t
    # tara_number: counting 1..9 around the cycle
    assert [C.tara_number(0, i) for i in range(0, 10)] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 1]
    assert C.tara_number(0, 26) == ((26) % 9) + 1


def test_tara_counts_both_directions():
    # Ashwini(0) -> Rohini(3): 4th = Kshema (good); Rohini -> Ashwini: count 25 -> 7 Naidhana (bad)
    a, b = _chart(nak="Ashwini"), _chart(nak="Rohini")
    t = C._tara_score(a, b)
    assert t["tara_numbers"] == {"a_to_b": 4, "b_to_a": 7}
    assert t["score"] == 1.5
    # symmetric regardless of who is person A
    assert C._tara_score(b, a)["score"] == t["score"]
    # all-good pair: nakshatra 0 -> 1 (Sampat), 1 -> 0 : count 27 -> 9 Param Mitra
    assert C._tara_score(_chart(nak="Ashwini"), _chart(nak="Bharani"))["score"] == 3.0
    # all-bad pair: 0 -> 2 (Vipat 3), 2 -> 0 count 26 -> 8 Mitra good => 1.5
    assert C._tara_score(_chart(nak="Ashwini"), _chart(nak="Krittika"))["score"] == 1.5


@pytest.mark.parametrize("count,reverse,dosha", [
    (1, 1, False), (2, 12, True), (12, 2, True), (3, 11, False), (11, 3, False),
    (4, 10, False), (10, 4, False), (5, 9, True), (9, 5, True),
    (6, 8, True), (8, 6, True), (7, 7, False),
])
def test_bhakoot_truth_table(count, reverse, dosha):
    a = _chart(moon_sign="Aries")
    b = _chart(moon_sign=C.SIGNS[(count - 1) % 12])
    out = C._bhakoot_score(a, b)
    assert out["moon_distance"] == count
    assert ((count - 1) + (reverse - 1)) % 12 == 0      # sanity of the table itself
    assert out["score"] == (0 if dosha else 7)


def test_bhakoot_all_12_relations():
    dosha_counts = {2, 12, 5, 9, 6, 8}
    for count in range(1, 13):
        out = C._bhakoot_score(_chart(moon_sign="Aries"), _chart(moon_sign=C.SIGNS[count - 1]))
        assert (out["score"] == 0) == (count in dosha_counts), count


@pytest.mark.parametrize("raw,canon", [
    ("Ashvini", "Ashwini"), ("Dhanishta", "Dhanishtha"), ("Satabhisha", "Shatabhisha"),
    ("Shatabhisha", "Shatabhisha"), ("Purvabhadrapada", "Purva Bhadrapada"),
    ("Poorva Bhadrapada", "Purva Bhadrapada"), ("uttara-ashadha", "Uttara Ashadha"),
    ("Moola", "Mula"), ("Jyestha", "Jyeshtha"), ("Mrigasira", "Mrigashira"),
])
def test_nakshatra_normaliser(raw, canon):
    assert C.normalize_nakshatra(raw) == canon


def test_normaliser_round_trips_and_rejects_junk():
    for n in C.NAKSHATRAS:
        assert C.normalize_nakshatra(n) == n
    assert C.normalize_nakshatra("Ashvini") in C.NAKSHATRAS
    assert C.normalize_nakshatra("") is None and C.normalize_nakshatra(None) is None
    assert C.normalize_nakshatra("Notastar") is None


def test_chart_py_spellings_resolve_to_the_right_yoni_gana_nadi():
    """chart.py says Ashvini / Dhanishta; the tables say Ashwini / Dhanishtha. The old
    .get(default) silently scored Ashvini as Horse/Manav/Adi by luck and Dhanishta as
    the same defaults instead of Lion / Rakshasa / Madhya."""
    a = _chart("Aries", "Ashvini")
    b = _chart("Aries", "Dhanishta")
    yoni = C._yoni_score(a, b)
    assert (yoni["a_value"], yoni["b_value"]) == ("Horse", "Lion")
    assert C._gana_score(a, b)["b_value"].startswith("Rakshasa")
    nadi = C._nadi_score(a, b)
    assert (nadi["a_value"], nadi["b_value"]) == ("Adi", "Madhya")
    # identical star in either spelling -> same-Nadi dosha, same yoni, same tara
    c1, c2 = _chart("Aries", "Dhanishta"), _chart("Aries", "Dhanishtha")
    assert C._nadi_score(c1, c2)["nadi_dosha"] is True
    assert C._yoni_score(c1, c2)["score"] == 4


def test_unknown_nakshatra_is_neutral_not_a_default_claim():
    a, b = _chart(nak="Ashwini"), _chart(nak="")
    nadi = C._nadi_score(a, b)
    assert nadi["nadi_dosha"] is False and nadi["match_pct"] == 50
    assert C._yoni_score(a, b)["score"] == 2
    assert C._tara_score(a, b)["match_pct"] == 50
    # both missing no longer reads "different Nadi - favorable" (old Adi vs Madhya defaults)
    assert C._nadi_score(_chart(nak=""), _chart(nak=""))["match_pct"] == 50


def test_graha_maitri_is_mutual_and_symmetric():
    # Moon sign lords: Cancer = Moon, Virgo = Mercury. Moon counts Mercury a friend (4);
    # Mercury counts Moon an enemy (1).
    a, b = _chart("Cancer"), _chart("Virgo")
    ab, ba = C._graha_maitri_score(a, b), C._graha_maitri_score(b, a)
    assert ab["score"] == ba["score"] == 2.5
    # every pair of Moon signs is symmetric
    for s1 in C.SIGNS:
        for s2 in C.SIGNS:
            assert C._graha_maitri_score(_chart(s1), _chart(s2))["score"] == \
                   C._graha_maitri_score(_chart(s2), _chart(s1))["score"]
    assert C._graha_maitri_score(_chart("Aries"), _chart("Scorpio"))["score"] == 5.0   # same ruler


def test_graha_maitri_counted_once():
    srcs = R.sources_for_reason("romantic")
    uses = [layer for layer, lst in srcs.items() if "graha_maitri" in {n for n, _ in lst}]
    assert uses == ["soul"]


# ── F. gender ────────────────────────────────────────────────────────────────

def test_spouse_karaka_follows_gender():
    from antar_engine.relationships import _spouse_karaka
    # chosen from the NATIVE's gender: a wife reads her husband-karaka (Jupiter),
    # a husband reads his wife-karaka (Venus); unknown stays the general Venus.
    assert _spouse_karaka("female")[0] == "Jupiter"
    assert _spouse_karaka("male")[0] == "Venus"
    assert _spouse_karaka(None)[0] == "Venus"


def test_forward_dasha_passes_gender_to_relationship_engine(monkeypatch):
    import main
    from antar_engine import relationships as rel
    seen = []
    monkeypatch.setattr(rel, "separation_timing", lambda cd, dsh, bd, g=None: seen.append(("sep", g)) or {})
    monkeypatch.setattr(rel, "analyze_relationship", lambda cd, g=None: seen.append(("an", g)) or {})
    d = _dashas(["Venus", "Jupiter"])
    main._forward_dasha_support(_chart(), d, _chart(lagna="Libra"), d, "spouse", "", "",
                                gender_a="female", gender_b="male")
    assert ("an", "female") in seen and ("an", "male") in seen
    assert ("sep", "female") in seen and ("sep", "male") in seen
    seen.clear()
    main._forward_dasha_support(_chart(), d, _chart(lagna="Libra"), d, "spouse", "", "")
    assert ("an", None) in seen          # unknown gender keeps the current behaviour


# ── G. reopen path keeps the role ────────────────────────────────────────────

def test_compose_uses_the_role_when_given():
    a, b = _chart("Aries", "Ashwini"), _chart("Leo", "Magha")
    raw = _raw(a, b, "employee")
    with_role = CL.compose_compat_v2(raw, a, b, "employee", "finance")
    no_role = CL.compose_compat_v2(raw, a, b, "employee", None)
    assert with_role["score"] != no_role["score"] or with_role["layers"] != no_role["layers"]


def test_session_endpoint_reads_role_back():
    import inspect
    import main
    src = inspect.getsource(main.compatibility_session) if hasattr(main, "compatibility_session") else ""
    if not src:      # endpoint function name differs: find it by its route
        for r in main.app.routes:
            if getattr(r, "path", "") == "/api/v1/compatibility/session/{session_id}":
                src = inspect.getsource(r.endpoint)
    assert "_s_role" in src and "compose_compat_v2(_raw, _ca, _cb, _reason, _s_role" in src
