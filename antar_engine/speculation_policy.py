"""
antar_engine/speculation_policy.py — how Antar answers speculation and gambling,
the way an astrologer would.

[speculation-policy 2026-10-03] Owner: "for speculation use the timing on when the
gains from unearned income are activated … gambling is part of speculation, so if
speculation is supported give the window and say that speculation is supported but
you will not give a gambling-specific answer; if the chart doesn't support it or
shows losses from speculation, say so … if the chart supports speculation and the
time is right they calculate; if not they straight out say no."

Two inputs, both already computed elsewhere:
  * PROMISE — domain_engines_tier1.engine_speculation(): the natal speculation read
    (5th house + its lord, Rahu, Jupiter, Mercury, the 5th–11th link) with gain and
    loss indicators and a 10–90 score. Ask never used it before.
  * TIMING — the event engine's window for the speculation concern (5/8/11:
    speculation, sudden/unearned gains, gains), i.e. when unearned income is
    activated.

States (first match wins):
  losses → loss indicators dominate              → "no — the reading points to losses"
  no     → no natal support, or the engine denies → "no"
  open   → supported and the window is active now → "supported — window open now, through X"
  later  → supported, window ahead                → "supported — but not yet; opens X"
Gambling (casino / lottery / betting) is read as speculation, plus one line: Antar
doesn't give game-specific answers. Never a "best day"; windows are periods.
"""
from __future__ import annotations

from typing import Optional

SUPPORT_SCORE = 40          # engine_speculation: >=65 favourable, 40-64 moderate, <40 risky
OPEN_CLIENTS = frozenset({"SUPPORTED", "YES", "LIKELY"})

_T = {
    "en": {
        "losses": "The timing doesn't support speculation — it points to losses from speculative bets rather than gains. The honest answer is no.",
        "no": "The timing doesn't show gains from speculation, so the honest answer is no.",
        "open": "The timing supports gains from speculation, and the window for unearned gains is open now{w}.",
        "later": "The timing supports gains from speculation — but not yet. The window for unearned gains opens {w}.",
        "later_nowin": "The timing supports gains from speculation — but not yet; the timing isn't active right now.",
        "through": " — through {w}",
        "gambling": "That's the timing for speculation in general — Antar doesn't give casino, lottery or betting-specific answers.",
        "next_no": "Keep your money in steady, earned income for now — this isn't your route to gains.",
        "next_open": "If you speculate at all, keep it small and capped — only money you can afford to lose.",
        "next_later": "Until then, prepare rather than bet — and keep any speculative money small.",
    },
    "es": {
        "losses": "El momento no respalda la especulación — apunta a pérdidas en apuestas especulativas más que a ganancias. La respuesta honesta es no.",
        "no": "El momento no muestra ganancias por especulación, así que la respuesta honesta es no.",
        "open": "El momento respalda ganancias por especulación, y la ventana de ingresos no ganados está abierta ahora{w}.",
        "later": "El momento respalda ganancias por especulación — pero todavía no. La ventana de ingresos no ganados se abre {w}.",
        "later_nowin": "El momento respalda ganancias por especulación — pero todavía no; el momento no está activo ahora.",
        "through": " — hasta {w}",
        "gambling": "Eso es para la especulación en general — Antar no da respuestas específicas de casino, lotería o apuestas.",
        "next_no": "Por ahora mantén tu dinero en ingresos estables y ganados — esta no es tu vía de ganancias.",
        "next_open": "Si especulas, que sea poco y con tope — solo dinero que puedas permitirte perder.",
        "next_later": "Mientras tanto, prepárate en vez de apostar — y mantén pequeño cualquier dinero especulativo.",
    },
    "pt": {
        "losses": "O momento não apoia a especulação — aponta para perdas em apostas especulativas, não ganhos. A resposta honesta é não.",
        "no": "O momento não mostra ganhos com especulação, então a resposta honesta é não.",
        "open": "O momento apoia ganhos com especulação, e a janela de ganhos não trabalhados está aberta agora{w}.",
        "later": "O momento apoia ganhos com especulação — mas ainda não. A janela de ganhos não trabalhados abre {w}.",
        "later_nowin": "O momento apoia ganhos com especulação — mas ainda não; o momento não está ativo agora.",
        "through": " — até {w}",
        "gambling": "Isso vale para a especulação em geral — o Antar não dá respostas específicas de cassino, loteria ou apostas.",
        "next_no": "Por enquanto, mantenha seu dinheiro em renda estável e trabalhada — este não é o seu caminho de ganhos.",
        "next_open": "Se especular, que seja pouco e com limite — só dinheiro que você pode perder.",
        "next_later": "Até lá, prepare-se em vez de apostar — e mantenha pequeno qualquer dinheiro especulativo.",
    },
    "hinglish": {
        "losses": "Timing speculation ko support nahi karti — yeh speculative daon mein faayde se zyada nuksaan dikhati hai. Seedha jawab hai: nahi.",
        "no": "Timing speculation se faayda nahi dikhati, isliye seedha jawab hai: nahi.",
        "open": "Timing speculation se faayde ko support karti hai, aur bina-mehnat ki kamai ki window abhi khuli hai{w}.",
        "later": "Timing speculation se faayde ko support karti hai — lekin abhi nahi. Bina-mehnat ki kamai ki window {w} mein khulegi.",
        "later_nowin": "Timing speculation se faayde ko support karti hai — lekin abhi nahi; abhi timing active nahi hai.",
        "through": " — {w} tak",
        "gambling": "Yeh speculation ki general timing hai — Antar casino, lottery ya betting ka specific jawab nahi deta.",
        "next_no": "Abhi apna paisa steady, mehnat ki kamai mein rakhiye — yeh aapka faayde ka raasta nahi hai.",
        "next_open": "Agar speculate karein to thoda aur limit ke saath — sirf utna jitna khona afford kar sakein.",
        "next_later": "Tab tak daon lagane ke bajay taiyari kijiye — aur speculative paisa chhota rakhiye.",
    },
}


