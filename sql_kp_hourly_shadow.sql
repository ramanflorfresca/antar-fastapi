-- [kp-hourly shadow 2026-10-12] One row per chart per local day: the Moon's sub-lord timeline, KP best/avoid
-- windows, and their overlap with the Abhijit / Rahu Kalam windows shown to users. Shadow only — never user-facing.
create table if not exists public.kp_hourly_shadow (
  chart_id    uuid        not null references public.charts(id) on delete cascade,
  local_date  date        not null,
  payload     jsonb       not null,
  created_at  timestamptz not null default now(),
  primary key (chart_id, local_date)
);
alter table public.kp_hourly_shadow enable row level security;   -- service role only; no policies = no client access
