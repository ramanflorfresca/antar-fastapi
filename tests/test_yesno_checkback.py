"""Yes/No "did it happen?" reminder (2026-10-02).

Pure helpers from antar_engine/yesno_checkback.py, plus the hourly job lifted
out of main.py with ast and run against a fake Supabase / push sender.
"""
import ast
import asyncio
import pathlib
import sys
import types
from datetime import datetime, timedelta, timezone

from antar_engine import yesno_checkback as yc
from antar_engine.kp.kp_prashna import _parse_marker

NOW = datetime(2026, 11, 1, 13, 13, tzinfo=timezone.utc)   # 8:13 AM in New York (EST)
MARK = ("[YN;engine=kp;kp=conditional;kpv=conditional;kpc=2;nat=conditional;tajik=YES;"
        "qt=gain;num=74;method=kp_number;hz=30;win=2026-10-04..2026-10-08;"
        "moment=2026-10-02T16:54:40+00:00]")


# ── helpers ────────────────────────────────────────────────────────────────
def test_mark_keeps_calibration_marker_parseable_and_is_idempotent():
    k = yc.mark_notified(MARK, "push", "2026-11-01T13:13:00+00:00")
    assert yc.is_notified(k) and not yc.is_notified(MARK)
    m = _parse_marker(k)
    assert m["kp"] == "conditional" and m["tajik"] == "YES" and m["notified"].startswith("push@")
    assert yc.mark_notified(k, "email", "later") == k
    assert yc.is_notified(yc.mark_notified("", "email", "t"))


def test_message_is_localized_and_plain():
    t, b = yc.build_message("Will I get my funding in the next 30 days?",
                            "2026-10-02T16:54:44+00:00", "en")
    assert t == "Did it happen?"
    assert b == "On Oct 2 you asked: “Will I get my funding in the next 30 days?”. Tell us how it went."
    assert yc.build_message("¿Me darán el trabajo?", "2026-10-02T00:00:00Z", "es")[1].startswith("El 2 oct")
    assert yc.build_message("Vou conseguir?", "2026-10-02T00:00:00Z", "pt-BR")[0] == "Aconteceu?"
    assert yc.build_message("x", None, "fr")[1] == "You asked: “x”. Tell us how it went."


def test_long_question_clipped_on_a_word():
    q = "Will " + "really " * 30 + "happen?"
    body = yc.build_message(q, None, "en")[1]
    assert "…" in body and "reall…" not in body


def test_email_escapes_the_users_question():
    _, html = yc.email_html("<script>x</script> will it?", None, "en")
    assert "<script>" not in html and "&lt;script&gt;" in html and 'href="https://antar.world/ask"' in html


def _row(**kw):
    r = {"id": "r1", "chart_id": "c1", "concern": "yesno", "feedback_status": "pending",
         "trackable_claim": "Will I get my funding in the next 30 days?",
         "created_at": "2026-10-02T16:54:44+00:00",
         "show_after": (NOW - timedelta(hours=2)).isoformat(), "correlation_key": MARK}
    r.update(kw)
    return r


def test_is_due_rules():
    assert yc.is_due(_row(), NOW)
    assert not yc.is_due(_row(feedback_status="yes"), NOW)
    assert not yc.is_due(_row(concern="career"), NOW)
    assert not yc.is_due(_row(show_after=(NOW + timedelta(hours=1)).isoformat()), NOW)
    assert not yc.is_due(_row(show_after=(NOW - timedelta(days=31)).isoformat()), NOW)
    assert not yc.is_due(_row(correlation_key=yc.mark_notified(MARK, "push", "t")), NOW)


def test_local_morning():
    assert yc.is_local_morning(NOW, -5)          # New York, 8 AM
    assert not yc.is_local_morning(NOW, 5.5)     # India, 6:43 PM
    assert yc.is_local_morning(datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc), 5.5)


# ── the hourly job, lifted from main.py ────────────────────────────────────
class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.payload = db, table, [], None

    def select(self, *_):
        return self

    def eq(self, c, v):
        self.filters.append(("eq", c, v)); return self

    def lte(self, *_):
        return self

    def gte(self, *_):
        return self

    def limit(self, *_):
        return self

    def in_(self, c, vals):
        self.filters.append(("in", c, vals)); return self

    def update(self, payload):
        self.payload = payload; return self

    def execute(self):
        rows = self.db[self.table]
        for kind, c, v in self.filters:
            rows = [r for r in rows if (r.get(c) in v if kind == "in" else r.get(c) == v)]
        if self.payload is not None:
            for r in rows:
                r.update(self.payload)
        return _Res([dict(r) for r in rows])


