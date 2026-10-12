"""The lean /potential entry and /prescribe fix projections must carry watch_outs.

main.py is too large to import in a unit test, so this guards the source: each
projection that builds a lean dict for the client has to name the field, which is
the exact trap that previously hid `what_changes` from the client.
"""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "main.py").read_text()


def _block(start_marker: str, end_marker: str) -> str:
    a = SRC.index(start_marker)
    return SRC[a:SRC.index(end_marker, a)]


def test_potential_entry_projection_carries_watch_outs():
    body = _block("def _shape_entry(dom, s, ov, best_for):", "return entry")
    assert re.search(r'"watch_outs"\s*:', body)
    assert "card.get(\"watch_outs\")" in body


def test_prescribe_fix_projection_carries_watch_outs():
    body = _block("def _shape_fix(cn, s):", "prescription = None")
    assert "compose_watch_outs" in body
    assert re.search(r'"watch_outs"\s*:\s*_wo', body)
