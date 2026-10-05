"""
antar_engine/wealth_magnitude.py — [wealth-engine 2026-09-23]

Native-level WEALTH read that survives falsification, unlike "which vertical wins"
(that idea was tested and killed — see the business-timing study). Two things the
chart CAN grade about the PERSON:

  MAGNITUDE  — how big can this person's wealth engine go? (dhana/raja/mahapurusha
               yogas + the strength of the wealth houses 2/10/11)
  STABILITY  — does it HOLD, or arrive-and-dissolve? (a node in a money house
               2/8/11) → the SIZING DISCIPLINE that fits the chart.

It NEVER names a vertical or predicts a specific company. It grades capacity and
tells the founder how to spread money across ventures — then execution + market decide which vehicle
catches the money. Deterministic, zero-LLM, plain-language summary.

Design: reuse yogas.detect_all_yogas (the yoga source of truth) for magnitude, and
mirror the node-in-money-house logic already in concern_engines for stability, but
turn it into actionable sizing advice.
"""
from __future__ import annotations
import re
from typing import Optional, List, Dict, Any

from antar_engine.yogas import (
    detect_all_yogas, _get_house, _house_lord,
    _is_exalted, _is_debilitated, _is_own_sign,
)

_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_STRENGTH_W = {"strong": 3.0, "moderate": 2.0, "weak": 1.0}
_WEALTH_CATS = {"wealth", "raj_yoga", "mahapurusha"}
_MONEY_HOUSES = (2, 8, 11)   # 2 own capital, 8 other-people's-money, 11 gains


def _cur_lords(dashas: Optional[dict]) -> set:
    """Set of planets whose Vimśottarī period (MD/AD) is running today."""
    if not isinstance(dashas, dict):
        return set()
    try:
        # [precision 2026-09-24] Vimśottarī-ONLY (matches the docstring). The mixed
        # _current_dasha_lords folds in Yoginī/chara, which would falsely mark a
        # secondary-system lord's period as "running" for the wealth read.
        from antar_engine.concern_engines import _vim_active_lords
        return _vim_active_lords(dashas) or set()
    except Exception:
        return set()


def _dignity_pts(planet: str, planets: dict) -> float:
    if _is_exalted(planet, planets) or _is_own_sign(planet, planets):
        return 1.0
    if _is_debilitated(planet, planets):
        return -1.0
    return 0.0


def _magnitude(planets: dict, lagna_sign: str,
               dashas: Optional[dict]) -> Dict[str, Any]:
    yogas = detect_all_yogas(planets, lagna_sign) or []
    drivers: List[str] = []
    yoga_score = 0.0
    wealth_planets: set = set()
    for y in yogas:
        if y.get("category") in _WEALTH_CATS:
            w = _STRENGTH_W.get(str(y.get("strength", "")).lower(), 1.0)
            yoga_score += w
            for p in (y.get("planets") or []):
                wealth_planets.add(p)
            drivers.append(f"{y.get('name')} ({y.get('strength')})")

    # strength of the wealth houses: lords' dignity + benefic occupants
    lord_score = 0.0
    for h in (2, 10, 11):
        lord = _house_lord(h, lagna_sign)
        if lord:
            pts = _dignity_pts(lord, planets)
            lord_score += pts
            if lord in _WEALTH_CATS:
                pass
            if pts:
                drivers.append(f"the {h}th-house ruler is "
                               f"{'strong' if pts > 0 else 'weak'}")
            wealth_planets.add(lord)
    occ_bonus = 0.0
    for p, v in planets.items():
        if not isinstance(v, dict):
            continue
        if v.get("house") in (2, 10, 11) and p in _BENEFICS:
            occ_bonus += 1.0 if _is_exalted(p, planets) else 0.5

    # [node-amplifier] Rahu in a wealth house is a big-GAINS magnitude driver (its
    # instability is handled separately in _stability). Crucially, add Rahu/Ketu
    # to wealth_planets when they sit in a money house so a running NODE dasha
    # (e.g. Rahu Mahadasha lighting an 11th-house Rahu) correctly reads as
    # "switched on now" — that is often the single biggest wealth activation.
    rahu_h, ketu_h = _get_house("Rahu", planets), _get_house("Ketu", planets)
    node_bonus = 0.0
    if rahu_h == 11:
        node_bonus += 2.0
        drivers.append("an amplifier sits in your gains area — big-gains potential")
    elif rahu_h in (2, 8):
        node_bonus += 1.0
    if rahu_h in _MONEY_HOUSES:
        wealth_planets.add("Rahu")
    if ketu_h in _MONEY_HOUSES:
        wealth_planets.add("Ketu")  # its dasha lights the theme (as instability)

    score = round(yoga_score + lord_score + occ_bonus + node_bonus, 2)
    if score >= 10:
        label = "exceptional"
    elif score >= 6.5:
        label = "high"
    elif score >= 3.5:
        label = "solid"
    else:
        label = "modest"

    # is the wealth engine "switched on" — does a running period (MD/AD) lord also
    # drive the wealth engine (a wealth-yoga planet, a 2/10/11 lord, or a node in
    # a money house)?
    cur = _cur_lords(dashas)
    lit = sorted(wealth_planets & cur)
    activated_now = bool(lit)

    return {"score": score, "label": label, "activated_now": activated_now,
            "lit_lords": lit, "drivers": drivers[:6]}


