"""
antar_engine/people_pointer.py

"Is my partner compatible with me?" / "Does my partner truly love me?" / "Is he the one?" can't be
answered from the ASKER's chart: the asker's chart shows how the bond feels from their side, never
what another person feels or whether they are in a relationship chapter. The real answer needs the
OTHER chart — which is exactly what People holds.

  • no saved partner  → say so plainly, give the asker's side (the bond's foundation), point to People
  • one saved partner → check whether THEIR current chapter has partnership in it (their 7th house,
                        7th lord, Venus or Darakaraka connected to the running period: occupy / rule /
                        aspect / conjoin / exchange — connection, not friendship), and combine it with
                        the asker's side. If both say the bond isn't there, say it kindly and stop —
                        never string a window over it.
  • several partners  → ask which one (the existing which-one chips)

Deterministic, no LLM, never raises. It never states a person's feelings or intentions: only (a) how the
bond holds from the asker's side and (b) whether the partner's current chapter is a partnership chapter.
"""
from __future__ import annotations

import re
from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import _aspects, _darakaraka, _house_of

_I = re.IGNORECASE
_P = r"(?:partner|spouse|husband|wife|boyfriend|girlfriend|fianc[eé]e?)"
_COMPAT = [
    re.compile(r"\bis\s+(?:my\s+)?" + _P + r"\s+(?:compatible|suitable|a\s+good\s+match|meant\s+for\s+me|the\s+right\s+(?:one|person|match|partner))\b", _I),
    re.compile(r"\bis\s+(?:he|she|he\s+or\s+she)\s+(?:the\s+one|the\s+right\s+(?:one|person)|meant\s+for\s+me|my\s+soul\s?mate)\b", _I),
    re.compile(r"\b(?:are\s+we|is\s+this\s+person)\s+(?:compatible|a\s+good\s+match|right\s+for\s+(?:me|each\s+other)|meant\s+to\s+be)\b", _I),
    re.compile(r"\b(?:es|son)\s+(?:mi\s+)?(?:pareja|esposo|esposa|novi[oa])\s+(?:compatible|el\s+indicado|la\s+indicada|para\s+m[ií])\b|\b[eé]\s+(?:meu|minha)\s+(?:parceiro|parceira|marido|esposa|namorad[oa])\s+(?:compat[ií]vel|a\s+pessoa\s+certa)\b", _I),
    re.compile(r"\b(?:mera|meri)\s+(?:partner|pati|patni|biwi|shohar)\s+(?:compatible|sahi)\b|\bkya\s+(?:woh|wo)\s+(?:mere\s+liye\s+)?(?:sahi|the\s+one)\b", _I),
]
_STATE = [
    re.compile(r"\b(?:does|do|did)\s+my\s+" + _P + r"\s+(?:truly\s+|really\s+|still\s+|actually\s+)?(?:love|care\s+about|like|want)\s+me\b", _I),
    re.compile(r"\b(?:will|would)\s+my\s+(?:spouse|husband|wife|partner)\s+(?:ever\s+)?(?:love|care\s+about)\s+me\b", _I),
    re.compile(r"\bis\s+my\s+" + _P + r"(?:'s|s')?\s+(?:dasha|period|chapter|season|phase)\b|\bmy\s+" + _P + r"(?:'s|s')\s+(?:dasha|period)\b[^?]{0,30}\b(?:our|the)\s+(?:marriage|relationship)\b", _I),
    re.compile(r"\bis\s+my\s+" + _P + r"\s+(?:invested|committed|serious|loyal)\b", _I),
    re.compile(r"\b(?:mi\s+(?:pareja|esposo|esposa))\s+(?:me\s+ama|me\s+quiere)\b|\b(?:meu|minha)\s+(?:parceiro|parceira|marido|esposa)\s+(?:me\s+ama|gosta\s+de\s+mim)\b", _I),
    re.compile(r"\b(?:mera|meri)\s+(?:partner|pati|patni|biwi|shohar)\s+(?:mujhse|mujhe)\s+(?:pyaar|pyar)\b", _I),
]
_NOT_ROMANTIC = re.compile(r"\b(deal|business|company|work|job|project|firm|venture|called|who|that|which)\b", _I)
_ROMANTIC = {"romantic", "relationship", "love", "marriage", "spouse", "girlfriend", "boyfriend", "husband", "wife", "fiance", "fiancee"}
_PARTNER_REL = {"spouse", "partner", "wife", "husband", "girlfriend", "boyfriend", "fiance", "fiancee", "ex"}


