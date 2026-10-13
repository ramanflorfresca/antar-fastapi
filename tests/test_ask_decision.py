from antar_engine import ask_decision as A

READ = ("Raman, the same caution still stands — the timing shows your savings under pressure. Protect your cashflow first. "
        "It holds if you grow income through daily work, service and routines, where it actually pays for you. "
        "It breaks if spending and commitments rise as fast as income does.")


def test_splits_prediction_holds_breaks_and_carries_move_and_why():
    d = A.build(READ, "Call the family member and set a date.", "You're in a long stretch of reach.", "en")
    assert d["prediction"].endswith("Protect your cashflow first.") and "It holds" not in d["prediction"]
    assert d["holds"] == "you grow income through daily work, service and routines, where it actually pays for you."
    assert d["breaks"] == "spending and commitments rise as fast as income does."
    assert d["move"].startswith("Call the family") and d["why"].startswith("You're in a long")
    assert d["version"] == "ask-decision-1"


def test_only_breaks_or_reversed_order():
    d = A.build("Hold off. It breaks if you rush. It holds if you wait.", None, None, "en")
    assert d["holds"] == "you wait." and d["breaks"] == "you rush." and "move" not in d and "why" not in d
    assert A.build("Hold off today. It breaks if you rush it.", "m", "b", "en")["breaks"] == "you rush it."


def test_spanish_and_portuguese_markers():
    es = A.build("Espera. Se sostiene si ahorras. Se rompe si gastas.", "Habla hoy.", None, "es-US")
    assert es["holds"] == "ahorras." and es["breaks"] == "gastas." and es["prediction"] == "Espera."
    pt = A.build("Espere. Se sustenta se poupar. Se rompe se gastar.", None, None, "pt")
    assert pt["holds"] == "poupar." and pt["breaks"] == "gastar."


def test_not_decision_shaped_returns_none():
    assert A.build("Here is a general thought about your week.", "x", "y", "en") is None
    assert A.build("", "x", "y") is None and A.build(None, None, None) is None
    assert A.build("It holds if you wait.", None, None, "en") is None          # no prediction before the marker
    assert A.build("Hold. It holds if X.", None, None, "xx")["holds"] == "X."  # unknown language falls back to English
