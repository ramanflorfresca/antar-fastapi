from antar_engine.answer_polish import drop_health_contradiction

ES = ("Jaime, tu salud este año necesita más atención de la usual. La energía y recuperación de tu cuerpo están bajo tensión real. "
      "El riesgo se mantiene bajo si actúas pronto. Tu salud está bien apoyada ahora, así que los hábitos pequeños rinden mucho. "
      "Se rompe si se aguanta la tensión sin dejar tiempo de recuperación.")
EN = ("This year calls for real attention to your health. Risk stays small if you act early. "
      "Your health is well supported right now, so small habits go a long way. It breaks if strain is pushed through without recovery time.")
CALM = ("Your health looks steady this year. Risk stays small if you act early. "
        "Your health is well supported right now, so small habits go a long way. It breaks if sleep is neglected for weeks.")
CALM_WITH_TEMPLATE_STRAIN = ("Your health looks steady this year. Risk stays small if you act early. "
                             "Your health is well supported right now, so small habits go a long way. It breaks if strain is pushed through without recovery time.")


def test_reassurance_dropped_when_read_says_strain():
    for t in (ES, EN):
        out, changed = drop_health_contradiction(t)
        assert changed and "apoyada ahora" not in out and "well supported right now" not in out


def test_reassurance_kept_when_read_is_calm():
    assert drop_health_contradiction(CALM) == (CALM, False)


def test_template_break_line_alone_does_not_count_as_strain():
    assert drop_health_contradiction(CALM_WITH_TEMPLATE_STRAIN) == (CALM_WITH_TEMPLATE_STRAIN, False)
