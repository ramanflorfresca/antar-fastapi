"""detect_concern routes everyday Spanish / Portuguese questions (it used to say 'general')."""
import pytest

from antar_engine.astrological_rules import detect_concern


@pytest.mark.parametrize("q,concern", [
    ("¿Voy a conseguir un nuevo trabajo este año?", "career"),
    ("¿Debo cambiar de trabajo?", "career"),
    ("¿Cuándo me ascenderán?", "career"),
    ("Vou conseguir um emprego novo?", "career"),
    ("Tenho uma entrevista, vou passar?", "career"),
    ("¿Me voy a casar?", "marriage"),
    ("Vou me casar este ano?", "marriage"),
    ("Quando vou me casar?", "marriage"),
    ("¿Cómo estará mi salud?", "health"),
    ("minha saúde vai melhorar?", "health"),
    ("Preciso fazer uma cirurgia?", "health"),
    ("Qual o melhor momento para abrir um negócio?", "business"),
    ("¿Es buen momento para abrir un negocio?", "business"),
    ("Vou ganhar mais dinheiro?", "wealth"),
    ("¿Tendré un buen sueldo?", "wealth"),
    ("¿Cuándo tendré paz interior?", "spiritual"),
])
def test_es_pt_questions_route(q, concern):
    assert detect_concern(q) == concern


@pytest.mark.parametrize("q", [
    "What does my ascendant say about me?",     # 'ascend' must not read as a promotion
    "Is a casa nueva a good idea?",             # residence still wins, not marriage
    "hello there",
])
def test_no_new_false_positives(q):
    assert detect_concern(q) in ("general", "property")