def _stability(planets: dict, lagna_sign: str) -> Dict[str, Any]:
    rahu_h = _get_house("Rahu", planets)
    ketu_h = _get_house("Ketu", planets)
    drivers: List[str] = []

    if ketu_h in _MONEY_HOUSES:
        return {
            "grade": "fragile", "node": f"Ketu-{ketu_h}", "lean": "spread",
            "sizing_advice": ("Gains here arrive but tend to DISSOLVE — putting "
                "everything into one venture is the trap. Cap how much you commit to "
                "any single venture, take profits out as they come, and never let "
                "one thing hold everything you've built."),
            "drivers": [f"the node of loss sits in a money area ({ketu_h}th) — "
                        "gains don't hold on their own"],
        }
    if rahu_h == 11:
        return {
            "grade": "volatile", "node": "Rahu-11", "lean": "spread",
            "sizing_advice": ("Big earning power that rises and falls a lot — the "
                "temptation is to stretch too far. Cap how much any one venture can take "
                "rides on each; running more than one is the chart-fit move, not a "
                "distraction. Move part of every gain into savings instead of putting it all back in."),
            "drivers": ["the node of amplification sits in the gains area (11th) — "
                        "large but volatile"],
        }
    if rahu_h in (2, 8):
        return {
            "grade": "volatile", "node": f"Rahu-{rahu_h}", "lean": "spread",
            "sizing_advice": ("Money here can inflate then reverse and invites "
                "over-leverage. Keep debt modest, size positions so a reversal "
                "can't sink you, and don't mistake a fast run-up for a floor."),
            "drivers": [f"the node of amplification sits in a money area ({rahu_h}th) "
                        "— prone to leverage and swings"],
        }

    # No node in a money house — check for malefic drag on 2/11.
    afflicted = False
    for h in (2, 11):
        for p, v in planets.items():
            if isinstance(v, dict) and v.get("house") == h and p in ("Saturn", "Mars"):
                afflicted = True
    if afflicted:
        return {
            "grade": "moderate", "node": None, "lean": "concentrate",
            "sizing_advice": ("Steady rather than explosive, with some drag — grow "
                "by compounding what works and avoid forcing the pace. Reinvest "
                "deliberately; don't chase."),
            "drivers": ["a hard planet weighs on a money area — steady, some friction"],
        }
    return {
        "grade": "stable", "node": None, "lean": "concentrate",
        "sizing_advice": ("Gains tend to HOLD — you can concentrate on what's "
            "working and let it compound rather than spreading thin."),
        "drivers": ["no destabiliser on the money areas — gains tend to hold"],
    }


