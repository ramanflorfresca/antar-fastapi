"""
antar_engine/circle_lens.py - the lens framework: one spec per relation type for the pair brief.

A pair's brief (circle_brief) reads the SAME two things for every relation: each person's running chapter
(circle_fit.season_at) and the pair's dated windows (circle_overlap). What differs by relation is what the bond
lives on, what a good or strained stretch means for it, which structure can be recommended and what to avoid:

  family        relations                           bond lives on (per person's ROLE in the bond)
  work_partner  cofounder, business                 partnership lean (circle_fit.partnership_lean), 4 structures
  work_hier     employee, boss                      work and service (6th, 10th, 11th), authority (10th, 11th, 1st)
  counsel       advisor                             guidance (9th, 5th) and Jupiter
  close         spouse, romantic, parent, child,    marriage 7th/Venus, romance 7th+5th, parent 5th/Jupiter,
                sibling, family, friend             child 4th+9th/Moon+Sun, sibling 3rd+11th/Mars, family 4th+2nd/Moon,
                                                    friend 11th+3rd/Mercury+Venus

Each person's role in the bond is what the OTHER is to them, inverted for the viewer (the viewer of a 'child'
relation is the parent). A person's capacity for the bond is a descriptive lean from their own chart:
points per significator house lord (+1 strong, +0.5 well placed, -1 placed in a strain house, -0.5 weak) and per karaka
(+1 strong, -0.75 weak, -0.5 in a strain house); net >= 2.0 'strong', <= -1.5 'strained', else 'steady'. Thresholds
are written down and NOT validated against outcomes; this describes how supported a bond is, never whether it lasts.
No chart term reaches the user. Deterministic. en / es / pt / hinglish (Hindi falls back to English).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from antar_engine import circle_copy as CC

SUPPORTIVE = {1, 2, 4, 5, 7, 9, 10, 11}
STRAIN = {6, 8, 12}
STRONG_MIN, STRAINED_MAX = 2.0, -1.5

# per ROLE in the bond: significator houses, karakas, the plain area noun key
ROLE_SPEC = {
    "spouse": {"houses": (7, 2), "karakas": ("Venus", "Jupiter"), "area": "marriage"},
    "romantic": {"houses": (7, 5), "karakas": ("Venus",), "area": "romance"},
    "parent": {"houses": (5,), "karakas": ("Jupiter",), "area": "children"},
    "child": {"houses": (4, 9), "karakas": ("Moon", "Sun"), "area": "home"},
    "sibling": {"houses": (3, 11), "karakas": ("Mars",), "area": "siblings"},
    "family": {"houses": (4, 2), "karakas": ("Moon",), "area": "family"},
    "friend": {"houses": (11, 3), "karakas": ("Mercury", "Venus"), "area": "friends"},
    "employee": {"houses": (6, 10), "karakas": ("Saturn",), "area": "work"},
    "boss": {"houses": (10, 11, 1), "karakas": ("Sun", "Saturn"), "area": "authority"},
    "advisor": {"houses": (9, 5), "karakas": ("Jupiter",), "area": "counsel"},
    "advisee": {"houses": (9, 5), "karakas": ("Jupiter",), "area": "guidance"},
}
# lens (what the OTHER is to the viewer) -> family, the pair-page topics that matter, and the phase wording family
LENSES = {
    "cofounder": {"family": "work_partner", "topics": ("money", "business", "career"), "phase": "work"},
    "business": {"family": "work_partner", "topics": ("money", "business"), "phase": "work"},
    "employee": {"family": "work_hier", "topics": ("career", "money"), "phase": "work"},
    "boss": {"family": "work_hier", "topics": ("career", "money"), "phase": "work"},
    "advisor": {"family": "counsel", "topics": ("career", "money", "peace"), "phase": "work"},
    "advisee": {"family": "counsel", "topics": ("career", "money", "peace"), "phase": "work"},      # the other side of advisor
    "spouse": {"family": "close", "topics": ("love", "family", "money"), "phase": "close"},
    "romantic": {"family": "close", "topics": ("love", "peace"), "phase": "close"},
    "parent": {"family": "close", "topics": ("family", "health", "peace"), "phase": "close"},
    "child": {"family": "close", "topics": ("family", "health", "peace"), "phase": "close"},
    "sibling": {"family": "close", "topics": ("family", "peace"), "phase": "close"},
    "family": {"family": "close", "topics": ("family", "peace"), "phase": "close"},
    "friend": {"family": "close", "topics": ("peace", "love"), "phase": "close"},
}


def lens_spec(relation: Optional[str]) -> Optional[dict]:
    return LENSES.get(str(relation or ""))


def roles_for(relation: str):
    """(viewer's role, other's role) in the bond, from what the other is to the viewer."""
    return CC.inverse_relation(relation), relation


# ── copy ─────────────────────────────────────────────────────────────────────────────────────
AREA = {
    "en": {"marriage": "Marriage and partnership", "romance": "Romance and commitment", "children": "Children and creativity", "home": "Home and parents",
           "siblings": "Siblings and courage", "family": "Home and family", "friends": "Friendships and networks", "work": "Work and service",
           "authority": "Authority and leadership", "counsel": "Counsel and guidance", "guidance": "Learning and guidance"},
    "es": {"marriage": "Matrimonio y pareja", "romance": "Romance y compromiso", "children": "Hijos y creatividad", "home": "Hogar y padres",
           "siblings": "Hermanos y coraje", "family": "Hogar y familia", "friends": "Amistades y redes", "work": "Trabajo y servicio",
           "authority": "Autoridad y liderazgo", "counsel": "Consejo y guía", "guidance": "Aprendizaje y guía"},
    "pt": {"marriage": "Casamento e parceria", "romance": "Romance e compromisso", "children": "Filhos e criatividade", "home": "Lar e pais",
           "siblings": "Irmãos e coragem", "family": "Lar e família", "friends": "Amizades e redes", "work": "Trabalho e serviço",
           "authority": "Autoridade e liderança", "counsel": "Conselho e orientação", "guidance": "Aprendizado e orientação"},
    "hinglish": {"marriage": "Vivaah aur saajhedaari", "romance": "Pyaar aur pratibaddhta", "children": "Bachche aur rachnatmakta", "home": "Ghar aur mata-pita",
                 "siblings": "Bhai-behen aur himmat", "family": "Ghar aur parivaar", "friends": "Dosti aur network", "work": "Kaam aur seva",
                 "authority": "Adhikaar aur netritva", "counsel": "Salah aur margdarshan", "guidance": "Seekhna aur margdarshan"},
}
REASON = {
    "h_strong": {"en": "{area}: this part of life is strong here.", "es": "{area}: esta parte de la vida es fuerte aquí.",
                 "pt": "{area}: esta parte da vida é forte aqui.", "hinglish": "{area}: jeevan ka ye hissa yahan mazboot hai."},
    "h_strain": {"en": "{area}: this part of life tends to carry strain.", "es": "{area}: esta parte de la vida suele cargar tensión.",
                 "pt": "{area}: esta parte da vida costuma carregar tensão.", "hinglish": "{area}: jeevan ka ye hissa aksar tanav lekar chalta hai."},
    "h_mixed": {"en": "{area}: strong in some ways, strained in others.", "es": "{area}: fuerte en algunos aspectos, tenso en otros.",
                "pt": "{area}: forte em alguns aspectos, tenso em outros.", "hinglish": "{area}: kuch maamlon mein mazboot, kuch mein tanav bhara."},
    "k_strong": {"en": "Naturally supportive in this kind of bond.", "es": "Naturalmente solidario en este tipo de vínculo.",
                 "pt": "Naturalmente solidário neste tipo de vínculo.", "hinglish": "Is tarah ke rishte mein svabhaavik roop se sahyogi."},
    "k_weak": {"en": "May need extra effort to show up well in this kind of bond.", "es": "Puede necesitar un esfuerzo extra para estar presente en este tipo de vínculo.",
               "pt": "Pode precisar de um esforço extra para estar presente neste tipo de vínculo.", "hinglish": "Is tarah ke rishte mein achhe se nibhane ke liye ek zyada koshish chahiye ho sakti hai."},
}
LEVEL_LABEL = {
    "strong": {"en": "Well supported", "es": "Bien respaldado", "pt": "Bem amparado", "hinglish": "Achhi tarah sahaara mila"},
    "steady": {"en": "Steady", "es": "Estable", "pt": "Estável", "hinglish": "Sthir"},
    "strained": {"en": "Needs extra care", "es": "Necesita cuidado extra", "pt": "Precisa de cuidado extra", "hinglish": "Ek zyada dhyaan chahiye"},
}
VERDICT_TITLE = {
    "natural_fit": {"en": "A natural fit", "es": "Un encaje natural", "pt": "Um encaixe natural", "hinglish": "Svabhaavik mel"},
    "workable_with_care": {"en": "Workable, with care", "es": "Viable, con cuidado", "pt": "Viável, com cuidado", "hinglish": "Chal sakta hai, dhyaan ke saath"},
    "needs_patience": {"en": "Needs patience", "es": "Necesita paciencia", "pt": "Precisa de paciência", "hinglish": "Dhairya chahiye"},
}
VERDICT_LINE = {
    "work_hier": {
        "natural_fit": {"en": "This looks like a good working fit. Keep expectations clear and review them from time to time.",
                        "es": "Esto parece un buen encaje de trabajo. Mantengan las expectativas claras y revísenlas de vez en cuando.",
                        "pt": "Isto parece um bom encaixe de trabalho. Mantenham as expectativas claras e revisem de tempos em tempos.",
                        "hinglish": "Ye kaam ke liye achha mel lagta hai. Apekshayein saaf rakhein aur samay-samay par dekhte rahein."},
        "workable_with_care": {"en": "This can work with clear expectations. Agree on scope, reporting and how disagreements are handled, in writing.",
                               "es": "Esto puede funcionar con expectativas claras. Acuerden por escrito el alcance, los reportes y cómo se manejan los desacuerdos.",
                               "pt": "Isto pode funcionar com expectativas claras. Combinem por escrito o escopo, os relatórios e como lidar com discordâncias.",
                               "hinglish": "Saaf apekshaon ke saath ye chal sakta hai. Kaam ki seema, reporting aur asahmati sambhalne ka tareeka likhit mein tay karein."},
        "needs_patience": {"en": "This is a strained fit right now. Keep it formal, with a short term and a defined scope, and review it early.",
                           "es": "Es un encaje tenso por ahora. Manténganlo formal, con plazo corto y alcance definido, y revísenlo pronto.",
                           "pt": "É um encaixe tenso por enquanto. Mantenham formal, com prazo curto e escopo definido, e revisem logo.",
                           "hinglish": "Abhi ye tanav bhara mel hai. Ise aupcharik rakhein, chhoti avadhi aur tay seema ke saath, aur jaldi dobara dekhein."},
    },
    "counsel": {
        "natural_fit": {"en": "A good counsel fit: the advice should land and be used.",
                        "es": "Un buen encaje de consejo: la orientación debería llegar y usarse.",
                        "pt": "Um bom encaixe de conselho: a orientação deve chegar e ser usada.",
                        "hinglish": "Salah ke liye achha mel: salah asar karegi aur kaam aayegi."},
        "workable_with_care": {"en": "Useful, with limits: take the advice as input, and decide for yourself.",
                               "es": "Útil, con límites: toma el consejo como un insumo y decide por ti mismo.",
                               "pt": "Útil, com limites: use o conselho como subsídio e decida por conta própria.",
                               "hinglish": "Kaam ka, par seemaon ke saath: salah ko ek input maanein aur faisla khud karein."},
        "needs_patience": {"en": "Look for another voice on the big decisions, and keep this one for smaller questions.",
                           "es": "Busquen otra voz para las grandes decisiones y dejen esta para preguntas menores.",
                           "pt": "Procurem outra voz para as grandes decisões e deixem esta para perguntas menores.",
                           "hinglish": "Bade faislon ke liye koi aur salahkaar dhoondhein, aur ise chhote sawaalon ke liye rakhein."},
    },
    "close": {
        "natural_fit": {"en": "A natural bond: it holds up with ordinary care.",
                        "es": "Un vínculo natural: se sostiene con un cuidado normal.",
                        "pt": "Um vínculo natural: se sustenta com um cuidado comum.",
                        "hinglish": "Svabhaavik rishta: aam dekhbhaal se tika rehta hai."},
        "workable_with_care": {"en": "A bond that needs care: make time for each other and say things plainly.",
                               "es": "Un vínculo que necesita cuidado: dense tiempo y digan las cosas con claridad.",
                               "pt": "Um vínculo que precisa de cuidado: reservem tempo um para o outro e digam as coisas com clareza.",
                               "hinglish": "Aisa rishta jise dhyaan chahiye: ek doosre ke liye samay nikaalein aur baat saaf kehein."},
        "needs_patience": {"en": "A bond that asks for patience: go slowly, avoid big moves and keep talking.",
                           "es": "Un vínculo que pide paciencia: vayan despacio, eviten movimientos grandes y sigan hablando.",
                           "pt": "Um vínculo que pede paciência: vão devagar, evitem movimentos grandes e continuem conversando.",
                           "hinglish": "Aisa rishta jo dhairya maangta hai: dheere chalein, bade kadam se bachein aur baat karte rahein."},
    },
}
PHASE_CLOSE = {
    "clear": {"en": "A calm time for this relationship: neither of you is in a clouded or testing stretch.",
              "es": "Un momento tranquilo para esta relación: ninguno está en un tramo nublado ni de prueba.",
              "pt": "Um momento tranquilo para esta relação: nenhum dos dois está num trecho nublado ou de prova.",
              "hinglish": "Is rishte ke liye shaant samay: aap dono mein se koi dhundhle ya pariksha wale daur mein nahin hai."},
    "testing": {"en": "Fine, with patience. At least one of you is in a testing stretch (delay, heat or ego), so keep talking and avoid big moves made in a hurry.",
                "es": "Bien, con paciencia. Al menos uno está en un tramo de prueba (demora, calor o ego), así que sigan hablando y eviten movimientos grandes hechos con prisa.",
                "pt": "Bem, com paciência. Pelo menos um está num trecho de prova (atraso, calor ou ego), então continuem conversando e evitem movimentos grandes feitos com pressa.",
                "hinglish": "Theek hai, dhairya ke saath. Aap mein se kam se kam ek pariksha wale daur (deri, garmi ya ahankaar) mein hai, isliye baat karte rahein aur jaldbaazi mein bade kadam na uthayein."},
    "one_heavy": {"en": "A delicate time. {name} is in a clouded stretch until {until}. {effect} Avoid big decisions about this relationship and keep things light.",
                  "es": "Un momento delicado. {name} está en un tramo nublado hasta el {until}. {effect} Eviten decisiones grandes sobre esta relación y mantengan las cosas ligeras.",
                  "pt": "Um momento delicado. {name} está num trecho nublado até {until}. {effect} Evitem decisões grandes sobre esta relação e mantenham as coisas leves.",
                  "hinglish": "Nazuk samay. {name} {until} tak dhundhle daur mein hai. {effect} Is rishte ke bade faisle taalein aur cheezein halki rakhein."},
    "both_heavy": {"en": "A delicate time. You are both in clouded stretches, where judgment gets unreliable and things look better or worse than they are. Wait on big decisions and keep things light.",
                   "es": "Un momento delicado. Los dos están en tramos nublados, donde el criterio se vuelve poco confiable y las cosas parecen mejores o peores de lo que son. Esperen para las decisiones grandes y mantengan las cosas ligeras.",
                   "pt": "Um momento delicado. Os dois estão em trechos nublados, em que o julgamento fica pouco confiável e as coisas parecem melhores ou piores do que são. Esperem para as decisões grandes e mantenham as coisas leves.",
                   "hinglish": "Nazuk samay. Aap dono dhundhle daur mein hain, jahan nirnay bharosemand nahin rehta aur cheezein asliyat se behtar ya buri dikhti hain. Bade faisle rok dein aur cheezein halki rakhein."},
    "better": {"en": "What feels hard now can ease: from {on} neither of you is in a clouded stretch.",
               "es": "Lo que se siente difícil ahora puede aliviarse: desde el {on} ninguno de los dos está en un tramo nublado.",
               "pt": "O que parece difícil agora pode aliviar: a partir de {on} nenhum dos dois está num trecho nublado.",
               "hinglish": "Jo abhi kathin lagta hai wo halka ho sakta hai: {on} se aap dono mein se koi dhundhle daur mein nahin hoga."},
}
CALL_CLOSE = {
    "not_now": {"en": "A delicate time", "es": "Un momento delicado", "pt": "Um momento delicado", "hinglish": "Nazuk samay"},
    "with_structure": {"en": "Fine, with patience", "es": "Bien, con paciencia", "pt": "Bem, com paciência", "hinglish": "Theek, dhairya ke saath"},
    "good_now": {"en": "A calm time", "es": "Un momento tranquilo", "pt": "Um momento tranquilo", "hinglish": "Shaant samay"},
}
DONT = {
    "close_careful": {"en": "Avoid big conversations or decisions about this relationship during {ranges}.",
                      "es": "Eviten las conversaciones o decisiones grandes sobre esta relación durante {ranges}.",
                      "pt": "Evitem conversas ou decisões grandes sobre esta relação durante {ranges}.",
                      "hinglish": "{ranges} ke dauran is rishte ke bare mein badi baat ya faisle se bachein."},
    "close_careful_none": {"en": "Avoid big conversations or decisions about this relationship while either of you is in a careful stretch. Check the Windows tab first.",
                           "es": "Eviten las conversaciones o decisiones grandes sobre esta relación mientras alguno esté en un tramo de cuidado. Revisen primero la pestaña de ventanas.",
                           "pt": "Evitem conversas ou decisões grandes sobre esta relação enquanto um dos dois estiver num trecho de cuidado. Vejam antes a aba de janelas.",
                           "hinglish": "Jab tak aap mein se koi savdhaani wale stretch mein ho, is rishte ke bare mein badi baat ya faisle se bachein. Pehle Windows tab dekhein."},
    "keepscore": {"en": "Don't keep score. Name one thing each of you will do differently this month.",
                  "es": "No lleven la cuenta. Nombren una cosa que cada uno hará distinto este mes.",
                  "pt": "Não fiquem fazendo contas. Nomeiem uma coisa que cada um fará diferente neste mês.",
                  "hinglish": "Hisaab na rakhein. Ek cheez tay karein jo is mahine aap dono alag tareeke se karenge."},
    "advice_own": {"en": "Don't hand over the decision. Take the advice, then decide for yourself.",
                   "es": "No entreguen la decisión. Tomen el consejo y luego decidan ustedes mismos.",
                   "pt": "Não entreguem a decisão. Ouçam o conselho e depois decidam por conta própria.",
                   "hinglish": "Faisla doosre ko na saunpein. Salah lein, phir khud tay karein."},
    "hier_scope": {"en": "Don't leave scope or reporting vague. Write down what is expected and who decides.",
                   "es": "No dejen vagos el alcance ni los reportes. Escriban qué se espera y quién decide.",
                   "pt": "Não deixem vagos o escopo nem os relatórios. Escrevam o que se espera e quem decide.",
                   "hinglish": "Kaam ki seema ya reporting ko dhundhla na chhodein. Likh lein ki kya apekshit hai aur faisla kaun karega."},
}
PACE = {
    "differs": {"en": "One of you moves faster than the other. Agree on a pace for big decisions so neither feels pushed or held back.",
                "es": "Uno de ustedes se mueve más rápido que el otro. Acuerden un ritmo para las decisiones grandes para que nadie se sienta empujado o frenado.",
                "pt": "Um de vocês anda mais rápido que o outro. Combinem um ritmo para as decisões grandes para que ninguém se sinta empurrado ou freado.",
                "hinglish": "Aap mein se ek doosre se tez chalta hai. Bade faislon ke liye ek raftaar tay karein taaki kisi ko dhakela ya roka hua na lage."},
    "close": {"en": "Your rhythms are close, which helps. Still agree who raises hard topics, and when.",
              "es": "Sus ritmos son parecidos, lo que ayuda. Aun así, acuerden quién saca los temas difíciles y cuándo.",
              "pt": "Os ritmos de vocês são parecidos, o que ajuda. Mesmo assim, combinem quem levanta os assuntos difíceis e quando.",
              "hinglish": "Aapki raftaar milti-julti hai, jo madad karta hai. Phir bhi tay karein ki kathin baatein kaun aur kab uthayega."},
}
TEXTS = (AREA, REASON, LEVEL_LABEL, VERDICT_TITLE, PHASE_CLOSE, CALL_CLOSE, DONT, PACE,
         *(VERDICT_LINE[f][k] for f in VERDICT_LINE for k in VERDICT_LINE[f]))


# ── a person's capacity for the bond, in their role ──────────────────────────────────────────
def bond_for(chart: dict, role: str, lang: str = "en") -> Optional[dict]:
    """{level: strong|steady|strained, label, reasons[plain, third-person], role}. None for roles with no spec
    (cofounder / business use circle_fit.partnership_lean). Never raises."""
    spec = ROLE_SPEC.get(role)
    if not spec:
        return None
    lang = CC.lang_of(lang)
    try:
        from antar_engine import career_mode as CM
        net, why = 0.0, []
        area = CC.pick(AREA, lang)[spec["area"]]
        for h in spec["houses"]:
            lord = CM._lord_of(chart, h)
            st, placed = CM._strength(chart, lord), CM._house_of(chart, lord)
            if st >= 1.0:
                net += 1.0; why.append("h_strong")
            elif st <= -1.0:
                net -= 0.5
            if placed in SUPPORTIVE:
                net += 0.5
            elif placed in STRAIN:
                net -= 1.0; why.append("h_strain")
        for k in spec["karakas"]:
            st, placed = CM._strength(chart, k), CM._house_of(chart, k)
            if st >= 1.0:
                net += 1.0; why.append("k_strong")
            elif st <= -1.0:
                net -= 0.75; why.append("k_weak")
            if placed in STRAIN:
                net -= 0.5
        level = "strong" if net >= STRONG_MIN else "strained" if net <= STRAINED_MAX else "steady"
        if "h_strong" in why and "h_strain" in why:      # one area can't be both: say it is mixed
            why = ["h_mixed"] + [k for k in why if k not in ("h_strong", "h_strain")]
        seen, reasons = set(), []
        for k in why:
            if k not in seen:
                seen.add(k)
                reasons.append(CC.pick(REASON[k], lang).format(area=area))
        return {"role": role, "level": level, "label": CC.pick(LEVEL_LABEL[level], lang), "reasons": reasons[:3]}
    except Exception:
        return None


def bond_verdict(lens: str, a_level: Optional[str], b_level: Optional[str], lang: str = "en") -> Optional[dict]:
    """The structure line for a non-business lens from the two people's levels (strong 2, steady 1, strained 0):
    total >= 3 natural fit, >= 2 workable with care, else needs patience."""
    spec = LENSES.get(lens)
    if not spec or spec["family"] == "work_partner":
        return None
    lang = CC.lang_of(lang)
    score = {"strong": 2, "steady": 1, "strained": 0}
    total = score.get(a_level, 1) + score.get(b_level, 1)
    key = "natural_fit" if total >= 3 else "workable_with_care" if total >= 2 else "needs_patience"
    fam = "close" if spec["family"] == "close" else spec["family"]
    return {"key": key, "title": CC.pick(VERDICT_TITLE[key], lang), "line": CC.pick(VERDICT_LINE[fam][key], lang), "lead": None, "other": None}
