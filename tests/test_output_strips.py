"""
Unit tests for antar_engine/output_strips.py

Run:  pytest tests/test_output_strips.py -v
"""

import pytest

from antar_engine.output_strips import (
    apply_user_facing_strips,
    _strip_instrument_names,
    _strip_vedic_jargon,
    _strip_raw_scores,
    _strip_day_names,
    _strip_planet_names,
    _translate_instrument_name,
)


# ─── _strip_instrument_names ──────────────────────────────────

def test_instrument_strip_replaces_codename_es():
    out = _strip_instrument_names('your Magnetism Field is active', 'es')
    assert 'Magnetism Field' not in out
    assert 'campo magnético' in out.lower()


def test_instrument_strip_handles_your_possessive():
    out = _strip_instrument_names('Your Ambition Engine empuja', 'es')
    # "Your Motor de Ambición" → "tu motor de ambición"
    assert 'your' not in out.lower()
    assert 'motor de ambición' in out.lower()


def test_instrument_strip_noop_for_english():
    s = 'your Magnetism Field is active'
    assert _strip_instrument_names(s, 'en') == s


# ─── _strip_vedic_jargon ──────────────────────────────────────

def test_vedic_strip_removes_named_yogas():
    out = _strip_vedic_jargon('Dos yogas muy auspiciosos: Gajakesari y Shubha Kartari', 'es')
    assert 'Gajakesari' not in out
    assert 'Shubha Kartari' not in out
    assert 'yogas' not in out.lower()


def test_vedic_strip_translates_compound_panchang():
    # "Abhijit Muhurta" must translate as a unit before the generic
    # "Muhurta → ventana" rule fires.
    out = _strip_vedic_jargon('Usa el Abhijit Muhurta hoy', 'es')
    assert 'Abhijit' not in out
    assert 'mediodía' in out.lower()


def test_vedic_strip_translates_md_ad_compound():
    out = _strip_vedic_jargon('Saturno MD + Marte AD presionan', 'es')
    assert ' MD ' not in f' {out} '
    assert ' AD ' not in f' {out} '
    assert 'período mayor' in out.lower()
    assert 'subperíodo' in out.lower()


def test_vedic_strip_preserves_planets():
    # _strip_vedic_jargon must NOT touch planet names; that's the
    # planet stripper's job.
    out = _strip_vedic_jargon('Saturno transita la casa 10', 'es')
    assert 'Saturno' in out


# ─── _strip_raw_scores ────────────────────────────────────────

def test_raw_scores_removed():
    assert '23/56' not in _strip_raw_scores('La energía es baja (23/56) hoy')
    assert '48/56' not in _strip_raw_scores('Júpiter fuerte (48/56) apoya')


def test_raw_scores_keeps_surrounding_prose():
    out = _strip_raw_scores('La energía es baja (23/56) hoy')
    assert 'baja' in out
    assert 'hoy' in out


def test_raw_scores_noop_if_no_match():
    assert _strip_raw_scores('Sin scores aquí') == 'Sin scores aquí'


# ─── _strip_day_names ─────────────────────────────────────────

def test_day_names_bare_dropped():
    out = _strip_day_names('El martes es un buen día para actuar', 'es')
    assert 'martes' not in out.lower()


def test_day_names_qualified_collapse_to_today():
    out = _strip_day_names('Este domingo descansa', 'es')
    assert 'domingo' not in out.lower()
    assert 'hoy' in out.lower()


def test_day_names_en_bare_dropped():
    out = _strip_day_names('On Tuesday the energy shifts', 'en')
    assert 'Tuesday' not in out


# ─── _strip_planet_names ──────────────────────────────────────

def test_planet_names_es_translated():
    out = _strip_planet_names('Saturno presiona la casa 10 hoy', 'es')
    assert 'Saturno' not in out
    assert 'disciplina' in out.lower()


def test_planet_names_drops_house_number():
    out = _strip_planet_names('10th house lord activates', 'en')
    assert '10th' not in out
    assert 'house' not in out.lower()