# [one-lean 2026-10-04] the stability grade IS the answer to "concentrate or
# diversify?" — said once, in sentence one, and the move carries it out. Live
# (Raman, Rahu-11): "reputation grows when you run more than one venture" + move
# "close the nearest deal before spreading attention" = a mixed signal.
LEAN_DIRECTIVE = {
    # [audit-r3 2026-10-04] SPREAD = "no single thing holds everything", NOT "run more
    # ventures" — the latter made every later cap/reserve answer read as a walk-back.
    # [audit-b4] one definition everywhere: spreading risk = a reserve OUTSIDE the ventures +
    # a cap on each — NOT "more ventures" (later turns kept contradicting that reading).
    "spread": ("THE ANSWER IS: SPREAD YOUR RISK — keep part of what you earn OUTSIDE your ventures "
               "(a reserve none of them can touch) and cap what any one venture can draw from you. "
               "Say this plainly in sentence one. Do NOT tell them to start more ventures or add income "
               "streams — the spread is the reserve outside, not more things to run. `next` MUST carry it "
               "out with a concrete rule — a share of every payment (e.g. 10%) into a separate savings "
               "account, and when. Never recommend concentrating or focusing on one deal."),
    "concentrate": ("THE ANSWER IS: CONCENTRATE — put the main effort and money into the ONE thing "
                    "that is already working and let it compound; anything else gets capped or paused. "
                    "Say this plainly in sentence one, including that 'anything else is capped or paused'. "
                    "`next` MUST carry it out concretely (name what to back and what to pause, and for how "
                    "long). Never recommend diversifying."),
}

_CONC_RX = re.compile(r"(?i)concentr|\bfocus|enfoc|\bfoc[ao]r|all[- ]in|put everything|"
                      r"all my eggs|ek jagah|one place|un solo|um s[oó]")
_DIV_RX = re.compile(r"(?i)diversif|\bspread|repartir|distribu|alag alag|several|varios|v[aá]rios")


def is_concentrate_vs_diversify(question: str) -> bool:
    q = question or ""
    return bool(_CONC_RX.search(q) and _DIV_RX.search(q))


# [allin-keeps-lean 2026-10-04] "I am 100% all in on Tezops AI and Antar" (a reply to
# the concentrate-or-diversify answer) skipped the wealth layer, so the SAME chart got
# "the reading supports it" one run and "pick one, the reading favours focus" the next.
# A statement of how their money/time is placed gets the same lean, applied to it.
_ALLOC_RX = re.compile(
    r"(?i)\b(i'?m|i am|went|go|going|gone|been|be)\s+(100\s?%\s+)?all[- ]in\b|\ball[- ]in\s+(on|with|for)\b|"
    r"\b100\s?%|\bhundred percent\b|\beverything (is |i have )?(in|into|on)\b|"
    r"\ball (of )?my (money|savings|time|capital|energy)\b|\bput (it )?all\b|"
    r"\btodo (mi dinero |mi tiempo )?(en|a)\b|\bvoy con todo\b|\btudo (em|no|na)\b|"
    r"\bsab kuch\b|\bpoora (paisa|time)\b")


def is_allocation_statement(question: str) -> bool:
    return bool(_ALLOC_RX.search(question or ""))


_ALLOC_TARGET_RX = re.compile(
    r"(?i)(?:all[- ]in|100\s?%|hundred percent|everything|all (?:of )?my \w+|put (?:it )?all|todo|tudo|"
    r"sab kuch|poora \w+)(?:\b|(?<=%)).*?\b(?:on|in|into|behind|en|em|no|na|mein)\b\s+(.+)$")
_HI_TARGET_RX = re.compile(r"(?i)\b(?:sab kuch|poora \w+)\s+(.+?)\s+(?:mein|me)\b")
_LIST_SPLIT_RX = re.compile(r"(?i)\s*(?:,|&|\band\b|\by\b|\be\b|\baur\b|\bplus\b|\bas well as\b)\s*")


