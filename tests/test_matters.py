from datetime import date

from antar_engine import matters as M

TODAY = date(2026, 10, 13)


def R(q, day, domain="finance", move=""):
    return {"question": q, "domain": domain, "created_at": f"2026-10-{day:02d}T12:00:00+00:00", "action_item": move}


ROWS = (
    [R("When will my income increase?", 12), R("When will my income increase?", 12), R("Is January a good time to increase my prices?", 12),
     R("Should I raise my prices next month?", 12, move="Write down three results your best client got."), R("When will my income increase?", 10)] +
    [R("How should I position my AI agents platform for small businesses?", 12, "business", "Ship the first piece."),
     R("How should I position my AI agents platform for small businesses?", 12, "business"),
     R("Which market should I start with for the AI agents platform?", 11, "business"),
     R("I am building AI agents for small businesses. Does this fit my chart?", 9, "business")] +
    [R("Should I invest in the stock market now?", 11, "speculation"), R("Should I buy gold?", 11, "speculation"), R("Is it a good time to invest in the stock market?", 8, "speculation")] +
    [R("What should I focus on today?", 12, "finance"), R("How is my week ahead?", 12, "general"), R("How does this month look for my money?", 12, "finance"),
     R("How is cash flow today", 12, "finance"), R("Should I take the lone one-off thing?", 12, "general")]
)


def titles(r):
    return [m["title"] for m in r["matters"]]


def test_horizon_checks_and_generic_domains_are_not_matters():
    assert all(M.is_generic(q) for q in ("What should I focus on today?", "How is my week ahead?", "How does this month look for my money?",
                                          "How is cash flow today", "How is speculation tomorrow", "What should I focus on at work this week?"))
    assert not M.is_generic("Should I raise my prices next month?") and not M.is_generic("How should I position my platform?")
    r = M.build(ROWS, None, "en", TODAY, limit=5)
    assert all(m["topic"] in ("money", "business") for m in r["matters"])        # 'general' domain never surfaces


def test_related_questions_group_and_are_titled():
    r = M.build(ROWS, None, "en", TODAY, limit=5)
    t = titles(r)
    assert "Income and pricing" in t and "Investing and trading" in t
    inc = next(m for m in r["matters"] if m["title"] == "Income and pricing")
    assert inc["asks"] == 4 and inc["days"] == 2 and inc["move"] == "Write down three results your best client got."   # the repeated same-day question counts once
    biz = [m for m in r["matters"] if m["topic"] == "business"]
    assert len(biz) == 1 and biz[0]["asks"] == 3 and biz[0]["title"] in ("Launching your product", "AI agents platform")


def test_same_day_repeats_are_one_ask_and_thin_groups_do_not_count():
    two = [R("When will my income increase?", 12)] * 5
    assert M.build(two, None, "en", TODAY)["empty"] is True                      # one distinct question, one day
    assert M.build([R("Should I buy gold?", 12, "speculation"), R("Should I buy gold?", 11, "speculation"), R("Should I buy gold?", 10, "speculation")],
                   None, "en", TODAY)["empty"] is False                         # three different days is a matter
    assert M.build([], None)["empty"] is True and M.build(None, None)["prompt"] == "What are you deciding right now?"


def test_old_questions_fall_out_and_recent_ones_rank_higher():
    old = [{"question": "Should I buy gold?", "domain": "speculation", "created_at": "2026-04-01T00:00:00+00:00"},
           {"question": "Is gold a good time to buy?", "domain": "speculation", "created_at": "2026-04-02T00:00:00+00:00"}]
    assert M.build(old, None, "en", TODAY)["empty"] is True
    mixed = ROWS + [R("Should I buy gold?", 2, "speculation")]
    assert M.build(mixed, None, "en", TODAY, limit=5)["matters"][0]["score"] >= M.build(mixed, None, "en", TODAY, limit=5)["matters"][-1]["score"]


def test_next_window_comes_from_the_feed_for_the_topic():
    feed = {"as_of": "2026-10-13", "tracks": [{"topic": "money", "windows": [
        {"kind": "open", "start": "2027-01-10", "end": "2027-05-09"}, {"kind": "care", "start": "2027-06-09", "end": "2027-09-06"}]}]}
    inc = next(m for m in M.build(ROWS, feed, "en", TODAY, limit=5)["matters"] if m["title"] == "Income and pricing")
    assert inc["next"] == {"open": {"start": "2027-01-10", "end": "2027-05-09"}, "care": {"start": "2027-06-09", "end": "2027-09-06"}}
    assert M.build(ROWS, None, "en", TODAY, limit=5)["matters"][0]["next"] is None


def test_limit_ids_and_spanish_prompt():
    r = M.build(ROWS, None, "en", TODAY, limit=1)
    assert len(r["matters"]) == 1 and len(r["matters"][0]["id"]) == 10
    assert M.build([], None, "es")["prompt"] == "¿Qué estás decidiendo ahora mismo?"
    es = M.build([R("¿Cuándo aumentarán mis ingresos?", 12), R("¿Debo subir mis precios?", 11)], None, "es", TODAY)
    assert es["matters"][0]["title"] == "Ingresos y precios"
