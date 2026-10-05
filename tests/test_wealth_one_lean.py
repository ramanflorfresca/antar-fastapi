"""[one-lean 2026-10-04] concentrate-vs-diversify gets ONE answer from the stability
grade (Raman: 'run more than one venture' + move 'focus on one deal first')."""
from antar_engine import wealth_magnitude as wm


def test_detector_all_languages():
    for q in ("Should I concentrate or diversify?", "¿Debo concentrarme o diversificar?",
              "Devo concentrar ou diversificar?", "Kya ek jagah focus karun ya diversify karun?",
              "Go all in or spread my money?"):
        assert wm.is_concentrate_vs_diversify(q), q
    assert not wm.is_concentrate_vs_diversify("Which profession fits me best?")


def test_every_grade_has_one_lean():
    planets_sets = [
        {"Ketu": {"house": 2}, "Rahu": {"house": 8}},      # fragile
        {"Rahu": {"house": 11}, "Ketu": {"house": 5}},     # volatile Rahu-11
        {"Rahu": {"house": 3}, "Ketu": {"house": 9}},      # stable
    ]
    leans = [wm._stability(p, "Aries")["lean"] for p in planets_sets]
    assert leans == ["spread", "spread", "concentrate"]
    for lean, text in wm.LEAN_DIRECTIVE.items():
        assert "sentence one" in text and "`next` MUST" in text


def test_allocation_statement_detector():
    yes = ["I am 100% all in on Tezops AI and Antar", "I'm all in", "Going all-in on Antar",
           "Everything is in my startup", "I put all my savings into real estate",
           "Voy con todo en mi negocio", "Tudo no meu negócio", "Sab kuch Antar mein lagaya hai"]
    no = ["Is it all in my head?", "Is it all in the timing?", "How is my money?",
          "When will funding come?"]
    assert all(wm.is_allocation_statement(q) for q in yes)
    assert not any(wm.is_allocation_statement(q) for q in no)
    assert "already fits" in wm.ALLOCATION_DIRECTIVE["spread"]
    assert "Never tell them to pick one" in wm.ALLOCATION_DIRECTIVE["spread"]