def _lang(language: str) -> str:
    l = (language or "en").lower()
    # [hi 2026-10-07] only Roman-script Hinglish takes the Hinglish copy; Devanagari "hi" gets
    # English here and Ask's Devanagari guard translates the finished answer.
    return "hinglish" if l.startswith("hinglish") or l == "hi-latn" else (l[:2] if l[:2] in ("es", "pt") else "en")


def natal_read(chart_data: dict, dashas: dict, birth_date: str) -> Optional[dict]:
    """engine_speculation on this chart, or None."""
    try:
        from antar_engine.domain_engines_tier1 import engine_speculation
        cd = chart_data or {}
        planets = cd.get("planets") or {}
        if not planets:
            return None
        return engine_speculation(planets, cd.get("house_lords") or {}, cd.get("yogas") or [],
                                  dashas or {}, birth_date or "")
    except Exception:
        return None


def state(natal: Optional[dict], client: str = "", ee_verdict: str = "") -> str:
    """losses | no | open | later (see module doc)."""
    n = natal or {}
    score = float(n.get("score") or 0)
    gains, risks = n.get("gain_indicators") or [], n.get("risk_indicators") or []
    if risks and (score < SUPPORT_SCORE or len(risks) > len(gains)):
        return "losses"
    denied = any(w in (ee_verdict or "").lower() for w in ("denied", "not_promised", "no_promise"))
    if (natal is not None and score < SUPPORT_SCORE) or denied:
        return "no"
    if (client or "").upper() in OPEN_CLIENTS:
        return "open"
    return "later"


def lead(st: str, window: str = "", gambling: bool = False, language: str = "en") -> dict:
    """{'read': opening line(s), 'next': the practical step} in the reader's language."""
    T = _T[_lang(language)]
    w = (window or "").strip()
    if st == "open":
        head = T["open"].format(w=T["through"].format(w=w) if w else "")
        nxt = T["next_open"]
    elif st == "later":
        head = T["later"].format(w=w) if w else T["later_nowin"]
        nxt = T["next_later"]
    else:
        head, nxt = T[st], T["next_no"]
    if gambling:
        head = head + " " + T["gambling"]
    return {"read": head, "next": nxt}


