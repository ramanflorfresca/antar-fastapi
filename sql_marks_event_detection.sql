-- ============================================================================
-- sql_marks_event_detection.sql
-- Event-detection framing for the admin accuracy tally (Cowork brief
-- 2026-06-11, CHANGE 4): hit / miss / phantom instead of binary
-- accurate/inaccurate, + conviction stored per mark for later calibration.
--
-- ONLY touches prediction_accuracy_marks — the isolated table created by
-- sql_prediction_accuracy_marks.sql on 2026-06-11. No other table is read,
-- altered, or written. (The additive-only discipline protects PRE-EXISTING
-- tables; this one is ours, created this week, holding test marks only.)
--
-- Run in the Supabase SQL Editor AFTER sql_prediction_accuracy_marks.sql.
-- ============================================================================

ALTER TABLE prediction_accuracy_marks
    DROP CONSTRAINT IF EXISTS prediction_accuracy_marks_mark_check;

ALTER TABLE prediction_accuracy_marks
    ADD CONSTRAINT prediction_accuracy_marks_mark_check
    CHECK (mark IN ('accurate', 'inaccurate', 'hit', 'miss', 'phantom'));

-- conviction snapshot at mark time (for future calibration curves — store
-- only, no analysis yet, per brief)
ALTER TABLE prediction_accuracy_marks
    ADD COLUMN IF NOT EXISTS conviction   text NULL,
    ADD COLUMN IF NOT EXISTS event_type   text NULL,
    ADD COLUMN IF NOT EXISTS window_start date NULL,
    ADD COLUMN IF NOT EXISTS window_end   date NULL;
