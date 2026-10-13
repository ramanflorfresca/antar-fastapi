import os
import re

import pytest

SRC = open(os.path.join(os.path.dirname(__file__), "..", "main.py")).read()
HOME_ENDPOINTS = ("get_instrument_brief", "get_instrument_timeline", "get_coming", "get_horizon_card", "get_matters", "get_shortcuts", "get_seasons")


def _body(name: str) -> str:
    i = SRC.index(f"async def {name}(")
    j = SRC.index("\n@app.", i)
    return SRC[i:j]


@pytest.mark.parametrize("name", HOME_ENDPOINTS)
def test_every_home_endpoint_rejects_a_malformed_chart_id_before_touching_the_database(name):
    body = _body(name)
    call = body.index("_require_chart_uuid(chart_id)")
    first_db = min(x for x in (body.find("supabase."), body.find("_topic_ctx_load")) if x >= 0)
    assert call < first_db                                     # validated first, so PostgREST never sees 'not-a-uuid'


def test_require_chart_uuid_maps_bad_input_to_404_and_good_input_through():
    import main as M
    from fastapi import HTTPException
    for bad in ("not-a-uuid", "", " ", "undefined", None, "a4c9d57b-fb9c-4890-8fe7", "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed-extra"):
        with pytest.raises(HTTPException) as e:
            M._require_chart_uuid(bad)
        assert e.value.status_code == 404
    good = "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed"
    assert M._require_chart_uuid(good) == good and M._require_chart_uuid(f"  {good.upper()} ") == good