import re as _re

# gambling = games of chance; plain speculation (stocks, trading, "speculation")
# does NOT get the no-game-specific line
GAMBLING_Q = _re.compile(
    r"(?i)\b(casino|lotter(y|ies)|lotto|bet|bets|betting|wager|poker|blackjack|roulette|jackpot|slots?|"
    r"slot machine|baccarat|craps|gambl\w*|sportsbook|apuesta\w*|apostar|aposta\w*|loter[ií]a|"
    r"cassino|jogo de azar|satta|jua|juaa|teen patti|matka)\b")


SPECULATION_Q = _re.compile(
    r"(?i)\b(speculat\w*|stocks?|stock market|share market|shares|equit(y|ies) market|trading|trade[sr]?|"
    r"day.?trad\w*|intraday|f&o|futures|options trading|forex|crypto\w*|bitcoin|commodit(y|ies) trading|"
    r"windfall|unearned|especulaci\w*|acciones|bolsa|criptomoneda\w*|especula\w*|a[cç][oõ]es|"
    r"criptomoeda\w*|satta|sattebaazi)\b")


def is_gambling(question: str) -> bool:
    return bool(GAMBLING_Q.search(question or ""))


_NOW_CLAIM = _re.compile(r"(?i)\b(right now|currently|current (period|chapter)|is active|are active|"
                         r"active (now|and)|wired in|ahora mismo|actualmente|agora mesmo|atualmente|abhi)\b")

_FUNDING_WORDS = ("funding", "investor", "raise capital", "fundraising", "financiaci", "inversionista",
                  "investidor", "captação", "funding trigger")


def merge(read: str, policy_read: str, st: str) -> str:
    """The policy lines ARE the answer. Live: narrated bodies under a speculation
    verdict contradicted it ("not yet" … "ahora es un buen momento" / "speculation
    is a standing weak spot" under "supports gains"), so nothing is appended."""
    return policy_read


def natal_window(natal: Optional[dict]) -> tuple:
    """(client, window) from engine_speculation's best_periods when the timing
    engine gave none: a running favourable period → ('SUPPORTED', ''); an upcoming
    one → ('NOT_YET', '<year>'); else ('', '')."""
    periods = (natal or {}).get("best_periods") or []
    if any(str(p).lower().startswith("current") for p in periods):
        return "SUPPORTED", ""
    for p in periods:
        m = _re.search(r"\b(20\d\d)\b", str(p))
        if m:
            return "NOT_YET", m.group(1)
    return "", ""



# ── KP on the birth chart (owner 2026-10-03: "KP is a good tool for speculation") ──
def kp_natal(chart_record: dict) -> Optional[dict]:
    """KP's natal speculation verdict (QUESTION_TYPES['speculation']: the deciding
    cusp's sub-lord signifying 2/5/6/11 favours, 8/12 denies → losses).
    {'verdict': yes|no|conditional, 'favour': [...], 'against': [...]} or None."""
    try:
        from antar_engine.kp.kp_service import _build_chart
        from antar_engine.kp.kp_significators import verdict as _kpv
        ch = _build_chart(chart_record or {})
        if ch is None:
            return None
        v = _kpv(ch, "speculation")
        d = v.get("debug") or {}
        return {"verdict": str(v.get("verdict") or "").lower(),
                "favour": list(d.get("favour_hit") or []), "against": list(d.get("against_hit") or [])}
    except Exception:
        return None


def combine(natal_state: str, kp: Optional[dict], client: str = "") -> str:
    """Two systems, astrologer-style: KP showing only the loss houses (8/12) is a
    'no — losses' whatever else says; a KP yes lifts a lukewarm natal 'no' into
    support (timing then decides open vs later); otherwise the natal state stands."""
    if not kp:
        return natal_state
    if kp.get("against") and not kp.get("favour"):
        return "losses"
    if natal_state == "no" and kp.get("verdict") == "yes":
        return "open" if (client or "").upper() in OPEN_CLIENTS else "later"
    return natal_state



