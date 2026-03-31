-- ANTAR Sprint P — Practice Engine Tables
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS practice_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_id        UUID NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    practice_id     TEXT NOT NULL,
    planet          TEXT,
    practice_type   TEXT NOT NULL DEFAULT 'remedy',
    energy_label    TEXT,
    domain          TEXT,
    prescribed_at   TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    streak_count    INT DEFAULT 0,
    user_note       TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice_schedule_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_id        UUID NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    cache_key       TEXT NOT NULL,
    schedule_data   JSONB NOT NULL,
    week_of         DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(chart_id, week_of)
);

CREATE INDEX IF NOT EXISTS idx_practice_log_chart_id ON practice_log(chart_id);
CREATE INDEX IF NOT EXISTS idx_practice_log_chart_completed ON practice_log(chart_id, completed_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_practice_log_chart_date ON practice_log(chart_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_practice_schedule_cache_chart_week ON practice_schedule_cache(chart_id, week_of DESC);

ALTER TABLE practice_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE practice_schedule_cache ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Allow all on practice_log" ON practice_log FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all on practice_schedule_cache" ON practice_schedule_cache FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

SELECT 'practice_log' AS tbl, count(*) AS rows FROM practice_log
UNION ALL
SELECT 'practice_schedule_cache', count(*) FROM practice_schedule_cache;
