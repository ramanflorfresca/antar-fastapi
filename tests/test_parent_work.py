"""Working with a parent (owner 2026-10-03)."""
from antar_engine import parent_work as pw


def test_who_detects_parent_in_languages():
    assert pw.who("Is my work better with partners or with my father?") == "father"
    assert pw.who("¿Me conviene trabajar con mi papá?") == "father"
    assert pw.who("Devo trabalhar com minha mãe?") == "mother"
    assert pw.who("How is my work with partners?") is None


def _cd(sun_h, l9_h):
    return {"planets": {"Sun": {"house": sun_h, "sign": "Leo"}, "Jupiter": {"house": 9, "sign": "Pisces"},
                        "Saturn": {"house": 3, "sign": "Gemini"}, "Mars": {"house": l9_h, "sign": "Aries"}},
            "house_lords": {"9": {"lord": "Mars"}, 9: {"lord": "Mars"}}, "divisional_charts": {}}


def test_block_is_plain_and_never_about_health():
    b = pw.block(_cd(10, 11), "1980-01-01", "father")
    assert "WORKING WITH THEIR FATHER" in b and "supportive" in b
    assert "NEVER mention the father's health" in b
    for jargon in ("house 10", "Sun in", "9th lord", "D12"):
        assert jargon not in b


def test_block_reports_friction():
    b = pw.block(_cd(8, 12), "1980-01-01", "father")
    assert "friction" in b and "authority clashes" in b


def test_no_chart_no_block():
    assert pw.block({}, "", "father") == "" and pw.block(_cd(10, 11), "", None) == ""
