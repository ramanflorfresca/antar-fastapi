"""Conversation audit — run scripted multi-turn Ask conversations on the test charts,
tap every suggested follow-up, repeat each conversation, and report failures grouped
by CLASS so they are fixed as classes, not one screenshot at a time.

[conversation-audit 2026-10-04] Owner: "we are going in circles instead of tackling it
systematically". scripts/answer_audit.py grades single questions on one chart; every
bug found by hand that day lived in what it never exercised: multi-turn threads, the
same question twice, tapped suggestions, the timing chip vs the read, missing moves,
other charts and languages. NOTHING is sent or saved (persist, claims, profile harvest
and the shadow log are stubbed). Writes Antar.world/answer_audit/conv_<stamp>.md + .json.

    venv311/bin/python scripts/conversation_audit.py [--repeats 2] [--persona Raman] [--no-judge]
"""
import argparse, asyncio, contextvars, datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402
from antar_engine.narration_validator import validate_narration  # noqa: E402
from antar_engine.daily_prediction_engine import _looks_broken  # noqa: E402
from antar_engine.readability import _CHILDISH_RX  # noqa: E402
from antar_engine.wealth_magnitude import wealth_profile  # noqa: E402

# ── personas (real charts; see memory test-personas) ──
PERSONAS = [
    {"name": "Raman", "chart": "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed", "tz": -240, "lang": "en",
     "one": "Antar", "two": "Tezops AI and Antar"},
    {"name": "Andres", "chart": "6ec6311c-d46e-4e97-a46c-859882071971", "tz": -300, "lang": "en",
     "one": "my advisory work", "two": "my advisory work and the real estate deal"},
    {"name": "Harleen", "chart": "e3a3dac7-cb91-468c-b9fe-51ff74ef1217", "tz": -240, "lang": "en",
     "one": "my bookkeeping work", "two": "my bookkeeping work and a side consulting business"},
    {"name": "Shashi", "chart": "9dff84f7-6171-4372-bdb6-1f266696816d", "tz": 330, "lang": "en",
     "one": "my business", "two": "my business and a property investment"},
    {"name": "Shashi-hi", "chart": "9dff84f7-6171-4372-bdb6-1f266696816d", "tz": 330, "lang": "hinglish",
     "one": "apne business", "two": "business aur property"},
    {"name": "Jaime", "chart": "216fd897-7d8a-4762-a945-25424bb7539a", "tz": -300, "lang": "es",
     "one": "mi negocio", "two": "mi negocio y en una finca"},
]

CHAINS = {
    "en": {
        "money": ["How is my money looking right now?", "When does my strongest money window open?",
                  "Should I concentrate or diversify?", "Which profession fits me best?"],
        "allin_one": ["Should I concentrate or diversify?", "I am 100% all in on {one}"],
        "allin_two": ["Should I concentrate or diversify?", "I am 100% all in on {two}"],
        "partner": ["Should I build alone or bring in a partner?"],
    },
    "es": {
        "money": ["¿Cómo está mi dinero ahora mismo?", "¿Cuándo se abre mi mejor ventana de dinero?",
                  "¿Debo concentrarme o diversificar?", "¿Qué profesión encaja mejor conmigo?"],
        "allin_one": ["¿Debo concentrarme o diversificar?", "Estoy 100% metido en {one}"],
        "allin_two": ["¿Debo concentrarme o diversificar?", "Estoy 100% metido en {two}"],
        "partner": ["¿Debo emprender solo o con un socio?"],
    },
    "hinglish": {
        "money": ["Abhi mera paisa kaisa dikh raha hai?", "Mera sabse strong money window kab khulega?",
                  "Kya ek jagah focus karun ya diversify karun?", "Kaun sa profession mere liye sabse sahi hai?"],
        "allin_one": ["Kya ek jagah focus karun ya diversify karun?", "Maine sab kuch {one} mein laga diya hai"],
        "allin_two": ["Kya ek jagah focus karun ya diversify karun?", "Maine sab kuch {two} mein laga diya hai"],
        "partner": ["Akele build karun ya partner ke saath?"],
    },
}

# ── checks (each tagged with a CLASS) ──
_MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|dic|fev|mai|set|out|dez)\w*"
_FUND = re.compile(r"(?i)\b(fund(ing|raise)?|raise (capital|money|funds)|investors?|backers?|"
                   r"financiaci[oó]n|financiamiento|financiamento|captar|inversionistas?)\b")
_PARTNER_WORDS = re.compile(r"(?i)\b(your (partner|spouse|wife|husband)|tu pareja|tu (esposa|esposo)|"
                            r"seu parceiro|sua parceira|apne (partner|pati|patni))\b")
