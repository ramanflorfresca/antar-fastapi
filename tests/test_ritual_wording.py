"""Rituals copy never says "season": users read it as the calendar season, and the
engine's own sense of it (daily-moving) is not what they picture. Say "right now" / "this phase"."""
import ast
import pathlib
import re

from antar_engine import daily_wisdom as DW

_BAD = re.compile(r"\bseasons?\b|\btemporadas?\b", re.I)
_ROOT = pathlib.Path(__file__).resolve().parent.parent / "antar_engine"


def test_why_now_lines_have_no_season_word():
    for key, by_lang in DW.WHY_NOW.items():
        for lang, text in by_lang.items():
            assert not _BAD.search(text), (key, lang, text)


def _user_strings(path):
    tree = ast.parse(path.read_text())
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                doc_ids.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            yield node.value


def test_practice_composer_strings_have_no_season_word():
    bad = [s for s in _user_strings(_ROOT / "practice_composer.py") if _BAD.search(s)]
    assert not bad, bad


def test_wisdom_chat_context_tells_the_model_not_to_say_season():
    out = DW.build_daily_wisdom({}, {"vimsottari": []}, "c1", "en")
    ctx = out.get("ask_context") or (out.get("chat") or {}).get("context") or ""
    assert ctx, out.keys()
    assert 'never say the word "season"' in ctx
