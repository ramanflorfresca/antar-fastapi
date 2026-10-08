"""
antar_engine/kp/kp_conditions.py — turn a KP Prashna verdict into a SPECIFIC,
plain-language condition: what carries it, what blocks it, whether the final
close is confirmed.

[kp-conditions 2026-10-02] Owner, on a live answer ("Possible — once one piece
falls into place… clear one key hurdle first"): "but what is that condition?
these answers need to be specific, not generic". The verdict already knows the
answer — the deciding cusp's sub-lord signifies houses that support (favour_hit)
and houses that block (against_hit), plus the 11th-house closing gate — but the
narrator only ever saw generic driver lines. This module names them in the
reader's terms, per question family (house 6 is a loan for money, the job
itself for work, friction for marriage). No planets, houses or jargon leave it.
"""
from __future__ import annotations

import re
from typing import Optional

_FAMILY = {
    "gain": "money", "money": "money", "deal_closes": "money", "speculation": "speculation",
    "job_new": "work", "promotion": "promotion",
    "marriage": "union", "reunion": "reunion", "romance": "union", "loss": "separation",
    "property": "property", "residence": "residence", "litigation_win": "legal", "recovery": "health",
    "foreign_travel": "travel", "education": "study", "childbirth": "child",
    "lost_found": "lost",
}

