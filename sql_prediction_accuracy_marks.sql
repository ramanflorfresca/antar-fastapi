-- ============================================================================
-- sql_prediction_accuracy_marks.sql
-- Admin past-prediction validation harness (Cowork brief 2026-06-10).
--
-- PURELY ADDITIVE. CREATE TABLE only. No ALTER, no DROP, no writes to any
-- existing table or row. Isolated from the 910df299 incident blast radius —
-- touches nothing pre-existing.
--
-- Run in the Supabase SQL Editor.
-- ============================================================================

CREATE TABLE IF NOT EXISTS prediction_accuracy_marks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_id      uuid NOT NULL,
    prediction_id text NOT NULL,
    mark          text NOT NULL CHECK (mark IN ('accurate', 'inaccurate')),
    marked_at     timestamptz NOT NULL DEFAULT now(),
    marked_by     text NULL,
    UNIQUE (chart_id, prediction_id)
);

-- Accuracy tally groups by chart.
CREATE INDEX IF NOT EXISTS idx_pam_chart_id
    ON prediction_accuracy_marks (chart_id);
