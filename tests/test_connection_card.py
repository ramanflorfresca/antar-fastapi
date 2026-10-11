"""[connection-card 2026-10-11] facts -> LLM phrasing -> validation -> store. The LLM only phrases; the engines decide."""
import asyncio
import copy
import json

from antar_engine import connection_card as CC

OUT = {
    "name_b": "saransh", "compat_type": "cofounder", "compat_type_label": "Cofounder", "badge": "MIXED", "score": 51,
    "headline": "A strong founder fit with clear gaps.", "summary": "S.",
    "catalysts": ["Little destructive friction sits between you and saransh."],
    "watch_points": ["You compete for the same spotlight.", "You handle conflict differently.", "Under pressure you clash."],
    "moves": [{"text": "Put decisions in writing."}, {"text": "Agree how you check in."}, {"text": "Decide who speaks for the work."}],
    "layers": [{"layer_key": "friction", "layer_label": "Friction & Growth", "score": 79, "headline": "h", "detail": "Little hidden friction."},
               {"layer_key": "soul", "layer_label": "Soul Alignment", "score": 57, "headline": "h", "detail": "Shared ground."}],
    "timing": {"line": "Your timelines line up around 2026-2031."},
    "roles": {"you": {"leads": ["tech", "finance"]}, "other": {"leads": ["creative"]}, "shared": ["sales"], "contested": ["vision"], "gaps": ["ops"],
              "capacity": {"you": {"level": "conditional"}, "other": {"level": "solo"}, "solo": True}},
}


def _good(facts):
    leads = [{"lane": l, "who": w, "line": "ok"} for l, w in
             (("tech", "you"), ("finance", "you"), ("creative", "other"), ("sales", "shared"), ("vision", "open"), ("ops", "open"))]
    return {"headline": "You build; saransh owns a lane outright.",
            "strengths": [{"title": "Low friction", "text": "You rarely wear each other down."}] * 3,
            "frictions": [{"issue": "You both want the stage.", "do": "Split who speaks for what."}] * 3,
            "leads": leads, "style": {"you": "You move fast.", "other": "They work best owning a lane."},
            "dos": ["Write it down.", "Check in weekly.", "Name an owner."], "donts": ["Don't assume.", "Don't wait.", "Don't overlap."],
            "now": "Your timelines line up through 2031."}


def test_facts_carry_the_engine_answers_and_the_solo_flag():
    f = CC.build_facts(OUT, "en")
    assert f["other"] == "saransh" and f["roles"]["you_lead"] == ["tech", "finance"] and f["roles"]["open_contested"] == ["vision"]
    assert f["roles"]["pair_has_a_solo_builder"] is True and f["roles"]["systems_agree"] is False and f["moves"][0] == "Put decisions in writing."
    assert CC.facts_hash(f) == CC.facts_hash(copy.deepcopy(f)) and CC.facts_hash(f) != CC.facts_hash({**f, "score": 52})


def test_fallback_card_is_complete_and_uses_only_engine_text():
    c = CC.fallback_card(CC.build_facts(OUT, "en"))
    assert c["headline"] == OUT["headline"] and len(c["frictions"]) == 3 and c["frictions"][0]["do"] == "Put decisions in writing."
    assert {l["lane"]: l["who"] for l in c["leads"]} == {"tech": "you", "finance": "you", "creative": "other", "sales": "shared", "vision": "open", "ops": "open"}
    assert CC.fallback_card({}) is not None


def test_a_good_card_validates():
    f = CC.build_facts(OUT, "en")
    ok, why = CC.validate(_good(f), f)
    assert ok, why


def test_chart_words_are_rejected_in_both_languages():
    f = CC.build_facts(OUT, "en")
    for bad in ("Saturn rules your 7th house.", "Your dasha period helps.", "Rahu pushes you.", "Tu casa 7 es fuerte.", "Marte te empuja."):
        c = _good(f)
        c["strengths"][0] = {"title": "x", "text": bad}
        ok, why = CC.validate(c, f)
        assert not ok and any(w.startswith("jargon") for w in why), bad


def test_a_gendered_pronoun_for_the_other_person_is_rejected():
    f = CC.build_facts(OUT, "en")
    for bad in ("He works best owning a lane.", "Give her a clear scope.", "That is his lane.", "\u00c9l trabaja mejor solo."):
        c = _good(f)
        c["style"]["other"] = bad
        ok, why = CC.validate(c, f)
        assert not ok and any(w.startswith("pronoun") for w in why), bad
    c = _good(f)
    c["style"]["other"] = "saransh works best owning a lane."
    assert CC.validate(c, f)[0]
    c["style"]["other"] = "Pasa el tiempo en el trabajo de la empresa y el dinero."          # the article "el" is not a pronoun
    assert CC.validate(c, f)[0]
    assert "never he, him, his, she or her" in CC.build_prompt(f)[0] and "nunca uses" in CC.build_prompt(CC.build_facts(OUT, "es"))[0]


