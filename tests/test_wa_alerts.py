"""WhatsApp alert senders (owner 2026-10-03: return channel, calm alerts only)."""
import asyncio, time
from datetime import date
from antar_engine import wa_alerts as wal

T = date(2026, 10, 10)


def _a(i, t, start, **kw):
    return dict({"id": f"a{i}", "alert_type": t, "window_start": start}, **kw)


def test_only_calm_kinds_are_ever_picked():
    rows = [_a(1, "strain_window", "2026-10-11"), _a(2, "risk_window", "2026-10-11"),
            _a(3, "lean_stretch", "2026-10-11")]
    assert wal.pick(rows, [], T) is None
    assert wal.pick(rows + [_a(4, "wealth_window", "2026-10-12")], [], T)["id"] == "a4"


def test_lead_and_grace_window():
    assert wal.pick([_a(1, "wealth_window", "2026-10-17")], [], T)          # 7 days ahead
    assert not wal.pick([_a(1, "wealth_window", "2026-10-18")], [], T)      # too early
    assert wal.pick([_a(1, "dasha_turn", "2026-10-08")], [], T)             # 2 days late
    assert not wal.pick([_a(1, "dasha_turn", "2026-10-07")], [], T)


def test_once_and_once_a_week():
    rows = [_a(1, "wealth_window", "2026-10-12"), _a(2, "dasha_turn", "2026-10-14")]
    assert wal.pick(rows, [{"id": "a1", "at": "2026-10-01"}], T)["id"] == "a2"
    assert wal.pick(rows, [{"id": "zz", "at": "2026-10-05"}], T) is None     # sent 5 days ago


def test_render_window_and_chapter_in_languages():
    r = wal.render(_a(1, "wealth_window", "2026-10-14"), "es", "Leena")
    assert r["template"] == "antar_window_alert_v1"
    assert r["variables"] == {"1": "Leena", "2": "tu mejor ventana de dinero", "3": "14 oct"}
    assert "{{" not in r["text"] and "14 oct" in r["text"] and r["how_q"].startswith("¿Cómo")
    c = wal.render(_a(2, "dasha_turn", "2026-11-12"), "en", "Leena", "Saturn")
    assert c["variables"]["3"] == "building something lasting through steady work"
    assert "Nov 12" in c["text"]
    g = wal.render(_a(2, "dasha_turn", "2026-11-12"), "pt", "", None)
    assert g["variables"]["1"] == "de novo" and "fase" in g["variables"]["3"]


def test_lord_for_matches_the_start_date():
    rows = [{"lord": "Venus", "start": date(2026, 11, 12)}, {"lord": "Sun", "start": date(2046, 1, 1)}]
    assert wal.lord_for(_a(1, "dasha_turn", "2026-11-12"), rows) == "Venus"


def test_job_sends_template_outside_24h_and_remembers(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    from datetime import datetime, timezone
    from antar_engine import messaging as msg, wa_templates as wt
    link = {"id": "L1", "chart_id": "c1", "channel_user_id": "+14075550123", "alerts_opt_in": True,
            "context": {"last_in": time.time() - 3 * 86400, "lang": "en"}}
    alerts = [{"id": "x1", "alert_type": "wealth_window",
               "window_start": datetime.now(timezone.utc).date().isoformat()}]

    class Q:
        def __init__(self, n): self.n = n
        def select(self, *a): return self
        def eq(self, *a): return self
        def is_(self, *a): return self
        def in_(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            data = {"messaging_links": [link], "charts": [{"name": "Leena Kaur"}], "user_alerts": alerts}[self.n]
            return type("R", (), {"data": data})()
    monkeypatch.setattr(main.supabase, "table", lambda n: Q(n))
    async def nosync(cid): return None
    monkeypatch.setattr(main, "_sync_life_alerts", nosync)
    now_utc_h = datetime.now(timezone.utc).hour
    monkeypatch.setattr(main, "_wa_resolve_tz", lambda c, n, x=None: (((9 - now_utc_h) % 24) * 60, "t", ""))
    sent, saved = [], []
    monkeypatch.setattr(wt, "send", lambda num, name, lang, v: sent.append((name, v)) or True)
    monkeypatch.setattr(msg, "whatsapp_send", lambda *a: (_ for _ in ()).throw(AssertionError("free-form outside 24h")))
    monkeypatch.setattr(msg, "save_link_context", lambda sb, l, c: saved.append(c))
    asyncio.run(main._wa_alert_job())
    assert sent and sent[0][0] == "antar_window_alert_v1" and sent[0][1]["1"] == "Leena"
    assert saved and saved[0]["alerts_sent"][0]["id"] == "x1" and saved[0]["last_alert"]["q"]


def test_job_respects_opt_out_and_kill_switch(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    monkeypatch.setenv("WHATSAPP_ALERTS", "off")
    monkeypatch.setattr(main.supabase, "table", lambda n: (_ for _ in ()).throw(AssertionError("ran")))
    asyncio.run(main._wa_alert_job())
