"""Ask subject resolver: who is the question about? Pure/deterministic."""
import pytest

from antar_engine.ask_subject import resolve_subject, norm_name

PEOPLE = [
    {"name_b": "Amik Singh", "chart_id_b": "c-amik", "compat_type": "child"},
    {"name_b": "Leena", "chart_id_b": "c-leena", "compat_type": "romantic"},
    {"name_b": "Dev", "chart_id_b": "c-dev", "compat_type": "boss-or-manager"},
]


def _r(q, people=PEOPLE):
    return resolve_subject(q, "me", people)


def test_son_marriage_is_the_son_not_self():
    r = _r("when will my son get married")
    assert r["subject"] == "person" and r["person"]["chart_id"] == "c-amik"
    assert r["relation"] == "child"


def test_name_variants_resolve_to_same_connection():
    for n in ("Amik", "Amick", "Ameek", "Amiq"):
        r = _r(f"how is {n} doing?")
        assert r["subject"] == "person" and r["person"]["chart_id"] == "c-amik", n
    assert norm_name("Amik") == norm_name("Amick") == norm_name("Ameek") == norm_name("Amiq")


def test_possessive():
    r = _r("What about Amik's health?")
    assert r["subject"] == "person" and r["person"]["name"] == "Amik Singh"


def test_two_children_is_ambiguous():
    ppl = PEOPLE + [{"name_b": "Priya", "chart_id_b": "c-priya", "compat_type": "child"}]
    r = _r("when will my son get married", ppl)
    assert r["subject"] == "ambiguous" and len(r["candidates"]) == 2


def test_same_first_name_ambiguous_but_full_name_resolves():
    ppl = PEOPLE + [{"name_b": "Amick Rao", "chart_id_b": "c-rao", "compat_type": "friend"}]
    assert _r("how is Amik doing", ppl)["subject"] == "ambiguous"
    r = _r("how is Amik Singh doing", ppl)
    assert r["subject"] == "person" and r["person"]["chart_id"] == "c-amik"


def test_no_people_unchanged_for_plain_questions():
    for q in ("how is my health", "will I get promoted", "when will I get married"):
        assert _r(q, [])["subject"] == "self"
        assert _r(q)["subject"] == "self"


def test_relation_without_saved_person_is_missing_not_self():
    r = _r("when will my daughter get married", [])
    assert r["subject"] == "person" and r["person"] is None and r["missing"]


@pytest.mark.parametrize("q,chart", [
    ("when will my son get married", "c-amik"),
    ("mi hijo cuando se casa?", "c-amik"),
    ("cuando va a casarse mi hija", "c-amik"),
    ("quando meu filho vai casar", "c-amik"),
    ("mera beta kab shaadi karega", "c-amik"),
    ("meri beti ki health kaisi hai", "c-amik"),
    ("how is my wife doing", "c-leena"),
    ("como esta mi esposa", "c-leena"),
    ("meri patni ki sehat kaisi hai", "c-leena"),
    ("is my husband going to recover", "c-leena"),
    ("how is my boss doing", "c-dev"),
])
def test_relation_words_multilingual(q, chart):
    r = _r(q)
    assert r["subject"] == "person" and r["person"]["chart_id"] == chart, (q, r)


@pytest.mark.parametrize("q", [
    "how is my childhood affecting me",
    "my childhood was hard, when will I heal",
    "should I hire Amik",
    "my wife and I keep fighting, what should I do",
    "how is my relationship with my son",
    "does my boss like me",
    "what about my own health",
    "tengo un bebe en camino, como me va",
    "will my career improve",
])
def test_context_mentions_stay_self(q):
    assert _r(q)["subject"] == "self", q


def test_word_boundary_substrings():
    assert _r("how is my childhood")["subject"] == "self"
    assert _r("when will I find a babel job")["subject"] == "self"


def test_only_askers_own_people_and_never_self_chart():
    ppl = [{"name_b": "Me", "chart_id_b": "me", "compat_type": "romantic"}]
    assert resolve_subject("how is my wife doing", "me", ppl)["person"] is None


def test_common_word_name_needs_capital():
    ppl = [{"name_b": "Will", "chart_id_b": "c-w", "compat_type": "friend"}]
    assert resolve_subject("will it rain, will I win", "me", ppl)["subject"] == "self"
    assert resolve_subject("How is Will doing", "me", ppl)["subject"] == "person"


def test_garbage_never_raises():
    for q in (None, "", "   ", "'''", "¿?"):
        assert resolve_subject(q, "me", [None, {}, {"name_b": "x"}])["subject"] == "self"


# ── spouse words mean a romantic partner [spouse-words 2026-10-12] ──
from antar_engine import ask_subject as _AS


def _p(name, cid, ctype, **kw):
    return {"name_b": name, "chart_id_b": cid, "compat_type": ctype, **kw}


def test_my_spouse_does_not_offer_business_partners_as_candidates():
    people = [_p("Sudha", "c1", "spouse", relation_detail="wife"), _p("Rakesh", "c2", "business"), _p("Saransh", "c3", "cofounder")]
    r = _AS.resolve_subject("How is my spouse doing?", "me", people)
    assert r["subject"] == "person" and r["person"]["name"] == "Sudha"


def test_bare_partner_word_still_offers_both_kinds():
    people = [_p("Sudha", "c1", "spouse"), _p("Rakesh", "c2", "business")]
    r = _AS.resolve_subject("How is my partner doing?", "me", people)
    assert r["subject"] == "ambiguous" and {c["name"] for c in r["candidates"]} == {"Sudha", "Rakesh"}


def test_two_romantic_people_still_ask_which_one():
    people = [_p("Dana", "c1", "romantic"), _p("Sam", "c2", "relationship"), _p("Biz", "c3", "business")]
    r = _AS.resolve_subject("How is my girlfriend doing?", "me", people)
    assert r["subject"] == "ambiguous" and {c["name"] for c in r["candidates"]} == {"Dana", "Sam"}


def test_no_romantic_person_leaves_the_candidates_alone():
    people = [_p("Rakesh", "c2", "business"), _p("Saransh", "c3", "cofounder")]
    r = _AS.resolve_subject("How is my wife doing?", "me", people)
    assert r["subject"] == "ambiguous" and len(r["candidates"]) == 2


def test_future_partner_trait_question():
    for q in ("Will my spouse be rich?", "Will my spouse be dominating?", "Will my husband be older than me?",
              "What will my spouse's profession be?", "¿Será mi esposo rico?"):
        assert _AS.is_future_partner_trait_q(q), q
    for q in ("How is my spouse doing?", "Will my spouse get the job?", "Is my wife happy?", "Will Dana be rich?"):
        assert not _AS.is_future_partner_trait_q(q), q
