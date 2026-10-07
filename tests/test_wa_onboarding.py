"""[wa-onboarding] chat-first onboarding state machine: parsers + step flow (no network)."""
from datetime import date

from antar_engine import wa_onboarding as wo


def test_parse_name():
    assert wo.parse_name("my name is raman singh") == "Raman Singh"
    assert wo.parse_name("Hi, I'm Priya") == "Priya"
    assert wo.parse_name("mera naam Amit hai") == "Amit"
    assert wo.parse_name("what is my future?") is None
    assert wo.parse_name("14 March") is None
    assert wo.parse_name("") is None


def test_parse_dob_formats_and_validation():
    assert wo.parse_dob("14 March 1990") == ("1990-03-14", False)
    assert wo.parse_dob("March 14th, 1990")[0] == "1990-03-14"
    assert wo.parse_dob("14 marzo 1990")[0] == "1990-03-14"
    assert wo.parse_dob("1990-03-14")[0] == "1990-03-14"
    assert wo.parse_dob("25/12/1985") == ("1985-12-25", False)
    assert wo.parse_dob("12/25/1985", "US")[0] == "1985-12-25"      # only one reading possible
    # ambiguous 04/05/1990: day-first outside the US, month-first inside — flagged either way
    assert wo.parse_dob("04/05/1990", "IN") == ("1990-05-04", True)
    assert wo.parse_dob("04/05/1990", "US") == ("1990-04-05", True)
    assert wo.parse_dob("31 February 1990")[0] is None
    assert wo.parse_dob("14 March 90")[0] is None                   # 2-digit year is never guessed
    assert wo.parse_dob(f"1 January {date.today().year + 1}")[0] is None
    assert wo.parse_dob("blah")[0] is None


def test_fmt_date_uses_month_word():
    assert wo.fmt_date("1990-03-04") == "4 March 1990"


def test_parse_tob():
    assert wo.parse_tob("6:40 am") == ("06:40", "exact")
    assert wo.parse_tob("6.40 PM") == ("18:40", "exact")
    assert wo.parse_tob("18:40") == ("18:40", "exact")
    assert wo.parse_tob("12:15 am") == ("00:15", "exact")
    assert wo.parse_tob("12 pm") == ("12:00", "exact")
    assert wo.parse_tob("around 6:30 am") == ("06:30", "approximate")
    assert wo.parse_tob("about noon") == ("12:00", "approximate")
    assert wo.parse_tob("don't know") == ("12:00", "unknown")
    assert wo.parse_tob("no sé") == ("12:00", "unknown")
    assert wo.parse_tob("pata nahi") == ("12:00", "unknown")
    assert wo.parse_tob("6") is None                                # bare number: ambiguous
    assert wo.parse_tob("25:99") is None
    assert wo.parse_tob("hello") is None


def test_yes_no_and_fix():
    assert wo.parse_yes_no("Yes!") == "yes"
    assert wo.parse_yes_no("sí") == "yes"
    assert wo.parse_yes_no("nahi") == "no"
    assert wo.parse_yes_no("maybe") is None
    assert wo.parse_yes_no("", "wob:yes") == "yes"
    assert wo.parse_fix("the time is wrong") == "tob"
    assert wo.parse_fix("fecha") == "dob"
    assert wo.parse_fix("", "wob:fix:pob") == "pob"
    assert wo.parse_fix("hmm") is None


def _run(st, *msgs):
    for m in msgs:
        r = wo.advance(st, m)
        st = r["state"]
    return r, st


def test_happy_path_to_confirm_and_build():
    st = wo.new_state("en", "IN")
    r, st = _run(st, "Raman")
    assert r["reply"] == "ask_dob" and st["name"] == "Raman"
    r, st = _run(st, "14 March 1990")
    assert r["reply"] == "ask_tob" and st["dob"] == "1990-03-14"
    r, st = _run(st, "6:40 am")
    assert r["reply"] == "ask_pob" and st["tob"] == "06:40"
    r = wo.advance(st, "Pune, India")
    assert r["action"] == "geocode_pob" and r["arg"] == "Pune, India"
    st = wo.set_place(r["state"], "pob", "Pune, India", 18.52, 73.86, "Asia/Kolkata", "UTC+5:30")
    assert st["step"] == "current"
    r = wo.advance(st, "skip")
    assert r["reply"] == "__confirm__" and r["state"]["step"] == "confirm"
    assert "14 March 1990" in wo.confirm_text(r["state"], "en")
    r2 = wo.advance(r["state"], "yes")
    assert r2["action"] == "build"
    f = wo.to_chart_fields(r2["state"])
    assert f["birth_date"] == "1990-03-14" and f["birth_time"] == "06:40:00"
    assert f["birth_lat"] == 18.52 and f["timezone_name"] == "Asia/Kolkata" and "current_city" not in f


def test_bad_input_stays_on_step():
    st = wo.new_state()
    r, st = _run(st, "what is my future?")
    assert r["reply"] == "bad_name" and st["step"] == "name"
    st = wo.new_state()
    st["step"] = "dob"
    r, st = _run(st, "sometime in spring")
    assert r["reply"] == "bad_dob" and st["step"] == "dob"


def test_confirm_no_then_fix_loops_back():
    st = {"step": "confirm", "lang": "en", "name": "A", "dob": "1990-03-14", "tob": "06:40",
          "pob": "Pune", "lat": 1.0, "lon": 2.0}
    r = wo.advance(st, "no")
    assert r["reply"] == "which_fix" and r["state"]["fixing"]
    r = wo.advance(r["state"], "time")
    assert r["state"]["step"] == "tob" and "fixing" not in r["state"]
    r = wo.advance(st, "no, the date is wrong")                    # fix named in the same message
    assert r["state"]["step"] == "dob"
    assert wo.advance(st, "banana")["reply"] == "yes_no"


