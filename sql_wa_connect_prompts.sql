-- sql_wa_connect_prompts.sql  (2026-10-06) — run once via Lovable (Build mode).
-- One row per account: did we show the one-time "Connect WhatsApp" popup, and did they click or dismiss it.
create table if not exists public.wa_connect_prompts (
  user_id      uuid primary key,
  shown_at     timestamptz,
  clicked_at   timestamptz,
  dismissed_at timestamptz,
  updated_at   timestamptz not null default now()
);
alter table public.wa_connect_prompts enable row level security;   -- backend (service role) only
