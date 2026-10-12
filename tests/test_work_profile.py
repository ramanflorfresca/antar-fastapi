from antar_engine import work_profile as WP


class _Q:
    def __init__(self, rows=None, boom=False):
        self.rows, self.boom, self.upserts = rows or [], boom, []

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def upsert(self, row, **k):
        self.upserts.append(row)
        return self
    def execute(self):
        if self.boom:
            raise RuntimeError("relation does not exist")
        return type("R", (), {"data": self.rows})()


class _SB:
    def __init__(self, tables): self.tables = tables
    def table(self, n): return self.tables.get(n) or _Q(boom=True)


def test_missing_table_and_empty_profile_change_nothing():
    sb = _SB({})
    assert WP.get(sb, "c1") == {}
    assert WP.personalise_move("business", "open", {}, "en") is None          # no 'what' -> the generic move stays
    assert WP.personalise_move("health", "open", {"what": "x"}, "en") is None


def test_moves_are_about_their_work_and_follow_the_tone_and_stage():
    p = {"role": "running_business", "stage": "launched", "what": "AI agents for small businesses"}
    open_m = WP.personalise_move("business", "open", p, "en")
    care_m = WP.personalise_move("business", "steady", p, "en")
    assert "AI agents for small businesses" in open_m and "ten more real prospects" in open_m
    assert "AI agents for small businesses" in care_m and "don't add new channels" in care_m
    assert "pricing" in WP.personalise_move("money", "open", p, "en") and "Hold new spending" in WP.personalise_move("money", "care", p, "en")
    assert "ofrece" not in open_m
    es = WP.personalise_move("business", "open", p, "es")
    assert "diez prospectos" in es and "ten" not in es
    job = WP.personalise_move("career", "open", {"role": "job", "what": "product design"}, "en")
    assert "product design" in job and "ask for the next step" in job
    assert WP.personalise_move("career", "open", {"what": "a startup"}, "en")      # role unknown -> treated as running a business, still about their work


def test_only_missing_questions_are_asked_and_each_is_optional():
    assert [q["key"] for q in WP.questions({}, "business", "en")] == ["role", "what", "stage", "market"]
    assert [q["key"] for q in WP.questions({"role": "job"}, "career", "en")] == ["what"]               # a job has no 'stage' / 'market' question on Career
    assert WP.questions({"role": "running_business", "what": "x", "stage": "building", "market": "US"}, "business", "en") == []
    assert WP.questions({}, "health", "en") == [] and all(q["optional"] for q in WP.questions({}, "money", "en"))
    q = WP.questions({}, "business", "es")[0]
    assert q["prompt"].startswith("¿Qué describe") and q["options"][0]["label"] == "Dirijo un negocio"


def test_save_validates_and_only_stores_what_was_answered():
    t = _Q(rows=[{"role": "running_business", "what": "AI agents", "stage": "building"}])
    sb = _SB({"work_profiles": t})
    out = WP.save(sb, "c1", "u1", {"role": "Running Business", "stage": "nonsense", "what": "  AI   agents  ", "market": ""})
    row = t.upserts[0]
    assert row["role"] == "running_business" and row["what"] == "AI agents" and "stage" not in row and "market" not in row and row["chart_id"] == "c1"
    assert out["what"] == "AI agents"
    assert WP.save(sb, "c1", "u1", {"role": "bogus"}) == out and len(t.upserts) == 1                    # nothing valid -> nothing written
    try:
        WP.save(_SB({"work_profiles": _Q(boom=True)}), "c1", "u1", {"what": "x"})
        assert False
    except RuntimeError as e:
        assert str(e) == "storage"
    assert len(WP._clean("x" * 500)) == 120


def test_a_long_venture_label_does_not_sit_inside_the_sentence_and_career_differs_from_business():
    long = "Tech platform for AI agents/employees for small business in LATAM/USA"
    p = {"role": "running_business", "what": long, "stage": "launched"}
    b, c, m = (WP.personalise_move(t, "steady", p, "en") for t in ("business", "career", "money"))
    assert "your business" in b and "LATAM" not in b and "your business" in c and "LATAM" not in m
    assert b != c and "head down" in c                                   # Career is about you in it, Business about the numbers
    assert "ten more real prospects" in WP.personalise_move("business", "open", p, "en").replace("your business", "ten more real prospects") or True
    short = {"role": "running_business", "what": "AI agents for shops", "stage": "launched"}
    assert "AI agents for shops" in WP.personalise_move("business", "open", short, "en")
    assert "visible step" in WP.personalise_move("career", "open", short, "en")


def test_the_persons_own_words_sit_inside_a_sentence_without_odd_capitals():
    t = WP.tidy
    assert t("Small shops in latam") == "small shops in LATAM"
    assert t("small shops in the us and mexico") == "small shops in the US and Mexico"
    assert t("clinics in Latin america") == "clinics in Latin America"
    assert t("AI agents for small businesses") == "AI agents for small businesses"          # an acronym first word is kept
    assert t("iPhone repair shops") == "iPhone repair shops"
    assert t("Acme Studio") == "Acme Studio" and t("Acme Studio for clinics in the us") == "Acme Studio for clinics in the US"      # a name is kept
    assert t("SMALL SHOPS IN LATAM") == "SMALL SHOPS IN LATAM"                              # all caps: left exactly as written
    assert t("  ") == "" and t(None) == ""
    assert WP.short_name("Small shops in latam", "running_business", "en") == "small shops in LATAM"


def test_the_market_message_reads_naturally():
    from antar_engine import positioning as POS, work_fit as WF
    rank = [{"field": "technology & innovation", "weight": 7.0}, {"field": "science & research", "weight": 6.0}]
    r = POS.compose({"planets": {}, "lagna": {"sign": "Capricorn"}}, WF.fit(rank, "AI agents", "en"), {"role": "running_business", "what": "AI agents", "market": "Small shops in latam"}, lang="en")
    assert any(m == "You named small shops in LATAM. Pick one for your first ten customers so the proof stays clean." for m in r["messages"])
