from antar_engine.output_strips import apply_user_facing_strips as strip
from antar_engine.narration_validator import validate_narration


def test_spanish_dasha_leak_is_plain():
    out = strip("Tu Antardasha (subperíodo planetario) actual pone a la persona clave bajo una carga.", language="es", field_type="plain")
    assert out == "Tu etapa actual pone a la persona clave bajo una carga."
    assert not validate_narration(out, language="en")


def test_english_dasha_words_are_plain():
    out = strip("Your current Antardasha (sub-period) is hard, and your Mahadasha runs to 2027.", language="en", field_type="plain")
    assert "dasha" not in out.lower() and "sub-period" not in out
    assert not validate_narration(out, language="en")