# ─── _translate_instrument_name ───────────────────────────────

def test_translate_instrument_label_exact_match():
    assert _translate_instrument_name('MAGNETISM FIELD', 'es') == 'CAMPO MAGNÉTICO'


def test_translate_instrument_label_case_insensitive():
    assert _translate_instrument_name('magnetism field', 'es') == 'CAMPO MAGNÉTICO'


def test_translate_instrument_label_english_noop():
    assert _translate_instrument_name('MAGNETISM FIELD', 'en') == 'MAGNETISM FIELD'


def test_translate_instrument_label_unknown_passthrough():
    assert _translate_instrument_name('NOT A LABEL', 'es') == 'NOT A LABEL'


# ─── apply_user_facing_strips — field_type='plain' ────────────

def test_apply_plain_full_strip_es():
    text = 'your Magnetism Field con tara Ati-Mitra (23/56) este martes'
    out = apply_user_facing_strips(text, 'es', field_type='plain')
    assert 'Magnetism' not in out
    assert 'tara' not in out.lower()
    assert '23/56' not in out
    assert 'martes' not in out.lower()


def test_apply_plain_compound_vedic_preserved_through_pipeline():
    # Ordering regression guard: "Abhijit Muhurta" must get translated
    # to "ventana favorable del mediodía" before _strip_planet_names'
    # banned-Sanskrit sweep would strip "muhurta" alone.
    text = 'Usa el Abhijit Muhurta para decidir'
    out = apply_user_facing_strips(text, 'es', field_type='plain')
    assert 'Abhijit' not in out
    assert 'mediodía' in out.lower()


# ─── apply_user_facing_strips — field_type='evidence' ─────────

def test_apply_evidence_keeps_vedic_and_scores():
    text = 'Saturno MD + tara Ati-Mitra (23/56) activa'
    out = apply_user_facing_strips(text, 'es', field_type='evidence')
    assert 'Saturno' in out
    assert 'tara' in out.lower()         # Vedic retained
    assert '23/56' in out                # score retained


def test_apply_evidence_still_strips_instruments():
    text = 'Tu Ambition Engine con Saturno MD'
    out = apply_user_facing_strips(text, 'es', field_type='evidence')
    assert 'Ambition Engine' not in out
    assert 'Saturno' in out


# ─── apply_user_facing_strips — field_type='window' ───────────

def test_apply_window_keeps_panchang():
    text = 'Ventana favorable (Abhijit Muhurta) — úsala hoy'
    out = apply_user_facing_strips(text, 'es', field_type='window')
    assert 'Abhijit Muhurta' in out       # Panchang preserved


def test_apply_window_strips_instrument():
    text = 'Magnetism Field abierto hasta Abhijit Muhurta'
    out = apply_user_facing_strips(text, 'es', field_type='window')
    assert 'Magnetism Field' not in out
    assert 'Abhijit Muhurta' in out


# ─── apply_user_facing_strips — recursion + non-strings ───────

def test_recursive_dict_and_list():
    d = {
        'senal_de_hoy': 'your Magnetism Field',
        'haz_hoy': ['con tara Ati-Mitra', 'otra tarea'],
    }
    out = apply_user_facing_strips(d, 'es', field_type='plain')
    assert 'Magnetism' not in out['senal_de_hoy']
    assert 'tara' not in out['haz_hoy'][0].lower()
    assert out['haz_hoy'][1] == 'otra tarea'


def test_handles_none_and_non_string_scalars():
    assert apply_user_facing_strips(None, 'es') is None
    assert apply_user_facing_strips(42, 'es') == 42
    assert apply_user_facing_strips(3.14, 'es') == 3.14
    assert apply_user_facing_strips(True, 'es') is True
    assert apply_user_facing_strips([], 'es') == []
    assert apply_user_facing_strips({}, 'es') == {}
    assert apply_user_facing_strips('', 'es') == ''