def named_count(question: str) -> int:
    """How many things they say they're all in on ('Tezops AI and Antar' → 2)."""
    q = (question or "").strip().rstrip("?.!")
    hm = _HI_TARGET_RX.search(q)          # Hinglish: "sab kuch X aur Y mein lagaya"
    m = None if hm else _ALLOC_TARGET_RX.search(q)
    target = hm.group(1) if hm else (m.group(1) if m else "")
    if not target:
        return 1
    return max(1, len([x for x in _LIST_SPLIT_RX.split(target) if re.search(r"\w", x)]))


# [lean-everywhere 2026-10-04] The money lean must hold on EVERY money/work answer, not
# only the concentrate question: Raman's profession answer said "one clear mandate
# beats three parallel bets… go deep on one venture, not wide" right after "spread".
LEAN_CONSISTENCY = {
    "spread": ("MONEY-LEAN GUARD: this reader's money reading says SPREAD across ventures with caps. "
               "Never tell them to pick one venture, cut ventures, or go deep on one instead of wide. "
               "Focus advice is about their ROLE or skill lane (what kind of work), not the number of ventures."),
    "concentrate": ("MONEY-LEAN GUARD: this reader's money reading says CONCENTRATE on what is working. "
                    "Never tell them to add ventures, start a second line, or diversify."),
}


def allocation_directive(lean: str, question: str) -> str:
    """Python decides which case this is — the narrator applies it, never re-decides.
    [allin-multi 2026-10-04] concentrate + two named ventures was rationalised as
    'together they form one track, so staying all-in fits' (Andres)."""
    multi = named_count(question) >= 2
    head = ("THEY JUST TOLD YOU HOW THEIR MONEY/TIME IS PLACED. Apply the chart's answer to "
            "exactly what they said; do not re-decide, and don't bring up raising money, "
            "investors or funding unless they did. Start from their reality (they ARE all in) and "
            "say what to do now. Make `next` concrete: an amount or share and where it goes "
            "(e.g. '10% of every payment into a separate savings account'), and when. ")
    if lean == "spread":
        return head + (ALLOCATION_DIRECTIVE["spread"] if multi else (
            "The answer is SPREAD YOUR RISK and they are all in on ONE thing — that is the "
            "concentration the reading warns about. Connect it to the earlier answer out loud: "
            "spreading doesn't mean leaving it — it means it can't hold everything they have. "
            "The fix: a cap on what it can take and a reserve outside it (that is what spreading "
            "risk means — not starting more ventures). `next` = the reserve step with an amount or "
            "share and when."))
    if lean == "concentrate":
        return head + (
            "The answer is CONCENTRATE and they named TWO OR MORE ventures. Say plainly that the "
            "split is the risk: back the one that is already earning or has traction, and cap or "
            "pause the other. Never call them one track or one effort, never say the split fits. "
            "`next` = decide which one gets the main effort and what the other is capped at."
            if multi else
            "The answer is CONCENTRATE and they are all in on ONE thing — that fits; affirm it "
            "plainly. `next` = protect it (a cash cushion, no new side bets).")
    return ""


def allocation_case(lean: str, question: str) -> str:
    """'conc_multi' / 'conc_single' / 'spread_multi' / 'spread_single' / ''."""
    if lean not in ("concentrate", "spread"):
        return ""
    return ("conc_" if lean == "concentrate" else "spread_") + (
        "multi" if named_count(question) >= 2 else "single")


