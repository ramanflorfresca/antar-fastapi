ALTER TABLE charts ADD COLUMN IF NOT EXISTS jaimini_data JSONB;
CREATE INDEX IF NOT EXISTS idx_charts_jaimini_data ON charts USING GIN (jaimini_data);
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'charts' AND column_name = 'jaimini_data';