def classify(question: str) -> Optional[str]:
    """'compat' | 'state' | None. Narrow on purpose: a boss, a client or a named person never matches."""
    q = (question or "").strip()
    if not q:
        return None
    if any(r.search(q) for r in _STATE):
        return "state"
    for r in _COMPAT:
        m = r.search(q)
        if m:
            tail = q[m.end():].strip(" ?.!¿¡")
            # "Is he the one who called?" / "Is my partner the right one for the deal?" are not this question
            if len(tail.split()) <= 3 and not _NOT_ROMANTIC.search(tail):
                return "compat"
    return None


def partner_candidates(people: list) -> list:
    """The asker's saved ROMANTIC people (not business partners, not a former partner)."""
    out = []
    for p in people or []:
        if not isinstance(p, dict) or not (p.get("chart_id_b") or p.get("chart_id")):
            continue
        ct = str(p.get("compat_type") or "").lower()
        rel = str(p.get("relation") or "").lower()
        if rel == "ex" or ct == "ex":
            continue
        if ct in _ROMANTIC or rel in _PARTNER_REL - {"ex"}:
            out.append(p)
    return out


# ── is the PARTNER in a partnership chapter? connection, not friendship ────────
def _sign_of(planets: dict, p: str) -> Optional[str]:
    return (planets.get(p) or {}).get("sign")


def _connected(lord: str, planets: dict, lagna: str) -> list:
    """Why `lord` (a running dasha lord) is wired to partnership: occupies / rules / aspects / conjoins /
    exchanges with the 7th house, the 7th lord, Venus or the Darakaraka. [] = not connected."""
    why = []
    seventh = _sign_n_from(lagna, 7)
    l7 = SIGN_LORD.get(seventh)
    dk = _darakaraka(planets)
    lh = _house_of(lord, planets)
    if lord == l7:
        why.append("rules the house of partnership")
    if lh == 7:
        why.append("sits in the house of partnership")
    elif lh and _aspects(lh, 7, lord):
        why.append("looks at the house of partnership")
    if lord == "Venus":
        why.append("is the planet of love itself")
    if dk and lord == dk:
        why.append("is the partner-significator")
    for tgt, label in ((l7, "the partnership lord"), ("Venus", "Venus"), (dk, "the partner-significator")):
        if not tgt or tgt == lord:
            continue
        th = _house_of(tgt, planets)
        if lh and th and lh == th:
            why.append(f"sits with {label}")
        elif lh and th and _aspects(lh, th, lord):
            why.append(f"looks at {label}")
    ls, ts = _sign_of(planets, lord), _sign_of(planets, l7) if l7 else None
    if l7 and l7 != lord and ls and ts and SIGN_LORD.get(ts) == lord and SIGN_LORD.get(ls) == l7:
        why.append("exchanges signs with the partnership lord")
    return why


