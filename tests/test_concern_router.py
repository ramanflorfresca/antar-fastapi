"""concern_router must import, and stay OFF in production unless switched on.

From 2026-03-30 a stray `}` made this module fail to import; main.py's
try/except hid it for six months, so /predict ran without these prompts.
The prompts predate the voice rules (planet names, D7/D60, "Luck Blueprint"),
so loading is fixed but use is gated behind CONCERN_ROUTER_MODE=on.
"""
import pathlib
import re

import antar_engine.concern_router as cr


def test_module_imports_with_every_domain():
    assert "general" in cr.DOMAIN_CONFIGS
    for k in ("finance", "career", "children", "property", "luck"):
        assert k in cr.DOMAIN_CONFIGS


def test_every_detectable_concern_has_a_config_or_falls_back():
    for concern in cr.CONCERN_KEYWORDS:
        cfg = cr.get_domain_config(concern)
        assert cfg["system_instruction"] and cfg["display_name"]


def test_prompts_build_for_every_domain():
    for concern in cr.DOMAIN_CONFIGS:
        assert "UNIVERSAL RULES" in cr.build_concern_system_prompt(concern)
        assert cr.get_priority_context_instruction(concern).startswith("PRIORITY CONTEXT")
    assert cr.get_domain_config("no-such-domain") is cr.DOMAIN_CONFIGS["general"]


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("CONCERN_ROUTER_MODE", raising=False)
    assert cr.is_enabled() is False
    monkeypatch.setenv("CONCERN_ROUTER_MODE", "on")
    assert cr.is_enabled() is True
    monkeypatch.setenv("CONCERN_ROUTER_MODE", "shadow")
    assert cr.is_enabled() is False


def test_every_main_call_site_is_gated():
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text().splitlines()
    calls = [i for i, line in enumerate(src)
             if re.search(r"\b(build_concern_system_prompt|get_priority_context_instruction)\(", line)
             and "import" not in line]
    assert len(calls) == 3
    for i in calls:
        window = "\n".join(src[max(0, i - 1): i + 1])
        assert "_cr_on()" in window, f"main.py:{i + 1} uses concern_router without the gate"
