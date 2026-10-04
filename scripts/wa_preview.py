"""WhatsApp UI preview — runs the REAL WhatsApp handler for the owner's linked number + chart, replays
a conversation, and records exactly what would be sent (inline TwiML text, REST text, or the tappable
list). NOTHING is delivered and nothing is saved: Twilio sends, link-context saves and Ask persistence
are stubbed. Output: Antar.world/wa_preview/<stamp>.md

    venv311/bin/python scripts/wa_preview.py --chart <chart_id> [--scenario NAME ...]
"""
import argparse, asyncio, datetime, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402
from antar_engine import messaging as msg  # noqa: E402

SCENARIOS = {
    "day": ["How is today for me", "@pick:1", "more", "@pick:2"],
    "ask": ["Should I take the funding offer this year?", "@pick:1"],
    "numbered": ["When is my next strong money window?", "1"],
    "yesno": ["yes or no: will the deal close this month?", "1", "17"],
    "detailed": ["yes or no: will the deal close this month?", "2"],
    "spec": ["Is today a good day to trade crypto?", "@pick:1"],
    "es": ["¿Cómo va mi dinero este mes?", "@pick:1"],
    "hinglish": ["Mera business kaisa chalega is saal?", "@pick:1"],
    "clarify": ["what should I do?"],
    "compare": ["Gold or defence — which should I focus on?"],
    "commands": ["help", "tips"],
    "greeting": ["hi"],
}


class Rec:
    def __init__(self):
        self.items = []

    def text(self, kind, t):
        self.items.append(("text", kind, t))

    def lst(self, kind, body, button, items):
        self.items.append(("list", kind, (body, button, items)))


async def run_turn(number, body, choice_id, ctxbox, rec):
    rec_start = len(rec.items)
    sink = main._WaSink(number, time.time(), inline=True)
    t0 = time.monotonic()
    task = asyncio.create_task(main._wa_handle(number, body, time.time(), 0, sink, "SMpreview", choice_id, None, None))
    await asyncio.wait({task}, timeout=main._WA_INLINE_DEADLINE_S)
    inline = sink.close()
    for t in inline:
        for p in msg.wa_split(t):
            rec.text("inline reply (TwiML)", p)
    await task
    return time.monotonic() - t0, rec.items[rec_start:]


async def main_async(chart, names):
    async def nop(*a, **k):
        return None
    main._ask_persist = nop
    main._nlu_shadow = nop
    main._ask_harvest_stated = lambda *a, **k: None
    import antar_engine.outcomes as oc
    oc.record_claim = lambda *a, **k: None
    rows = main.supabase.table("messaging_links").select("*").eq("channel", "whatsapp").eq("chart_id", chart) \
        .eq("status", "linked").limit(1).execute().data or []
    if not rows:
        print("no linked WhatsApp number for this chart"); return
    link = dict(rows[0])
    number = link["channel_user_id"]
    state = {"link": link}
    link["context"] = dict(msg.link_context(link), rest_ok_at=int(time.time()), last_in=int(time.time()))
    rec = Rec()
    msg.get_whatsapp_link = lambda sb, n: state["link"]
    def _save(sb, lk, ctx):
        state["link"] = dict(state["link"], context=json.loads(json.dumps(ctx, default=str)))
        return True
    msg.save_link_context = _save
    msg.whatsapp_send = lambda n, t, ts=None, *a, **k: (rec.text("REST text", t) or True)
    msg.whatsapp_send_list = lambda n, body, btn, items, ts=None, *a, **k: (rec.lst("REST list picker", body, btn, items) or True)
    main._time_sleep = None
    out = [f"# WhatsApp UI preview {datetime.datetime.utcnow():%Y-%m-%dT%H%M}", "",
           f"chart `{chart[:8]}` · number …{number[-4:]} · REST assumed working (rest_ok_at fresh)", ""]
    for name in names:
        out += [f"## Scenario: {name}", ""]
        state["link"]["context"] = dict(msg.link_context(state["link"]), rest_ok_at=int(time.time()), last_in=int(time.time()))
        last_list = None
        for step in SCENARIOS[name]:
            choice = ""
            body = step
            if step.startswith("@pick:"):
                idx = int(step.split(":")[1]) - 1
                if not last_list or idx >= len(last_list):
                    out += [f"**user** taps list item {idx + 1} — (no list was offered!)", ""]
                    continue
                title, cid, _d = last_list[idx]
                body, choice = title[:24], cid
                out += [f"**user** taps list item {idx + 1}: `{title}`", ""]
            else:
                out += [f"**user** sends: `{step}`", ""]
            secs, got = await run_turn(number, body, choice, state, rec)
            last_list = None
            if not got:
                out += ["_(nothing sent)_", ""]
            for kind_, how, payload in got:
                if kind_ == "text":
                    out += [f"**bot** · {how}", "```", payload, "```", ""]
                else:
                    b, btn, items = payload
                    last_list = items
                    out += [f"**bot** · {how} — button **[{btn}]**", "```", b, "```",
                            "list items: " + " · ".join(f"`{i[0]}`" for i in items), ""]
            out += [f"_{secs:.1f}s_", ""]
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Antar.world", "wa_preview")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{datetime.datetime.utcnow():%Y-%m-%dT%H%M}.md")
    open(p, "w").write("\n".join(out))
    print(p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", required=True)
    ap.add_argument("--scenario", action="append")
    a = ap.parse_args()
    asyncio.run(main_async(a.chart, a.scenario or list(SCENARIOS)))
