from antar_engine.answer_polish import polish_answer

READ = ("Jaime, tu proyecto avanza pero más lentamente de lo que tu esfuerzo merece. Lo que sí funciona es tu red de contactos. "
        "Mantén el proyecto activo y visible, pero no busques financiación todavía — espera hasta finales de 2027. "
        "Se sostiene si dejas que los resultados se acumulen.")
EN = ("Your project is moving, but slower than your effort deserves. Your network is the lever right now. "
      "Hold off on raising funding until late 2027. It holds if results are allowed to compound.")


def _run(read, q, concern, lang="es"):
    return polish_answer({"read": read, "next": "Muestra el proyecto a un contacto clave."}, lang, typed_question=q, concern=concern)["read"]


def test_business_question_drops_unasked_funding_sentence():
    assert "financiaci" not in _run(READ, "¿Cómo se ven los próximos meses para mi proyecto?", "business")
    assert "funding" not in _run(EN, "How do the next months look for my project?", "business", "en")


def test_funding_question_keeps_it():
    assert "financiaci" in _run(READ, "¿Cuándo es el mejor momento para conseguir financiación?", "funding")
    assert "financiaci" in _run(READ, "¿Debo buscar financiación para mi proyecto?", "business")
