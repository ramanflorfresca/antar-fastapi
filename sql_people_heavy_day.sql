-- [people-heavy-day 2026-10-12] Starred connections (max 3 per chart) and a one-per-day send log.
-- Run in the Supabase SQL Editor before the alert can fire. The backend fails open without it.
create table if not exists people_alert_stars (
  id                   uuid primary key default gen_random_uuid(),
  chart_id             uuid not null,
  connection_chart_id  uuid not null,
  created_at           timestamptz not null default now()
);
create unique index if not exists idx_people_alert_stars_pair on people_alert_stars (chart_id, connection_chart_id);

create table if not exists people_alert_log (
  id                   uuid primary key default gen_random_uuid(),
  chart_id             uuid not null,
  local_date           date not null,
  connection_chart_id  uuid not null,
  channel              text,
  sent_at              timestamptz not null default now()
);
-- one alert per chart per local day, whatever the number of starred people
create unique index if not exists idx_people_alert_log_day on people_alert_log (chart_id, local_date);
