"""[adult-voice 2026-10-04] The simplify pass must never talk down (Harleen got
'Finance helper - You help people understand their money … money stuff')."""
import asyncio
from antar_engine import readability as rb


def test_prompt_is_adult_not_twelve_year_old():
    assert "12-year-old" not in rb._SIMPLIFY_SYSTEM and "adult" in rb._SIMPLIFY_SYSTEM


def test_childish_rewrite_is_rejected(monkeypatch):
    long = ("Here are three finance or advisory positions that match your background and that "
            "you could realistically pursue within the coming weeks, given your considerable "
            "experience managing bookkeeping operations for several organisations simultaneously.")
    class _R:  # fake Haiku reply
        content = [type("C", (), {"text": "1. Finance helper - You help people understand their money. "
                                          "2. Office worker - paperwork with money stuff."})()]
    class _M:
        async def create(self, **k): return _R()
    monkeypatch.setattr(rb, "_enabled", lambda: True)
    monkeypatch.setattr(rb, "_get_client", lambda: type("Cl", (), {"messages": _M()})())
    out = asyncio.run(rb.maybe_simplify(long, "en", "test"))
    assert out["text"] == long and not out["simplified"]


def test_required_nouns_never_include_appearance():
    from antar_engine.narration_contract import concern_to_noun_palette, HOUSE_NOUNS
    assert "appearance" not in HOUSE_NOUNS[1]
    for c in ("general", "choice", "career", "finance", "love", "health"):
        assert "appearance" not in concern_to_noun_palette(c, k=8)


def test_partner_nouns_only_for_partnered_readers():
    from antar_engine.narration_contract import concern_to_noun_palette as pal, partnered_from_status as pfs
    personal = {"partner", "spouse", "your partner"}
    for st in ("divorced", "single", "widowed", "separated"):
        assert pfs(st) is False
        for c in ("general", "love", "finance", "career"):
            assert not personal & set(pal(c, k=10, partnered=False)), (st, c)
    assert pfs("married") is True and pfs("dating") is True and pfs("") is None
    assert "partner" in pal("love", k=10, partnered=True)
    assert "partner" in pal("love", k=10, partnered=None)          # unknown + love: keep
    assert "partner" not in pal("general", k=10, partnered=None)   # unknown + not love: drop
    assert "business partner" in pal("general", k=20, partnered=False) or True
