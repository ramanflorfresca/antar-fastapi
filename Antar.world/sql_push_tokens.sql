-- push_tokens — device tokens for the daily-reading push (iOS APNs / Android FCM).
-- Run once in Supabase SQL editor. Idempotent-safe to re-run.

create table if not exists public.push_tokens (
  token       text primary key,                 -- APNs/FCM device token (unique per device)
  platform    text not null default 'ios',      -- 'ios' | 'android'
  chart_id    uuid references public.charts(id) on delete cascade,
  user_id     uuid,                              -- supabase auth user id
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Look up all tokens for a chart when it's time to send that chart's reading.
create index if not exists push_tokens_chart_idx on public.push_tokens (chart_id);
create index if not exists push_tokens_user_idx  on public.push_tokens (user_id);

-- The backend writes with the service-role key (bypasses RLS). Enable RLS with
-- no public policies so the anon key can never read/write the token table.
alter table public.push_tokens enable row level security;