# Generic meaning of each house, then per-family overrides where it differs.
_HOUSE = {
    "en": {
        "promotion": {2: "the raise that comes with it", 6: "the results you've already delivered", 10: "the people who decide on your promotion", 11: "a senior person backing you", 5: "a risky bet on a flashy project", 8: "office politics or a frozen budget", 9: "an outside option pulling you away", 12: "a move that costs more than it pays"},
        "reunion": {2: "the history you share", 7: "their own wish to come back", 11: "friends bringing you back together", 1: "insisting on your own terms", 6: "the old reason you split", 10: "pride or what others will say", 12: "distance or silence"},
        "speculation": {2: "only money you can afford to lose", 5: "a well-judged, limited bet", 6: "an opponent's mistake", 11: "the gain actually landing", 8: "a sudden loss", 12: "money quietly slipping away"},
        "legal": {6: "the strength of your case and evidence", 11: "the outcome you want being granted", 5: "a gamble on how the judge or other side reacts", 8: "delays, appeals or hidden clauses", 12: "legal costs outrunning what you'd win"},
        "health": {1: "your own body's strength", 5: "a treatment that suits you", 11: "recovery fully taking hold", 6: "the illness itself staying active", 8: "a complication or setback", 12: "a hospital stay or long rest"},
        "travel": {3: "the paperwork and short steps moving", 9: "the long-distance route opening (visa, approval)", 12: "actually settling in a far-off place", 4: "ties that keep you at home"},
        "study": {4: "steady study and preparation", 9: "the institution or examiner backing you", 11: "the result coming through", 3: "rushing or careless answers", 8: "a delay or re-evaluation", 12: "distraction or a costly detour"},
        "child": {2: "the family growing", 5: "conception itself", 11: "the wish being fulfilled", 1: "your own health needing care first", 4: "home pressures", 10: "work demands pulling energy away"},
        "lost": {2: "it being with your own things", 6: "retracing your steps carefully", 11: "someone returning or reporting it", 5: "it being left somewhere casual", 8: "it being hidden or hard to reach", 12: "it having gone far or out of reach"},
        "generic": {1: "your own drive", 2: "your own resources", 3: "your own follow-up",
                    4: "your home base", 5: "a risky bet", 6: "hard, steady work",
                    7: "the other party's willingness", 8: "hidden conditions and delays",
                    9: "a mentor or a lucky break", 10: "your standing and reputation",
                    11: "people who already know you", 12: "extra costs or losses"},
        "money": {2: "your own savings", 5: "a speculative gamble",
                  6: "a loan or credit", 7: "a partner on the other side",
                  8: "money with heavy strings attached (investor terms, long due diligence)",
                  11: "people who already know your work", 12: "costs eating the money"},
        "sales": {2: "repeat business from current clients", 5: "chasing flashy, risky prospects",
                  6: "serving well and outworking competitors", 7: "the client's own decision",
                  8: "slow approvals or tough contract terms", 10: "your reputation in the market",
                  11: "referrals from people who know your work", 12: "deals that cost more than they bring"},
        "income": {2: "your existing income", 5: "a speculative gamble", 6: "extra work or a side income",
                   8: "money tied up in other people's terms", 11: "people who already know your work",
                   12: "spending running ahead of income"},
        "partner": {2: "your own stake in it", 5: "a risky side bet", 6: "doing the hands-on work yourself",
                    7: "your partners' real commitment", 8: "a lopsided split with your partners",
                    10: "your standing with the people who award the work",
                    11: "the contacts your partners bring", 12: "costs piling up before it pays"},
        "work": {2: "the pay on offer", 5: "a risky, glamorous move", 6: "doing the job itself well",
                 8: "office politics or a stalled process", 9: "a far-off option pulling you away",
                 10: "the people who decide on the role", 11: "a referral from your network",
                 12: "a move that costs more than it pays"},
        "separation": {1: "one of you choosing your own path", 2: "money you have tied up together",
                       6: "disputes about work, money or terms", 7: "your partner's own wish to keep it going",
                       8: "a sudden rupture or something hidden coming out", 11: "shared goals that still pay off",
                       12: "a quiet exit or the cost of staying"},
        "union": {1: "insisting on your own terms", 2: "family acceptance",
                  3: "you making the first move", 5: "real chemistry",
                  6: "old friction", 7: "the other person's own willingness",
                  10: "career pulling priorities away", 11: "friends and family helping",
                  12: "distance or secrecy"},
        "residence": {2: "the money side of the move (deposits, costs)",
                      3: "actually leaving where you are now",
                      4: "the pull to stay (lease, family or home ties)",
                      6: "a work or health obligation keeping you put",
                      8: "delays or conditions on the move (approvals, paperwork)",
                      10: "a new base tied to your work",
                      11: "the right contact or help making it happen",
                      12: "a fresh start further away"},
        "property": {3: "rushed paperwork", 4: "the right place with a clean title",
                     8: "loan or legal conditions", 11: "the right contact closing it",
                     12: "costs outrunning the value"},
    },
    "es": {
        "promotion": {2: "el aumento que trae", 6: "los resultados que ya entregaste", 10: "quienes deciden tu ascenso", 11: "una persona de peso que te respalde", 5: "apostar por un proyecto vistoso y arriesgado", 8: "política interna o un presupuesto congelado", 9: "una opción externa que te aleja", 12: "un cambio que cuesta más de lo que deja"},
        "reunion": {2: "la historia que comparten", 7: "su propio deseo de volver", 11: "amigos que los vuelven a juntar", 1: "insistir en tus propias condiciones", 6: "la vieja razón por la que se separaron", 10: "el orgullo o el qué dirán", 12: "la distancia o el silencio"},
        "speculation": {2: "solo dinero que puedes perder", 5: "una apuesta medida y limitada", 6: "un error del contrario", 11: "que la ganancia realmente llegue", 8: "una pérdida repentina", 12: "dinero que se escapa en silencio"},
        "legal": {6: "la fuerza de tu caso y tus pruebas", 11: "que te den el resultado que buscas", 5: "apostar a cómo reaccione el juez o la otra parte", 8: "demoras, apelaciones o cláusulas ocultas", 12: "costos legales que superan lo que ganarías"},
        "health": {1: "la fuerza de tu propio cuerpo", 5: "un tratamiento que te siente bien", 11: "que la recuperación se afiance", 6: "que la enfermedad siga activa", 8: "una complicación o recaída", 12: "una hospitalización o un reposo largo"},
        "travel": {3: "que los papeles y los primeros pasos avancen", 9: "que se abra la vía larga (visa, aprobación)", 12: "instalarte de verdad en un lugar lejano", 4: "lo que te ata a casa"},
        "study": {4: "estudio y preparación constantes", 9: "que la institución o el examinador te respalde", 11: "que el resultado salga", 3: "apurarte o responder sin cuidado", 8: "una demora o una revisión", 12: "distracciones o un desvío costoso"},
        "child": {2: "que la familia crezca", 5: "la concepción en sí", 11: "que el deseo se cumpla", 1: "tu propia salud que necesita cuidado primero", 4: "presiones en casa", 10: "exigencias del trabajo que roban energía"},
        "lost": {2: "que esté entre tus propias cosas", 6: "repasar tus pasos con cuidado", 11: "que alguien lo devuelva o avise", 5: "que lo hayas dejado en un sitio casual", 8: "que esté escondido o difícil de alcanzar", 12: "que se haya ido lejos o fuera de alcance"},
        "generic": {1: "tu propio impulso", 2: "tus propios recursos", 3: "tu propio seguimiento",
                    4: "tu base en casa", 5: "una apuesta arriesgada", 6: "trabajo constante y duro",
                    7: "la disposición de la otra parte", 8: "condiciones ocultas y demoras",
                    9: "un mentor o un golpe de suerte", 10: "tu posición y reputación",
                    11: "gente que ya te conoce", 12: "costos extra o pérdidas"},
        "money": {2: "tus propios ahorros", 5: "una apuesta especulativa",
                  6: "un préstamo o crédito", 7: "un socio del otro lado",
                  8: "dinero con muchas condiciones (exigencias del inversionista, due diligence larga)",
                  11: "gente que ya conoce tu trabajo", 12: "costos que se comen el dinero"},
        "sales": {2: "negocio repetido con clientes actuales", 6: "servir bien y superar a la competencia",
                  7: "la propia decisión del cliente", 8: "aprobaciones lentas o condiciones duras de contrato",
                  11: "recomendaciones de gente que conoce tu trabajo",
                  12: "acuerdos que cuestan más de lo que dejan"},
        "residence": {3: "irte de donde estás ahora", 4: "lo que te ata a quedarte (contrato, familia, hogar)",
                      8: "demoras o condiciones de la mudanza (trámites, aprobaciones)",
                      10: "una nueva base ligada a tu trabajo", 12: "un nuevo comienzo más lejos"},
        "partner": {2: "tu propia parte en esto", 6: "hacer tú mismo el trabajo práctico",
                    7: "el compromiso real de tus socios", 8: "un reparto desigual con tus socios",
                    10: "tu reputación ante quienes adjudican el trabajo",
                    11: "los contactos que aportan tus socios", 12: "costos que se acumulan antes de que pague"},
        "work": {6: "hacer bien el trabajo en sí", 10: "quienes deciden sobre el puesto",
                 11: "una recomendación de tu red"},
        "separation": {1: "que uno de los dos elija su propio camino", 2: "el dinero que tienen atado juntos",
                       6: "disputas por trabajo, dinero o condiciones", 7: "el deseo de tu socio o pareja de seguir",
                       8: "una ruptura repentina o algo oculto que sale a la luz", 11: "metas compartidas que aún rinden",
                       12: "una salida silenciosa o el costo de quedarse"},
        "union": {3: "dar tú el primer paso", 5: "química de verdad", 6: "viejas fricciones", 7: "la propia disposición de la otra persona",
                  11: "amigos y familia que ayudan"},
    },
    "pt": {
        "promotion": {2: "o aumento que vem junto", 6: "os resultados que você já entregou", 10: "quem decide a sua promoção", 11: "alguém sênior te apoiando", 5: "apostar num projeto vistoso e arriscado", 8: "política interna ou um orçamento congelado", 9: "uma opção de fora te puxando", 12: "uma mudança que custa mais do que rende"},
        "reunion": {2: "a história que vocês têm", 7: "a própria vontade de voltar", 11: "amigos reaproximando vocês", 1: "insistir nos seus próprios termos", 6: "o velho motivo da separação", 10: "o orgulho ou o que vão dizer", 12: "a distância ou o silêncio"},
        "speculation": {2: "só dinheiro que você pode perder", 5: "uma aposta medida e limitada", 6: "um erro do adversário", 11: "o ganho realmente chegar", 8: "uma perda repentina", 12: "dinheiro escapando aos poucos"},
        "legal": {6: "a força do seu caso e das suas provas", 11: "o resultado que você quer ser concedido", 5: "apostar em como o juiz ou a outra parte vai reagir", 8: "atrasos, recursos ou cláusulas ocultas", 12: "custos legais maiores do que você ganharia"},
        "health": {1: "a força do seu próprio corpo", 5: "um tratamento que funcione para você", 11: "a recuperação se firmar", 6: "a doença continuar ativa", 8: "uma complicação ou recaída", 12: "uma internação ou um repouso longo"},
        "travel": {3: "a papelada e os primeiros passos andarem", 9: "a via longa se abrir (visto, aprovação)", 12: "se estabelecer de fato num lugar distante", 4: "o que te prende em casa"},
        "study": {4: "estudo e preparação constantes", 9: "a instituição ou o examinador te apoiar", 11: "o resultado sair", 3: "pressa ou respostas descuidadas", 8: "um atraso ou uma revisão", 12: "distrações ou um desvio caro"},
        "child": {2: "a família crescer", 5: "a concepção em si", 11: "o desejo se realizar", 1: "sua própria saúde precisando de cuidado primeiro", 4: "pressões em casa", 10: "exigências do trabalho tirando energia"},
        "lost": {2: "estar entre as suas próprias coisas", 6: "refazer seus passos com cuidado", 11: "alguém devolver ou avisar", 5: "ter ficado num lugar casual", 8: "estar escondido ou difícil de alcançar", 12: "ter ido longe ou para fora de alcance"},
        "generic": {1: "seu próprio impulso", 2: "seus próprios recursos", 3: "seu próprio acompanhamento",
                    4: "sua base em casa", 5: "uma aposta arriscada", 6: "trabalho constante e duro",
                    7: "a disposição da outra parte", 8: "condições ocultas e atrasos",
                    9: "um mentor ou um golpe de sorte", 10: "sua posição e reputação",
                    11: "gente que já te conhece", 12: "custos extras ou perdas"},
        "money": {2: "suas próprias economias", 5: "uma aposta especulativa",
                  6: "um empréstimo ou crédito", 7: "um sócio do outro lado",
                  8: "dinheiro com muitas condições (exigências do investidor, due diligence longa)",
                  11: "gente que já conhece seu trabalho", 12: "custos comendo o dinheiro"},
        "sales": {2: "negócios repetidos com clientes atuais", 6: "atender bem e superar a concorrência",
                  7: "a própria decisão do cliente", 8: "aprovações lentas ou cláusulas duras de contrato",
                  11: "indicações de gente que conhece seu trabalho",
                  12: "acordos que custam mais do que rendem"},
        "residence": {3: "sair de onde você está agora", 4: "o que te prende a ficar (contrato, família, casa)",
                      8: "atrasos ou condições da mudança (papelada, aprovações)",
                      10: "uma nova base ligada ao seu trabalho", 12: "um recomeço mais longe"},
        "partner": {2: "sua própria parte nisso", 6: "fazer você mesmo o trabalho prático",
                    7: "o compromisso real dos seus sócios", 8: "uma divisão desigual com seus sócios",
                    10: "sua reputação com quem concede o trabalho",
                    11: "os contatos que seus sócios trazem", 12: "custos que se acumulam antes de pagar"},
        "work": {6: "fazer bem o trabalho em si", 10: "quem decide sobre a vaga",
                 11: "uma indicação da sua rede"},
        "separation": {1: "um de vocês escolher o próprio caminho", 2: "o dinheiro que vocês têm amarrado juntos",
                       6: "disputas por trabalho, dinheiro ou condições", 7: "a vontade do seu sócio ou parceiro de continuar",
                       8: "uma ruptura repentina ou algo oculto vindo à tona", 11: "metas em comum que ainda rendem",
                       12: "uma saída silenciosa ou o custo de ficar"},
        "union": {3: "você dar o primeiro passo", 5: "química de verdade", 6: "velhos atritos", 7: "a própria vontade da outra pessoa",
                  11: "amigos e família ajudando"},
    },
}

