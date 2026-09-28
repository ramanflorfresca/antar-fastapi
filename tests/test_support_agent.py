"""
Unit tests for the /api/v1/support answering brain.

Pure logic only — no network, no Claude, no Supabase. The LLM's judgement is
not testable here; what IS testable is that a well-formed reply is parsed, that
a malformed one still yields a usable answer, that billing goes to the billing
mailbox, and that the system prompt stays cacheable.

Run:  pytest tests/test_support_agent.py -v
"""

from antar_engine import support_agent as sa


# ─── parse_model_reply ──────────────────────────────────────────
def test_parse_reads_route_tag():
    route, text = sa.parse_model_reply("ROUTE: billing\n\nI can't see your account.")
    assert route == "billing"
    assert text == "I can't see your account."


def test_parse_accepts_every_valid_route():
    for r in ("answer", "unknown", "billing", "offtopic"):
        assert sa.parse_model_reply(f"ROUTE: {r}\n\nbody")[0] == r


def test_parse_keeps_prose_when_tag_is_missing():
    """A weaker fallback model may just answer. Losing a usable reply over a
    missing header would be the worse failure."""
    route, text = sa.parse_model_reply("Antar is free to start.")
    assert route == "answer"
    assert text == "Antar is free to start."


def test_parse_ignores_an_invented_route():
    """An unrecognised tag still gets stripped — the user must never see a
    control line — and the reply degrades to a plain answer."""
    route, text = sa.parse_model_reply("ROUTE: escalate\n\nbody")
    assert route == "answer"
    assert text == "body"


def test_parse_strips_markdown():
    _, text = sa.parse_model_reply("ROUTE: answer\n\nOpen **Plans** and `Settings`.")
    assert "**" not in text and "`" not in text
    assert "Plans" in text and "Settings" in text


def test_parse_empty_reply_is_unknown():
    assert sa.parse_model_reply("")[0] == "unknown"
    assert sa.parse_model_reply("   \n ")[0] == "unknown"


# ─── compose_response ───────────────────────────────────────────
def test_answer_is_high_confidence():
    p = sa.compose_response("answer", "Everything readable is free.", "en")
    assert p["confidence"] == "high"
    assert p["contact_email"] == sa.CONTACT_EMAIL


def test_billing_routes_to_the_billing_mailbox():
    """The FAQ publishes two addresses; a payment problem must not go to the
    general one."""
    p = sa.compose_response("billing", "I can't see your payments.", "en")
    assert p["contact_email"] == sa.CONTACT_EMAIL_BILLING
    assert p["confidence"] == "low"


def test_unknown_without_text_still_says_something():
    p = sa.compose_response("unknown", "", "en")
    assert p["answer"].strip()
    assert p["confidence"] == "low"


def test_offtopic_has_a_redirect():
    p = sa.compose_response("offtopic", "", "en")
    assert p["answer"] == sa.OFFTOPIC_TEXT["en"]


def test_every_language_gets_localized_furniture():
    for lang in sa.SUPPORTED_LANGUAGES:
        p = sa.compose_response("unknown", "", lang)
        assert p["language"] == lang
        assert p["disclaimer"] == sa.DISCLAIMER_TEXT[lang]
        assert p["followup"] == sa.FOLLOWUP_TEXT[lang]
        assert "{sla}" not in p["answer"]


def test_unsupported_language_falls_back_to_english():
    assert sa.normalize_language("de") == "en"
    assert sa.normalize_language("es-419") == "es"
    assert sa.normalize_language(None) == "en"


def test_fallback_is_flagged_unavailable():
    p = sa.fallback_response("pt")
    assert p["confidence"] == "unavailable"
    assert p["language"] == "pt"
    assert p["answer"].strip()


