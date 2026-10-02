"""Ask deal-role override must read the USER's words only (2026-10-02).

Our own role-clarify answer lists every role ("broker/agent earning a
commission, taking an equity stake…"). With answers in the context, the next
short question after a clarify — "How wealthy can I become in this
lifetime?" — resolved to 'career' and came back as a "your strongest fields"
read (live, Raman's thread, 2026-09-24).

main.py is too heavy to import in a unit test, so the few pure helpers are
lifted out with ast.
"""
import ast
import pathlib

_WANT_FUNCS = {"_ask_role_concern", "_is_wealth_magnitude_q", "_is_career_type_q"}
_WANT_CONSTS = {"_ASK_DEAL_WORDS", "_ASK_ROLE_WORDS"}


def _load():
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    ns: dict = {}
    for node in ast.parse(src).body:
        is_const = isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") in _WANT_CONSTS for t in node.targets)
        is_func = isinstance(node, ast.FunctionDef) and node.name in _WANT_FUNCS
        if is_const or is_func:
            exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
    assert _WANT_FUNCS <= set(ns)
    return ns["_ask_role_concern"]


_CLARIFY = ("Happy to help — but to read this precisely I need your role in the deal. "
            "Are you the broker/agent earning a commission, taking an equity stake, "
            "or buying it yourself?")


def test_our_clarify_text_does_not_reroute_next_question():
    rc = _load()
    thread = [{"q": "How big can my wealth get, and should I concentrate on one venture "
                    "or diversify?", "a": _CLARIFY}]
    assert rc("How wealthy can I become in this lifetime?", thread) is None


def test_role_chip_replies_still_route():
    rc = _load()
    thread = [{"q": "Should I take this real estate deal or wait?", "a": _CLARIFY}]
    assert rc("Equity stake", thread) == "finance"
    assert rc("Broker / commission", thread) == "career"


def test_unrelated_question_after_deal_untouched():
    rc = _load()
    assert rc("how is my love life?", [{"q": "Should I take the deal?", "a": _CLARIFY}]) is None
