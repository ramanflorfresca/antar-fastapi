-- ============================================================================
-- sql_event_engine_config.sql
-- Named life-event engine: tunable vocabulary + age bands + stage gates
-- (Cowork brief 2026-06-11). Raman tunes mappings here — NO code change needed.
--
-- PURELY ADDITIVE: CREATE TABLE + seed INSERTs (ON CONFLICT DO NOTHING).
-- Touches nothing pre-existing. Run in the Supabase SQL Editor.
--
-- All numeric house/karaka values are DRAFT — founder to correct.
-- The engine falls back to identical hardcoded defaults if this table is
-- missing or unreadable (antar_engine/event_gating.py).
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_engine_config (
    event_type      text PRIMARY KEY,
    domain          text NOT NULL,          -- Career|Business|Love|Family|Health
    houses          text NOT NULL,          -- CSV, e.g. '6,10,11' (draft)
    karaka          text NOT NULL,          -- primary karaka planet (draft)
    direction       text NOT NULL DEFAULT 'opening',  -- opening|watch
    -- trapezoid age-plausibility curve (soft): rise → peak_start → peak_end → fade
    age_rise        int  NOT NULL,
    age_peak_start  int  NOT NULL,
    age_peak_end    int  NOT NULL,
    age_fade        int  NOT NULL,
    -- hard stage gates (NULL = none). Values the engine understands:
    --   requires_prior_partnership | suppress_if_married | requires_partnership_fertile
    stage_rule      text NULL,
    -- forward tolerance: events land up to this many days AFTER the dasha
    -- window (systematic early-bias measured on 3 ground-truth charts)
    window_tolerance_days int NOT NULL DEFAULT 60,
    enabled         boolean NOT NULL DEFAULT true,
    draft           boolean NOT NULL DEFAULT true,   -- awaiting founder ruling
    updated_at      timestamptz NOT NULL DEFAULT now()
);

INSERT INTO event_engine_config
(event_type, domain, houses, karaka, direction, age_rise, age_peak_start, age_peak_end, age_fade, stage_rule, window_tolerance_days, enabled, draft) VALUES
('career_pivot',              'Career',   '6,10,11', 'Sun',     'opening', 18, 20, 62, 66, NULL,                          60, true, true),
('professional_setback',      'Career',   '6,8,10',  'Saturn',  'watch',   18, 20, 62, 66, NULL,                          60, true, true),
('financial_disruption',      'Business', '2,6,8',   'Saturn',  'watch',   22, 26, 60, 68, NULL,                          60, true, true),
('legal_entanglement',        'Business', '6,8,12',  'Mars',    'watch',   22, 26, 60, 70, NULL,                          60, true, true),
('major_acquisition',         'Business', '4,2,11',  'Venus',   'opening', 21, 25, 65, 75, NULL,                          60, true, true),
('serious_partnership_began', 'Love',     '7,2,5',   'Venus',   'opening', 18, 22, 35, 45, 'suppress_if_married',         90, true, true),
('serious_partnership_ended', 'Love',     '7,6,8',   'Saturn',  'watch',   24, 28, 55, 62, 'requires_prior_partnership',  90, true, true),
('family_expansion_first',    'Family',   '5,9',     'Jupiter', 'opening', 20, 24, 42, 48, 'requires_partnership_fertile',90, true, true),
('family_expansion_second',   'Family',   '5,9',     'Jupiter', 'opening', 22, 26, 44, 50, 'requires_partnership_fertile',90, true, true),
('major_relocation',          'Family',   '4,3,12',  'Rahu',    'opening', 16, 18, 70, 80, NULL,                          60, true, true),
('loss_of_father',            'Family',   '9,8',     'Sun',     'watch',   30, 40, 70, 80, NULL,                          90, true, true),
('loss_of_mother',            'Family',   '4,8',     'Moon',    'watch',   35, 45, 75, 85, NULL,                          90, true, true)
ON CONFLICT (event_type) DO NOTHING;
