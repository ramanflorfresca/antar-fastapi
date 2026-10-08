"""
antar_engine/circle_moves.py - "What to do": two or three practical moves for a relationship.

The old relationship page turned every weak area into a colour-and-weekday remedy ("wear green on
Wednesday") that is about the reader's own chart, not about the other person, and has nothing to do with
how two people actually work together. This replaces it with plain things the two of you can DO, picked
from the areas the reading scored lowest.

Deterministic copy, no LLM, no astrology terms, no promise of an outcome. One line per (area, family):
  work  = business, cofounder, employee, boss-or-manager, advisor
  close = romantic, spouse, friend, family, sibling, parent, child
Only areas that are NOT flowing produce a move; the weakest come first; at most 3.
en / es / pt / hinglish (anything else is served in English).
"""
from __future__ import annotations

from typing import List, Optional

from antar_engine import circle_copy as CC

AREAS = ("soul", "chemistry", "public", "lifepath", "communication", "friction")
WORK = {"business", "cofounder", "employee", "boss-or-manager", "advisor"}
MAX_MOVES = 3

AREA_LABEL = {
    "en": {"soul": "Shared priorities", "chemistry": "Working together day to day", "public": "How you show up together",
           "lifepath": "Timing", "communication": "Communication and trust", "friction": "Handling disagreement"},
    "es": {"soul": "Prioridades compartidas", "chemistry": "Trabajar juntos día a día", "public": "Cómo se presentan juntos",
           "lifepath": "Momento oportuno", "communication": "Comunicación y confianza", "friction": "Manejar los desacuerdos"},
    "pt": {"soul": "Prioridades em comum", "chemistry": "Trabalhar juntos no dia a dia", "public": "Como vocês se apresentam juntos",
           "lifepath": "Momento certo", "communication": "Comunicação e confiança", "friction": "Lidar com discordâncias"},
    "hinglish": {"soul": "Saanjhi priorities", "chemistry": "Roz saath kaam karna", "public": "Saath mein kaise dikhte hain",
                 "lifepath": "Sahi samay", "communication": "Baatcheet aur bharosa", "friction": "Asahmati sambhalna"},
}