def test_invalid_field_type_raises():
    with pytest.raises(ValueError):
        apply_user_facing_strips('x', 'es', field_type='bogus')


def test_invalid_depth_raises():
    with pytest.raises(ValueError):
        apply_user_facing_strips('x', 'es', depth='bogus')


# ─── depth='power_user' gate ──────────────────────────────────

def test_power_user_depth_keeps_vedic_on_plain():
    text = 'Gajakesari activo'
    out_user = apply_user_facing_strips(text, 'es', field_type='plain', depth='user')
    out_pro  = apply_user_facing_strips(text, 'es', field_type='plain', depth='power_user')
    assert 'Gajakesari' not in out_user
    assert 'Gajakesari' in out_pro


# ─── Regression: el_movimiento-style evidence stays untouched ─

def test_evidence_el_movimiento_preserves_full_depth():
    em = 'Saturno MD + Marte AD activan casa 10. Tara Vipat + Gulika Kala (23/56).'
    out = apply_user_facing_strips(em, 'es', field_type='evidence')
    for token in ('Saturno', 'Marte', 'MD', 'AD', 'Tara', 'Gulika Kala', '23/56'):
        assert token in out, f'{token!r} lost from evidence output: {out!r}'


# [output-strips] timing field tests
# ═══════════════════════════════════════════════════════════════
# Added with Phase 3.3 (weekly_briefing migration): field_type='timing'
# is 'plain' minus the day-name strip.  Used for best_day / best_week
# style fields where the weekday is the information.

def test_timing_preserves_day_names():
    out = apply_user_facing_strips('Wednesday — mid-week clarity', 'en', field_type='timing')
    assert 'Wednesday' in out


def test_timing_still_strips_vedic():
    out = apply_user_facing_strips(
        'Tuesday — Gajakesari yoga active', 'en', field_type='timing'
    )
    assert 'Tuesday' in out
    assert 'Gajakesari' not in out


def test_timing_still_strips_instruments_in_spanish():
    out = apply_user_facing_strips(
        'Miércoles — tu Magnetism Field fuerte', 'es', field_type='timing'
    )
    assert 'Miércoles' in out            # day preserved
    assert 'Magnetism Field' not in out  # instrument translated
    assert 'campo magnético' in out.lower()


def test_timing_still_strips_raw_scores():
    out = apply_user_facing_strips(
        'Friday — strong flow (48/56)', 'en', field_type='timing'
    )
    assert 'Friday' in out
    assert '48/56' not in out


def test_timing_translates_planet_names():
    out = apply_user_facing_strips(
        'Monday — Saturn pressure eases', 'en', field_type='timing'
    )
    assert 'Monday' in out
    # Saturn → energy phrase
    assert 'Saturn' not in out or 'discipline' in out.lower()


# [plural-days] regression tests
# ═══════════════════════════════════════════════════════════════
# Phase 3.4 production curl caught 'saturdays' leaking because
# \b{day}\b doesn't match when the trailing 's' is a word-char.
# Pattern now allows \b{day}s?\b so both forms are stripped.

def test_day_names_plural_en():
    out = _strip_day_names('Saturdays are the strongest days', 'en')
    assert 'saturday' not in out.lower()


def test_day_names_plural_lowercase_en():
    out = _strip_day_names('three saturdays of momentum', 'en')
    assert 'saturday' not in out.lower()


def test_day_names_plural_es():
    out = _strip_day_names('Los sábados son fuertes', 'es')
    assert 'sábado' not in out.lower()
    assert 'sabado' not in out.lower()


def test_day_names_apply_plain_catches_plural_en():
    out = apply_user_facing_strips(
        'On Saturdays the window opens', 'en', field_type='plain'
    )
    assert 'saturday' not in out.lower()


def test_day_names_qualified_plural_collapses_to_today_en():
    out = _strip_day_names('the Saturdays ahead', 'en')
    # 'the Saturdays' → qualified form collapses to 'today'
    assert 'saturday' not in out.lower()
    assert 'today' in out.lower()
