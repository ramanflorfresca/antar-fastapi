"""day_map carries a stable topic key; the Today check-in is scoped + plain; 'until,' is broken."""
from antar_engine import daily_life_areas as L
from antar_engine import prediction_tracker as P
from antar_engine.daily_prediction_engine import _looks_broken
from antar_engine.topic_copy import TOPIC_KEYS


def test_area_topic_values_are_real_topic_keys_or_none():
    assert set(L.AREA_TOPIC) >= set(L.FRIENDLY_LABEL)
    for k, t in L.AREA_TOPIC.items():
        assert t is None or t in TOPIC_KEYS, (k, t)
    assert L.AREA_TOPIC["money"] == "money" and L.AREA_TOPIC["speculation"] == "business"
    assert L.AREA_TOPIC["relationship"] == "love" and L.AREA_TOPIC["spiritual"] == "peace"


def test_every_day_map_row_has_a_topic_field():
    active = [{"key": "money", "polarity": "opportunity", "tone": 2.0, "transit_count": 2},
              {"key": "speculation", "polarity": "risk", "tone": -2.0, "transit_count": 2},
              {"key": "relationship", "polarity": "opportunity", "tone": 1.5, "transit_count": 1}]
    rows = L.build_day_map(active, [], None)
    assert rows and all("topic" in r for r in rows)
    by = {r["key"]: r["topic"] for r in rows}
    assert by.get("money") == "money" and by.get("speculation") == "business"
    assert {"key", "topic", "label", "line", "tone"} <= set(rows[0])


def test_plain_claim_drops_the_energy_euphemism_and_fixes_the_verb():
    raw = ("You are in a clarifying pressure — your discipline and structure energy is asking "
           "what is truly real and lasting in your life.")
    out = P._plain_claim(raw)
    assert "energy" not in out and "discipline and structure are asking" in out
    assert P._plain_claim("A steady day for deals.") == "A steady day for deals."
    assert "your growth and wisdom" in P._plain_claim("your growth and wisdom energy opens a door")


class _SB:
    def __init__(self, rows): self.rows = rows
    def table(self, _): return self
    def select(self, *_): return self
    def eq(self, *_): return self
    def lte(self, *_): return self
    def order(self, *_, **__): return self
    def limit(self, *_): return self
    def update(self, *_): return self
    def execute(self): return type("R", (), {"data": self.rows})()


def test_today_surface_returns_only_todays_own_claim_not_a_chapter_claim():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    rows = [{"id": "ch", "correlation_key": "chapter-1", "show_after": "2026-01-01",
             "trackable_claim": "You are in a clarifying pressure — your discipline and structure energy is asking x."},
            {"id": "dy", "correlation_key": f"daily-{today}", "show_after": "2026-01-02",
             "trackable_claim": "A steady day with a real window for deals."}]
    both = P.get_pending_feedback("c", _SB(rows))
    only = P.get_pending_feedback("c", _SB(rows), surface="today")
    assert {r["id"] for r in both} == {"ch", "dy"}
    assert [r["id"] for r in only] == ["dy"]
    chapter = next(r for r in both if r["id"] == "ch")
    assert "energy" not in chapter["trackable_claim"]            # plain wording even off the Today surface


def test_dangling_until_is_a_broken_sentence():
    assert _looks_broken("document it and hold your response until, when the day's friction eases.")
    assert _looks_broken("Wait until.")
    assert not _looks_broken("Hold your response until the evening, when the day's friction eases.")
    assert not _looks_broken("Wait until 4:54 PM, then decide.")


def test_ping_text_quotes_the_claim_in_plain_words():
    import main
    t = main._build_ping_text(
        "You are in a clarifying pressure — Saturn is asking what is truly real and lasting in your life.",
        "current_chapter")
    assert t.startswith("Your chart said:") and "energy" not in t and "Saturn" not in t
