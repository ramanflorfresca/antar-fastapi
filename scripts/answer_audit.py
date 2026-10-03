"""Answer audit loop — generate questions, run the full Ask pipeline (dry), grade
every answer, report the failures. One iteration of "learn from the responses".

[answer-audit 2026-10-03] Owner: "can't you run these iterations and learn from
the responses?" Each run:
  1. builds a question bank: question forms × life phases × EN/ES/PT/Hinglish
     (tests/test_question_forms.py) + adversarial cases (comparisons, wealth
     promises, stated facts, parents, partners, typos, betting);
  2. runs each through ask_endpoint on the given chart(s) — NOTHING is sent or
     saved (persist, claims, profile harvest and the shadow log are stubbed);
  3. grades each answer with deterministic checks (language, banned words,
     verdict lead on how-to/comparison/wealth questions, investment advice,
     empty answer) and an AI grader (answers the question? wrong topic? invented
     facts? verdict fits? tone?);
  4. writes Antar.world/answer_audit/<stamp>.md + .json, failures first.
Nothing self-modifies: failures are fixed in code + a regression test.

    venv311/bin/python scripts/answer_audit.py --chart <id> [--n 40] [--seed 7]
"""
import argparse, asyncio, datetime, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402
from antar_engine import understand as und, messaging as msg  # noqa: E402
from antar_engine.narration_validator import validate_narration  # noqa: E402
from test_question_forms import PHASES, TEMPLATES  # noqa: E402

LANG = {"en": "en", "es": "es", "pt": "pt", "hi": "hinglish"}
ADVERSARIAL = [
    ("en", "Gold or defence — which should I focus on?"),
    ("en", "Will my startup make me a millionaire by 2028?"),
    ("en", "Which work will give me the most potential?"),
    ("en", "I was laid off in March. Should I go back to accounting or try something new?"),
    ("en", "How is my work with partners?"),
    ("en", "Is it better to work with my father or with partners?"),
    ("en", "My mother is getting older — should I move back to India to be near her?"),
    ("en", "Why do I keep losing money even though I work hard?"),
    ("en", "What type of courses should I take?"),
    ("en", "Is it a good time to talk to my ex again, or should I let it go?"),
    ("en", "how is my carrer lookin this yr"),
    ("en", "Will I win at the casino tonight?"),
    ("en", "Should I put my savings into crypto or gold?"),
    ("es", "¿Me conviene asociarme con mi hermano en el negocio?"),
    ("es", "Estoy separado. ¿Volveremos a estar juntos este año?"),
    ("pt", "Meu sócio quer sair da empresa. Vale a pena comprar a parte dele?"),
    ("pt", "Por que meu dinheiro nunca sobra no fim do mês?"),
    ("hi", "Mera beta 12th mein hai, uske liye engineering sahi rahega ya medical?"),
    ("hi", "Kya is saal meri shaadi hogi?"),
    ("hi", "Mujhe naukri chhod ke business karna chahiye?"),
]
_LEAD_VERDICT = re.compile(r"(?i)^\s*\*?\s*(yes|likely|not yet|not now|no|sí|si|sim|não|nao|haan|nahi)\b\s*[—–-]")

JUDGE = (
    "You grade ONE answer from an astrology guidance app for a real person. Be fair and specific.\n"
    "ALLOWED (never count these as problems): what 'the reading' shows (strengths, pressures, "
    "'pressure on savings', 'the reading shows…'), timing windows and periods named by the reading "
    "('Nov 2026 – Jan 2027', 'this chapter'), readings about a parent or partner relationship, facts the "
    "person stated in the question and simple arithmetic on them (laid off in March → seven months), a "
    "'Yes / Not yet / Likely' lead on yes-no, when or how-is questions, gentle practical next steps.\n"
    "PROBLEMS: (a) doesn't answer what was actually asked (e.g. asked which courses, names none); "
    "(b) wrong topic; (c) INVENTED facts = claims about the person's life, history, job, business, "
    "debts, relationships or situation stated AS KNOWN FACT (not as what the reading shows) that they "
    "never told us — e.g. 'your unstable business', 'the loan you took', 'your finance years'; "
    "(d) a Yes/No/Not-yet verdict line on a how-to / why / which / comparison question, or a wealth "
    "promise / ranking industries by outcome; (e) investment advice (where to put money); (f) cold or "
    "blaming tone when the person sounds like they're struggling; (g) planet/house/sign names.\n"
    "Reply STRICT JSON only: {\"answers_question\": bool, \"wrong_topic\": bool, \"invented_facts\": "
    "[short quotes of (c) only], \"verdict_fits\": bool, \"tone_ok\": bool, \"score\": 1-5, "
    "\"note\": \"one sentence naming the single biggest problem, or 'good'\"}")


def bank(n: int, seed: int) -> list:
    rnd = random.Random(seed)
    phases = list(PHASES)
    forms = list(TEMPLATES["en"])
    out = [(lang, q) for lang, q in ADVERSARIAL]
    combos = [(lang, form, ph) for lang in TEMPLATES for form in forms for ph in phases]
    rnd.shuffle(combos)
    for lang, form, ph in combos[: max(0, n - len(out))]:
        out.append((lang, TEMPLATES[lang][form].format(n=PHASES[ph][lang])))
    return out[:n] if n else out


