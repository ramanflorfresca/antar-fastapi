from antar_engine import wa_numbers as wn


def test_country_lang_phone_and_bsuid():
    assert wn.country_lang("+573001234567") == "es"
    assert wn.country_lang("CO.113012345678") == "es"
    assert wn.country_lang("+5511987654321") == "pt"
    assert wn.country_lang("+919812345678") is None
    assert wn.country_lang("+14155550123") is None
    assert wn.country_lang("") is None
