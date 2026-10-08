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


# ── 3. seasons ───────────────────────────────────────────────────────────────────────────────
THEMES = ("expansion", "gains", "action", "partnership", "initiative", "consolidation", "friction", "transformation", "release")
HEAVY = {"friction", "transformation", "release"}
THEME_LABEL = {
    "en": {"expansion": "a season of expansion", "gains": "a season of building gains", "action": "a season of action and visibility",
           "partnership": "a season of partnership", "initiative": "a season of taking initiative", "consolidation": "a season of consolidating",
           "friction": "a season of effort and friction", "transformation": "a season of transformation", "release": "a season of letting go"},
    "es": {"expansion": "una etapa de expansión", "gains": "una etapa de construir ganancias", "action": "una etapa de acción y visibilidad",
           "partnership": "una etapa de alianzas", "initiative": "una etapa de tomar la iniciativa", "consolidation": "una etapa de consolidar",
           "friction": "una etapa de esfuerzo y fricción", "transformation": "una etapa de transformación", "release": "una etapa de soltar"},
    "pt": {"expansion": "uma fase de expansão", "gains": "uma fase de construir ganhos", "action": "uma fase de ação e visibilidade",
           "partnership": "uma fase de parcerias", "initiative": "uma fase de tomar a iniciativa", "consolidation": "uma fase de consolidar",
           "friction": "uma fase de esforço e atrito", "transformation": "uma fase de transformação", "release": "uma fase de soltar"},
    "hinglish": {"expansion": "vistaar ka daur", "gains": "laabh banane ka daur", "action": "karm aur drishyata ka daur",
                 "partnership": "saajhedaari ka daur", "initiative": "pehal karne ka daur", "consolidation": "majboot karne ka daur",
                 "friction": "mehnat aur takraav ka daur", "transformation": "badlaav ka daur", "release": "chhodne ka daur"},
}
_POS = {1: 1.0, 5: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 2: 1.0, 7: 0.5, 3: 0.5, 4: 0.5}
_POS_THEME = {1: "expansion", 5: "expansion", 9: "expansion", 11: "gains", 2: "gains", 10: "action", 7: "partnership", 3: "initiative", 4: "consolidation"}
_HEAVY_W = {8: 1.5, 12: 1.5, 6: 1.0}
_HEAVY_THEME = {8: "transformation", 12: "release", 6: "friction"}
HEAVY_NET = -0.5


def _co():
    from antar_engine import career_mode as CM
    return CM


def lord_theme(chart: dict, planet: str) -> Optional[str]:
    """The season a running sub-period lord brings, from the houses it rules (nodes act through the lord of
    the sign they sit in). net = +1 per supportive house (0.5 for 7/3/4), -1.5 for 8/12, -1 for 6, +-0.5 for
    a strong / weak planet; net <= -0.5 -> the heaviest house's theme, otherwise the best supportive theme."""
    CM = _co()
    try:
        p = planet
        if p in ("Rahu", "Ketu"):
            p = CM._dispositor(chart, p) or p
        ruled = [h for h in range(1, 13) if CM._lord_of(chart, h) == p]
        if not ruled:
            return None
        net = sum(_POS.get(h, 0) for h in ruled) - sum(_HEAVY_W.get(h, 0) for h in ruled)
        st = CM._strength(chart, planet)
        net += 0.5 if st >= 1.0 else -0.5 if st <= -1.0 else 0.0
        heavy = [h for h in ruled if h in _HEAVY_W]
        if net <= HEAVY_NET and heavy:
            return _HEAVY_THEME[max(heavy, key=lambda h: _HEAVY_W[h])]
        pos = [h for h in ruled if h in _POS]
        if pos:
            return _POS_THEME[max(pos, key=lambda h: _POS[h])]
        return _HEAVY_THEME[max(heavy, key=lambda h: _HEAVY_W[h])] if heavy else None
    except Exception:
        return None


