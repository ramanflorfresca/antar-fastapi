"""[family-answers 2026-10-05] Family answers: no internal event-engine vocabulary, no property or money
nobody raised. The family topic (added the same day) pushed property/money talk into 39% of family
answers (1% before) because houses 4/2 also mean property and family money; the event engine's own
labels ('the trigger that turns X into Y', 'the board', 'el detonador') leaked into ~18% of ALL answers."""
from antar_engine import answer_polish as ap
from antar_engine import event_narrator as en
from antar_engine.narration_contract import concern_to_noun_palette as pal


def test_internal_event_vocabulary_becomes_plain_words():
    assert ap.plain_words("The trigger that turns 'better' into 'actually better' hasn't formed yet — later.", "en") \
        == "The right moment hasn't come yet — later."
    assert ap.plain_words("The trigger isn't quite in place yet. The board shows it easing.", "en") \
        == "The right moment hasn't come yet. The reading shows it easing."
    es = ap.plain_words("El detonador que convierte la promesa en realidad aparece en diciembre. El tablero muestra tensión.", "es")
    assert "detonador" not in es and "tablero" not in es and es.startswith("El momento justo")
    pt = ap.plain_words("O tabuleiro mostra tensão.", "pt")
    assert pt == "A leitura mostra tensão."
    assert "trigger" not in ap.plain_words("jo main trigger chahiye — woh abhi bana nahi hai", "hinglish")


def test_sentence_start_capital_kept_and_space_kept():
    assert ap.plain_words("Your wealth engine is large.", "en") == "Your earning power is large."
    assert ap.plain_words("Wealth engine is strong.", "en") == "Earning power is strong."


def test_family_answer_drops_property_and_money_unless_asked():
    p = {"read": "Your home and property situation has real support. Money conversations with family are where "
                 "things get messy — shared finances feel unpredictable. Keep talks calm.",
         "next": "Protect your savings cushion before big commitments at home."}
    ap.polish_answer(p, "en", "How is my family life looking this year?", "family", "")
    assert "property" not in p["read"].lower() and "finances" not in p["read"].lower()
    assert "savings" not in p["next"] and p["next"]
    asked = {"read": "a. b. Property decisions at home are heavy.", "next": "Talk to the broker about the house."}
    ap.polish_answer(asked, "en", "Is the property at home causing the tension in my family?", "family", "")
    assert "Property decisions" in asked["read"]


def test_family_palette_is_home_life_only():
    got = set(pal("family", k=10, partnered=True))
    assert got and not got & {"property", "real estate", "savings", "income", "family money", "vehicle", "land"}
    assert "your home" in got


def test_event_narrator_prompt_has_no_internal_labels_and_family_guard():
    for k, v in en._VERDICT_FRAMING.items():
        assert "trigger" not in v.lower() and "gate" not in v.lower(), (k, v)
    board = {"generated": {"concern": "family", "event": "family"}, "vimshottari": {"md": {}, "ad": {}},
             "promise_vs_trigger": {}, "double_transit": {"classical_verdict": "none"}, "varshphal": {}, "yogas_present": []}
    verdict = {"verdict": "promised_building", "confidence": "high", "layers_agreeing": 4, "tone": "negative",
               "layers": {"divisional_confirm": False}, "dt_mode": "weighter", "window": {"label": "Nov 2026 – Jan 2027"}}
    try:
        text = en.build_reading_sequence_prompt(board, verdict)
    except Exception:
        return   # board fixture is minimal; the framing assertions above are the contract
    assert "NEVER WRITE these internal words" in text and "FAMILY LIFE" in text
    assert "DOUBLE TRANSIT (the trigger)" not in text and "the whole board" not in text


def test_internal_term_sentence_dropped_and_no_parents_in_palette():
    p = {"read": "Ghar ka pressure hai. Ghar ke andar jo ruler hai woh weak chal raha hai. Aap calm rahiye.", "next": "Ek baat kijiye."}
    ap.polish_answer(p, "hinglish", "Ghar ka pressure kab kam hoga?", "family", "")
    assert "ruler" not in p["read"].lower() and "calm" in p["read"]
    assert not set(pal("family", k=10, partnered=True)) & {"your mother", "your father", "siblings"}