def checks(q: str, qlang: str, u: dict, read: str, nxt: str) -> list:
    issues = []
    text = f"{read} {nxt or ''}".strip()
    if not read:
        return ["empty answer"]
    got = main._wa_lang(read, "en")
    if qlang in ("es", "pt") and got != qlang:
        issues.append(f"language: asked {qlang}, answered {got}")
    if qlang == "en" and got in ("es", "pt"):
        issues.append(f"language: asked en, answered {got}")
    vios = validate_narration(text, language="en")
    if vios:
        issues.append("banned words: " + ", ".join(sorted({str(v).split(':')[0] for v in vios}))[:120])
    no_verdict = und.suppress_verdict(u) or und.is_comparison(u) or (u or {}).get("outcome_claim")
    if no_verdict and _LEAD_VERDICT.search(read):
        issues.append(f"verdict lead on a {(u or {}).get('intent')} / comparison / wealth question")
    if und._INVEST_SENT.search(text):
        issues.append("investment advice")
    return issues


_PROFILE = {}


async def judge(q: str, read: str, nxt: str) -> dict:
    try:
        known = "; ".join(f"{k}={v}" for k, v in _PROFILE.items() if v)
        raw = await asyncio.wait_for(main.call_llm_claude(
            prompt=(f"KNOWN ABOUT THIS PERSON (from their profile — mentioning these is NOT invented): "
                    f"{known or 'nothing'}\n\nQUESTION: {q}\n\nANSWER: {read}\n\nNEXT STEP: {nxt or ''}"),
            system_override=JUDGE, max_tokens_override=300, temperature_override=0), timeout=40)
        raw = raw[0] if isinstance(raw, tuple) else raw
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        return {"error": type(e).__name__}


async def one(sem, chart, lang, q):
    async with sem:
        try:
            u = await main._nlu_read(q, None) or {}
            r = await main.ask_endpoint(main.AskRequest(question=q, chart_id=chart, mode="explore",
                                                        language=LANG[lang], tz_offset=-240))
            r = r if isinstance(r, dict) else json.loads(getattr(r, "body", b"{}") or b"{}")
            read, nxt = (r.get("read") or r.get("why") or "").strip(), r.get("next") or ""
            wa, _ = msg.format_ask_whatsapp_v2(r, LANG[lang], asked=q, compact=True)
        except Exception as e:
            return {"q": q, "lang": lang, "error": f"{type(e).__name__}: {e}"[:200]}
        det = checks(q, lang, u, read, nxt)
        j = await judge(q, read, nxt)
        bad = det + ([] if j.get("answers_question", True) else ["doesn't answer the question"]) \
            + (["wrong topic"] if j.get("wrong_topic") else []) \
            + ([f"invented: {', '.join(j['invented_facts'])}"] if j.get("invented_facts") else []) \
            + ([] if j.get("verdict_fits", True) else ["verdict doesn't fit"]) \
            + ([] if j.get("tone_ok", True) else ["tone"])
        return {"q": q, "lang": lang, "intent": u.get("intent"), "area": u.get("area"),
                "read": read, "next": nxt, "whatsapp": wa, "checks": det, "judge": j, "issues": bad}


async def run(charts, n, seed):
    async def nop(*a, **k):
        return None
    main._ask_persist = nop
    main._nlu_shadow = nop
    main._ask_harvest_stated = lambda *a, **k: None
    import antar_engine.outcomes as oc
    oc.record_claim = lambda *a, **k: None
    row = (main.supabase.table("charts").select(
        "name,gender,career_stage,profession,life_work,marital_status,children_status,ventures")
        .eq("id", charts[0]).limit(1).execute().data or [{}])[0]
    _PROFILE.update(row)
    sem = asyncio.Semaphore(3)
    qs = bank(n, seed)
    results = []
    for chart in charts:
        results += await asyncio.gather(*[one(sem, chart, lang, q) for lang, q in qs])
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M")
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Antar.world", "answer_audit")
    os.makedirs(outdir, exist_ok=True)
    json.dump(results, open(os.path.join(outdir, f"{stamp}.json"), "w"), ensure_ascii=False, indent=1)
    fails = [r for r in results if r.get("issues") or r.get("error")]
    by = {}
    for r in fails:
        for i in (r.get("issues") or [r.get("error")]):
            by.setdefault(i.split(":")[0], 0)
            by[i.split(":")[0]] += 1
    lines = [f"# Answer audit {stamp}", "", f"{len(results)} answers · {len(fails)} with issues", "",
             "## Issues by type", ""] + [f"- **{k}**: {v}" for k, v in sorted(by.items(), key=lambda x: -x[1])] + \
            ["", "## Failures", ""]
    for r in fails:
        lines += [f"### {r['q']}", f"- lang {r['lang']} · intent {r.get('intent')} · area {r.get('area')}",
                  f"- issues: {'; '.join(r.get('issues') or [r.get('error','')])}",
                  f"- judge: {(r.get('judge') or {}).get('note', '')}", "", "```", r.get("whatsapp", "")[:900], "```", ""]
    path = os.path.join(outdir, f"{stamp}.md")
    open(path, "w").write("\n".join(lines))
    print(f"{len(results)} answers · {len(fails)} with issues → {path}")
    for k, v in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {v:3d}  {k}")
    scores = [r["judge"].get("score") for r in results if isinstance((r.get("judge") or {}).get("score"), (int, float))]
    if scores:
        print(f"  mean judge score {sum(scores)/len(scores):.2f}/5")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", action="append", required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    asyncio.run(run(a.chart, a.n, a.seed))