def _day(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def season_at(chart: dict, vim_rows: list, on: date) -> Optional[dict]:
    """{theme, ends (date), heavy}: the sub-period running on `on`."""
    for r in vim_rows or []:
        if str(r.get("level") or "").lower() not in ("antardasha", "bhukti"):
            continue
        s, e = _day(r.get("start_date") or r.get("start")), _day(r.get("end_date") or r.get("end"))
        if s and e and s <= on <= e:
            th = lord_theme(chart, r.get("lord_or_sign") or r.get("planet_or_sign") or "")
            return {"theme": th, "ends": e, "heavy": th in HEAVY} if th else None
    return None


def better_from(a: Tuple[dict, list], b: Tuple[dict, list], today: date, horizon_days: int = 1825) -> Optional[date]:
    """First day (stepping 15 days) on which NEITHER person is in a heavy season, or None within the horizon."""
    d = today
    while (d - today).days <= horizon_days:
        sa, sb = season_at(a[0], a[1], d), season_at(b[0], b[1], d)
        if sa and sb and not sa["heavy"] and not sb["heavy"]:
            return d
        d += timedelta(days=15)
    return None


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
    "clear": {"en": "Neither of you is in a heavy season right now, so this is a workable time to formalize.",
              "es": "Ninguno de los dos está en una etapa pesada ahora, así que es un buen momento para formalizar.",
              "pt": "Nenhum dos dois está numa fase pesada agora, então é um bom momento para formalizar.",
              "hinglish": "Abhi aap dono mein se koi bhaari daur mein nahin hai, isliye formalize karne ka achha samay hai."},
    "one_heavy": {"en": "{name} is in {theme} until {until}. Go step by step: start with a trial project before you formalize.",
                  "es": "{name} está en {theme} hasta el {until}. Vayan paso a paso: empiecen con un proyecto de prueba antes de formalizar.",
                  "pt": "{name} está em {theme} até {until}. Vão passo a passo: comecem com um projeto de teste antes de formalizar.",
                  "hinglish": "{name} {until} tak {theme} mein hai. Kadam-dar-kadam chalein: formalize karne se pehle ek trial project se shuru karein."},
    "both_heavy": {"en": "You are both in heavy seasons right now, so this is not the moment to formalize.",
                   "es": "Los dos están en etapas pesadas ahora, así que no es el momento de formalizar.",
                   "pt": "Os dois estão em fases pesadas agora, então não é o momento de formalizar.",
                   "hinglish": "Abhi aap dono bhaari daur mein hain, isliye formalize karne ka ye samay nahin hai."},
    "better": {"en": "What doesn't work now can work later: from {on} neither of you is in a heavy season.",
               "es": "Lo que no funciona ahora puede funcionar después: desde el {on} ninguno de los dos está en una etapa pesada.",
               "pt": "O que não funciona agora pode funcionar depois: a partir de {on} nenhum dos dois está numa fase pesada.",
               "hinglish": "Jo abhi nahin chalta wo baad mein chal sakta hai: {on} se aap dono mein se koi bhaari daur mein nahin hoga."},
}
TEXTS = (TEMPERAMENT_EN,)       # English-only trait lines are translated by the route (like the yoga effects)
COPY_TABLES = (THEME_LABEL, {k: v for k, v in REASON.items()}, LEAN_LABEL,
               {k: v["title"] for k, v in VERDICT.items()}, {k: v["line"] for k, v in VERDICT.items()}, PHASE_LINE)


def phase(a: dict, b: dict, a_name: str, b_name: str, a_pack: Tuple[dict, list], b_pack: Tuple[dict, list],
          lang: str, today: date) -> dict:
    """The pair's seasons now and the first clear stretch. a / b are season dicts (or None)."""
    lang = CC.lang_of(lang)
    lab = CC.pick(THEME_LABEL, lang)
    ha, hb = bool(a and a["heavy"]), bool(b and b["heavy"])
    status = "both_heavy" if ha and hb else "one_heavy" if ha or hb else "clear"
    if status == "one_heavy":
        who, se = (a_name, a) if ha else (b_name, b)
        line = CC.pick(PHASE_LINE["one_heavy"], lang).format(name=who, theme=lab[se["theme"]], until=C.day_label_y(se["ends"], lang))
    else:
        line = CC.pick(PHASE_LINE[status], lang)
    better = None
    if status != "clear":
        d = better_from(a_pack, b_pack, today)
        if d:
            better = {"on": d.isoformat(), "label": C.day_label_y(d, lang),
                      "line": CC.pick(PHASE_LINE["better"], lang).format(on=C.day_label_y(d, lang))}
    return {"status": status, "line": line, "better": better}


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
