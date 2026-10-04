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