_UNPARTNERED = {"single", "divorced", "separated", "widowed", "never_married", "unmarried"}
_EN_LEAK = re.compile(r"(?i)\b(venture|ventures|savings|cushion|cash flow|the reading|your move)\b")
_SPREAD = re.compile(r"(?i)\b(spread|diversif\w*|repart\w*|alag alag|second (income|line|stream)|"
                     r"segunda fuente|ya es diversificaci)")
_CONC = re.compile(r"(?i)\b(concentrate( everything| on one)?|concentra(r|te)? (todo|en un)|go deep on one|"
                   r"pick (the )?one (venture|deal|business)|focus on one (venture|deal|business)|"
                   r"double down on one|el[ií]ge un (solo )?(negocio|emprendimiento)|ek hi (venture|jagah))")
_PARTNER_YES = re.compile(r"(?i)(backs (bringing in )?the right partner|respalda (sumar )?al socio|"
                          r"apoia (trazer )?o s[oó]cio|sahi partner)")
_PARTNER_NO = re.compile(r"(?i)(keep it yours|lo mantengas tuyo|manter isso seu|apne paas rakho|"
                         r"stay solo|go alone|autonom)")
_SENT = re.compile(r"(?<=[.!?])\s+")


_NEG = re.compile(r"(?i)\b(not|no|never|don'?t|instead of|rather than|nahi|sin|sem|n[aã]o)\b[^.!?]{0,25}$")


def _hits(rx, text: str) -> bool:
    """A lean phrase counts only when it isn't negated ('not through spreading')."""
    for m in rx.finditer(text or ""):
        if not _NEG.search((text or "")[max(0, m.start() - 40):m.start()]):
            return True
    return False


def _lean_of(text: str) -> str:
    t = text or ""
    for tag, rx in (("partner_yes", _PARTNER_YES), ("partner_no", _PARTNER_NO),
                    ("spread", _SPREAD), ("concentrate", _CONC)):
        if _hits(rx, t):
            return tag
    return ""


def turn_checks(p: dict, q: str, lang: str, persona: dict, profile: dict, chart_lean: str) -> list:
    out = []
    read = (p.get("read") or p.get("why") or "").strip()
    nxt = (p.get("next") or "").strip()
    if not read:
        return ["EMPTY_READ"]
    if p.get("needs_clarification"):
        out.append("CLARIFY_ASKED")
        return out
    if not nxt:
        out.append("MISSING_MOVE")
    elif _looks_broken(nxt) or len(nxt.split()) < 6:
        out.append("BROKEN_MOVE")
    got = main._wa_lang(read, "en")
    if lang in ("es", "pt") and got != lang:
        out.append("WRONG_LANGUAGE")
    if lang in ("es", "pt") and _EN_LEAK.search(f"{read} {nxt}"):
        out.append("ENGLISH_LEAK")
    if validate_narration(main._ask_voice_text(f"{read} {nxt}", q), language="en"):
        out.append("BANNED_WORDS")
    if _CHILDISH_RX.search(f"{read} {nxt}"):
        out.append("TALKS_DOWN")
    sents = [s for s in _SENT.split(read) if s.strip()]
    if len(sents) < 3 and len(read) < 220:
        out.append("THIN_READ")
    if len(sents) >= 2:   # echo = sentence two mostly re-says sentence one (not just the same lean)
        _w = lambda x: {w for w in re.findall(r"[a-zà-ÿ']{4,}", x.lower())}
        a, b = _w(sents[0]), _w(sents[1])
        if b and len(a & b) >= 0.6 * len(b):
            out.append("OPENER_ECHO")
    tm = (p.get("timing") or "").strip()
    if tm:
        tyears = set(re.findall(r"20\d\d", tm))
        s1years = set(re.findall(r"20\d\d", sents[0])) if sents else set()
        if s1years and tyears and not (s1years & tyears):
            out.append("TIMING_MISMATCH")
        ym = main._ask_ym_tokens(tm)
        now = datetime.datetime.utcnow()
        if str(p.get("verdict") or "").upper() == "NOT_YET" and ym and ym[0] <= (now.year, now.month):
            out.append("PAST_WINDOW_NOT_YET")
    _fund_txt = f"{read} {nxt}"
    if re.search(r"(?i)partner|socio|s[oó]cio|saajhedaar", q):
        _fund_txt = re.sub(r"(?i)\binvestors?\b", "", _fund_txt)   # "a partner, not an investor"
    if _FUND.search(_fund_txt) and not _FUND.search(q):
        out.append("FUNDING_UNASKED")
    if (str(profile.get("marital_status") or "").lower() in _UNPARTNERED
            and _PARTNER_WORDS.search(f"{read} {nxt}") and not _PARTNER_WORDS.search(q)):
        out.append("PARTNER_ASSUMED")
    lean = _lean_of(f"{read} {nxt}")
    if chart_lean == "spread" and _hits(_CONC, f"{read} {nxt}") and not _hits(_SPREAD, sents[0] if sents else ""):
        out.append("LEAN_CONTRADICTION")
    if chart_lean == "concentrate" and _hits(_SPREAD, f"{read} {nxt}") and not _hits(_CONC, sents[0] if sents else ""):
        out.append("LEAN_CONTRADICTION")
    fus = p.get("suggested_followups") or []
    if not fus:
        out.append("FU_NONE")
    else:
        if len(fus) != 3:
            out.append("FU_COUNT")
        if any(main._ask_norm(f["q"]) == main._ask_norm(q) for f in fus):
            out.append("FU_REPEATS_QUESTION")
        if any(len(f.get("title") or "") > 24 for f in fus):
            out.append("FU_TITLE_TOO_LONG")
        if lang in ("es", "pt") and any(main._wa_lang(f["q"], lang) != lang for f in fus):
            out.append("FU_WRONG_LANGUAGE")
    return out