_TEMPLATES = {
    "en": {"and": " and ",
           "yes": "It's carried by {sup}.", "yes_drag": " Keep an eye on {blk}.",
           "cond": "It can come through {sup}; what could stop it is {blk}.",
           "gate": "The route is {sup}, but the final yes isn't locked in, so get a clear, written commitment before you count on it.",
           "gate_work": "The route is {sup}, but the final yes isn't locked in, so count on it only once the offer is in writing.",
           "gate_union": "The route is {sup}, but the final yes isn't locked in, so count on it only once you've both said a clear yes.",
           "gate_property": "The route is {sup}, but the final yes isn't locked in, so count on it only once the papers are signed.",
           "gate_study": "The route is {sup}, but the final yes isn't locked in, so count on it only once the result or admission is confirmed.",
           "gate_child": "The route is {sup}, but the final confirmation isn't there yet, so give it time and care rather than counting days.",
           "gate_lost": "It can turn up through {sup}, but it isn't certain yet, so keep looking in the likely places.",
           "gate_speculation": "The route is {sup}, but the final yes isn't locked in, so treat any win as not real until it's actually in your account.",
           "gate_sales": "The route is {sup}, but the final yes isn't locked in, so count on it only once a client has signed and paid.",
           "gate_partner": "The route is {sup}, but the final yes isn't locked in, so count on it only once the split with your partners is agreed in writing.",
           "gate_income": "The route is {sup}, but the final yes isn't locked in, so count on it only once the first payment lands.",
           "gate_blk": " Watch out for {blk}.",
           "no": "No supporting route shows up for this right now.",
           "no_blk": " What stands in the way: {blk}.",
           "label": "What it hinges on",
           "sep_yes": "What drives the split: {sup}.", "sep_yes_hold": " What could still hold it together: {blk}.",
           "sep_cond": "It can split over {sup}, unless {blk} holds it together.",
           "sep_no": "Nothing in this reading pushes it to break right now.", "sep_no_hold": " What holds it together: {blk}.",
           "generic": "This reading is general — the question doesn't name one area of life, so there's no specific condition to give. Ask it again naming the area (work, money, a relationship, a move) for a sharper read.",
           "generic_label": "Note"},
    "es": {"and": " y ",
           "yes": "Lo sostiene {sup}.", "yes_drag": " Vigila {blk}.",
           "cond": "Puede llegar a través de {sup}; lo que podría frenarlo: {blk}.",
           "gate": "La vía es {sup}, pero el sí final no está asegurado: consigue un compromiso claro y por escrito antes de contar con ello.",
           "gate_work": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando tengas la oferta por escrito.",
           "gate_union": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando ambos hayan dicho un sí claro.",
           "gate_property": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando los papeles estén firmados.",
           "gate_study": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando el resultado o la admisión estén confirmados.",
           "gate_child": "La vía es {sup}, pero la confirmación final aún no está: dale tiempo y cuidado en vez de contar los días.",
           "gate_lost": "Puede aparecer gracias a {sup}, pero aún no es seguro: sigue buscando en los lugares probables.",
           "gate_speculation": "La vía es {sup}, pero el sí final no está asegurado: no cuentes una ganancia hasta que esté en tu cuenta.",
           "gate_sales": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando un cliente haya firmado y pagado.",
           "gate_partner": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando el reparto con tus socios esté acordado por escrito.",
           "gate_income": "La vía es {sup}, pero el sí final no está asegurado: cuenta con ello solo cuando llegue el primer pago.",
           "gate_blk": " Cuidado con {blk}.",
           "no": "Ahora mismo no aparece una vía que lo respalde.",
           "no_blk": " Lo que se interpone: {blk}.",
           "label": "De qué depende",
           "sep_yes": "Lo que empuja la separación: {sup}.", "sep_yes_hold": " Lo que aún podría sostenerlo: {blk}.",
           "sep_cond": "Puede romperse por {sup}, a menos que {blk} lo sostenga.",
           "sep_no": "Nada en esta lectura lo empuja a romperse ahora.", "sep_no_hold": " Lo que lo sostiene: {blk}.",
           "generic": "Esta lectura es general: la pregunta no nombra un área de la vida, así que no hay una condición concreta que dar. Vuelve a preguntarlo nombrando el área (trabajo, dinero, una relación, una mudanza) para una lectura más precisa.",
           "generic_label": "Nota"},
    "pt": {"and": " e ",
           "yes": "Quem sustenta isso é {sup}.", "yes_drag": " Fique de olho em {blk}.",
           "cond": "Pode vir através de {sup}; o que pode impedir: {blk}.",
           "gate": "O caminho é {sup}, mas o sim final não está garantido: consiga um compromisso claro e por escrito antes de contar com isso.",
           "gate_work": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando a oferta estiver por escrito.",
           "gate_union": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando os dois tiverem dito um sim claro.",
           "gate_property": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando os papéis estiverem assinados.",
           "gate_study": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando o resultado ou a admissão forem confirmados.",
           "gate_child": "O caminho é {sup}, mas a confirmação final ainda não veio: dê tempo e cuidado em vez de contar os dias.",
           "gate_lost": "Pode aparecer por {sup}, mas ainda não é certo: continue procurando nos lugares prováveis.",
           "gate_speculation": "O caminho é {sup}, mas o sim final não está garantido: não conte um ganho até ele estar na sua conta.",
           "gate_sales": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando um cliente tiver assinado e pago.",
           "gate_partner": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando a divisão com seus sócios estiver acordada por escrito.",
           "gate_income": "O caminho é {sup}, mas o sim final não está garantido: conte com isso só quando o primeiro pagamento cair.",
           "gate_blk": " Cuidado com {blk}.",
           "no": "Agora não aparece um caminho que sustente isso.",
           "no_blk": " O que está no caminho: {blk}.",
           "label": "Do que depende",
           "sep_yes": "O que empurra a separação: {sup}.", "sep_yes_hold": " O que ainda pode segurar: {blk}.",
           "sep_cond": "Pode romper por {sup}, a menos que {blk} segure.",
           "sep_no": "Nada nesta leitura empurra para romper agora.", "sep_no_hold": " O que segura: {blk}.",
           "generic": "Esta leitura é geral: a pergunta não nomeia uma área da vida, então não há uma condição específica para dar. Pergunte de novo nomeando a área (trabalho, dinheiro, um relacionamento, uma mudança) para uma leitura mais precisa.",
           "generic_label": "Nota"},
}


