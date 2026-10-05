"""[audit-wider 2026-10-05] The routing audit measured 29% of our OWN follow-up chips landing in
the wrong topic: family 16/16, "When does my energy pick up?" → BUSINESS ("pick up" is a business
keyword). A tapped chip must reach its own topic."""
from antar_engine.astrological_rules import detect_concern as d
from antar_engine import ask_consultation as ac, event_evidence as ee

FAMILY = ["How is my family life looking this year?", "When does the pressure at home ease?",
          "How do I handle the tension at home right now?", "¿Cómo se ve mi vida familiar este año?",
          "¿Cuándo baja la presión en casa?", "Como está minha vida familiar este ano?",
          "Quando a pressão em casa alivia?", "Ghar ka pressure kab kam hoga?",
          "Is saal meri family life kaisi dikh rahi hai?", "Abhi ghar ki tension kaise sambhalun?"]
ENERGY = ["When does my energy pick up?", "What is draining my energy right now?", "¿Cuándo sube mi energía?",
          "¿Qué está drenando mi energía ahora?", "Quando minha energia melhora?",
          "Meri energy kab badhegi?", "Abhi meri energy kahan khatam ho rahi hai?"]


def test_family_and_energy_chips_route_home():
    assert all(d(q) == "family" for q in FAMILY), [(q, d(q)) for q in FAMILY if d(q) != "family"]
    assert all(d(q) == "health" for q in ENERGY), [(q, d(q)) for q in ENERGY if d(q) != "health"]


def test_other_routes_not_stolen():
    assert d("Should I buy a home this year?") == "property"
    assert d("Is this a good time to plan a child?") == "children"
    assert d("When is my startup growth going to pick up?") == "business"
    assert d("How is my love life looking?") == "love"
    assert d("Will the energy sector grow?") != "health"


def test_family_is_wired_end_to_end():
    assert ac.CONCERN_HOUSES["family"] == [4, 2] and ac.CONCERN_KARAKAS["family"] == ["Moon", "Venus"]
    assert ac.prescan_domain("family") == "general" and ac._DOMAIN_NOUN["family"] == "family window"
    assert ee.CONCERN_TO_EVENT["family"] == "family" and "family" in ee.EVENT_MAP
    from antar_engine.narration_contract import concern_to_noun_palette as pal
    assert "your home" in pal("family", k=12, partnered=True)   # personal nouns are right on a family question


def test_alone_or_partner_is_business_and_cash_flow_is_money():
    for q in ("Should I build alone or bring in a partner?", "¿Debo emprender solo o con un socio?",
              "Akele build karun ya partner ke saath?"):
        assert d(q) == "business", q
    assert d("Is my partner loyal?") == "love"
    assert d("¿Cómo está mi flujo de caja mientras espero?") == "finance"
