"""[partner-lean 2026-10-04] alone-or-partner gets one answer (Jaime flipped run to run)."""
from antar_engine import partner_lean as pl
from antar_engine import wealth_magnitude as wm


def test_detector():
    for q in ("Should I build alone or bring in a partner?", "¿Debo emprender solo o con un socio?",
              "Devo empreender sozinho ou com um sócio?", "Akele build karun ya partner ke saath?"):
        assert pl.is_alone_or_partner(q), q
    for q in ("Is my partner loyal?", "Solo quiero saber mi dinero"):
        assert not pl.is_alone_or_partner(q), q


def test_every_case_has_directive_and_four_language_opener():
    for case in ("partner_yes", "partner_yes_later", "partner_solo"):
        assert "`next`" in pl.PARTNER_DIRECTIVE[case]
        assert set(pl.PARTNER_OPENER[case]) == {"en", "es", "pt", "hi"}


def test_opener_replaces_the_narrators_flip():
    r = wm.apply_alloc_opener("Jaime, un socio podría reducir esa carga. Tu negocio crece. Contrata ayuda. "
                              "Revisa en 2027.", "partner_solo", "es", "Jaime",
                              openers=pl.PARTNER_OPENER, restate=pl.PARTNER_RESTATE)
    assert r.startswith("Jaime, la lectura dice que por ahora lo mantengas tuyo") and "reducir esa carga" not in r


def test_thin_guard_keeps_content():
    r = wm.apply_alloc_opener("Jaime, un solo negocio es el riesgo. Concentrar todo es el riesgo. Protege un fondo.",
                              "spread_single", "es", "Jaime")
    assert "Protege un fondo" in r and "Concentrar todo" in r   # second drop skipped: <3 would remain
