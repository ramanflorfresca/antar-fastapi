"""[people-reading 2026-10-11] each saved connection says how far its reading goes and what produces the next part."""
from antar_engine import people_reading as PR

L1 = "Person A and saransh have a strong cofounder fit with specific gaps to close. Settle equity, roles, and decision rights early."
L2 = "How to work with Gerardo\n\nPut him over operations and finance; keep yourself on vision."
L3 = "The timing to watch\n\nRight now you're on different clocks."


def test_layer_one_only_points_at_the_roles_step():
    r = PR.stage(L1, None, None, "saransh", "en")
    assert r == {"stage": 1, "has_roles": False, "has_timing": False, "next_step": "add_context",
                 "headline": "You and saransh have a strong cofounder fit with specific gaps to close."}


def test_roles_present_points_at_the_timing_step_and_all_three_has_no_next_step():
    assert PR.stage(L1, L2, None, "G")["next_step"] == "add_product" and PR.stage(L1, L2, None, "G")["stage"] == 2
    full = PR.stage(L1, L2, L3, "G")
    assert full["stage"] == 3 and full["next_step"] is None and full["has_roles"] and full["has_timing"]


def test_headline_is_english_only_and_clean():
    assert PR.stage(L1, None, None, "x", "es")["headline"] is None and PR.stage(L1, None, None, "x", "pt-BR")["headline"] is None
    r = PR.stage("**Raman** and Gerardo can build something real. More.", None, None, "G")
    assert r["headline"] == "Raman and Gerardo can build something real."
    assert len(PR.stage("A" * 400, None, None, "")["headline"]) <= 200


def test_empty_and_garbage_never_raise_and_blank_layers_count_as_absent():
    assert PR.stage(None, "   ", "", "")["stage"] == 1 and PR.stage(None, None, None)["headline"] is None
    assert PR.stage(object(), 5, [], None)["stage"] in (1, 2, 3)


def test_network_rows_carry_the_reading_stage(monkeypatch):
    import main
    from tests.test_compat_types_catalog import _FakeSB
    sessions = [
        {"id": "s1", "chart_id_b": "p1", "name_b": "Gerardo", "compat_type": "business", "score": 60, "created_at": "2026-10-01",
         "layer1_analysis": L1, "layer2_analysis": L2, "layer3_analysis": L3},
        {"id": "s2", "chart_id_b": "p2", "name_b": "saransh", "compat_type": "cofounder", "score": 51, "created_at": "2026-09-01",
         "layer1_analysis": L1, "layer2_analysis": None, "layer3_analysis": None},
    ]
    monkeypatch.setattr(main, "supabase", _FakeSB({"compatibility_sessions": sessions}))
    monkeypatch.setattr(main, "_network_today_glance", lambda cid, lang: {"available": True})
    monkeypatch.setattr(main, "_connection_notes_bulk", lambda a, ids: {})
    en = main.get_network("chart-a", "en")["people"]
    g, s = en[0]["primary"]["reading"], en[1]["primary"]["reading"]
    assert g["stage"] == 3 and g["next_step"] is None
    assert s["stage"] == 1 and s["next_step"] == "add_context" and s["headline"].startswith("You and saransh")
    assert en[1]["relationships"][0]["reading"] == s                       # every relationship row carries it too
    assert main.get_network("chart-a", "es")["people"][1]["primary"]["reading"]["headline"] is None