MOVE = {
    "work": {
        "en": {
            "soul": "Each of you says your top priority for this in one sentence, out loud, before you decide anything big.",
            "chemistry": "Agree how you'll work day to day: how often you check in, and which channel is for what.",
            "public": "Decide together how you'll present this to others, and who speaks for it, before anyone outside hears about it.",
            "lifepath": "Put the big moves in order. Do the one that suits both of you first and leave the other for a better stretch.",
            "communication": "Put decisions in writing: who decided what, and by when.",
            "friction": "Agree in advance who has the final say on each area, and what you'll do when you disagree.",
        },
        "es": {
            "soul": "Cada uno dice en una frase su prioridad principal en esto, en voz alta, antes de decidir algo importante.",
            "chemistry": "Acuerden cómo van a trabajar día a día: cada cuánto hablan y qué canal se usa para qué.",
            "public": "Decidan juntos cómo van a presentar esto a los demás y quién habla por ustedes, antes de que alguien de afuera se entere.",
            "lifepath": "Pongan las decisiones grandes en orden. Hagan primero la que les conviene a los dos y dejen la otra para un mejor momento.",
            "communication": "Dejen las decisiones por escrito: quién decidió qué y para cuándo.",
            "friction": "Acuerden de antemano quién tiene la última palabra en cada área y qué harán cuando no estén de acuerdo.",
        },
        "pt": {
            "soul": "Cada um diz em uma frase a sua prioridade principal nisso, em voz alta, antes de decidir algo grande.",
            "chemistry": "Combinem como vão trabalhar no dia a dia: com que frequência conversam e qual canal serve para quê.",
            "public": "Decidam juntos como vão apresentar isso aos outros e quem fala por vocês, antes que alguém de fora fique sabendo.",
            "lifepath": "Coloquem as decisões grandes em ordem. Façam primeiro a que serve aos dois e deixem a outra para um momento melhor.",
            "communication": "Deixem as decisões por escrito: quem decidiu o quê e até quando.",
            "friction": "Combinem de antemão quem tem a palavra final em cada área e o que farão quando discordarem.",
        },
        "hinglish": {
            "soul": "Koi bada faisla lene se pehle aap dono apni sabse badi priority ek vaakya mein, zor se bolein.",
            "chemistry": "Roz ka kaam kaise chalega ye tay karein: kitni baar baat hogi aur kaunsa channel kis kaam ke liye.",
            "public": "Bahar kisi ko pata chalne se pehle saath mein tay karein ki ise doosron ke saamne kaise rakhna hai aur kaun bolega.",
            "lifepath": "Bade kadam ek kram mein rakhein. Jo dono ko suit kare use pehle karein, baaki ko behtar samay ke liye chhodein.",
            "communication": "Faisle likhit mein rakhein: kisne kya tay kiya aur kab tak.",
            "friction": "Pehle se tay karein ki har area mein antim faisla kiska hoga, aur asahmati hone par kya karenge.",
        },
    },
    "close": {
        "en": {
            "soul": "Talk about what each of you wants most from this, and write down the one thing you both agree on.",
            "chemistry": "Set aside regular time together with no agenda, even a short one.",
            "public": "Talk about how you want to be seen together by family and friends, and agree on what stays private.",
            "lifepath": "Talk through the next year: what each of you needs and when, and plan around the busy stretches.",
            "communication": "When something matters, say it plainly and ask what they heard. Don't count on being understood.",
            "friction": "Pick one recurring sore spot and agree on one small change you'll each make this month.",
        },
        "es": {
            "soul": "Hablen de lo que cada uno más quiere de esto y anoten lo único en lo que los dos están de acuerdo.",
            "chemistry": "Reserven un tiempo regular juntos sin agenda, aunque sea corto.",
            "public": "Hablen de cómo quieren que los vean juntos la familia y los amigos, y acuerden qué se queda en privado.",
            "lifepath": "Repasen juntos el próximo año: qué necesita cada uno y cuándo, y planeen según los tramos más ocupados.",
            "communication": "Cuando algo importa, dilo claro y pregunta qué entendió la otra persona. No des por hecho que te entienden.",
            "friction": "Elijan un punto sensible que se repite y acuerden un pequeño cambio que hará cada uno este mes.",
        },
        "pt": {
            "soul": "Conversem sobre o que cada um mais quer disso e anotem a única coisa em que os dois concordam.",
            "chemistry": "Reservem um tempo regular juntos sem pauta, mesmo que curto.",
            "public": "Conversem sobre como querem ser vistos juntos pela família e pelos amigos, e combinem o que fica em privado.",
            "lifepath": "Conversem sobre o próximo ano: do que cada um precisa e quando, e planejem em torno dos períodos mais cheios.",
            "communication": "Quando algo importa, diga com clareza e pergunte o que a outra pessoa entendeu. Não conte com ser entendido.",
            "friction": "Escolham um ponto sensível que se repete e combinem uma pequena mudança que cada um fará neste mês.",
        },
        "hinglish": {
            "soul": "Baat karein ki aap dono is rishte se sabse zyada kya chahte hain, aur wo ek cheez likh lein jis par dono sahmat hain.",
            "chemistry": "Saath mein niyamit samay rakhein, bina kisi agenda ke, chhota hi sahi.",
            "public": "Baat karein ki parivaar aur doston ke saamne aap saath mein kaise dikhna chahte hain, aur kya nijee rahega ye tay karein.",
            "lifepath": "Agle saal ki baat karein: har ek ko kya chahiye aur kab, aur vyast daur ke hisaab se plan banayein.",
            "communication": "Jab kuch zaroori ho to saaf bolein aur poochhein ki unhone kya suna. Ye maan kar na chalein ki samajh liya jayega.",
            "friction": "Ek baar-baar wali takleef chunein aur tay karein ki is mahine aap dono ek chhota badlaav karenge.",
        },
    },
}
TEXTS = (AREA_LABEL, MOVE["work"], MOVE["close"])        # for the jargon guard


def family(reason: Optional[str]) -> str:
    return "work" if str(reason or "") in WORK else "close"


def _norm(layer: dict) -> Optional[dict]:
    key = layer.get("layer_key") or layer.get("key")
    if key not in AREAS or layer.get("applicable") is False:
        return None
    try:
        score = float(layer.get("score"))
    except (TypeError, ValueError):
        return None
    if "passed" in layer:
        flowing = bool(layer.get("passed"))
    else:
        flowing = layer.get("status") == "flows"
    return {"key": key, "score": score, "flowing": flowing}


def moves_for(layers: Optional[list], reason: Optional[str], language=None, limit: int = MAX_MOVES) -> List[dict]:
    """[{area, area_label, text}] for the weakest non-flowing areas, weakest first. [] when everything
    flows or the layers are missing. `layers` may be the engine's layers or circle_reading's."""
    lang = CC.lang_of(language)
    fam = family(reason)
    rows = [n for n in (_norm(l) for l in (layers or []) if isinstance(l, dict)) if n and not n["flowing"]]
    rows.sort(key=lambda r: (r["score"], AREAS.index(r["key"])))
    labels, texts = CC.pick(AREA_LABEL, lang), CC.pick(MOVE[fam], lang)
    return [{"area": r["key"], "area_label": labels[r["key"]], "text": texts[r["key"]]}
            for r in rows[:max(0, int(limit))]]
