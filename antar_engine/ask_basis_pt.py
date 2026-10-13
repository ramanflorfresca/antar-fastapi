"""[pt-moves 2026-10-11] Portuguese chart-linked FALLBACK moves.

The Portuguese drift audit found a canned fallback ("A partir desta semana, mova uma parte fixa de cada pagamento…") because
chart_move() only existed for en / es: whenever the model's move was dropped (pressure, generic) a Portuguese reader got the
stock line. Same facts and the same weakness test as ask_basis / ask_basis_es, native Portuguese. Only chart_move is here —
the 📍 line and the holds / breaks lines are not built for Portuguese (not a priority)."""
from __future__ import annotations

from antar_engine import ask_basis as B
from antar_engine import ask_basis_es as _ES          # the fact-gathering is language-neutral
from antar_engine import decision_i18n as I18

# the channel text comes after "por este canal:" so a leading article never collides with a preposition
_ACT = {
    "career": "ponha o esforço neste canal: {ch} — e leve um resultado concreto a quem decide",
    "business": "ponha o esforço neste canal: {ch} — e lance a menor versão que consiga gerar receita",
    "love": "a proximidade chega até você por este canal: {ch} — dê o primeiro passo por aí em vez de esperar ser encontrado",
    "marriage": "a proximidade chega até você por este canal: {ch} — dê o primeiro passo por aí em vez de esperar ser encontrado",
    "reconciliation": "faça um primeiro contato breve e direto dentro da sua janela — a proximidade chega até você por este canal: {ch}; procure por aí e deixe a outra pessoa decidir o próximo passo",
    "wealth": "separe uma parte fixa de cada pagamento antes de gastar e ponha o esforço novo neste canal: {ch}",
    "finance": "separe uma parte fixa de cada pagamento antes de gastar e ponha o esforço novo neste canal: {ch}",
    "property": "defina o seu teto e o que é indispensável antes de visitar qualquer coisa — esta decisão passa por este canal: {ch}",
    "funding": "prepare primeiro os registros — o pedido passa por este canal: {ch}",
    "children": "organize suas finanças e o seu apoio antes de a janela abrir — esta área aparece por este canal: {ch}",
    "domestic_move": "defina o indispensável e o orçamento antes de se comprometer com um lugar — esta decisão passa por este canal: {ch}",
    "foreign": "liste o que precisa estar pronto para mudar para o exterior ser realista — dinheiro, trabalho, situação legal — e comece pelo que você controla; esta área se abre por este canal: {ch}",
    "foreign_move": "liste o que precisa estar pronto para mudar para o exterior ser realista — dinheiro, trabalho, situação legal — e comece pelo que você controla; esta área se abre por este canal: {ch}",
    "education": "escolha um programa e um prazo de trabalho, e ponha o esforço neste canal: {ch}",
    "family": "decida uma coisa concreta para fazer pelas pessoas mais próximas este mês e conte a elas — esta área rende por este canal: {ch}",
    "legal": "reúna seus documentos em um só lugar e peça orientação sobre a pergunta que mais importa — esta área se move por este canal: {ch}",
    "divorce": "decida o que precisa estar resolvido primeiro e consiga por escrito — isto passa por este canal: {ch}",
    "loss": "liste o que está em risco e proteja primeiro o mais importante — os vazamentos aqui vêm por este canal: {ch}",
}


def chart_move(concern, chart_data, dashas) -> str:
    try:
        if concern not in B._ACT:
            return ""
        f = _ES._facts(concern, chart_data, dashas)
        if not f:
            return ""
        ch = B._PT_CHANNEL.get(f["pl"]["house"], "")
        if not ch:
            return ""
        end = I18.date_long(f["end"], "pt") if f["end"] else ""
        if concern == "health":
            when = (f" Conte com uma recuperação mais lenta durante esta etapa (até {end}) — não espere que se resolva sozinha."
                    if (f["weak"] and end) else "")
            return "Organize primeiro os horários de sono e de refeição e faça checar cedo qualquer coisa incomum." + when
        if concern == "speculation":
            tail = f" Reavalie quando esta etapa terminar em {end}." if (f["weak"] and end) else ""
            return ("Defina o máximo que você pode perder, escreva antes de colocar qualquer coisa e pare nesse número — "
                    "os ganhos aqui chegam aos trancos e escapam." + tail)
        act = _ACT.get(concern)
        if not act:
            return ""
        lead = ""      # [weak-leadin] the weakness is said once, in plain words, in conditions()
        tail = f" Reavalie quando esta etapa terminar em {end}." if (f["weak"] and end) else ""
        out = lead + act.format(ch=ch) + "." + tail
        return out[0].upper() + out[1:]
    except Exception:
        return ""