def _running(dashas: dict) -> dict:
    """{'md','ad','pd'} Vimsottari lords running today."""
    from datetime import date
    today = date.today().isoformat()
    out = {}
    for r in (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []:
        if not isinstance(r, dict):
            continue
        s = str(r.get("start_date") or r.get("start") or "")[:10]
        e = str(r.get("end_date") or r.get("end") or "")[:10]
        if not (s and e and s <= today <= e):
            continue
        lv = str(r.get("level") or r.get("type") or "").lower()
        key = {"mahadasha": "md", "1": "md", "antardasha": "ad", "antar": "ad", "2": "ad",
               "pratyantardasha": "pd", "pratyantar": "pd", "3": "pd"}.get(lv)
        lord = r.get("lord_or_sign") or r.get("planet_or_sign") or r.get("lord")
        if key and lord and key not in out:
            out[key] = str(lord).title()
    return out


def partner_activation(partner_chart: dict, partner_dashas: dict) -> dict:
    """{available, state: active|touching|quiet, tiers[], why[]}. `active` = the main chapter or
    sub-chapter is wired to partnership; `touching` = only the third level is; `quiet` = none."""
    try:
        cd = partner_chart if isinstance(partner_chart, dict) else {}
        planets, lagna = cd.get("planets") or {}, (cd.get("lagna") or {}).get("sign")
        if not planets or lagna not in SIGNS:
            return {"available": False}
        run = _running(partner_dashas)
        if not run:
            return {"available": False}
        tiers, strong, why = [], [], []
        for k in ("md", "ad", "pd"):
            if run.get(k):
                w = _connected(run[k], planets, lagna)
                if w:
                    tiers.append(k)
                    if any(not x.startswith("looks at") for x in w):     # rules / occupies / conjoins / exchanges / IS the significator
                        strong.append(k)
                    why.append(f"{run[k]} ({k}) {w[0]}")
        # a bare aspect is a weak link: it takes both the main and the sub chapter to make a partnership chapter
        state = ("active" if ("md" in strong or "ad" in strong or ("md" in tiers and "ad" in tiers))
                 else "touching" if tiers else "quiet")
        return {"available": True, "state": state, "tiers": tiers, "why": why, "running": run}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


# ── the answer ────────────────────────────────────────────────────────────────
_T = {
    "en": {
        "side_care": "This bond asks for more deliberate care than most — it has points that strain easily under pressure.",
        "verdict_care": "Both sides ask for deliberate care this season: a direct, calm conversation about what each of you needs is worth having — and you don't have to carry it alone.",
        "next_care": "Pick one moment this week to say what you need, plainly and without blame — then listen for what they need.",
        "cant_state": "A chart can't tell me what {name} feels. What it can show is where {name}'s season is and how the bond holds from your side.",
        "cant": "A chart can't tell me what someone else feels, or whether they're \"the one\" — and I won't guess that from yours.",
        "pointer": "Add them in People (name, birth date, time and place) and I can compare your two charts and check whether their current chapter has partnership in it.",
        "side": {"sound": "From your side, the bond has what it takes to hold under pressure.",
                 "mixed": "From your side, the bond can hold, but only with deliberate care.",
                 "fragile": "From your side, the lasting support under this bond looks thin."},
        "next_missing": "Add them in People, then ask again.",
        "theirs": {"active": "In {name}'s chart, the current chapter has partnership in it — this is a season where commitment is on their agenda.",
                   "touching": "In {name}'s chart, partnership is only touched at the edges of the current chapter — it is not what the season is built around.",
                   "quiet": "In {name}'s chart, the current chapter is not built around partnership — whatever the feelings, this is not a relationship season for them."},
        "verdict_stop": "Both sides point the same way: the support under this bond is thin and their season isn't one for commitment. The honest read is to stop waiting on it and decide what you want for yourself.",
        "verdict_go": "Both sides are workable: a direct, calm conversation is worth having now.",
        "verdict_mix": "The picture is mixed: put the weight on what you can decide yourself, and treat any conversation as a question, not a test.",
        "next_stop": "Decide what you need from this bond and by when — then act on that, not on their reply.",
        "next_go": "Have the direct conversation this month; say what you want plainly.",
        "next_mix": "Say what you need once, plainly, then watch what changes rather than waiting for a promise.",
        "unreadable": "I have {name} saved, but their chart isn't readable right now, so I won't guess from yours. Open them in People to re-check their birth details, then ask again.",
        "full": "Open {name} in People for the full compatibility read.",
    },
    "es": {
        "side_care": "Este vínculo pide más cuidado deliberado que la mayoría: tiene puntos que se tensan con facilidad bajo presión.",
        "verdict_care": "Los dos lados piden cuidado deliberado en esta temporada: vale la pena una conversación directa y tranquila sobre lo que cada uno necesita, y no tienes que cargarla solo.",
        "next_care": "Elige un momento esta semana para decir lo que necesitas, con claridad y sin culpar; luego escucha lo que necesita la otra persona.",
        "cant_state": "Una carta no puede decirme lo que siente {name}. Lo que sí puede mostrar es en qué temporada está {name} y cómo se sostiene el vínculo desde tu lado.",
        "cant": "Una carta no puede decirme lo que siente otra persona, ni si es \"la indicada\" — y no voy a adivinarlo con la tuya.",
        "pointer": "Agrégala en Personas (nombre, fecha, hora y lugar de nacimiento) y podré comparar las dos cartas y ver si su etapa actual tiene la pareja en el centro.",
        "side": {"sound": "Desde tu lado, el vínculo tiene lo necesario para aguantar la presión.",
                 "mixed": "Desde tu lado, el vínculo puede sostenerse, pero solo con cuidado deliberado.",
                 "fragile": "Desde tu lado, el apoyo duradero bajo este vínculo se ve escaso."},
        "next_missing": "Agrégala en Personas y vuelve a preguntar.",
        "theirs": {"active": "En la carta de {name}, la etapa actual tiene la pareja en el centro: es una temporada en que el compromiso está en su agenda.",
                   "touching": "En la carta de {name}, la pareja solo se roza en los bordes de la etapa actual: no es sobre lo que se construye la temporada.",
                   "quiet": "En la carta de {name}, la etapa actual no gira en torno a la pareja: sea lo que sea que sienta, esta no es una temporada de relación para esa persona."},
        "verdict_stop": "Los dos lados apuntan en la misma dirección: el apoyo bajo este vínculo es escaso y su temporada no es de compromiso. La lectura honesta es dejar de esperar y decidir qué quieres para ti.",
        "verdict_go": "Los dos lados son viables: vale la pena tener ahora una conversación directa y tranquila.",
        "verdict_mix": "El panorama es mixto: pon el peso en lo que tú puedes decidir, y toma cualquier conversación como una pregunta, no como una prueba.",
        "next_stop": "Decide qué necesitas de este vínculo y para cuándo; actúa según eso, no según su respuesta.",
        "next_go": "Ten la conversación directa este mes; di lo que quieres con claridad.",
        "next_mix": "Di lo que necesitas una vez, con claridad, y observa qué cambia en vez de esperar una promesa.",
        "unreadable": "Tengo guardado a {name}, pero su carta no se puede leer ahora, así que no voy a adivinar con la tuya. Ábrelo en Personas para revisar sus datos de nacimiento y vuelve a preguntar.",
        "full": "Abre a {name} en Personas para la lectura de compatibilidad completa.",
    },
    "pt": {
        "side_care": "Este vínculo pede mais cuidado deliberado que a maioria: tem pontos que se tensionam com facilidade sob pressão.",
        "verdict_care": "Os dois lados pedem cuidado deliberado nesta temporada: vale uma conversa direta e tranquila sobre o que cada um precisa, e você não precisa carregá-la sozinho.",
        "next_care": "Escolha um momento esta semana para dizer o que precisa, com clareza e sem culpar; depois ouça o que a outra pessoa precisa.",
        "cant_state": "Um mapa não consegue me dizer o que {name} sente. O que ele mostra é em que temporada {name} está e como o vínculo se sustenta do seu lado.",
        "cant": "Um mapa não consegue me dizer o que outra pessoa sente, nem se ela é \"a pessoa certa\" — e não vou adivinhar isso com o seu.",
        "pointer": "Adicione em Pessoas (nome, data, hora e local de nascimento) e posso comparar os dois mapas e ver se a fase atual dela tem o relacionamento no centro.",
        "side": {"sound": "Do seu lado, o vínculo tem o que é preciso para aguentar a pressão.",
                 "mixed": "Do seu lado, o vínculo pode se sustentar, mas só com cuidado deliberado.",
                 "fragile": "Do seu lado, o apoio duradouro sob este vínculo parece escasso."},
        "next_missing": "Adicione em Pessoas e pergunte de novo.",
        "theirs": {"active": "No mapa de {name}, a fase atual tem o relacionamento no centro: é uma temporada em que o compromisso está na agenda.",
                   "touching": "No mapa de {name}, o relacionamento só é tocado nas bordas da fase atual: não é em torno disso que a temporada se constrói.",
                   "quiet": "No mapa de {name}, a fase atual não gira em torno do relacionamento: seja o que for que sinta, esta não é uma temporada de relação para a pessoa."},
        "verdict_stop": "Os dois lados apontam para o mesmo lugar: o apoio sob este vínculo é escasso e a temporada dela não é de compromisso. A leitura honesta é parar de esperar e decidir o que você quer para si.",
        "verdict_go": "Os dois lados são viáveis: vale ter agora uma conversa direta e tranquila.",
        "verdict_mix": "O quadro é misto: ponha o peso no que você pode decidir e trate qualquer conversa como uma pergunta, não como um teste.",
        "next_stop": "Decida o que você precisa deste vínculo e até quando — e aja por isso, não pela resposta dela.",
        "next_go": "Tenha a conversa direta neste mês; diga o que quer com clareza.",
        "next_mix": "Diga o que precisa uma vez, com clareza, e observe o que muda em vez de esperar uma promessa.",
        "unreadable": "Tenho {name} salvo(a), mas o mapa não pode ser lido agora, então não vou adivinhar com o seu. Abra em Pessoas para rever os dados de nascimento e pergunte de novo.",
        "full": "Abra {name} em Pessoas para a leitura de compatibilidade completa.",
    },
    "hinglish": {
        "side_care": "Is bond ko zyada soch-samajh ke dhyan ki zaroorat hai — kuch jagah dabav mein jaldi khinchav aa jaata hai.",
        "verdict_care": "Dono taraf is mausam mein dhyan maangti hain: ek seedhi, shaant baat — ki aap dono ko kya chahiye — karna sahi rahega, aur ise akele dhona zaroori nahi.",
        "next_care": "Is hafte ek pal chuno aur bina dosh diye saaf kaho ki aapko kya chahiye — phir suno ki unhe kya chahiye.",
        "cant_state": "Ek chart yeh nahi bata sakta ki {name} kya mehsoos karte hain. Woh yeh dikha sakta hai ki {name} ka mausam kahan hai aur aapki taraf se bond kaise tik raha hai.",
        "cant": "Ek chart yeh nahi bata sakta ki doosra insaan kya mehsoos karta hai ya woh \"the one\" hai ya nahi — aur main yeh aapke chart se andaza nahi lagaunga.",
        "pointer": "Unhe People mein add karo (naam, janam tithi, samay aur jagah) — phir main dono charts compare karke dekh sakta hoon ki unka abhi ka daur partnership ka hai ya nahi.",
        "side": {"sound": "Aapki taraf se, is bond mein dabav jhelne ki taqat hai.",
                 "mixed": "Aapki taraf se, bond tik sakta hai, par sirf soch-samajh ke dhyan se.",
                 "fragile": "Aapki taraf se, is bond ke neeche ka lambe samay ka sahara patla dikhta hai."},
        "next_missing": "People mein add karo, phir poocho.",
        "theirs": {"active": "{name} ke chart mein abhi ka daur partnership wala hai — yeh commitment ka mausam hai.",
                   "touching": "{name} ke chart mein partnership abhi ke daur ke kinare par hi chhoota hai — mausam us par nahi bana.",
                   "quiet": "{name} ke chart mein abhi ka daur partnership par nahi bana — feelings jo bhi hon, yeh unke liye rishte ka mausam nahi hai."},
        "verdict_stop": "Dono taraf ek hi taraf ishara kar rahi hain: is bond ka sahara patla hai aur unka mausam commitment ka nahi. Imaandaar padhai yeh hai ki intezaar chhodo aur khud ke liye tay karo ki aap kya chahte ho.",
        "verdict_go": "Dono taraf theek hain: abhi seedhi, shaant baat karna sahi rahega.",
        "verdict_mix": "Tasveer mili-juli hai: wazan us par rakho jo aap khud tay kar sakte ho, aur kisi bhi baat ko sawal samjho, imtihaan nahi.",
        "next_stop": "Tay karo ki is bond se aapko kya chahiye aur kab tak — aur us par amal karo, unke jawab par nahi.",
        "next_go": "Is mahine seedhi baat karo; jo chahiye saaf kaho.",
        "next_mix": "Jo chahiye woh ek baar saaf kaho, phir dekho kya badalta hai — vaade ka intezaar mat karo.",
        "unreadable": "{name} saved hain, par unka chart abhi padha nahi ja sakta, isliye aapke chart se andaza nahi lagaunga. People mein unki birth details check karo aur phir poocho.",
        "full": "Poori compatibility read ke liye People mein {name} ko kholo.",
    },
}


def _lg(language: str) -> str:
    l = (language or "en").split("-")[0].lower()
    return l if l in _T else "en"


def _side_band(asker_chart: Optional[dict]) -> Optional[str]:
    try:
        from antar_engine.relationship_foundation import analyze_foundation
        a = analyze_foundation(asker_chart or {})
        return a["foundation"]["band"] if a.get("available") else None
    except Exception:
        return None


def missing_payload(language: str, asker_chart: Optional[dict] = None, kind: str = "compat", partnered: bool = False) -> dict:
    t = _T[_lg(language)]
    band = _side_band(asker_chart)
    side = (t["side_care"] if (partnered and band == "fragile") else t["side"].get(band)) if band else ""
    read = " ".join(x for x in (t["cant"], side, t["pointer"]) if x)
    return {"mode": "explore", "read": read, "next": t["next_missing"], "locked": False,
            "subject": {"relation": "partner", "chart_available": False},
            "people_pointer": {"kind": kind, "state": "missing"}}


def unreadable_payload(name: str, language: str, kind: str = "compat") -> dict:
    return {"mode": "explore", "read": _T[_lg(language)]["unreadable"].format(name=name), "next": None, "locked": False,
            "subject": {"name": name, "relation": "partner", "chart_available": False},
            "people_pointer": {"kind": kind, "state": "unreadable"}}


def is_partnered(marital_status: Optional[str], partner: Optional[dict] = None) -> bool:
    """The reader is IN the relationship being asked about: married / partnered, or the saved person is their spouse."""
    ms = str(marital_status or "").strip().lower().replace("-", "_").replace(" ", "_")
    if ms in ("married", "partnered", "engaged", "in_relationship", "in_a_relationship", "domestic_partnership"):
        return True
    p = partner or {}
    return str(p.get("compat_type") or "").lower() in ("spouse", "husband", "wife") or str(p.get("relation") or "").lower() in ("spouse", "husband", "wife")


def partner_payload(name: str, language: str, asker_chart: dict, partner_chart: dict, partner_dashas: dict,
                    kind: str = "compat", partnered: bool = False) -> dict:
    """The answer when exactly one romantic person with a readable chart is saved."""
    t = _T[_lg(language)]
    act = partner_activation(partner_chart, partner_dashas)
    if not act.get("available"):
        return unreadable_payload(name, language, kind)
    band = _side_band(asker_chart)
    state = act["state"]
    if partnered and band == "fragile":
        # never "stop waiting on it" to someone about their own spouse, from a heuristic that is not yet validated
        verdict, nxt = t["verdict_care"], t["next_care"]
    elif band == "fragile" and state in ("quiet", "touching"):
        verdict, nxt = t["verdict_stop"], t["next_stop"]
    elif band in ("sound", "mixed") and state == "active":
        verdict, nxt = t["verdict_go"], t["next_go"]
    else:
        verdict, nxt = t["verdict_mix"], t["next_mix"]
    parts = ([t["cant_state"].format(name=name)] if kind == "state" else []) + [t["theirs"][state].format(name=name)]
    if band:
        parts.append(t["side_care"] if (partnered and band == "fragile") else t["side"][band])
    parts += [verdict, t["full"].format(name=name)]
    return {"mode": "explore", "read": " ".join(parts), "next": nxt, "locked": False,
            "subject": {"name": name, "relation": "partner", "chart_available": True},
            "people_pointer": {"kind": kind, "state": "read", "partner_season": state, "your_side": band}}
