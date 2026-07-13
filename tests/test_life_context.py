"""Life-context gating: never name a child/spouse the user may not have."""
from antar_engine.today_narration import summarize_drivers, _apply_life_context

_CHILDREN_DEBUG = {
    "chosen": ["children"],
    "net": {"children": -1.5},
    "votes": ["D:dasha_mdh5:children:-1.5"],
}


def _children_beat(context):
    beats = summarize_drivers(_CHILDREN_DEBUG, context=context)
    return next(b for b in beats if b["domain"] == "children")


def test_no_kids_drops_child_noun():
    b = _children_beat({"children_status": "no_children_unsure"})
    joined = " ".join(b["concrete_nouns"]).lower()
    assert "child" not in joined and "kid" not in joined
    assert any("project" in n or "romance" in n or "idea" in n for n in b["concrete_nouns"])
    assert "child" not in b["life_area"].lower()


def test_unknown_status_is_safe_default():
    # We don't KNOW they have kids -> still don't assert "a child".
    b = _children_beat({"children_status": "unknown"})
    assert "child" not in " ".join(b["concrete_nouns"]).lower()


def test_positive_status_keeps_child():
    b = _children_beat({"children_status": "has_children"})
    assert any("child" in n.lower() for n in b["concrete_nouns"])


def test_no_context_unchanged():
    b = _children_beat(None)
    assert any("child" in n.lower() for n in b["concrete_nouns"])   # legacy behavior preserved


def test_spouse_dropped_when_not_married():
    nouns, theme = _apply_life_context(
        "partner", ["your spouse", "a business partner", "a deal"],
        "your spouse and the deals you make", {"marital_status": "single"})
    assert not any("spouse" in n.lower() for n in nouns)
    assert "spouse" not in theme.lower()