_FUNDING_Q = re.compile(r"(?i)\b(fund|funding|funded|invest|investor|investment|raise|raising|"
                        r"loan|capital|financ\w*|inversi\w*|pr[eé]stamo|empr[eé]stimo|captar|aporte)")
_SALES_Q = re.compile(r"(?i)\b(client|clients|customer|customers|sale|sales|deal|deals|contract|"
                      r"order|orders|lead|leads|cliente|clientes|venta|ventas|venda|vendas|"
                      r"contrato|pedido|pedidos|"
                      # [kp-advisory 2026-10-03] advisory / consulting / services earn from
                      # clients ("gold advisory" was read as generic side income)
                      r"advisory|advisor|adviser|advising|consult\w*|agency|services|freelanc\w*|"
                      r"asesor\w*|consultor\w*|assessor\w*|consultoria|agencia|agência)\b")


_PARTNER_Q = re.compile(r"(?i)(\bwith (?:other people|others|partners?|my partners?|a partner|friends)\b|"
                        r"\bpartners?(?:hip)?\b|\bjoint venture\b|\bco-?founders?\b|"
                        r"\bs[oó]ci[oa]s?\b|\bsociedad\b|\bsociedade\b|"
                        r"\bcon otr[oa]s\b|\bcom outr[oa]s\b)")


