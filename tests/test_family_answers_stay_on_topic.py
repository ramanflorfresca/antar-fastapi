import re
from antar_engine import ask_basis as B

_OFF = re.compile(r"(?i)\b(property|propiedad|propriedade|patrim|savings|ahorro|poupan|family money|dinero de la familia|dinheiro da fam|money|dinero|dinheiro)\b")


def test_family_channel_words_are_home_words():
    for house in (2, 4):
        for lang in ("en", "es", "pt"):
            assert not _OFF.search(B._channel(lang, "family", house)), (lang, house)


def test_other_topics_keep_their_channel():
    assert "property" in B._channel("en", "property", 4)
    assert "savings" in B._channel("en", "wealth", 2)


def test_family_breaks_line_has_no_money():
    assert "money" not in B._BREAKS["family"]
