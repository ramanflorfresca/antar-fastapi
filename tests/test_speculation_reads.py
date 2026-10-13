import re

from antar_engine import speculation_policy as SP

WIN = "Jun 2027 – Oct 2027"


def _sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def test_a_later_read_is_no_longer_two_bare_sentences_and_differs_by_question():
    month = SP.lead("later", WIN, language="en", question="How does this month look for my money?")
    when = SP.lead("later", WIN, language="en", question="When does my next window for unearned gains open?")
    plain = SP.lead("later", WIN, language="en", question="Is now a good time for stocks?")
    for r in (month, when, plain):
        assert len(_sentences(r["read"])) >= 3 and WIN in r["read"] and "slow build" in r["read"]            # head + (question line) + one why line
    assert "this month is for preparing" in month["read"] and "this month" not in when["read"]
    assert "decide your cap before it opens" in when["read"] and "decide your cap" not in month["read"]
    assert month["read"] != when["read"] and month["next"] == when["next"]


def test_every_state_carries_a_why_line_in_every_language():
    for lang in ("en", "es", "pt", "hinglish"):
        for st, key in (("open", "why_open"), ("later", "why_later"), ("no", "why_no"), ("losses", "why_losses")):
            r = SP.lead(st, WIN, language=lang)
            assert SP._T[lang][key] in r["read"] and len(_sentences(r["read"])) >= 2
        m = SP.lead("later", WIN, language=lang, question={"en": "this month", "es": "este mes", "pt": "este mês", "hinglish": "is mahine"}[lang])
        assert SP._T[lang]["q_month"] in m["read"]
    es = SP.lead("later", WIN, language="es", question="¿Cuándo se abre mi próxima ventana?")
    assert "Marca esa ventana" in es["read"] and "Until" not in es["read"] and "Hasta entonces" not in es["read"] and "chart" not in es["read"].lower() and "carta" not in es["read"].lower()


def test_gambling_note_and_no_window_cases_still_work():
    g = SP.lead("later", "", gambling=True, language="en", question="When will I win at the casino?")
    assert SP._T["en"]["gambling"] in g["read"] and SP._T["en"]["later_nowin"] in g["read"]
    assert SP.lead("open", WIN, language="en")["read"].startswith("The timing supports gains from speculation, and the window")
    assert "Until then" not in SP.lead("no", WIN, language="en")["read"]


def test_open_read_is_question_aware_and_long_enough():
    from antar_engine import speculation_policy as sp
    import re
    for lg in ("en", "es", "pt", "hinglish"):
        reads = {q: sp.lead("open", "Oct 2026 - Dec 2026", language=lg, question=q)["read"]
                 for q in ("How is speculation this week?", "How does this month look for my money?",
                           "When does my next window for unearned gains open?")}
        assert len(set(reads.values())) == 3, lg
        for r in reads.values():
            assert len(re.findall(r"[.!?]", r)) >= 3, (lg, r)