class _SB:
    def __init__(self, db, emails):
        self.db = db
        self.auth = types.SimpleNamespace(admin=types.SimpleNamespace(
            get_user_by_id=lambda uid: types.SimpleNamespace(
                user=types.SimpleNamespace(email=emails.get(uid)))))

    def table(self, name):
        return _Q(self.db, name)


def _load_job(sb, configured=True, sent=1):
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    node = next(n for n in ast.parse(src).body
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "_yesno_checkback_job")
    pushes, emails = [], []

    async def send_to_tokens(_sb, toks, title, body, data=None):
        pushes.append({"toks": toks, "title": title, "body": body, "data": data})
        return {"sent": sent, "failed": 0, "pruned": 0}

    fake_push = types.ModuleType("antar_engine.push_sender")
    fake_push.is_configured = lambda: configured
    fake_push.send_to_tokens = send_to_tokens

    async def send_email(to, subject, html):
        emails.append({"to": to, "subject": subject}); return True

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    ns = {"supabase": sb, "send_email": send_email, "os": __import__("os"),
          "datetime": _DT, "timedelta": timedelta, "timezone": timezone,
          "_COUNTRY_TZ_OFFSETS": {"US": -5, "IN": 5.5, "DEFAULT": 0}}
    exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
    return ns["_yesno_checkback_job"], fake_push, pushes, emails


def _run(job, fake_push, monkeypatch):
    import antar_engine
    monkeypatch.setitem(sys.modules, "antar_engine.push_sender", fake_push)
    monkeypatch.setattr(antar_engine, "push_sender", fake_push, raising=False)
    asyncio.run(job())


def _db(rows, tokens=()):
    return {
        "user_correlations": rows,
        "charts": [{"id": "c1", "user_id": "u1", "current_country": "US", "language_preference": "en"},
                   {"id": "c2", "user_id": "u2", "current_country": "IN", "language_preference": "es"},
                   {"id": "c3", "user_id": "u3", "current_country": "US", "language_preference": "pt"}],
        "device_tokens": list(tokens),
    }


def test_job_pushes_once_at_local_morning_and_stamps(monkeypatch):
    monkeypatch.delenv("YESNO_CHECKBACK_EMAIL", raising=False)
    db = _db([_row(), _row(id="r2", chart_id="c2")],
             [{"token": "t1", "chart_id": "c1", "platform": "android"},
              {"token": "t2", "chart_id": "c2", "platform": "android"}])
    job, push, pushes, emails = _load_job(_SB(db, {}))
    _run(job, push, monkeypatch)
    assert len(pushes) == 1                                  # India isn't at 8 AM
    p = pushes[0]
    assert p["title"] == "Did it happen?" and "Oct 2" in p["body"]
    assert p["data"] == {"type": "yesno_checkback", "route": "/ask", "correlation_id": "r1"}
    stamped = {r["id"]: r["correlation_key"] for r in db["user_correlations"]}
    assert yc.is_notified(stamped["r1"]) and not yc.is_notified(stamped["r2"])
    assert _parse_marker(stamped["r1"])["kp"] == "conditional"   # calibration intact
    _run(job, push, monkeypatch)                             # next hour: no repeat
    assert len(pushes) == 1 and emails == []


def test_job_email_fallback_only_when_enabled(monkeypatch):
    db = _db([_row(chart_id="c3")])                          # no device token
    job, push, pushes, emails = _load_job(_SB(db, {"u3": "pat@example.com"}))
    monkeypatch.delenv("YESNO_CHECKBACK_EMAIL", raising=False)
    _run(job, push, monkeypatch)
    assert pushes == [] and emails == []
    assert not yc.is_notified(db["user_correlations"][0]["correlation_key"])   # still due
    monkeypatch.setenv("YESNO_CHECKBACK_EMAIL", "on")
    _run(job, push, monkeypatch)
    assert emails == [{"to": "pat@example.com", "subject": "Antar — Aconteceu?"}]
    assert "notified=email@" in db["user_correlations"][0]["correlation_key"]


def test_failed_push_is_not_stamped(monkeypatch):
    monkeypatch.delenv("YESNO_CHECKBACK_EMAIL", raising=False)
    db = _db([_row()], [{"token": "t1", "chart_id": "c1", "platform": "android"}])
    job, push, pushes, _ = _load_job(_SB(db, {}), sent=0)
    _run(job, push, monkeypatch)
    assert len(pushes) == 1
    assert not yc.is_notified(db["user_correlations"][0]["correlation_key"])   # retried later
