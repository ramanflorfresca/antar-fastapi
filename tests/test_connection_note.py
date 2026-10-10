from antar_engine.connection_note import split_note

ANDRES = ("How to work with Andres\n\nAndres is a sharp, principled advisor — not an operational right-hand. "
          "His real gift is judgment and counsel: people trust his read on what's fair and right, and respect for him "
          "builds slowly over time. But his career energy is concentrated and over-expansive.\n\nUse him as: a narrow-domain advisor.")
GERARDO = ("How to work with Gerardo\n\nHe's an executive-builder: he runs on structure, discipline and the spoken word, "
           "and he does his best work with a clear mandate and a visible scoreboard.")


def test_heading_is_split_from_the_body_so_the_name_is_not_repeated():
    r = split_note(ANDRES)
    assert r["note_title"] == "How to work with Andres"
    assert r["note_body"].startswith("Andres is a sharp")
    assert "How to work with" not in r["note_preview"]
    assert not r["note_preview"].startswith("Andres Andres")


def test_gerardo_preview_does_not_glue_heading_to_the_first_word():
    r = split_note(GERARDO)
    assert r["note_title"] == "How to work with Gerardo"
    assert r["note_preview"].startswith("He's an executive-builder")


def test_preview_ends_at_a_sentence_never_mid_word():
    r = split_note(ANDRES)
    p = r["note_preview"]
    assert len(p) <= 180 and p.endswith((".", "!", "?"))
    assert p.endswith("over time.") or p.endswith("right-hand.") or p.endswith("counsel: people trust his read on what's fair and right, and respect for him builds slowly over time.")


def test_a_long_single_sentence_is_cut_at_a_word_with_an_ellipsis():
    body = "word " * 80
    p = split_note(body)["note_preview"]
    assert p.endswith("…") and len(p) <= 181 and not p[:-1].endswith(" ")


def test_a_note_without_a_heading_is_all_body():
    r = split_note("He is steady and kind. Keep it simple.")
    assert r["note_title"] == "" and r["note_body"].startswith("He is steady") and r["note_preview"] == "He is steady and kind. Keep it simple."


def test_a_first_line_that_is_a_sentence_is_not_a_heading():
    r = split_note("Great to work with.\nHe delivers.")
    assert r["note_title"] == "" and r["note_body"].startswith("Great to work with.")


def test_empty_and_odd_input():
    for bad in (None, "", "   ", 5, {}):
        r = split_note(bad)
        assert set(r) == {"note_title", "note_body", "note_preview"}
    assert split_note("")["note_preview"] == ""


def test_markdown_bold_and_hash_headings_are_cleaned():
    r = split_note("## **How to work with Ana**\n\nAna is direct.")
    assert r["note_title"] == "How to work with Ana" and r["note_preview"] == "Ana is direct."