def test_a_lead_that_contradicts_the_engine_or_assigns_an_open_lane_is_rejected():
    f = CC.build_facts(OUT, "en")
    c = _good(f)
    c["leads"][0]["who"] = "other"                                   # tech is YOURS
    assert not CC.validate(c, f)[0]
    c = _good(f)
    c["leads"][4]["who"] = "you"                                     # vision is open (contested)
    assert not CC.validate(c, f)[0]
    c = _good(f)
    c["leads"] = c["leads"][:-1]                                     # a lane missing
    assert "leads incomplete" in CC.validate(c, f)[1]
    f2 = CC.build_facts({**OUT, "roles": None}, "en")
    assert not CC.validate(_good(f), f2)[0]                           # leads without roles


def test_counts_and_shape_are_enforced():
    f = CC.build_facts(OUT, "en")
    for key, val in (("strengths", [{"text": "a"}]), ("frictions", [{"issue": "a", "do": ""}] * 3), ("dos", ["a"]), ("headline", "")):
        c = _good(f)
        c[key] = val
        assert not CC.validate(c, f)[0], key
    assert CC.validate("nope", f) == (False, ["not an object"])


def test_parse_json_handles_fences_and_noise():
    assert CC.parse_json('```json\n{"a": 1}\n```') == {"a": 1} and CC.parse_json('Here: {"a": 2} thanks') == {"a": 2} and CC.parse_json("no json") is None


def test_generate_accepts_a_good_answer_and_marks_it_llm():
    f = CC.build_facts(OUT, "en")

    async def llm(prompt, system):
        return json.dumps(_good(f))
    card, why = asyncio.run(CC.generate(f, llm))
    assert why == [] and card["source"] == "llm" and card["version"] == CC.CARD_VERSION


def test_generate_retries_once_with_the_rejection_reason_then_gives_up():
    f = CC.build_facts(OUT, "en")
    seen = []

    async def bad_then_good(prompt, system):
        seen.append(prompt)
        bad = _good(f)
        bad["headline"] = "Your Saturn dasha helps."
        return json.dumps(bad if len(seen) == 1 else _good(f))
    card, _ = asyncio.run(CC.generate(f, bad_then_good))
    assert card and len(seen) == 2 and "jargon" in seen[1]

    async def always_bad(prompt, system):
        return "not json"
    card, why = asyncio.run(CC.generate(f, always_bad))
    assert card is None and why

    async def boom(prompt, system):
        raise RuntimeError("x")
    assert asyncio.run(CC.generate(f, boom))[0] is None


def test_prompt_forbids_chart_words_and_carries_the_lane_names():
    system, user = CC.build_prompt(CC.build_facts(OUT, "en"))
    assert "no astrology or chart words" in system and "built to" in system and "technology & product" in user
    assert "sin astrolog" not in system and "nada de astrología" in CC.build_prompt(CC.build_facts(OUT, "es"))[0]


class _Q:
    def __init__(self, rows, log):
        self.data, self.log = rows, log

    def __getattr__(self, name):
        return lambda *a, **k: (self.log.append((name, k)) or self)

    def execute(self):
        return self


class _SB:
    def __init__(self, rows=None):
        self.rows, self.log = rows or [], []

    def table(self, name):
        return _Q(self.rows, self.log)


def test_storage_is_keyed_by_facts_and_fail_open():
    CC._MEM.clear()
    card = {"headline": "h", "source": "llm"}
    sb = _SB([{"card": card, "facts_hash": "abc"}])
    assert CC.cached(sb, "s1", "en", "abc") == card            # DB hit with the same facts
    CC._MEM.clear()
    assert CC.cached(sb, "s1", "en", "zzz") is None            # the facts changed -> stale -> regenerate
    CC.store(sb, "s1", "en", "zzz", card, "m")
    assert CC.cached(_SB([]), "s1", "en", "zzz") == card       # in-process copy survives a missing table

    class _Boom:
        def table(self, n):
            raise RuntimeError("no table")
    CC._MEM.clear()
    assert CC.cached(_Boom(), "s2", "en", "a") is None
    CC.store(_Boom(), "s2", "en", "a", card)                    # never raises
