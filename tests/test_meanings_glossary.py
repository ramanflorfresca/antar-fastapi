"""[glossary 2026-10-12] The glossary export: same table as the Why sheet, complete in en and es, never doom."""
import json
import re

import pytest

from antar_engine import meanings as M

_DOOM = re.compile(r"\b(malefic|benefic|doomed|cursed|you will (die|get sick|fall ill)|bad luck|evil|lifespan)\b", re.I)


@pytest.mark.parametrize("lg", ["en", "es"])
def test_glossary_is_complete(lg):
    g = M.glossary(lg)
    assert g["language"] == lg and g["intro"] and g["aims_note"] and g["pull_intro"]
    assert [a["id"] for a in g["aims"]] == ["dharma", "artha", "kama", "moksha"]
    assert sorted(h for a in g["aims"] for h in a["houses"]) == list(range(1, 13))
    assert [h["id"] for h in g["houses"]] == list(range(1, 13))
    assert [p["id"] for p in g["planets"]] == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    for p in g["planets"]:
        assert all(p[k] for k in ("name", "verb", "covers", "watch", "helps", "nature", "nature_label", "pull", "vedic"))
    for h in g["houses"]:
        assert all(h[k] for k in ("name", "q", "covers", "watch", "helps", "aim", "aim_line"))
    ids = [t["id"] for t in g["terms"]]
    assert ids == ["vargottama", "combust", "retrograde", "exalted", "debilitated", "own sign", "sub_period", "house_lord", "significator"]
    assert all(t["term"] and t["plain"] for t in g["terms"])


def test_unknown_language_falls_back_to_english():
    assert M.glossary("xx")["language"] == "en" and M.glossary("es-MX")["language"] == "es"


def test_no_doom_wording_and_pull_is_a_spectrum_not_a_label():
    for lg in M.LANGS:
        g = M.glossary(lg)
        blob = json.dumps(g, ensure_ascii=False)
        assert not _DOOM.search(blob)
    assert M.PULL["Sun"]["en"] == "spiritual and material" and M.PULL["Saturn"]["en"].startswith("material through effort")


def test_export_is_json_serialisable():
    json.dumps({lg: M.glossary(lg) for lg in M.LANGS}, ensure_ascii=False)
