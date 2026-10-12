"""[why-argument 2026-10-12] The Why sheet as an argument for this answer: methods, promise, thin spots, what changes it."""
import re
from datetime import date

from antar_engine import why_argument as WA

TODAY = date(2026, 10, 12)
_BAD = re.compile(r"\b(malefic|benefic|doom|cursed|you will (die|get sick)|lifespan)\b", re.I)


def _conv(**over):
    c = {
        "locks": {
            "vimshottari": {"active": True, "why": "x", "window": "Oct 2026 – Oct 2028", "planet": "Rahu", "kind": "shift",
                            "role": "occupies", "start": "2026-10-12", "end": "2028-10-31"},
            "chara": {"active": True, "why": "x", "window": "Oct 2026 – Oct 2028", "planet": "Venus", "sign": "Taurus",
                      "role": "ruler", "kind": "chapter", "start": "2026-10-12", "end": "2028-10-31"},
            "yogini": {"active": True, "why": "x", "window": "Oct 2026", "planet": "Mars", "kind": "shift", "role": "rules",
                       "start": "2026-10-12", "end": "2026-10-31"},
            "varshphal": {"active": True, "why": "x", "window": "Nov 2025 – Nov 2026", "planet": "Mars",
                          "planets": ["Mars", "Mercury"], "start": "2025-11-26", "end": "2026-11-26"},
        },
        "varga_confirm": {"status": "confirmed", "mult": 1.15, "note": "…"},
        "promise_band": "strong", "window_start": "2026-10-12", "window_end": "2026-10-31", "window_label": "Oct 2026",
        "next_window_label": None,
    }
    c.update(over)
    return c


def _chart(venus_sign="Libra", venus_lon=190.0):
    def p(sign, house, lon):
        return {"sign": sign, "house": house, "longitude": lon}
    return {"lagna": {"sign": "Cancer"},
            "planets": {"Sun": p("Libra", 4, 185.0), "Moon": p("Taurus", 11, 40.0), "Mars": p("Scorpio", 5, 215.0),
                        "Mercury": p("Libra", 4, 195.0), "Jupiter": p("Cancer", 1, 100.0), "Venus": p(venus_sign, 4, venus_lon),
                        "Saturn": p("Gemini", 12, 70.0), "Rahu": p("Aquarius", 8, 310.0), "Ketu": p("Leo", 2, 130.0)}}


def test_four_methods_agree_each_with_its_own_plain_line_and_window():
    a = WA.build(_conv(), "career", _chart(), "en", TODAY, timing="Nov 2026 – Jan 2027")
    assert a["call"] == {"label": "Nov 2026 – Jan 2027", "open_now": True}
    assert [m["key"] for m in a["methods"]] == ["vimshottari", "chara", "varshphal", "yogini"]
    vim, chara, year, yog = a["methods"]
    assert vim["line"] == "Your current shift is Ambition (Rahu): it sits in your career area, Oct 2026 – Oct 2028."
    assert chara["line"] == "The running sign period is Taurus. Its ruler, Comfort (Venus), rules your career area, Oct 2026 – Oct 2028."
    assert year["line"] == "This year's chart brings Drive (Mars) and Intellect (Mercury) into your career area, valid Nov 2025 – Nov 2026."
    assert yog["note"] and "same star" in yog["note"]
    assert all(m["agrees"] and m["state_label"] == "agrees" for m in a["methods"])
    assert a["agreement"] == {"agree": 4, "of": 4, "line": "All 4 timing methods agree."}


def test_what_changes_it_uses_the_first_real_end_and_never_the_lightly_counted_cycle():
    a = WA.build(_conv(), "career", _chart(), "en", TODAY)
    assert a["change"] == ["The support from your year chart ends Nov 2026, so the strongest stretch comes before then. "
                           "After that 2 methods carry it until Oct 2028."]


def test_a_method_that_sits_out_is_named_and_counted():
    c = _conv()
    c["locks"]["varshphal"] = {"active": False, "why": "no", "window": "", "planet": "", "start": None, "end": None}
    a = WA.build(c, "career", _chart(), "en", TODAY)
    assert a["agreement"]["line"] == "3 of 4 timing methods agree; your year chart sits this out."
    year = next(m for m in a["methods"] if m["key"] == "varshphal")
    assert year["agrees"] is False and "does not move the planets that matter for career" in year["line"]
    assert a["change"][0].startswith("Support runs until Oct 2028") or "until Oct 2028" in a["change"][0]


def test_nothing_agrees():
    c = _conv()
    for k in c["locks"].values():
        k.update({"active": False, "start": None, "end": None})
    a = WA.build(c, "career", _chart(), "en", TODAY)
    assert a["agreement"]["line"] == "No timing method points at this in the next two years." and a["change"] == []


def test_the_promise_lines_the_divisional_chart_and_a_weak_natural_promise():
    assert WA.build(_conv(), "career", _chart(), "en", TODAY)["promise"] == [
        "Your career chart backs this: the area itself is built to deliver, not only open."]
    c = _conv(varga_confirm={"status": "denied"}, promise_band="absent")
    p = WA.build(c, "career", _chart(), "en", TODAY)["promise"]
    assert "weakens this" in p[0] and "steady effort, not luck" in p[0] and "does not give career a strong natural promise" in p[1]
    assert WA.build(_conv(varga_confirm={"status": "neutral"}), "career", _chart(), "en", TODAY)["promise"] == []


def test_where_it_is_thin_names_the_combust_ruler_and_what_helps():
    # Cancer lagna: the 10th is Aries (Mars rules); make the main support (Sun) combust-free and Mars combust
    ch = _chart()
    ch["planets"]["Mars"]["longitude"] = ch["planets"]["Sun"]["longitude"] + 3
    thin = WA.build(_conv(), "career", ch, "en", TODAY)["thin"]
    assert thin and "Drive (Mars) runs your career area, and it is combust" in thin[0]["line"]
    assert "deliberate effort" in thin[0]["helps"] and not _BAD.search(thin[0]["line"])


def test_next_opening_is_added_when_there_is_one():
    a = WA.build(_conv(next_window_label="Mar 2028 – May 2028"), "career", _chart(), "en", TODAY)
    assert a["change"][-1] == "The next opening after that: Mar 2028 – May 2028."


def test_spanish_is_native():
    a = WA.build(_conv(), "career", _chart(), "es", TODAY)
    assert a["methods"][0]["line"] == "Tu cambio actual es Ambición (Rahu): está en tu área de carrera, oct 2026 – oct 2028."
    assert a["methods"][3]["note"].startswith("Cuenta menos") and a["agreement"]["line"] == "Los 4 métodos de tiempo coinciden."
    assert a["methods"][2]["line"].startswith("La carta de este año lleva a Impulso (Marte) y Intelecto (Mercurio)")
    assert a["change"][0].startswith("El apoyo de tu carta del año termina en nov 2026")


def test_other_languages_and_missing_data_give_none_and_never_raise():
    assert WA.build(_conv(), "career", _chart(), "hi", TODAY) is None
    assert WA.build({}, "career", _chart(), "en", TODAY) is None
    assert WA.build(None, "career", None, "en", TODAY) is None
    assert WA.build({"locks": {"vimshottari": {"active": True, "start": "bad", "end": "bad", "planet": "Rahu"}}}, "career", None, "en", TODAY) is not None


def test_every_line_is_free_of_doom_and_lifespan_wording():
    for lg in ("en", "es"):
        a = WA.build(_conv(), "career", _chart(), lg, TODAY)
        for m in a["methods"]:
            assert not _BAD.search(m["line"])
