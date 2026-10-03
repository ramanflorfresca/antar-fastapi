-- [nlu 2026-10-03] shadow log for the understanding layer (antar_engine/understand.py):
-- the model's reading of each Ask/WhatsApp message next to the keyword decisions.
-- Run in Lovable (Build mode). Until it exists, Railway stdout ([nlu][shadow]) is the record.
create table if not exists public.nlu_log (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  chart_id uuid,
  channel text,
  mode text,
  question text,
  understanding jsonb,
  keyword jsonb,
  disagree text[] not null default '{}'
);
create index if not exists nlu_log_created_idx on public.nlu_log (created_at desc);
alter table public.nlu_log enable row level security;
