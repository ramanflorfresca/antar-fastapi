-- ============================================================
-- Antar — runtime app config (admin-panel editable backend settings)
-- Run this in the Supabase SQL Editor. Idempotent.
-- The code (antar_engine/app_config.py) is fail-safe: without this table it
-- falls back to hard defaults, so order isn't critical — but the panel can't
-- persist changes until the table exists.
-- ============================================================
create table if not exists app_config (
  key         text primary key,
  value       text        not null,
  updated_at  timestamptz not null default now(),
  updated_by  text
);
