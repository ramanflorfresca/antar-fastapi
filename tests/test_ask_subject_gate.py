"""Ask subject gate in main.py: a question about a saved Person is read from THAT
person's chart, never the asker's. main.py is too heavy to import, so the gate and
its two loaders are lifted out with ast and run against fakes."""
import ast
import asyncio
import pathlib
import re

import pytest

from antar_engine import ask_subject_person as asp

ROOT = pathlib.Path(__file__).resolve().parents[1]
_WANT = {"_ask_load_people_sync", "_ask_load_person_sync", "_ask_subject_gate"}

PLANETS = {p: {"sign": "Aries", "house": h} for p, h in zip(
    ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"],
    [1, 2, 3, 4, 5, 6, 7, 8, 2])}
KID_CHART = {"lagna": {"sign": "Leo"},
             "planets": {p: dict(v, sign="Taurus") for p, v in PLANETS.items()}}
ME_CHART = {"lagna": {"sign": "Aries"}, "planets": dict(PLANETS)}


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.f = db, table, {}

    def select(self, *_a, **_k): return self
    def eq(self, k, v): self.f[k] = v; return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def single(self): self._single = True; return self

    def execute(self):
        rows = [r for r in self.db[self.table]
                if all(r.get(k) == v for k, v in self.f.items())]
        class R: pass
        r = R()
        r.data = (rows[0] if rows else {}) if getattr(self, "_single", False) else rows
        return r


class _SB:
    def __init__(self, db): self.db = db
    def table(self, t): return _Q(self.db, t)


def _build(people, llm_text="Amik looks steady for the next stretch.", charts=None):
    src = (ROOT / "main.py").read_text()
    ns = {"asyncio": asyncio, "re": re, "os": __import__("os")}
    db = {"chart_connections": [dict(chart_id_a="me", **p) for p in people],
          "charts": charts if charts is not None else [
              {"id": "me", "chart_data": ME_CHART, "first_name": "Raman"},
              {"id": "kid", "chart_data": KID_CHART, "first_name": "Amik"}]}
    calls = {"llm": [], "persist": 0}

    async def llm(prompt, system_override="", **k):
        calls["llm"].append((prompt, system_override))
        return llm_text, 1

    async def persist(*a, **k): calls["persist"] += 1

    ns.update(supabase=_SB(db), get_dashas_for_chart=lambda cid: {},
              _safe_jsonb=lambda x: x, _ask_concern_route=lambda q: None,
              _detect_concern=lambda q: "marriage" if "marri" in q.lower() else "general",
              call_llm_claude=llm, SYSTEM_PROMPT="BASE", _ask_persist=persist,
              _ask_recent_thread=lambda *a, **k: [])
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in _WANT:
            exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
    assert _WANT <= set(ns)
    return ns, calls


KID = {"chart_id_b": "kid", "name_b": "Amik", "compat_type": "child"}


def _run(ns, q, lang="en"):
    return asyncio.run(ns["_ask_subject_gate"](q, "me", lang, 0))


def test_son_marriage_reads_the_childs_chart_with_narrator_contract():
    ns, calls = _build([KID])
    payload, counts = _run(ns, "when will my son get married")
    assert counts is True and payload["subject"]["name"] == "Amik"
    prompt, system = calls["llm"][0]
    assert "This question is about Amik (child)" in system
    assert "Use ONLY the supplied reading of Amik's chart" in system
    assert "Amik's rising sign: Leo" in prompt          # the child's chart
    assert "Aries" not in prompt.split("BOND CONTEXT")[0]   # not the asker's lagna as theirs
    assert "BOND CONTEXT" in prompt and "house of children" in prompt


def test_self_question_returns_none_unchanged():
    ns, calls = _build([KID])
    assert _run(ns, "how is my health") is None
    assert calls["llm"] == []
    ns, _ = _build([])
    assert _run(ns, "when will I get married") is None


def test_two_children_clarifies_with_names_in_language():
    ns, _ = _build([KID, {"chart_id_b": "k2", "name_b": "Priya", "compat_type": "child"}])
    payload, counts = _run(ns, "mi hijo cuando se casa?", "es")
    assert counts is False and payload["needs_clarification"]
    assert set(payload["clarification_chips"]) == {"Amik", "Priya"}
    assert "¿a cuál" in payload["read"]


def test_missing_person_is_honest_not_the_askers_reading():
    ns, calls = _build([])
    payload, counts = _run(ns, "when will my daughter get married")
    assert counts is False and calls["llm"] == []
    assert "don't have your child's chart" in payload["read"]


def test_unreadable_chart_does_not_fall_back_to_asker():
    ns, calls = _build([KID], charts=[{"id": "me", "chart_data": ME_CHART},
                                      {"id": "kid", "chart_data": {}}])
    payload, counts = _run(ns, "how is Amik doing")
    assert counts is False and calls["llm"] == []
    assert "isn't readable" in payload["read"]


def test_guard_drops_reader_own_claims_and_names_the_person():
    out = asp.guard_read("Your health is fragile. Things look calm for him.", "Amik Singh")
    assert "Your health" not in out and out.startswith("Amik:")
    assert asp.guard_read("Your marriage is the issue.", "Amik") == ""


def test_gate_runs_before_asker_engines_in_ask_endpoint():
    src = (ROOT / "main.py").read_text()
    body = src[src.index("async def ask_endpoint"):]
    gate = body.index("_ask_subject_gate(")
    for later in ("_ask_needs_lifefact_clarify(", "_detect_concern(question)",
                  "_ask_needs_career_clarify("):
        assert gate < body.index(later), later


def test_gate_fails_open_to_self_on_error():
    ns, _ = _build([KID])
    ns["supabase"] = None            # every load raises
    assert _run(ns, "when will my son get married") is None
