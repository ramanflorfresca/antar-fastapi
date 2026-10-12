"""[output-contract 2026-10-12] The Ask output contract bans 'chart', 'horoscope', 'astrology', houses and house numbers (and the Spanish carta / casa N) in USER-FACING text; the App Store 4.3 defence
rests on the landing screen not reading as an astrology app. The conversation audit found ~40 answers saying "your chart" from our own template lines. This keeps the answer-template modules clean.
Docstrings, comments, log lines and the technical `basis_facts` strings (which carry {l1}-style placeholders) are exempt."""
import ast
import re
from pathlib import Path

RX = re.compile(r"\b(charts?|horoscopes?|astrolog\w*|cartas?|mapa astral|casa \d+|\d+(?:st|nd|rd|th) house)\b", re.I)
FILES = ["ask_basis", "ask_basis_es", "basis_plain", "positioning", "work_fit", "work_profile", "staff_decision", "authority_read", "partner_roles", "pair_view", "divorced_union", "ask_families", "ask_followups", "medical_safety"]
ROOT = Path(__file__).resolve().parent.parent / "antar_engine"


def _user_facing_hits(name):
    tree = ast.parse((ROOT / f"{name}.py").read_text(encoding="utf-8"))
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            docs.add(id(n.body[0].value))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and RX.search(n.value) and " " in n.value and len(n.value) > 14:
            v = n.value.strip()
            if v.startswith(("[", "(?i)", "#")) or "{l1}" in v or "{l10}" in v:       # log lines, regexes, technical basis_facts
                continue
            out.append((n.lineno, v[:90]))
    return out


def test_answer_template_modules_never_say_chart_horoscope_or_house_numbers_to_the_user():
    bad = {f: _user_facing_hits(f) for f in FILES}
    bad = {f: h for f, h in bad.items() if h}
    assert not bad, bad