JUDGE_CONV = (
    "You review ONE conversation between a person and an astrology guidance app. Earlier answers are "
    "context; judge the WHOLE conversation. Report only real problems a careful human editor would fix.\n"
    "ALLOWED: what 'the reading' shows, timing windows, gentle next steps, facts in the KNOWN PROFILE.\n"
    "PROBLEMS: (1) CONTRADICTION — an answer or move contradicts an earlier answer in the same "
    "conversation (e.g. 'spread across ventures' then 'pick one venture'); (2) ODD PHRASE — a phrase "
    "that reads wrong or unnatural to a native speaker (wrong word, wrong register, forced vocabulary, "
    "a family word dropped into a business answer); "
    "(3) ASSUMPTION — states as fact something about the person not in the profile or their messages "
    "(a partner, children, a loan, raising money); (4) NON-ANSWER — doesn't answer what was asked; "
    "(5) INCOMPLETE MOVE — the next step is cut off or missing.\n"
    "QUOTE RULE: every item must begin with an EXACT quote copied from the conversation in single "
    "quotes, then a short reason. Never report something that is not in the text.\n"
    "Reply STRICT JSON only: {\"contradictions\": [short quotes], \"odd_phrases\": [short quotes], "
    "\"assumptions\": [short quotes], \"non_answers\": [question text], \"incomplete_moves\": [quotes], "
    "\"score\": 1-5}")


async def judge_conversation(profile: dict, turns: list) -> dict:
    known = "; ".join(f"{k}={v}" for k, v in profile.items() if v)
    convo = "\n\n".join(f"Q{i+1}: {t['q']}\nA{i+1}: {t['read']}\nMOVE{i+1}: {t['next']}"
                        for i, t in enumerate(turns))
    try:
        raw = await asyncio.wait_for(main.call_llm_claude(
            prompt=f"KNOWN PROFILE: {known or 'nothing'}\n\nCONVERSATION:\n{convo}",
            system_override=JUDGE_CONV, max_tokens_override=700, temperature_override=0), timeout=60)
        raw = raw[0] if isinstance(raw, tuple) else raw
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        return {"error": type(e).__name__}


# ── conversation runner (per-task thread via contextvar so chains run concurrently) ──
_THREAD: contextvars.ContextVar = contextvars.ContextVar("audit_thread", default=None)


def _thread_for(cid, limit=4, within_minutes=240):
    t = _THREAD.get()
    return list(t[-limit:]) if t else []


async def ask(persona, q, thread):
    _THREAD.set(thread)
    r = await main.ask_endpoint(main.AskRequest(question=q, chart_id=persona["chart"], mode="explore",
                                                language=persona["lang"], tz_offset=persona["tz"]))
    r = r if isinstance(r, dict) else json.loads(getattr(r, "body", b"{}") or b"{}")
    thread.append({"q": q, "a": (r.get("read") or "")[:600], "domain": r.get("domain") or "", "m": ""})
    return r