# ── "what is the safest way to play this?" — a how-to, not the promise question ──
# [spec-howto 2026-10-03] live (owner's phone): option 2 "What is my safest way to play
# this?" returned the SAME window answer as the question before it. A how-to gets
# practical risk rules — never where to put money, never a day.
RISK_HOWTO = _re.compile(
    r"(?i)\b(safest|safe way|safely|how (much )?(should|can|do) i (risk|put|stake|keep|limit|protect)|"
    r"how (do|to) i (keep|limit|protect|manage|reduce)|stop.?loss|loss limit|risk (management|control)|"
    r"limit (my )?(losses|risk)|c[oó]mo (limito|protejo|mantengo)|forma m[aá]s segura|manera m[aá]s segura|"
    r"como (limito|protejo|mantenho)|forma mais segura|maneira mais segura|kaise (bachu|surakshit)|"
    r"surakshit tarika)\b")


def is_risk_howto(question: str) -> bool:
    return bool(RISK_HOWTO.search(question or ""))


_RISK = {
    "en": {
        "rules": ("The safest way: only use money you could lose completely and still pay your bills and "
                  "any loans; decide a hard loss limit before you start and stop when you reach it; never "
                  "borrow to speculate; and keep it a small share of what you have."),
        "no": "Given your timing, the safest way is to not speculate at all for now.",
        "timing": " Your window for unearned gains opens {w} — until then, keep it to a very small amount.",
        "open": " Your window for unearned gains is open now{t}, so a small, capped amount fits.",
        "next_no": "Put that money into steady, earned income or a cushion instead.",
        "next": "Write down your loss limit today, before any decision.",
        "gambling": " Antar doesn't give casino, lottery or betting-specific answers.",
    },
    "es": {
        "rules": ("La forma más segura: usa solo dinero que puedas perder por completo y aun así pagar tus "
                  "cuentas y deudas; fija un límite de pérdida firme antes de empezar y detente al llegar a él; "
                  "nunca te endeudes para especular; y que sea una parte pequeña de lo que tienes."),
        "no": "Según el momento, lo más seguro es no especular por ahora.",
        "timing": " Tu ventana de ganancias no ganadas se abre {w} — hasta entonces, una cantidad muy pequeña.",
        "open": " Tu ventana de ganancias no ganadas está abierta ahora{t}, así que encaja una cantidad pequeña y con tope.",
        "next_no": "Mejor pon ese dinero en ingresos estables y ganados o en un colchón.",
        "next": "Escribe hoy tu límite de pérdida, antes de cualquier decisión.",
        "gambling": " Antar no da respuestas específicas de casino, lotería o apuestas.",
    },
    "pt": {
        "rules": ("A forma mais segura: use só dinheiro que você possa perder por completo e ainda pagar suas "
                  "contas e dívidas; defina um limite de perda firme antes de começar e pare ao atingi-lo; "
                  "nunca se endivide para especular; e mantenha uma parte pequena do que você tem."),
        "no": "Pelo momento, o mais seguro é não especular por enquanto.",
        "timing": " Sua janela de ganhos não trabalhados abre {w} — até lá, um valor bem pequeno.",
        "open": " Sua janela de ganhos não trabalhados está aberta agora{t}, então cabe um valor pequeno e com teto.",
        "next_no": "Prefira colocar esse dinheiro em renda estável e trabalhada ou numa reserva.",
        "next": "Anote hoje o seu limite de perda, antes de qualquer decisão.",
        "gambling": " O Antar não dá respostas específicas de cassino, loteria ou apostas.",
    },
    "hinglish": {
        "rules": ("Sabse surakshit tarika: sirf wahi paisa lagayein jo poora kho dein tab bhi bills aur karz chukte "
                  "rahein; shuru karne se pehle nuksaan ki pakki limit tay karein aur wahan rukein; speculate "
                  "karne ke liye kabhi udhaar na lein; aur apne paise ka chhota hissa hi rakhein."),
        "no": "Timing ke hisaab se abhi speculate na karna hi sabse surakshit hai.",
        "timing": " Bina-mehnat ki kamai ki window {w} mein khulegi — tab tak bahut chhoti raqam.",
        "open": " Bina-mehnat ki kamai ki window abhi khuli hai{t}, to chhoti aur limit wali raqam theek hai.",
        "next_no": "Woh paisa steady, mehnat ki kamai ya cushion mein rakhein.",
        "next": "Aaj hi apni nuksaan ki limit likh lein, kisi bhi faisle se pehle.",
        "gambling": " Antar casino, lottery ya betting ka specific jawab nahi deta.",
    },
}


