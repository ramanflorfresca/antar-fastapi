"""
antar_engine/circle_fit.py - "Are we built to partner?": the plain-language fit verdict for cofounder / business pairs.

The owner's frame: businesses don't fail, people do. A venture between two people who work hard, think alike and
cover each other survives, even if it struggles for years; two people who aren't built for partnership are better
off with ONE owner and the other as a consultant paid in task-based equity. And a season that doesn't work now can
work in a different one. So this module answers three things, in plain words (no house, lord, dasha or planet
terms ever reach the user):

  1. WHO each person is, from the Moon's nakshatra: a working temperament (27 fixed lines, tendencies not fate).
  2. WHETHER each is built for partnership, leans towards leading alone, or could go either way: points from the
     7th house / 11th lord (partnership, networks) against the 3rd lord / owner-mode / fused-identity-and-work
     (self-launch). Thresholds below are written down and NOT validated against outcomes: this is a descriptive
     lean, shown with its reasons, never a prediction that a venture works.
  3. WHICH SEASON each is in (from the running sub-period lord and the houses it rules: expansion, gains, action,
     partnership, initiative, consolidation, or the heavy ones: friction, transformation, release), and when the
     first stretch comes in which neither is in a heavy season. "Not the right time" is a date, not a verdict.

The VERDICT then picks one of four structures: full partners / partners with clear lanes / one founder plus an
advisor (task-based equity) / one owner, work by contract. Deterministic, no LLM. Pure except for reading charts.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from antar_engine import circle_copy as CC
from antar_engine import topic_copy as C

# ── 1. temperament by the Moon's nakshatra (index 0..26, the engine's own order) ─────────────
TEMPERAMENT_EN = (
    "Quick to start and restless with delay; first to move and quick to recover.",
    "Intense and able to carry heavy loads; takes responsibility seriously and won't be pushed around.",
    "Sharp, direct and demanding; cuts through excuses and holds high standards.",
    "Magnetic and steady; builds comfort and loyalty, and expects the same back.",
    "Curious and always searching; strong at finding options, slower to commit to one.",
    "Intense under pressure; brilliant at breaking old structures down and rebuilding.",
    "Resilient and optimistic; bounces back and keeps others hopeful.",
    "Nurturing and dependable; protects people and builds things that last.",
    "Perceptive and guarded; reads people well and keeps their cards close.",
    "Proud and authoritative; wants standing and respect, and leads from the front.",
    "Sociable and generous with ideas; works best with energy, appreciation and time to recharge.",
    "Dependable and fair; keeps promises and earns trust through consistency.",
    "Skilled with details and with their hands; a resourceful problem-solver who gets things executed.",
    "Creative and design-minded; wants the work to look and feel excellent.",
    "Independent and flexible; values freedom, adapts quickly and dislikes being controlled.",
    "Determined and goal-driven; keeps going until the target is reached, sometimes single-mindedly.",
    "Loyal and cooperative; strong in teams and in long relationships.",
    "Protective and commanding; takes charge in a crisis and dislikes coming second.",
    "Digs to the root; strips things back to fundamentals and has no patience for pretense.",
    "Persuasive and hard to discourage; confident and competitive.",
    "Principled and patient; plays the long game and finishes what they start.",
    "A listener and learner; absorbs, advises and communicates well.",
    "Rhythmic, ambitious and resourceful; drawn to results and works well in groups.",
    "Private, analytical and independent; works well alone and sees what others miss.",
    "Intense, idealistic and unconventional; driven by a cause and can swing between extremes.",
    "Deep, calm and disciplined; steady under pressure and thinks things through.",
    "Caring, imaginative and protective; finishes what others abandon and avoids conflict.",
)


def temperament(chart: dict) -> Optional[dict]:
    """{nakshatra, trait} from the Moon (English trait; the route translates the `trait` field)."""
    try:
        moon = ((chart or {}).get("planets") or {}).get("Moon") or {}
        i = moon.get("nakshatra_index")
        if not isinstance(i, int) or not 0 <= i <= 26:
            from antar_engine.nakshatra_groups import get_nakshatra_index
            i = get_nakshatra_index(moon.get("nakshatra") or "")
        if not isinstance(i, int) or not 0 <= i <= 26:
            return None
        return {"nakshatra": moon.get("nakshatra"), "trait": TEMPERAMENT_EN[i]}
    except Exception:
        return None


# ── 3. chapters: the running big chapter and the stretch inside it, in plain words ───────────
# Each person is in one big chapter and one stretch inside it. Both have a plain nature, and the stretch has a
# direct effect on how that person handles a partnership right now. tone: clouded (judgment on big commitments is
# unreliable: illusion, detachment), testing (delay, heat, ego: workable only with structure), steady, favorable.
TONE = {"Rahu": "clouded", "Ketu": "clouded", "Saturn": "testing", "Mars": "testing", "Sun": "testing",
        "Moon": "steady", "Mercury": "favorable", "Venus": "favorable", "Jupiter": "favorable"}
PLANETS = tuple(TONE)
MD_PHRASE = {
    "en": {"Sun": "a long chapter of authority and visibility", "Moon": "a long chapter of feeling and change", "Mars": "a long chapter of drive and conflict",
           "Mercury": "a long chapter of business and communication", "Jupiter": "a long chapter of growth and wisdom", "Venus": "a long chapter of relationships and comfort",
           "Saturn": "a long chapter of discipline and delay", "Rahu": "a long chapter of ambition and chasing the unfamiliar", "Ketu": "a long chapter of detachment and letting go"},
    "es": {"Sun": "una larga etapa de autoridad y visibilidad", "Moon": "una larga etapa de emociones y cambio", "Mars": "una larga etapa de impulso y conflicto",
           "Mercury": "una larga etapa de negocios y comunicación", "Jupiter": "una larga etapa de crecimiento y sabiduría", "Venus": "una larga etapa de relaciones y comodidad",
           "Saturn": "una larga etapa de disciplina y demora", "Rahu": "una larga etapa de ambición y de perseguir lo desconocido", "Ketu": "una larga etapa de desapego y de soltar"},
    "pt": {"Sun": "uma longa fase de autoridade e visibilidade", "Moon": "uma longa fase de emoções e mudança", "Mars": "uma longa fase de impulso e conflito",
           "Mercury": "uma longa fase de negócios e comunicação", "Jupiter": "uma longa fase de crescimento e sabedoria", "Venus": "uma longa fase de relacionamentos e conforto",
           "Saturn": "uma longa fase de disciplina e atraso", "Rahu": "uma longa fase de ambição e de perseguir o desconhecido", "Ketu": "uma longa fase de desapego e de soltar"},
    "hinglish": {"Sun": "adhikaar aur drishyata ka lamba daur", "Moon": "bhaavna aur badlaav ka lamba daur", "Mars": "josh aur takraav ka lamba daur",
                 "Mercury": "vyapar aur sanvaad ka lamba daur", "Jupiter": "vikas aur gyaan ka lamba daur", "Venus": "rishton aur aaram ka lamba daur",
                 "Saturn": "anushasan aur deri ka lamba daur", "Rahu": "mahatvakanksha aur anjaan ke peeche bhaagne ka lamba daur", "Ketu": "vairagya aur chhodne ka lamba daur"},
}
AD_PHRASE = {
    "en": {"Sun": "ego and authority", "Moon": "mood and change", "Mars": "heat and haste", "Mercury": "deals and talk",
           "Jupiter": "growth and counsel", "Venus": "comfort and harmony", "Saturn": "delay and heavy responsibility",
           "Rahu": "illusion and chasing the unfamiliar", "Ketu": "detachment"},
    "es": {"Sun": "ego y autoridad", "Moon": "ánimo y cambio", "Mars": "calor y prisa", "Mercury": "tratos y charla",
           "Jupiter": "crecimiento y consejo", "Venus": "comodidad y armonía", "Saturn": "demora y mucha responsabilidad",
           "Rahu": "ilusión y perseguir lo desconocido", "Ketu": "desapego"},
    "pt": {"Sun": "ego e autoridade", "Moon": "humor e mudança", "Mars": "calor e pressa", "Mercury": "negócios e conversa",
           "Jupiter": "crescimento e conselho", "Venus": "conforto e harmonia", "Saturn": "atraso e muita responsabilidade",
           "Rahu": "ilusão e perseguir o desconhecido", "Ketu": "desapego"},
    "hinglish": {"Sun": "ahankaar aur adhikaar", "Moon": "mizaaj aur badlaav", "Mars": "garmi aur jaldbaazi", "Mercury": "sauda aur baatcheet",
                 "Jupiter": "vikas aur salah", "Venus": "aaram aur tal-mel", "Saturn": "deri aur bhaari zimmedaari",
                 "Rahu": "bhram aur anjaan ke peeche bhaagna", "Ketu": "vairagya"},
}
# the whole line: the big chapter with its end date, where the person is inside it, then what comes next
CHAPTER_TMPL = {"en": "{md} (to {md_end})", "es": "{md} (hasta el {md_end})", "pt": "{md} (até {md_end})", "hinglish": "{md} ({md_end} tak)"}
STRETCH_TMPL = {
    "first": {"en": "now in its first stretch: {ad}, until {ad_end}", "es": "ahora en su primer tramo: {ad}, hasta el {ad_end}",
              "pt": "agora no primeiro trecho: {ad}, até {ad_end}", "hinglish": "abhi iske pehle daur mein: {ad}, {ad_end} tak"},
    "last": {"en": "now in its last stretch: {ad}, until {ad_end}, when this chapter closes", "es": "ahora en su último tramo: {ad}, hasta el {ad_end}, cuando se cierra esta etapa",
             "pt": "agora no último trecho: {ad}, até {ad_end}, quando esta fase se encerra", "hinglish": "abhi iske aakhri daur mein: {ad}, {ad_end} tak, jab ye daur khatam hoga"},
    "mid": {"en": "now in a stretch of {ad}, until {ad_end}", "es": "ahora en un tramo de {ad}, hasta el {ad_end}",
            "pt": "agora num trecho de {ad}, até {ad_end}", "hinglish": "abhi {ad} ke daur mein, {ad_end} tak"},
}
NEXT_TMPL = {"en": "Next comes {md}.", "es": "Sigue {md}.", "pt": "Em seguida vem {md}.", "hinglish": "Aage {md} aata hai."}


EFFECT = {
    "en": {"Rahu": "Illusion is strong here: big promises look better than they are, and real opportunities get missed unless there is discipline.",
           "Ketu": "Detachment is strong here: interest fades, commitments get dropped and decisions go quiet.",
           "Saturn": "Delay and heavy responsibility: everything moves slower than planned and needs patience and structure.",
           "Mars": "Heat and haste: quick decisions and conflict, so act on a plan and not on impulse.",
           "Sun": "Ego and authority: clashes over who leads and who gets the credit.",
           "Moon": "Mood-driven: decisions follow feelings and change often.",
           "Mercury": "Deals and talk: good for contracts and ideas, with a risk of overthinking and mixed signals.",
           "Venus": "Comfort and harmony: good for working together, with a risk of indulgence and avoiding hard conversations.",
           "Jupiter": "Growth and good counsel: favorable, with a risk of overpromising."},
    "es": {"Rahu": "Aquí la ilusión es fuerte: las grandes promesas parecen mejores de lo que son y se pierden oportunidades reales si falta disciplina.",
           "Ketu": "Aquí el desapego es fuerte: el interés se apaga, los compromisos se sueltan y las decisiones se quedan en silencio.",
           "Saturn": "Demora y mucha responsabilidad: todo avanza más lento de lo planeado y pide paciencia y estructura.",
           "Mars": "Calor y prisa: decisiones rápidas y conflicto, así que actúa con un plan y no por impulso.",
           "Sun": "Ego y autoridad: choques sobre quién lidera y quién se lleva el crédito.",
           "Moon": "Guiado por el ánimo: las decisiones siguen los sentimientos y cambian a menudo.",
           "Mercury": "Tratos y charla: bueno para contratos e ideas, con riesgo de pensar demasiado y de señales mezcladas.",
           "Venus": "Comodidad y armonía: bueno para trabajar juntos, con riesgo de indulgencia y de evitar conversaciones difíciles.",
           "Jupiter": "Crecimiento y buen consejo: favorable, con riesgo de prometer de más."},
    "pt": {"Rahu": "Aqui a ilusão é forte: grandes promessas parecem melhores do que são e oportunidades reais se perdem sem disciplina.",
           "Ketu": "Aqui o desapego é forte: o interesse some, compromissos são largados e as decisões ficam em silêncio.",
           "Saturn": "Atraso e muita responsabilidade: tudo anda mais devagar que o planejado e pede paciência e estrutura.",
           "Mars": "Calor e pressa: decisões rápidas e conflito, então aja com um plano e não por impulso.",
           "Sun": "Ego e autoridade: choques sobre quem lidera e quem leva o crédito.",
           "Moon": "Guiado pelo humor: as decisões seguem os sentimentos e mudam com frequência.",
           "Mercury": "Negócios e conversa: bom para contratos e ideias, com risco de pensar demais e de sinais misturados.",
           "Venus": "Conforto e harmonia: bom para trabalhar junto, com risco de indulgência e de evitar conversas difíceis.",
           "Jupiter": "Crescimento e bom conselho: favorável, com risco de prometer demais."},
    "hinglish": {"Rahu": "Yahan bhram prabal hai: bade vaade asliyat se behtar dikhte hain aur anushasan na ho to asli mauke haath se nikal jaate hain.",
                 "Ketu": "Yahan vairagya prabal hai: ruchi ghat jaati hai, commitments chhoot jaate hain aur faisle thande pad jaate hain.",
                 "Saturn": "Deri aur bhaari zimmedaari: sab kuch plan se dheere chalta hai aur sabr aur dhaanche ki zaroorat hoti hai.",
                 "Mars": "Garmi aur jaldbaazi: tez faisle aur takraav, isliye plan par chalein, impulse par nahin.",
                 "Sun": "Ahankaar aur adhikaar: kaun lead kare aur credit kiska ho, is par takraav.",
                 "Moon": "Mizaaj se chalne wala: faisle bhaavna ke hisaab se hote aur badalte rehte hain.",
                 "Mercury": "Sauda aur baatcheet: contract aur ideas ke liye achha, par zyada sochne aur ulajhe signal ka khatra.",
                 "Venus": "Aaram aur tal-mel: saath kaam ke liye achha, par bhog-vilas aur kathin baat taalne ka khatra.",
                 "Jupiter": "Vikas aur achhi salah: anukool, par zyada vaade karne ka khatra."},
}


def _co():
    from antar_engine import career_mode as CM
    return CM


def _day(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _tone(md: Optional[str], ad: Optional[str]) -> str:
    t = TONE.get(ad or "", "steady")
    if TONE.get(md or "") == "clouded" and t in ("favorable", "steady"):
        return "testing"          # a good stretch inside a clouded chapter still needs structure
    return t


def season_at(chart: dict, vim_rows: list, on: date) -> Optional[dict]:
    """The running chapter (maha) and the stretch inside it (antar) on `on`:
    {md, ad, md_start, md_end, ad_start, ad_end(=ends), pos (first|mid|last), next_md, tone, heavy (= clouded)}.
    `chart` is unused here (kept for the callers)."""
    md = ad = next_md = None
    md_s = md_e = ad_s = ad_e = None
    rows = vim_rows or []
    for r in rows:
        lvl = str(r.get("level") or "").lower()
        s, e = _day(r.get("start_date") or r.get("start")), _day(r.get("end_date") or r.get("end"))
        if not (s and e and s <= on <= e):
            continue
        lord = r.get("lord_or_sign") or r.get("planet_or_sign")
        if lvl == "mahadasha":
            md, md_s, md_e = lord, s, e
        elif lvl in ("antardasha", "bhukti"):
            ad, ad_s, ad_e = lord, s, e
    if ad not in TONE or not ad_e:
        # the stretch rows are missing but the big chapter is known: say the chapter, not nothing
        if md in TONE and md_e:
            tone = TONE[md]
            return {"md": md, "ad": None, "md_start": md_s, "md_end": md_e, "ad_start": None, "ends": md_e, "pos": "mid",
                    "next_md": None, "tone": tone, "heavy": tone == "clouded"}
        return None
    if md_e:
        for r in rows:
            if str(r.get("level") or "").lower() == "mahadasha" and _day(r.get("start_date") or r.get("start")) == md_e:
                next_md = r.get("lord_or_sign") or r.get("planet_or_sign")
                break
    pos = "first" if md_s and ad_s and abs((ad_s - md_s).days) <= 1 else "last" if md_e and abs((ad_e - md_e).days) <= 1 else "mid"
    tone = _tone(md, ad)
    return {"md": md, "ad": ad, "md_start": md_s, "md_end": md_e, "ad_start": ad_s, "ends": ad_e, "pos": pos,
            "next_md": next_md, "tone": tone, "heavy": tone == "clouded"}


def describe(se: dict, lang: str = "en") -> dict:
    """Plain words for one person's running chapter: the big chapter with its end date, where they are inside it
    (first / middle / last stretch, with the stretch's end date) and, in the last stretch, what comes next; plus
    what the stretch does to a partnership now."""
    lang = CC.lang_of(lang)
    ends_label = C.day_label_y(se["ends"], lang)
    if not se.get("ad"):                      # chapter only (no stretch rows for this chart)
        label = CC.pick(CHAPTER_TMPL, lang).format(md=CC.pick(MD_PHRASE, lang)[se["md"]], md_end=ends_label)
        label = label[0].upper() + label[1:] + "."
        return {"label": label, "effect": CC.pick(EFFECT, lang)[se["md"]], "tone": se["tone"], "heavy": se["heavy"],
                "position": None, "ends": se["ends"].isoformat(), "ends_label": ends_label, "chapter_ends": se["md_end"].isoformat()}
    ad = CC.pick(AD_PHRASE, lang)[se["ad"]]
    stretch = CC.pick(STRETCH_TMPL[se.get("pos") or "mid"], lang).format(ad=ad, ad_end=ends_label)
    if se.get("md") in TONE and se.get("md_end"):
        chapter = CC.pick(CHAPTER_TMPL, lang).format(md=CC.pick(MD_PHRASE, lang)[se["md"]], md_end=C.day_label_y(se["md_end"], lang))
        label = f"{chapter}, {stretch}."
    else:
        label = stretch[0].upper() + stretch[1:] + "."
    if se.get("pos") == "last" and se.get("next_md") in TONE:
        label += " " + CC.pick(NEXT_TMPL, lang).format(md=CC.pick(MD_PHRASE, lang)[se["next_md"]])
    label = label[0].upper() + label[1:]
    return {"label": label, "effect": CC.pick(EFFECT, lang)[se["ad"]], "tone": se["tone"], "heavy": se["heavy"],
            "position": se.get("pos"), "ends": se["ends"].isoformat(), "ends_label": ends_label,
            "chapter_ends": se["md_end"].isoformat() if se.get("md_end") else None,
            "confidence": ({"level": se["confidence"]["level"], "line": se["confidence"]["line"]} if se.get("confidence") else None)}


def better_from(a: Tuple[dict, list], b: Tuple[dict, list], today: date, horizon_days: int = 1825) -> Optional[date]:
    """First day (stepping 15 days) on which NEITHER person is in a clouded stretch, or None within the horizon."""
    d = today
    while (d - today).days <= horizon_days:
        sa, sb = season_at(a[0], a[1], d), season_at(b[0], b[1], d)
        if sa and sb and not sa["heavy"] and not sb["heavy"]:
            return d
        d += timedelta(days=15)
    return None


# ── 3b. cross-check: the same moment read by two more timing systems ───────────────────────────
# Vimshottari (above) is the lead. Yogini (a Moon-nakshatra cycle, so partly correlated with it) and Jaimini chara
# (a sign-based cycle read through the soul and career karakas, which is independent of it) each vote on one thing:
# is this person in a heavy stretch right now? Agreement raises confidence; when neither confirms a clouded stretch it is
# noted in the person's line and the call carries a lower confidence. The lead system's call is NEVER overridden.
# Today only; never invents.
CHARA_HEAVY, CHARA_GOOD = -0.3, 0.3
# OFF on purpose. Measured over all 174 real charts with dasha rows (2026-10-08): chara reads heavy in 1% of charts (median
# strength +0.73; it grades how well a period DELIVERS, not whether judgment is clouded) and Yogini agrees with a clouded
# Vimshottari stretch in 3 of 39 cases against ~10 expected by chance. Confirmation would read "low" ~90% of the time and
# undercut the lead read for no reason. Re-enable only after the other systems are calibrated against their own question.
SHOW_CROSSCHECK = False
CONF_LINE = {
    "high": {"en": "Two other ways of reading the timeline point the same way.", "es": "Otras dos formas de leer la línea de tiempo apuntan en la misma dirección.",
             "pt": "Outras duas formas de ler a linha do tempo apontam na mesma direção.", "hinglish": "Timeline padhne ke do aur tareeke isi taraf ishara karte hain."},
    "medium_one": {"en": "One other way of reading the timeline points the same way.", "es": "Otra forma de leer la línea de tiempo apunta en la misma dirección.",
                   "pt": "Outra forma de ler a linha do tempo aponta na mesma direção.", "hinglish": "Timeline padhne ka ek aur tareeka isi taraf ishara karta hai."},
    "medium": {"en": "One other way of reading the timeline points the same way, one doesn't.", "es": "Una forma de leer la línea de tiempo apunta en la misma dirección y otra no.",
               "pt": "Uma forma de ler a linha do tempo aponta na mesma direção e outra não.", "hinglish": "Timeline padhne ka ek tareeka isi taraf ishara karta hai, ek nahin."},
    "low": {"en": "The other ways of reading the timeline don't confirm this, so hold it more lightly.",
            "es": "Las otras formas de leer la línea de tiempo no lo confirman, así que tómalo con más ligereza.",
            "pt": "As outras formas de ler a linha do tempo não confirmam isso, então leve com mais leveza.",
            "hinglish": "Timeline padhne ke baaki tareeke ise confirm nahin karte, isliye ise halke mein lein."},
    "split_clear": {"en": "Another way of reading the timeline sees a heavier stretch than this does, so take care.",
                    "es": "Otra forma de leer la línea de tiempo ve un tramo más pesado que este, así que ten cuidado.",
                    "pt": "Outra forma de ler a linha do tempo vê um trecho mais pesado que este, então tenha cuidado.",
                    "hinglish": "Timeline padhne ka ek aur tareeka ise zyada bhaari dekhta hai, isliye savdhaan rahein."},
}


def yogini_at(dashas: dict, on: date) -> Optional[dict]:
    """{lord, heavy, ends}: the running Yogini chapter (1 to 8 years) on `on`; None without rows."""
    for r in (dashas or {}).get("yogini") or []:
        if str(r.get("level") or r.get("type") or "").lower() != "mahadasha":
            continue
        s, e = _day(r.get("start_date") or r.get("start")), _day(r.get("end_date") or r.get("end"))
        if s and e and s <= on <= e:
            lord = r.get("lord_or_sign") or r.get("planet_or_sign")
            if lord in TONE:
                return {"lord": lord, "heavy": TONE[lord] == "clouded", "ends": e}
    return None


def chara_at(chart: dict, jaimini_data: Optional[dict], dashas: dict, on: date) -> Optional[dict]:
    """{strength, heavy, good}: the running Jaimini chara sign read through the soul and career karakas
    (antar_engine.chara_dasha.chara_activation); None when unavailable."""
    try:
        from antar_engine.chara_dasha import chara_activation
        li = ((chart or {}).get("lagna") or {}).get("sign_index")
        r = chara_activation(chart, jaimini_data or {}, dashas or {}, li if isinstance(li, int) else 0, on.isoformat())
        if not r.get("available"):
            return None
        st = float(r.get("strength") or 0.0)
        return {"strength": st, "heavy": st <= CHARA_HEAVY, "good": st >= CHARA_GOOD}
    except Exception:
        return None


def crosscheck(vim_heavy: bool, yogini: Optional[dict], chara: Optional[dict], lang: str = "en") -> Optional[dict]:
    """How many of the OTHER systems agree with the lead's heavy / not-heavy call. Returns None when neither other
    system is available. level: high (all agree) | medium (some) | low (none; only meaningful for a heavy call)."""
    lang = CC.lang_of(lang)
    votes = [v for v in ((yogini or {}).get("heavy") if yogini else None, (chara or {}).get("heavy") if chara else None) if v is not None]
    if not votes:
        return None
    agree = sum(1 for v in votes if v == vim_heavy)
    level = "high" if agree == len(votes) else "medium" if agree else "low"
    if level == "high" and len(votes) < 2:
        key = "medium_one"
    elif level == "high":
        key = "high"
    elif level == "medium":
        key = "medium"
    elif vim_heavy:
        key = "low"
    else:
        key = "split_clear"                      # lead says fine, the others see a heavy stretch
    return {"level": level, "agree": agree, "of": len(votes), "line": CC.pick(CONF_LINE[key], lang), "key": key}


def season_checked(chart: dict, vim_rows: list, dashas: dict, jaimini_data: Optional[dict], on: date, lang: str = "en") -> Optional[dict]:
    """The lead season (season_at) plus the cross-check as `confidence`. The lead's tone and call are never changed."""
    se = season_at(chart, vim_rows, on)
    if not se:
        return None
    if not SHOW_CROSSCHECK:
        return dict(se, confidence=None)
    cc = crosscheck(se["heavy"], yogini_at(dashas, on), chara_at(chart, jaimini_data, dashas, on), lang)
    return dict(se, confidence=cc)


# ── 2. partnership lean ──────────────────────────────────────────────────────────────────────
PARTNER_MIN, SOLO_MAX = 1.5, -1.5          # lean = partner points minus solo points; a lean needs a clear margin
SUPPORTIVE_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
REASON = {
    "p_strong7": {"en": "A real appetite and capacity for partnership.", "es": "Un verdadero apetito y capacidad para las alianzas.",
                  "pt": "Um verdadeiro apetite e capacidade para parcerias.", "hinglish": "Saajhedaari ke liye sachchi ruchi aur kshamata."},
    "p_good7": {"en": "Partnerships tend to feed the work rather than drain it.", "es": "Las alianzas suelen alimentar el trabajo en lugar de agotarlo.",
                "pt": "As parcerias costumam alimentar o trabalho em vez de drená-lo.", "hinglish": "Saajhedaari aam taur par kaam ko badhati hai, thakati nahin."},
    "p_net11": {"en": "Works well through networks and other people.", "es": "Funciona bien a través de redes y otras personas.",
                "pt": "Funciona bem por meio de redes e de outras pessoas.", "hinglish": "Network aur doosre logon ke zariye achha kaam karta hai."},
    "n_bad7": {"en": "Partnership tends to be where friction or hidden costs show up.", "es": "La alianza suele ser donde aparecen la fricción o los costos ocultos.",
               "pt": "A parceria costuma ser onde aparecem o atrito ou os custos ocultos.", "hinglish": "Saajhedaari mein aam taur par takraav ya chhupe kharche aate hain."},
    "s_self3": {"en": "Launches and drives things personally.", "es": "Lanza y mueve las cosas personalmente.",
                "pt": "Lança e conduz as coisas pessoalmente.", "hinglish": "Cheezein khud shuru karta aur chalata hai."},
    "s_owner": {"en": "Leans towards owning and running their own thing.", "es": "Se inclina por ser dueño y dirigir lo propio.",
                "pt": "Inclina-se a ser dono e a comandar o que é seu.", "hinglish": "Apna khud ka kaam chalane aur uska malik banne ki taraf jhukta hai."},
    "s_fused": {"en": "Work and identity are fused, so the final say matters a lot.", "es": "El trabajo y la identidad están fundidos, así que la última palabra importa mucho.",
                "pt": "Trabalho e identidade estão fundidos, então a palavra final importa muito.", "hinglish": "Kaam aur pehchaan ek ho gaye hain, isliye antim faisla bahut mayne rakhta hai."},
}
LEAN_LABEL = {
    "partner": {"en": "Built for partnership", "es": "Hecho para las alianzas", "pt": "Feito para parcerias", "hinglish": "Saajhedaari ke liye bana"},
    "either": {"en": "Could go either way", "es": "Puede ir en cualquier dirección", "pt": "Pode ir para qualquer lado", "hinglish": "Dono taraf ja sakta hai"},
    "solo": {"en": "Better leading alone", "es": "Mejor liderando en solitario", "pt": "Melhor liderando sozinho", "hinglish": "Akele netritva ke liye behtar"},
}


def partnership_lean(chart: dict) -> dict:
    """{lean: partner|either|solo, partner_pts, solo_pts, reasons:[keys]} from the chart. Never raises."""
    CM = _co()
    out = {"lean": "either", "partner_pts": 0.0, "solo_pts": 0.0, "reasons": []}
    try:
        p = s = 0.0
        why: List[str] = []
        l7, l11, l3, l10, l1 = (CM._lord_of(chart, h) for h in (7, 11, 3, 10, 1))
        h7 = CM._house_of(chart, l7)
        if CM._strength(chart, l7) >= 1.0:
            p += 1.5; why.append("p_strong7")
        if h7 in SUPPORTIVE_HOUSES:
            p += 1.0; why.append("p_good7")
        if CM._strength(chart, l11) >= 1.0:
            p += 1.0; why.append("p_net11")
        if h7 in (6, 8, 12):
            p -= 1.5; why.append("n_bad7")
        if CM._strength(chart, l3) >= 1.0:
            s += 1.0; why.append("s_self3")
        m = CM.career_mode(chart)
        if m.get("ownership") == "owned" and m.get("mode") in ("venture", "business"):
            s += 1.0; why.append("s_owner")
        if CM._house_of(chart, l10) in (1, 10) or CM._house_of(chart, l1) in (1, 10):
            s += 1.0; why.append("s_fused")
        net = p - s
        out.update(lean="partner" if net >= PARTNER_MIN else "solo" if net <= SOLO_MAX else "either",
                   partner_pts=round(p, 2), solo_pts=round(s, 2), reasons=why)
    except Exception:
        pass
    return out


# ── the verdict ──────────────────────────────────────────────────────────────────────────────
VERDICT = {
    "full_partners": {
        "title": {"en": "Built to partner", "es": "Hechos para asociarse", "pt": "Feitos para se associar", "hinglish": "Saath mein kaam ke liye bane"},
        "line": {"en": "You two are built to partner. Go in as full partners, with who owns what written down.",
                 "es": "Ustedes están hechos para asociarse. Entren como socios plenos, con lo que le toca a cada uno por escrito.",
                 "pt": "Vocês são feitos para se associar. Entrem como sócios plenos, com o que cabe a cada um por escrito.",
                 "hinglish": "Aap dono saath mein kaam karne ke liye bane hain. Poore saajhedaar ban kar chalein, kaun kya sambhalega likhit mein tay karke."},
    },
    "partners_with_lanes": {
        "title": {"en": "Partners, with clear lanes", "es": "Socios, con carriles claros", "pt": "Sócios, com faixas claras", "hinglish": "Saajhedaar, saaf zimmedaariyon ke saath"},
        "line": {"en": "You can partner, but only with clear lanes. Decide who owns what, and who has the final say, before anything else.",
                 "es": "Pueden asociarse, pero solo con carriles claros. Decidan quién se encarga de qué y quién tiene la última palabra, antes que nada.",
                 "pt": "Vocês podem se associar, mas só com faixas claras. Decidam quem cuida de quê e quem tem a palavra final, antes de tudo.",
                 "hinglish": "Aap saajhedaari kar sakte hain, lekin saaf zimmedaariyon ke saath hi. Sabse pehle tay karein ki kaun kya sambhalega aur antim faisla kiska hoga."},
    },
    "founder_plus_advisor": {
        "title": {"en": "One founder, one advisor", "es": "Un fundador, un asesor", "pt": "Um fundador, um conselheiro", "hinglish": "Ek founder, ek salahkaar"},
        "line": {"en": "{lead} is better built to lead this alone. Keep {other} close as a consultant or advisor and give equity for the work done, on a task or vesting basis, not as a co-founder.",
                 "es": "{lead} está mejor hecho para liderar esto en solitario. Mantengan a {other} cerca como consultor o asesor y denle participación por el trabajo hecho, por tarea o con consolidación gradual, no como cofundador.",
                 "pt": "{lead} é mais bem preparado para liderar isso sozinho. Mantenham {other} por perto como consultor ou conselheiro e deem participação pelo trabalho feito, por tarefa ou com aquisição gradual, não como cofundador.",
                 "hinglish": "{lead} ise akele chalane ke liye zyada behtar bana hai. {other} ko consultant ya salahkaar ki tarah paas rakhein aur kiye gaye kaam ke badle task ya vesting ke aadhar par equity dein, co-founder ki tarah nahin."},
    },
    "solo_contract": {
        "title": {"en": "One owner, work by contract", "es": "Un dueño, trabajo por contrato", "pt": "Um dono, trabalho por contrato", "hinglish": "Ek malik, kaam anubandh par"},
        "line": {"en": "Neither of you leans towards a full partnership. Run it with one owner and work together by contract, with clear scope and payment.",
                 "es": "Ninguno de los dos se inclina por una sociedad plena. Dirijan esto con un solo dueño y trabajen juntos por contrato, con alcance y pago claros.",
                 "pt": "Nenhum dos dois se inclina a uma sociedade plena. Conduzam isso com um único dono e trabalhem juntos por contrato, com escopo e pagamento claros.",
                 "hinglish": "Aap mein se koi poori saajhedaari ki taraf nahin jhukta. Ek malik ke saath chalayein aur anubandh par saath kaam karein, kaam ki seema aur bhugtan saaf rakhkar."},
    },
}
PHASE_LINE = {
    "clear": {"en": "A workable time to formalize: neither of you is in a clouded or testing stretch.",
              "es": "Un buen momento para formalizar: ninguno de los dos está en un tramo nublado ni de prueba.",
              "pt": "Um bom momento para formalizar: nenhum dos dois está num trecho nublado ou de prova.",
              "hinglish": "Formalize karne ka achha samay: aap dono mein se koi dhundhle ya pariksha wale daur mein nahin hai."},
    "testing": {"en": "Possible, with structure. At least one of you is in a testing stretch (delay, heat or ego), so put roles, money and decisions in writing before you start.",
                "es": "Posible, con estructura. Al menos uno está en un tramo de prueba (demora, calor o ego), así que pongan por escrito los roles, el dinero y las decisiones antes de empezar.",
                "pt": "Possível, com estrutura. Pelo menos um está num trecho de prova (atraso, calor ou ego), então coloquem por escrito os papéis, o dinheiro e as decisões antes de começar.",
                "hinglish": "Possible, structure ke saath. Aap mein se kam se kam ek pariksha wale daur (deri, garmi ya ahankaar) mein hai, isliye shuru karne se pehle roles, paise aur faisle likhit mein rakhein."},
    "one_heavy": {"en": "Not now. {name} is in a clouded stretch until {until}. {effect} Hold off on formalizing and start with a small trial project.",
                  "es": "Ahora no. {name} está en un tramo nublado hasta el {until}. {effect} Esperen para formalizar y empiecen con un pequeño proyecto de prueba.",
                  "pt": "Agora não. {name} está num trecho nublado até {until}. {effect} Esperem para formalizar e comecem com um pequeno projeto de teste.",
                  "hinglish": "Abhi nahin. {name} {until} tak dhundhle daur mein hai. {effect} Formalize karna rok dein aur ek chhote trial project se shuru karein."},
    "both_heavy": {"en": "Not now. You are both in clouded stretches, where judgment on big commitments gets unreliable and deals look better than they are. Wait, and test with something small.",
                   "es": "Ahora no. Los dos están en tramos nublados, donde el criterio sobre grandes compromisos se vuelve poco confiable y los tratos parecen mejores de lo que son. Esperen y prueben con algo pequeño.",
                   "pt": "Agora não. Os dois estão em trechos nublados, em que o julgamento sobre grandes compromissos fica pouco confiável e os negócios parecem melhores do que são. Esperem e testem com algo pequeno.",
                   "hinglish": "Abhi nahin. Aap dono dhundhle daur mein hain, jahan bade commitments par nirnay bharosemand nahin rehta aur sauda asliyat se behtar dikhta hai. Ruk jaayein aur kuch chhota karke parakhein."},
    "better": {"en": "What doesn't work now can work later: from {on} neither of you is in a clouded stretch.",
               "es": "Lo que no funciona ahora puede funcionar después: desde el {on} ninguno de los dos está en un tramo nublado.",
               "pt": "O que não funciona agora pode funcionar depois: a partir de {on} nenhum dos dois está num trecho nublado.",
               "hinglish": "Jo abhi nahin chalta wo baad mein chal sakta hai: {on} se aap dono mein se koi dhundhle daur mein nahin hoga."},
}
CALL = {
    "not_now": {"en": "Not now", "es": "Ahora no", "pt": "Agora não", "hinglish": "Abhi nahin"},
    "with_structure": {"en": "Possible, with structure", "es": "Posible, con estructura", "pt": "Possível, com estrutura", "hinglish": "Possible, structure ke saath"},
    "good_now": {"en": "A good time", "es": "Un buen momento", "pt": "Um bom momento", "hinglish": "Achha samay"},
}
TEXTS = (TEMPERAMENT_EN,)       # English-only trait lines are translated by the route (like the yoga effects)
COPY_TABLES = (CONF_LINE["high"], CONF_LINE["medium_one"], CONF_LINE["medium"], CONF_LINE["low"], CONF_LINE["split_clear"], MD_PHRASE, AD_PHRASE, CHAPTER_TMPL, STRETCH_TMPL["first"], STRETCH_TMPL["last"], STRETCH_TMPL["mid"], NEXT_TMPL, EFFECT, {k: v for k, v in REASON.items()}, LEAN_LABEL,
               {k: v["title"] for k, v in VERDICT.items()}, {k: v["line"] for k, v in VERDICT.items()}, PHASE_LINE, CALL)


def phase(a: Optional[dict], b: Optional[dict], a_name: str, b_name: str, a_pack: Tuple[dict, list], b_pack: Tuple[dict, list],
          lang: str, today: date, family: str = "work") -> dict:
    """The pair's chapters now -> a direct call (not now / possible with structure / a good time) + the first clear date.
    a / b are season_at results (or None)."""
    lang = CC.lang_of(lang)
    if family == "close":
        from antar_engine import circle_lens as _L
        lines, calls = _L.PHASE_CLOSE, _L.CALL_CLOSE
    else:
        lines, calls = PHASE_LINE, CALL
    ha, hb = bool(a and a["heavy"]), bool(b and b["heavy"])
    testing = any(x and x["tone"] == "testing" for x in (a, b))
    status = "both_heavy" if ha and hb else "one_heavy" if ha or hb else "testing" if testing else "clear"
    if status == "one_heavy":
        who, se = (a_name, a) if ha else (b_name, b)
        d = describe(se, lang)
        line = CC.pick(lines["one_heavy"], lang).format(name=who, until=d["ends_label"], effect=d["effect"])
    else:
        line = CC.pick(lines[status], lang)
    call = {"both_heavy": "not_now", "one_heavy": "not_now", "testing": "with_structure", "clear": "good_now"}[status]
    better = None
    if status in ("both_heavy", "one_heavy"):
        d = better_from(a_pack, b_pack, today)
        if d:
            better = {"on": d.isoformat(), "label": C.day_label_y(d, lang),
                      "line": CC.pick(lines["better"], lang).format(on=C.day_label_y(d, lang))}
    conf = None
    order = {"low": 0, "medium": 1, "high": 2}
    for se in (a, b):
        c = (se or {}).get("confidence")
        if se and se.get("heavy") and c and (conf is None or order[c["level"]] < order[conf["level"]]):
            conf = {"level": c["level"], "line": c["line"]}
    return {"status": status, "call": call, "call_title": CC.pick(calls[call], lang), "line": line, "better": better,
            "confidence": conf}


def verdict(a: dict, b: dict, complementary: bool, lang: str = "en") -> dict:
    """a, b: {first_name, lean}. Chooses the structure. `complementary` = one driver + one anchor."""
    lang = CC.lang_of(lang)
    la, lb = a["lean"], b["lean"]
    if la == "solo" and lb == "solo":
        key, lead, other = "solo_contract", None, None
    elif "solo" in (la, lb):
        lead, other = (a, b) if la == "solo" else (b, a)
        key = "founder_plus_advisor"
    elif la == lb == "partner" and complementary:
        key, lead, other = "full_partners", None, None
    else:
        key, lead, other = "partners_with_lanes", None, None
    v = VERDICT[key]
    line = CC.pick(v["line"], lang)
    if lead:
        line = line.format(lead=lead["first_name"], other=other["first_name"])
    return {"key": key, "title": CC.pick(v["title"], lang), "line": line,
            "lead": lead["first_name"] if lead else None, "other": other["first_name"] if other else None}
