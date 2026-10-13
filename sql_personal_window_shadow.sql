-- [personal-window shadow 2026-10-13] One row per chart per local day: the candidate personal best/avoid window
-- (hora ruler x lagna x running pratyantar/sookshma lords x panchang kalas), the per-hora scores, and its overlap with
-- the Abhijit / Rahu Kalam windows. Shadow only — never user-facing.
create table if not exists public.personal_window_shadow (
  chart_id    uuid        not null references public.charts(id) on delete cascade,
  local_date  date        not null,
  payload     jsonb       not null,
  created_at  timestamptz not null default now(),
  primary key (chart_id, local_date)
);
alter table public.personal_window_shadow enable row level security;   -- service role only; no policies = no client access