# ─── build_system_prompt ────────────────────────────────────────
def test_prompt_prefix_is_identical_across_languages():
    """Everything before the LIVE DATA marker must be byte-identical, or each
    language writes its own cache entry instead of sharing one."""
    prefixes = {l: sa.build_system_prompt(l).split("## LIVE DATA")[0]
                for l in sa.SUPPORTED_LANGUAGES}
    assert len(set(prefixes.values())) == 1


def test_prompt_prefix_clears_the_cacheable_minimum():
    """call_llm_claude folds a prefix under ~8200 chars back into the dynamic
    tail — below that, Sonnet silently refuses to cache it."""
    prefix = sa.build_system_prompt("en").split("## LIVE DATA")[0]
    assert len(prefix) >= 8200


def test_prompt_names_the_requested_language_after_the_marker():
    tail = sa.build_system_prompt("es").split("## LIVE DATA")[1]
    assert "Spanish" in tail
    assert "Portuguese" in sa.build_system_prompt("pt").split("## LIVE DATA")[1]


def test_prompt_has_no_unfilled_placeholders():
    for lang in sa.SUPPORTED_LANGUAGES:
        assert "{language_name}" not in sa.build_system_prompt(lang)


def test_prompt_carries_both_mailboxes_and_the_price():
    p = sa.build_system_prompt("en")
    assert sa.CONTACT_EMAIL in p
    assert sa.CONTACT_EMAIL_BILLING in p
    assert "4.99" in p and "39.99" in p


# ─── rate_limit_ok ──────────────────────────────────────────────
def test_rate_limit_admits_then_blocks():
    key = "test-ip-rate-1"
    assert all(sa.rate_limit_ok(key, limit=3) for _ in range(3))
    assert sa.rate_limit_ok(key, limit=3) is False


def test_rate_limit_buckets_are_per_key():
    assert sa.rate_limit_ok("test-ip-rate-2", limit=1) is True
    assert sa.rate_limit_ok("test-ip-rate-2", limit=1) is False
    assert sa.rate_limit_ok("test-ip-rate-3", limit=1) is True


def test_rate_limit_window_expires():
    key = "test-ip-rate-4"
    assert sa.rate_limit_ok(key, limit=1, window_seconds=0.01) is True
    import time
    time.sleep(0.05)
    assert sa.rate_limit_ok(key, limit=1, window_seconds=0.01) is True


# ─── clean_history ──────────────────────────────────────────────
def test_history_drops_a_leading_assistant_turn():
    h = sa.clean_history([{"role": "assistant", "content": "hi"},
                          {"role": "user", "content": "q"},
                          {"role": "assistant", "content": "a"}])
    assert h[0]["role"] == "user"


def test_history_merges_consecutive_same_roles():
    """Claude requires alternating roles; a 400 here would lose a real answer."""
    h = sa.clean_history([{"role": "user", "content": "a"},
                          {"role": "user", "content": "b"},
                          {"role": "assistant", "content": "c"}])
    assert [m["role"] for m in h] == ["user", "assistant"]
    assert h[0]["content"] == "a\n\nb"


def test_history_drops_a_trailing_user_turn():
    """call_llm_claude appends the live question as the final user message."""
    h = sa.clean_history([{"role": "user", "content": "a"},
                          {"role": "assistant", "content": "b"},
                          {"role": "user", "content": "c"}])
    assert h[-1]["role"] == "assistant"


def test_history_truncates_and_tolerates_garbage():
    h = sa.clean_history([{"role": "user", "content": "x" * 5000},
                          "not a dict", {"role": "user"}, None,
                          {"role": "assistant", "content": "ok"}])
    assert [m["role"] for m in h] == ["user", "assistant"]
    assert len(h[0]["content"]) <= sa.MAX_QUESTION_CHARS


def test_history_of_a_lone_user_turn_is_empty():
    """The live question is appended by call_llm_claude, so a history that is
    just that question must not be sent twice."""
    assert sa.clean_history([{"role": "user", "content": "q"}]) == []


def test_history_handles_none_and_empty():
    assert sa.clean_history(None) == []
    assert sa.clean_history([]) == []
