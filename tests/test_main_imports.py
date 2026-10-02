"""Every antar_engine import in main.py must actually load (2026-10-02).

main.py wraps most engine imports in try/except, so a module that can't be
imported fails SILENTLY — the feature just never runs. Found this way:
  - concern_router: IndentationError Mar 30 → Oct 2 (deleted, #72)
  - food_engine: `from __future__` not first, Jun 22 → Oct 2 (fixed)
  - /predict "system state": imported get_instrument_scores and
    get_lk_state, which never existed anywhere (block deleted)
This test turns that class of bug into a red CI run.
"""
import ast
import contextlib
import importlib
import io
import pathlib

# Modules main.py still names but can never reach. Each needs a reason; remove
# the entry when the dead code is removed.
KNOWN_UNREACHABLE = {
    # Deleted 2026-07-31 (P4 astro consolidation). Only referenced below an
    # unconditional HTTP 410 in the deprecated /api/v1/astrocartography/*
    # endpoints (replaced by /api/v1/places/*).
    "antar_engine.astrocartography_v2",
}


def _import(name):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return importlib.import_module(name)


def _engine_imports():
    tree = ast.parse((pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("antar_engine"):
            yield n.module, [a.name for a in n.names], n.lineno
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("antar_engine"):
                    yield a.name, [], n.lineno


def test_every_engine_import_in_main_resolves():
    problems = []
    for module, names, line in _engine_imports():
        if module in KNOWN_UNREACHABLE:
            continue
        try:
            mod = _import(module)
        except Exception as e:  # noqa: BLE001 — report every failure
            problems.append(f"main.py:{line} import {module} → {type(e).__name__}: {e}")
            continue
        for name in names:
            if name == "*" or hasattr(mod, name):
                continue
            try:
                _import(f"{module}.{name}")      # `from antar_engine import submodule`
            except Exception:
                problems.append(f"main.py:{line} {module} has no '{name}'")
    assert not problems, "\n".join(problems)


def test_known_unreachable_is_still_needed():
    referenced = {m for m, _, _ in _engine_imports()}
    for module in KNOWN_UNREACHABLE:
        assert module in referenced, f"{module} no longer referenced — drop it from KNOWN_UNREACHABLE"