# The two cases where the narrator's instinct ("all in = commitment = good") fights
# the chart. Python owns sentence one there; an affirming first sentence is dropped.
ALLOC_OPENER = {
    "conc_multi": {
        # [audit-b3] tried an "acknowledging" variant — the audit graded it worse
        # (contradictions 22→44: it read as walking the verdict back). Kept the verdict.
        "en": "{n}the reading says concentrate — being all in on two things at once is the split to fix.",
        "es": "{n}la lectura dice concentrarse — estar con todo en dos cosas a la vez es la división que hay que corregir.",
        "pt": "{n}a leitura diz concentrar — estar com tudo em duas coisas ao mesmo tempo é a divisão a corrigir.",
        "hi": "{n}reading kehti hai ek jagah focus karo — do cheezon mein ek saath poora lagana hi woh split hai jise theek karna hai.",
    },
    "spread_single": {
        "en": "{n}the reading says spread your risk — one venture holding everything is the risk here.",
        "es": "{n}la lectura dice repartir — que un solo proyecto lo sostenga todo es el riesgo aquí.",
        "pt": "{n}a leitura diz espalhar — um único projeto segurando tudo é o risco aqui.",
        "hi": "{n}reading kehti hai alag alag rakho — ek hi venture mein sab kuch hona hi yahan risk hai.",
    },
}
_AFFIRM_RX = re.compile(r"(?i)(right call|strongest move|exactly|\bfits?\b|solid pairing|good call|"
                        r"\bbacks?\b|\bsupports?\b|the right place|flags|acierto|encaja|correcto|"
                        r"\bcerto\b|combina|respalda|apoia|sahi (hai|faisla))")


_STOP = {"the", "and", "you", "your", "for", "not", "now", "but", "this", "that", "with", "here",
         "says", "reading", "lectura", "leitura", "dice", "diz", "kehti", "hai", "que", "por", "para",
         "los", "las", "una", "uno", "del", "com", "uma", "the", "are", "has", "have", "isn't", "don't"}

# [alloc-restate 2026-10-04] the narrator often opens with its own copy of the
# verdict ("The split itself is the risk — the reading says concentrate, not divide")
# right under Python's sentence one — drop that echo too.
_NEVER = re.compile(r"(?!x)x")
_RESTATE_RX = {
    "conc_multi": re.compile(r"(?i)\bsplit\b|concentrat|\bdivid|divisi[oó]n|divis[aã]o|ek jagah|"
                             r"\byahi( toh)?\b"),
    "spread_single": re.compile(r"(?i)\bspread\b|one venture|concentration|repartir|espalhar|alag alag|"
                                r"\b[uú]nic[oa]\b|un solo|um s[oó]|concentra|"
                                r"\byahi( toh)?\b|sabse bada (warning|risk)"),
}


def apply_alloc_opener(read: str, case: str, language: str = "en", name: str = "",
                       openers: dict = None, restate: dict = None) -> str:
    """Prepend Python's sentence one for the contested cases; drop an affirming opener."""
    openers = ALLOC_OPENER if openers is None else openers
    restate = _RESTATE_RX if restate is None else restate
    tmpl = (openers.get(case) or {})
    if not tmpl or not isinstance(read, str):
        return read
    lang = "hi" if (language or "en").lower() in ("hi", "hinglish") else (language or "en").lower()[:2]
    op = (tmpl.get(lang) or tmpl["en"]).format(n=(f"{name}, " if name else ""))
    op = op[0].upper() + op[1:]
    for i in range(2):   # the narrator's own verdict sentence(s) at the top
        sents = re.split(r"(?<=[.!?])\s+", read.strip(), maxsplit=1)
        if not (len(sents) > 1 and len(sents[0]) <= 160 and (
                _AFFIRM_RX.search(sents[0]) or restate.get(case, _NEVER).search(sents[0]))):
            break
        # [thin-guard 2026-10-04] a second drop only when ≥3 sentences would remain
        # (Jaime's answer shrank to "…es positivo. Solo un fondo separado puede protegerte.")
        if i == 1 and len(re.split(r"(?<=[.!?])\s+", sents[1].strip())) < 3:
            break
        read = sents[1]
    # [audit-b4] the narrator's next sentence mostly re-says Python's opener in other words
    # ("…bring in help by contract, not as a partner. Keep it yours for now.") — drop it
    def _cw(x):
        return {w for w in re.findall(r"[a-zà-ÿ']{3,}", (x or "").lower())} - _STOP
    _opw = _cw(op)
    sents = re.split(r"(?<=[.!?])\s+", read.strip(), maxsplit=1)
    if len(sents) > 1 and _opw:
        _s0 = _cw(sents[0])
        if (_s0 and len(_s0 & _opw) >= 0.6 * len(_s0)
                and len(re.split(r"(?<=[.!?])\s+", sents[1].strip())) >= 2):   # never thin it out
            read = sents[1]
    # the rest may still open with the name — drop a duplicate "Name, " lead
    if name:
        read = re.sub(rf"^{re.escape(name)},\s*", "", read.strip())
        read = read[:1].upper() + read[1:]
    return (op + " " + read).strip()


