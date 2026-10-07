"""GET /api/v1/languages: the language list for the pre-account onboarding step."""


def test_public_languages_needs_no_login_and_matches_the_settings_list():
    import main
    out = main.public_languages()
    assert out["available"] == ["en", "hi", "hinglish", "es", "pt"]      # the five agreed, in order
    assert "fr" not in out["available"]
    assert set(out["labels"]) == set(out["available"])
    assert all(out["labels"][c] for c in out["available"])
    assert set(out["available"]) <= set(main.SETTINGS_AVAILABLE_LANGS)


def test_route_is_registered_without_an_auth_header_parameter():
    import main
    route = next(r for r in main.app.routes if getattr(r, "path", "") == "/api/v1/languages")
    assert "GET" in route.methods
    assert not any(p.name.lower() == "authorization" for p in route.dependant.header_params)
