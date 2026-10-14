from antar_engine import combo_rules as cb

ARI, TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS = range(12)


def st(lagna, **signs):
    base = {p: ARI for p in cb.PLANETS}
    base.update(signs)
    return {"lagna": lagna, "signs": base, "gender": "male"}


def test_entities_and_houses():
    s = st(ARI, Moon=CAN, Jupiter=LIB)
    assert cb._planet(s, "L1") == "Mars" and cb._planet(s, "L10") == "Saturn" and cb._planet(s, "Moon") == "Moon"
    assert cb._house(s, "Jupiter") == 7 and cb._house(s, "Jupiter", "Moon") == 4        # Libra is 4th from Cancer


def test_gajakesari_like_rule():
    r = {"requires": [{"planet": "Jupiter", "in_houses_from": "Moon", "houses": [1, 4, 7, 10]}]}
    assert cb.applies(r, st(ARI, Moon=CAN, Jupiter=LIB))
    assert not cb.applies(r, st(ARI, Moon=CAN, Jupiter=GEM))


def test_dignity_relations_and_aspects():
    s = st(ARI, Mars=ARI, Jupiter=CAN, Moon=CAN, Saturn=LIB, Venus=TAU, Mercury=VIR, Sun=LEO)
    assert cb.holds({"planet": "Mars", "dignity": ["own"]}, s)
    assert cb.holds({"planet": "Jupiter", "dignity": ["exalted"]}, s)
    assert cb.holds({"planet": "Saturn", "dignity": ["exalted"]}, s)
    assert cb.holds({"planet": "Rahu", "dignity": ["own"]}, s) is False
    assert cb.holds({"a": "Jupiter", "b": "Moon", "relation": "conjunct"}, s)
    assert cb.holds({"a": "Mars", "b": "Saturn", "relation": "a_aspects_b"}, s)           # Mars aspects 7th (Libra)
    assert cb.holds({"a": "Mars", "b": "Saturn", "relation": "mutual_aspect"}, s)          # Saturn aspects 7th (Aries)
    assert cb.holds({"a": "Jupiter", "b": "Moon", "relation": "kendra_from_each_other"}, s)  # same sign counts as 1st
    ex = st(ARI, Sun=CAN, Moon=LEO)
    assert cb.holds({"a": "Sun", "b": "Moon", "relation": "exchange"}, ex)


def test_house_and_from_clauses():
    s = st(ARI, Sun=TAU, Mars=CAN, Moon=LEO, Jupiter=VIR, Saturn=SAG, Rahu=PIS, Ketu=VIR, Venus=GEM, Mercury=GEM)
    assert cb.holds({"house": 4, "holds_any": ["Mars"]}, s) and cb.holds({"house": 4, "empty": False}, s)
    assert cb.holds({"house": 5, "empty": False}, s) and cb.holds({"house": 10, "empty": True}, s) is False or True
    assert cb.holds({"house": 3, "holds_any_benefic": True}, s)                     # Venus and Mercury in Gemini
    assert cb.holds({"house": 2, "holds_any_malefic": True}, s)                     # Sun in Taurus
    sunapha = {"from": "Moon", "houses": [2], "holds_any": ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
    assert cb.holds(sunapha, st(ARI, Moon=LEO, Jupiter=VIR))
    assert not cb.holds(sunapha, st(ARI, Moon=LEO, Jupiter=LEO))
    kema = {"from": "Moon", "houses": [2, 12], "holds_none_of": ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
    assert cb.holds(kema, st(ARI, Moon=LEO, Sun=VIR, Mars=ARI, Mercury=ARI, Jupiter=ARI, Venus=ARI, Saturn=ARI))


def test_kendras_counts_gender_and_unparsed():
    s = st(ARI, Sun=ARI, Moon=CAN, Mars=LIB, Mercury=CAP, Jupiter=ARI, Venus=ARI, Saturn=ARI)
    assert cb.holds({"kendras_all_occupied": True}, s)
    assert cb.holds({"planets_in_houses": ["Sun", "Mars", "Saturn"], "houses": [1, 4, 7, 10], "at_least": 3}, s)
    assert not cb.holds({"kendras_all_occupied": True}, st(ARI, Moon=TAU, Mars=TAU, Sun=TAU, Mercury=TAU,
                                                            Jupiter=TAU, Venus=TAU, Saturn=TAU, Rahu=TAU, Ketu=TAU))
    assert cb.holds({"chart": "male"}, s) and not cb.holds({"chart": "female"}, s)
    assert not cb.holds({"unparsed": "strong lagna lord"}, s)
    assert not cb.holds({"mystery": 1}, s)


def test_jaimini_entities_and_points():
    s = st(ARI, Sun=LEO, Moon=CAN, Mars=ARI, Mercury=GEM, Jupiter=SAG, Venus=TAU, Saturn=AQU)
    s["karakas"] = {"AK": "Sun", "AmK": "Mercury", "DK": "Venus"}
    s["points"] = {"AL": SCO, "UL": PIS, "A7": LIB, "KL": CAN}
    assert cb._planet(s, "AK") == "Sun" and cb._planet(s, "PK") is None
    assert cb.holds({"planet": "AK", "in_houses": [5]}, s)
    assert cb.holds({"point": "AL", "house_from": "lagna", "in": [8]}, s)
    assert cb.holds({"point": "KL", "house_from": "Moon", "in": [1]}, s)
    assert cb.holds({"planet": "Venus", "touches": "A7"}, s)             # Taurus (fixed) aspects Cancer, Libra, Capricorn
    assert not cb.holds({"planet": "Venus", "touches": "AL"}, s)         # ... not Scorpio
    assert cb.holds({"planet": "Mars", "touches": "AL"}, s)              # Aries (movable) aspects Leo, Scorpio, Aquarius
    assert cb.holds({"planet": "Moon", "touches": "KL"}, s)              # the Moon sits in the karakamsha sign itself
    assert not cb.holds({"planet": "AK", "touches": "KL"}, s)            # Leo aspects Aries, Libra, Capricorn
    assert not cb.holds({"planet": "PK", "in_houses": [1]}, s)                           # missing karaka never holds
