"""Check-in pings must never cut a claim mid-word (2026-10-02, Today showed
"…courage and decisive action are your fuel is the sub...")."""
import ast
import pathlib


def _load():
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    ns: dict = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in ("_clip_claim", "_build_ping_text"):
            exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
    return ns


LONG = ("Within your larger chapter, right now a high-energy action period — courage and "
        "decisive action are your fuel is the sub-theme that runs through the next several "
        "months, asking you to move before you feel fully ready.")


def test_never_mid_word_and_within_limit():
    clip = _load()["_clip_claim"]
    out = clip(LONG, 160)
    assert len(out) <= 160
    assert out.endswith("…") or out.endswith(".")
    head = out.rstrip("…")
    assert LONG.startswith(head)
    assert LONG[len(head)] in " —,;"   # cut lands on a break, not inside a word


def test_prefers_the_first_whole_sentence():
    clip = _load()["_clip_claim"]
    t = "You are in a clarifying pressure season. " + "More detail follows here. " * 10
    assert clip(t, 160) == "You are in a clarifying pressure season."


def test_short_text_untouched_and_planet_names_stripped():
    clip = _load()["_clip_claim"]
    assert clip("A short claim.", 160) == "A short claim."
    out = clip("You are in a clarifying pressure — Saturn is asking what is truly real.", 160)
    assert "Saturn" not in out


def test_ping_text_wraps_clean_claim():
    ns = _load()
    msg = ns["_build_ping_text"](LONG, "sub_theme")
    assert msg.startswith('Your pattern suggested: "')
    assert "is the sub..." not in msg and msg.endswith("— Did this unfold for you?")