ALLOCATION_DIRECTIVE = {
    "spread": ("THEY JUST TOLD YOU HOW THEIR MONEY/TIME IS PLACED. Apply the SAME answer — SPREAD "
               "YOUR RISK = a reserve outside the ventures + a cap on each — to exactly what they said; "
               "do not re-decide. With two or more ventures say plainly: running two doesn't change it — "
               "both are still inside your business, so the reserve outside them is what's missing. Never "
               "say the two ventures ARE the spread, never tell them to pick one or to add more. `next` = "
               "the most each venture can draw from them and what share of every payment goes straight "
               "to savings."),
    "concentrate": ("THEY JUST TOLD YOU HOW THEIR MONEY/TIME IS PLACED. Apply the SAME answer — "
                    "CONCENTRATE — to exactly what they said; do not re-decide. All in on ONE thing "
                    "that is working fits; split across several means back the strongest and pause "
                    "the rest. `next` = the concrete step that does that."),
}


def wealth_profile(chart_data: dict, dashas: Optional[dict] = None,
                   chart_record: Optional[dict] = None) -> dict:
    """Native wealth read: {magnitude, stability, headline, summary, guard}.
    Never raises; returns {available: False} when the chart is unreadable."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        planets = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign") or (chart_record or {}).get("lagna_sign")
        if not planets or not lagna:
            return {"available": False}

        mag = _magnitude(planets, lagna, dashas)
        sta = _stability(planets, lagna)

        _mag_word = {"exceptional": "an exceptional wealth engine",
                     "high": "a large wealth engine",
                     "solid": "a solid wealth engine",
                     "modest": "a modest, work-it wealth engine"}[mag["label"]]
        _sta_tail = {
            "fragile": "but a fragile one, so cap what you put into any one venture — gains dissolve if you concentrate",
            "volatile": "but a volatile one, so spread across several ventures and cap the downside",
            "moderate": "steady with some drag, so compound what works and don't force it",
            "stable": "and a stable one, so you can concentrate on what works and let it compound",
        }[sta["grade"]]
        headline = f"{_mag_word.capitalize()}, {_sta_tail}."

        _when = (" And it's switched on now — your current life-period is one of "
                 "its own drivers, so this is a build-and-raise window, not a wait."
                 if mag["activated_now"] else
                 " It's more latent than lit right now — it turns on when the right "
                 "life-period runs; build the groundwork for then.")
        summary = (
            f"Your chart carries {_mag_word} — this is about how BIG your money "
            f"capacity can go, not which business it comes through.{_when} "
            f"The important part is HOW it behaves: {sta['sizing_advice']} "
            "The chart can grade your capacity and how to spread your money across "
            "ventures — it cannot tell you which venture becomes the big one; that's "
            "execution and market, and it's yours to decide."
        )

        return {
            "available": True,
            "magnitude": mag,
            "stability": sta,
            "headline": headline,
            "summary": summary,
            "guard": ("Grades wealth CAPACITY + how to spread money across ventures "
                      "— never picks a vertical or predicts a specific company."),
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