def test_stale_and_every_key_has_all_languages():
    assert wo.is_stale(None) and wo.is_stale({"updated": 1})
    assert not wo.is_stale({"updated": wo.time.time()})
    for k, v in wo.T.items():
        assert set(v) == {"en", "es", "pt", "hinglish"}, k


class _SB:
    def __init__(self, fail=False):
        self.rows, self.fail = {}, fail

    def table(self, name):
        return self

    def select(self, *_):
        return self

    def eq(self, k, v):
        self.k, self.v = k, v
        return self

    def limit(self, n):
        return self

    def upsert(self, row, on_conflict=None):
        self.rows[row["number"]] = row
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("Could not find the table 'public.wa_onboarding' in the schema cache")
        return type("R", (), {"data": [self.rows[self.v]] if getattr(self, "v", None) in self.rows else []})()


def test_persistence_roundtrip_and_missing_table():
    sb = _SB()
    assert wo.save(sb, "+1555", {"step": "dob"})
    st, avail = wo.load(sb, "+1555")
    assert avail and st == {"step": "dob"}
    st, avail = wo.load(_SB(fail=True), "+1555")
    assert st is None and avail is False


# ── end to end through _wa_handle (hermetic: stubs mirror test_whatsapp_channel._Conv) ────────────

def _conv(monkeypatch, store, policy="ok", enabled=True):
    import main
    from tests.test_whatsapp_channel import _Conv
    from antar_engine import messaging as msg
    conv = _Conv(main, monkeypatch, link=None, policy=policy)
    if enabled:
        monkeypatch.setenv("WHATSAPP_ONBOARDING", "on")
    else:
        monkeypatch.delenv("WHATSAPP_ONBOARDING", raising=False)
    monkeypatch.setattr(wo, "load", lambda sb, n: (store.get(n), not store.get("__missing__")))
    monkeypatch.setattr(wo, "save", lambda sb, n, st, status="open", chart_id=None, user_id=None:
                        store.__setitem__(n, dict(st, status=status)) or True)
    created = {}

    async def fake_geo(place, lat_lon=None):
        if "nowhere" in (place or ""):
            return None
        return (place, 18.52, 73.86, "Asia/Kolkata")

    async def fake_create(req, uid, http_request=None):
        created["req"], created["uid"] = req, uid
        return type("R", (), {"chart_id": "chart-new"})()

    monkeypatch.setattr(main, "_wa_geocode", fake_geo)
    monkeypatch.setattr(main, "_wa_phone_user", lambda n: "user-new")
    monkeypatch.setattr(main, "_create_chart_for_user", fake_create)

    def link_direct(sb, cid, uid, number, consent=None):
        conv.link = {"id": "L1", "chart_id": cid, "user_id": uid, "context": {}}
        created["consent"] = consent
        return True
    monkeypatch.setattr(msg, "link_whatsapp_direct", link_direct)
    monkeypatch.setattr(main, "_wa_welcome", lambda lk, lang: ("Welcome *Raman*", ["Q1?", "Q2?", "Q3?"]))
    return conv, created


def test_stranger_walks_the_whole_flow(monkeypatch):
    store = {}
    conv, created = _conv(monkeypatch, store)
    for msg_ in ("hi", "Raman", "14 March 1990", "6:40 am", "Pune, India", "skip"):
        conv.run(msg_)
    assert any("call you" in t.lower() for t in conv.sent[:1])
    assert any("14 March 1990" in t for t in conv.sent)            # month as a word at the confirm
    assert "req" not in created                                    # nothing built before the yes
    conv.run("", choice_id="wob:yes")
    assert created["uid"] == "user-new" and created["req"].birth_date == "1990-03-14"
    assert created["req"].birth_time.startswith("06:40") and created["req"].full_name == "Raman"
    assert created["consent"]                                      # consent recorded at link time
    assert store["+919812345678"]["status"] == "done"
    assert any("Welcome" in t for t in conv.sent + [str(l) for l in conv.lists])


def test_off_or_no_consent_or_missing_table_keeps_old_behaviour(monkeypatch):
    for kw in ({"enabled": False}, {"policy": "needed"}, {"policy": "unknown"}):
        store = {}
        conv, created = _conv(monkeypatch, store, **kw)
        conv.run("Hi")
        assert "req" not in created and not store                  # no state, nothing created
    store = {"__missing__": True}
    conv, created = _conv(monkeypatch, store)
    conv.run("Hi")
    assert len(conv.sent) == 1 and "req" not in created             # falls back to the connect reply


def test_unknown_place_asks_again_and_hello_resumes(monkeypatch):
    store = {}
    conv, created = _conv(monkeypatch, store)
    for m_ in ("hi", "Raman", "14 March 1990", "6:40 am"):
        conv.run(m_)
    conv.sent.clear()
    conv.run("nowhere land")
    assert store["+919812345678"]["step"] == "pob" and len(conv.sent) == 1
    conv.sent.clear()
    conv.run("hello")                                              # a nudge mid-flow is not a place
    assert store["+919812345678"]["step"] == "pob" and len(conv.sent) == 2
    assert "req" not in created


def test_build_failure_keeps_state_for_retry(monkeypatch):
    import main
    store = {}
    conv, created = _conv(monkeypatch, store)
    for m_ in ("hi", "Raman", "14 March 1990", "6:40 am", "Pune, India", "skip"):
        conv.run(m_)

    async def boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(main, "_create_chart_for_user", boom)
    conv.run("yes")
    assert store["+919812345678"]["step"] == "confirm" and conv.link is None
    assert "Nothing is lost" in conv.sent[-1]