# [vehicle-condition 2026-10-08] KP files a car/vehicle purchase or lease under "property" (4th
# house), so "Can I lease a car?" was told it hinges on "the right place with a clean title" and
# "rushed paperwork" — house-buying words. The KP maths is unchanged; only the plain meanings change.
_HOUSE["en"]["vehicle"] = {
    3: "signing in a rush", 4: "the right car on terms you've read in full",
    8: "fine print (mileage caps, end-of-lease charges, hidden fees)",
    11: "a dealer or lender you already trust closing it",
    12: "the total cost (fees, insurance, deposit) outrunning the value"}
_HOUSE["es"]["vehicle"] = {
    3: "firmar con prisa", 4: "el coche adecuado con condiciones que leíste completas",
    8: "la letra pequeña (límite de kilometraje, cargos al final del contrato, comisiones ocultas)",
    11: "un concesionario o financiador de confianza que lo cierre",
    12: "que el costo total (comisiones, seguro, depósito) supere el valor"}
_HOUSE["pt"]["vehicle"] = {
    3: "assinar com pressa", 4: "o carro certo com condições que você leu por inteiro",
    8: "as letras miúdas (limite de quilometragem, cobranças no fim do contrato, taxas ocultas)",
    11: "uma concessionária ou financiadora de confiança fechando",
    12: "o custo total (taxas, seguro, entrada) passar do valor"}