async def run_chain(sem, persona, chain_name, steps, rep, profile, chart_lean, use_judge):
    async with sem:
        thread, turns = [], []
        try:
            last = None
            for q in steps:
                q = q.format(one=persona["one"], two=persona["two"])
                p = await ask(persona, q, thread)
                turns.append(_turn(p, q, persona, profile, chart_lean, chain_name, rep, tap=None))
                last = p
            base = list(thread)
            for f in (last.get("suggested_followups") or []):
                t2 = list(base)
                p = await ask(persona, f["q"], t2)
                turns.append(_turn(p, f["q"], persona, profile, chart_lean, chain_name, rep, tap=f.get("lane")))
        except Exception as e:
            turns.append({"persona": persona["name"], "chain": chain_name, "rep": rep, "q": "(error)",
                          "issues": ["ERROR"], "error": f"{type(e).__name__}: {e}"[:200]})
        conv = {"persona": persona["name"], "chain": chain_name, "rep": rep, "turns": turns}
        if use_judge and turns:
            main_turns = [t for t in turns if t.get("tap") is None and "read" in t]
            conv["judge"] = await judge_conversation(profile, main_turns)
        return conv


def _turn(p, q, persona, profile, chart_lean, chain, rep, tap):
    return {"persona": persona["name"], "chain": chain, "rep": rep, "tap": tap, "q": q,
            "verdict": p.get("verdict"), "timing": p.get("timing"),
            "read": (p.get("read") or p.get("why") or "").strip(), "next": (p.get("next") or "").strip(),
            "followups": [f"{f.get('title')} | {f.get('q')}" for f in (p.get("suggested_followups") or [])],
            "lean": _lean_of((_SENT.split((p.get("read") or "").strip()) or [""])[0]),
            "issues": turn_checks(p, q, persona["lang"], persona, profile, chart_lean)}


def repeat_flips(convs: list) -> list:
    """Same persona/chain/question across repeats: verdict, timing or lean must match."""
    by = {}
    for c in convs:
        for t in c["turns"]:
            if t.get("tap") is None and "read" in t:
                by.setdefault((t["persona"], t["chain"], t["q"]), []).append(t)
    flips = []
    for key, ts in by.items():
        if len(ts) < 2:
            continue
        for fld in ("verdict", "timing", "lean"):
            vals = {str(t.get(fld) or "") for t in ts}
            if fld == "lean":
                vals.discard("")          # a lean stated in one run and not the other is not a flip
            if len(vals) > 1:
                flips.append({"persona": key[0], "chain": key[1], "q": key[2], "field": fld,
                              "values": sorted(vals)})
    return flips


async def run(personas, repeats, use_judge):
    async def nop(*a, **k):
        return None
    main._ask_persist = nop
    main._nlu_shadow = nop
    main._ask_harvest_stated = lambda *a, **k: None
    main._ask_recent_thread = _thread_for
    import antar_engine.outcomes as oc
    oc.record_claim = lambda *a, **k: None
    sem = asyncio.Semaphore(4)
    jobs = []
    for persona in personas:
        row = (main.supabase.table("charts").select(
            "first_name,gender,marital_status,children_status,profession,life_work,chart_data,lagna_sign")
            .eq("id", persona["chart"]).limit(1).execute().data or [{}])[0]
        cd = row.pop("chart_data", None)
        cd = cd if isinstance(cd, dict) else (json.loads(cd) if cd else {})
        wp = wealth_profile(cd, main.get_dashas_for_chart(persona["chart"]) or {},
                            {"lagna_sign": row.get("lagna_sign")})
        chart_lean = ((wp or {}).get("stability") or {}).get("lean") or ""
        profile = {k: v for k, v in row.items() if k != "lagna_sign"}
        for rep in range(repeats):
            for chain_name, steps in CHAINS[persona["lang"]].items():
                jobs.append(run_chain(sem, persona, chain_name, steps, rep, profile, chart_lean, use_judge))
    convs = await asyncio.gather(*jobs)
    return convs


def _verified(item, convo_text: str) -> bool:
    """[audit-honesty] keep a judge finding only if the phrase it quotes is really in the
    conversation — the judge echoed its own prompt example ('your appearance in the market')."""
    m = re.search(r"'([^']{4,200})'", str(item))
    if not m:
        return True
    norm = lambda x: re.sub(r"[^\w%]+", " ", x.lower()).strip()
    return norm(m.group(1))[:60] in norm(convo_text)


