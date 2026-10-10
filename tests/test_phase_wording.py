"""User-facing deterministic copy says "phase", not "season": readers take "season" for the calendar."""
import ast
import pathlib
import re

_BAD = re.compile(r"\bseasons?\b|\btemporadas?\b", re.I)
_ROOT = pathlib.Path(__file__).resolve().parent.parent / "antar_engine"
_FILES = ("compatibility_templates.py", "aligned_path.py", "season_protection.py", "lk_conditions.py",
          "circle_brief.py", "chart_identity.py")


def _strings(path):
    tree = ast.parse(path.read_text())
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(n, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                docs.add(id(body[0].value))
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and " " in n.value:
            yield n.value


def test_user_facing_copy_has_no_season_word():
    bad = {}
    for f in _FILES:
        hits = [s[:90] for s in _strings(_ROOT / f) if _BAD.search(s)]
        if hits:
            bad[f] = hits
    assert not bad, bad


def test_the_aligned_path_block_is_titled_right_now():
    from antar_engine import aligned_path as AP
    src = (_ROOT / "aligned_path.py").read_text()
    assert '"title": "Right now"' in src and '"title": "Your season"' not in src