_VEHICLE_Q = re.compile(r"(?<!\w)(car|cars|vehicle|suv|truck|van|motorcycle|bike|scooter|"
                        r"coche|auto|autom[oó]vil|moto|carro|ve[ií]culo|gaadi|gadi|gaadee)(?!\w)", re.I)


def _money_family(question: str) -> str:
    """KP files funding, clients and income under one 'gain' type; the reader's
    words decide which plain meanings fit (a clients question isn't about loans)."""
    q = question or ""
    if _FUNDING_Q.search(q):
        return "money"
    if _PARTNER_Q.search(q):
        return "partner"          # [kp-partner 2026-10-03] "…business with other people"
    if _SALES_Q.search(q):
        return "sales"
    return "income"


def _lang(language: str) -> str:
    l = (language or "en").lower()[:2]
    return l if l in _TEMPLATES else "en"


def _phrase(house: int, family: str, lang: str) -> Optional[str]:
    t = _HOUSE[lang]
    return (t.get(family) or {}).get(house) or t["generic"].get(house) or (
        _HOUSE["en"].get(family) or {}).get(house) or _HOUSE["en"]["generic"].get(house)


def _join(items: list, lang: str) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + _TEMPLATES[lang]["and"] + items[-1]


def explain(kp: dict, language: str = "en", question: str = "") -> dict:
    """{'supports': [...], 'blocks': [...], 'close_ok': bool, 'condition': str,
    'label': str} — empty dict when the KP result has no usable debug."""
    kp = kp or {}
    dbg = kp.get("debug") or {}
    qt = kp.get("question_type") or dbg.get("question_type") or ""
    if not dbg or "favour_hit" not in dbg:
        return {}
    lang = _lang(language)
    family = _FAMILY.get(qt, "generic")
    if kp.get("generic"):
        # [kp-honest-generic 2026-10-03] owner: "can't have same answers or reasoning
        # for every question". An unrecognised matter has no area-specific houses to
        # name — say so, never dress generic house meanings up as a specific condition.
        T = _TEMPLATES[lang]
        return {"supports": [], "blocks": [], "close_ok": dbg.get("gate_ok", True) is not False,
                "condition": T["generic"], "label": T["generic_label"], "generic": True}
    if family == "property" and _VEHICLE_Q.search(question or kp.get("question") or ""):
        family = "vehicle"
    if family == "money" and qt != "speculation":
        family = _money_family(question or kp.get("question") or "")
    sup = [_phrase(h, family, lang) for h in (dbg.get("favour_hit") or [])]
    blk = [_phrase(h, family, lang) for h in (dbg.get("against_hit") or [])]
    gate_ok = dbg.get("gate_ok", True) is not False
    lean = str(kp.get("lean") or dbg.get("horary_verdict") or "").lower()
    T = _TEMPLATES[lang]
    # [kp-one-condition 2026-10-03] "Possible — on one condition" must then name ONE
    # condition, not a list of four worries: at most one watch-out next to the
    # closing gate or a yes, two next to a conditional/no.
    _rank = [8, 12, 7, 5, 4, 3, 2, 6, 9, 10, 11, 1]
    _bh = sorted(dbg.get("against_hit") or [], key=lambda h: _rank.index(h) if h in _rank else 99)
    blk_top = [_phrase(h, family, lang) for h in _bh]
    s = _join(sup, lang)
    b1, b2 = _join(blk_top[:1], lang), _join(blk_top[:2], lang)
    if family == "separation":
        # favour = what drives the ending; against = what keeps it together
        if lean in ("no",) or not sup:
            text = T["sep_no"] + (T["sep_no_hold"].format(blk=b2) if b2 else "")
        elif lean in ("conditional", "not_now") and b1:
            text = T["sep_cond"].format(sup=s, blk=b1)
        else:
            text = T["sep_yes"].format(sup=s) + (T["sep_yes_hold"].format(blk=b1) if b1 else "")
    elif lean in ("no",) or not sup:
        text = T["no"] + (T["no_blk"].format(blk=b2) if b2 else "")
    elif not gate_ok:
        g = (T.get("gate_" + family) or T.get("gate_" + {"promotion": "work", "reunion": "union"}.get(family, ""))
             or T["gate"])
        text = g.format(sup=s) + (T["gate_blk"].format(blk=b1) if b1 else "")
    elif lean in ("conditional", "not_now") and b2:
        text = T["cond"].format(sup=s, blk=b2)
    else:
        text = T["yes"].format(sup=s) + (T["yes_drag"].format(blk=b1) if b1 else "")
    return {"supports": sup, "blocks": blk, "close_ok": gate_ok,
            "condition": text, "label": T["label"]}