def report(convs: list, stamp: str) -> str:
    classes = {}
    def add(cls, ex):
        classes.setdefault(cls, []).append(ex)
    n_turns = 0
    for c in convs:
        for t in c["turns"]:
            n_turns += 1
            for i in t.get("issues") or []:
                add(i, f"{t['persona']} · {t['chain']} · {'tap '+t['tap'] if t.get('tap') else 'turn'} · "
                       f"“{t['q']}” → {(t.get('read') or t.get('error') or '')[:160]} | MOVE: {(t.get('next') or '')[:100]}")
        j = c.get("judge") or {}
        convo_text = " ".join(f"{t.get('q','')} {t.get('read','')} {t.get('next','')}" for t in c["turns"])
        for key, cls in (("contradictions", "JUDGE_CONTRADICTION"), ("odd_phrases", "JUDGE_ODD_PHRASE"),
                         ("assumptions", "JUDGE_ASSUMPTION"), ("non_answers", "JUDGE_NON_ANSWER"),
                         ("incomplete_moves", "JUDGE_INCOMPLETE_MOVE")):
            for x in j.get(key) or []:
                if key != "non_answers" and not _verified(x, convo_text):
                    add("JUDGE_UNVERIFIED (ignored)", f"{c['persona']} · {str(x)[:120]}")
                    continue
                add(cls, f"{c['persona']} · {c['chain']} · rep {c['rep']} · {str(x)[:200]}")
    for f in repeat_flips(convs):
        add(f"REPEAT_FLIP_{f['field'].upper()}", f"{f['persona']} · {f['chain']} · “{f['q']}” → {f['values']}")
    scores = [c["judge"].get("score") for c in convs if isinstance((c.get("judge") or {}).get("score"), (int, float))]
    _ign = classes.pop("JUDGE_UNVERIFIED (ignored)", [])
    order = sorted(classes.items(), key=lambda kv: -len(kv[1]))
    if _ign:
        order.append(("JUDGE_UNVERIFIED (ignored — quote not in the text)", _ign))
    lines = [f"# Conversation audit {stamp}", "",
             f"{len(convs)} conversations · {n_turns} answers · "
             f"{sum(len(v) for v in classes.values())} findings in {len(classes)} classes"
             + (f" ({len(_ign)} unverified judge quotes ignored)" if _ign else "")
             + (f" · mean judge {sum(scores)/len(scores):.2f}/5" if scores else ""), "",
             "## Classes (most frequent first)", ""]
    lines += [f"- **{k}**: {len(v)}" for k, v in order]
    for k, v in order:
        lines += ["", f"## {k} ({len(v)})", ""] + [f"- {x}" for x in v[:8]]
        if len(v) > 8:
            lines.append(f"- … {len(v) - 8} more in the .json")
    return "\n".join(lines)


def rescore(path: str) -> list:
    """Re-apply the deterministic checks to a saved run (judge findings kept) — measure a
    checker change without re-running every answer."""
    convs = json.load(open(path))
    meta = {}
    for persona in PERSONAS:
        row = (main.supabase.table("charts").select(
            "first_name,gender,marital_status,children_status,profession,life_work,chart_data,lagna_sign")
            .eq("id", persona["chart"]).limit(1).execute().data or [{}])[0]
        cd = row.pop("chart_data", None)
        cd = cd if isinstance(cd, dict) else (json.loads(cd) if cd else {})
        wp = wealth_profile(cd, main.get_dashas_for_chart(persona["chart"]) or {},
                            {"lagna_sign": row.get("lagna_sign")})
        meta[persona["name"]] = (persona, {k: v for k, v in row.items() if k != "lagna_sign"},
                                 ((wp or {}).get("stability") or {}).get("lean") or "")
    for c in convs:
        for t in c["turns"]:
            if "read" not in t or t["persona"] not in meta:
                continue
            persona, profile, lean = meta[t["persona"]]
            fus = [{"title": x.split(" | ", 1)[0], "q": x.split(" | ", 1)[-1]} for x in t.get("followups") or []]
            p = {"read": t["read"], "next": t["next"], "timing": t.get("timing"),
                 "verdict": t.get("verdict"), "suggested_followups": fus}
            t["issues"] = turn_checks(p, t["q"], persona["lang"], persona, profile, lean)
            t["lean"] = _lean_of((_SENT.split(t["read"].strip()) or [""])[0])
    return convs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--persona", action="append")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--rescore", help="re-check a saved conv_*.json instead of running")
    a = ap.parse_args()
    ps = [p for p in PERSONAS if not a.persona or p["name"] in a.persona]
    convs = rescore(a.rescore) if a.rescore else asyncio.run(run(ps, a.repeats, not a.no_judge))
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M")
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Antar.world", "answer_audit")
    os.makedirs(outdir, exist_ok=True)
    json.dump(convs, open(os.path.join(outdir, f"conv_{stamp}.json"), "w"), ensure_ascii=False, indent=1)
    md = report(convs, stamp)
    path = os.path.join(outdir, f"conv_{stamp}.md")
    open(path, "w").write(md)
    head, rest = md.split("## Classes (most frequent first)", 1)
    print(head.strip() + "\n" + rest.split("\n## ", 1)[0].strip())
    print(f"→ {path}")
