-- ============================================================================
-- sql_event_delivery_bands.sql
-- PD-delivery rule, AI-derived from the 3-chart / 11-event ground-truth set
-- (2026-06-11) and stored as DETERMINISTIC config. No LLM at runtime.
--
-- Empirical finding: externally-confirmed events (marriage, children,
-- divorce, parent loss, job change, relocation) deliver at fraction
-- 0.38–0.89 through the qualifying AD (median ≈0.6) — never the opening
-- third. Self-initiated beginnings (startup, live-in) fire at the AD's
-- opening (≤0.05). The mapper was emitting the opening PD for everything —
-- that WAS the measured 9–25-month early bias.
--
-- delivery_center/_halfwidth are FRACTIONS of the qualifying AD span.
-- NULL center = keep the mapper's raw PD window (events that land on time,
-- e.g. property purchases). Values are CALIBRATION-SET DRAFT — re-tune on a
-- fresh chart set before any user-facing claim.
--
-- ONLY touches event_engine_config (ours, created 2026-06-11). Additive
-- column + UPDATE/INSERT on that table only. Run AFTER sql_event_engine_config.sql.
-- ============================================================================

ALTER TABLE event_engine_config
    ADD COLUMN IF NOT EXISTS delivery_center    real NULL,
    ADD COLUMN IF NOT EXISTS delivery_halfwidth real NULL,
    ADD COLUMN IF NOT EXISTS min_score          real NOT NULL DEFAULT 6.0;

UPDATE event_engine_config SET delivery_center=0.45, delivery_halfwidth=0.20 WHERE event_type='serious_partnership_began';
UPDATE event_engine_config SET delivery_center=0.63, delivery_halfwidth=0.20 WHERE event_type='serious_partnership_ended';
UPDATE event_engine_config SET delivery_center=0.70, delivery_halfwidth=0.20 WHERE event_type='family_expansion_first';
UPDATE event_engine_config SET delivery_center=0.70, delivery_halfwidth=0.20 WHERE event_type='family_expansion_second';
UPDATE event_engine_config SET delivery_center=0.75, delivery_halfwidth=0.20 WHERE event_type='career_pivot';
UPDATE event_engine_config SET delivery_center=0.50, delivery_halfwidth=0.20 WHERE event_type='loss_of_father';
UPDATE event_engine_config SET delivery_center=0.50, delivery_halfwidth=0.20 WHERE event_type='loss_of_mother';
UPDATE event_engine_config SET delivery_center=0.62, delivery_halfwidth=0.20, min_score=4.0 WHERE event_type='major_relocation';
-- major_acquisition: lands on time → NULL center, keep raw windows

-- business_start: new event type. Significations (classical, DRAFT):
-- 3H self-effort/initiative, 7H commerce, 10H karma, 11H gains;
-- Mercury = commerce karaka, Mars = initiative, Rahu = entrepreneurial leap.
-- Initiation regime: fires at the AD opening.
INSERT INTO event_engine_config
(event_type, domain, houses, karaka, direction, age_rise, age_peak_start, age_peak_end, age_fade, stage_rule, window_tolerance_days, enabled, draft, delivery_center, delivery_halfwidth, min_score)
VALUES ('business_start', 'Business', '3,7,10,11', 'Mercury', 'opening', 22, 25, 55, 62, NULL, 60, true, true, 0.10, 0.12, 6.0)
ON CONFLICT (event_type) DO NOTHING;