def risk_lead(st: str, window: str = "", gambling: bool = False, language: str = "en") -> dict:
    """{'read','next'} for a how-to-play-safely question (state-aware, no day, no investment advice)."""
    R = _RISK[_lang(language)]
    w = (window or "").strip()
    if st in ("losses", "no"):
        read, nxt = R["no"], R["next_no"]
    else:
        read = R["rules"]
        if st == "open":
            read += R["open"].format(t=(" — " + w) if w else "")
        elif w:
            read += R["timing"].format(w=w)
        nxt = R["next"]
    if gambling:
        read += R["gambling"]
    return {"read": read, "next": nxt}



# ── day-level questions (owner 2026-10-03: "someone who is a day trader or crypto trader would want this") ──
DAY_Q = _re.compile(
    r"(?i)\b(which day|what day|best day|good day|today|tonight|tomorrow|this week|next week|this weekend|"
    r"coming days|next few days|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"qu[eé] d[ií]a|hoy|esta noche|ma[nñ]ana|esta semana|pr[oó]xim[ao]s d[ií]as|"
    r"que dia|qual dia|hoje|esta noite|amanh[aã]|essa semana|nesta semana|desta semana|"
    r"aaj|kal|is hafte|kaun sa din|kaunsa din)\b")


def is_day_question(question: str) -> bool:
    return bool(DAY_Q.search(question or ""))


_DAYCTX = {
    "en": {"open": "Your window for unearned gains is open now{t} — keep any position small and capped.",
           "later": "Your window for unearned gains opens {w} — until then, treat any single day as low-conviction and keep positions small.",
           "later_nowin": "Treat any single day as low-conviction and keep positions small."},
    "es": {"open": "Tu ventana de ganancias no ganadas está abierta ahora{t} — mantén cualquier posición pequeña y con tope.",
           "later": "Tu ventana de ganancias no ganadas se abre {w} — hasta entonces, trata cualquier día como de baja convicción y mantén posiciones pequeñas.",
           "later_nowin": "Trata cualquier día como de baja convicción y mantén posiciones pequeñas."},
    "pt": {"open": "Sua janela de ganhos não trabalhados está aberta agora{t} — mantenha qualquer posição pequena e com teto.",
           "later": "Sua janela de ganhos não trabalhados abre {w} — até lá, trate qualquer dia como de baixa convicção e mantenha posições pequenas.",
           "later_nowin": "Trate qualquer dia como de baixa convicção e mantenha posições pequenas."},
    "hinglish": {"open": "Bina-mehnat ki kamai ki window abhi khuli hai{t} — positions chhoti aur limit mein rakhein.",
                 "later": "Bina-mehnat ki kamai ki window {w} mein khulegi — tab tak kisi bhi ek din ko kam bharose ka maanein aur positions chhoti rakhein.",
                 "later_nowin": "Kisi bhi ek din ko kam bharose ka maanein aur positions chhoti rakhein."},
}


def day_context(st: str, window: str = "", language: str = "en") -> str:
    D = _DAYCTX[_lang(language)]
    w = (window or "").strip()
    if st == "open":
        return D["open"].format(t=(" — " + w) if w else "")
    return D["later"].format(w=w) if w else D["later_nowin"]
