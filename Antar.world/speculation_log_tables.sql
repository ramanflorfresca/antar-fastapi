-- KP speculation shadow logger — schema (run via Lovable Cloud Build mode;
-- Lovable owns Supabase DDL). Shadow-only research tables; behavioral-sensitive
-- (treat like health data — purge on chart delete). See
-- Antar.world/KP_SPECULATION_TIMING_STUDY.md Appendix A.

create table if not exists speculation_sessions (
  id                    uuid primary key default gen_random_uuid(),
  chart_id              uuid not null references charts(id) on delete cascade,
  started_at            timestamptz not null,
  ended_at              timestamptz not null,
  lat                   double precision not null,
  lng                   double precision not null,
  tz_offset             double precision not null default 0,
  game_type             text,                         -- poker/slots/table/sports/crypto/...
  net_units             double precision,             -- signed session total
  unit_currency         text default 'unit',
  stake_baseline        double precision,
  alcohol_units_total   double precision default 0,   -- the Rahu confound (MANDATORY for analysis)
  chasing_flag          boolean default false,
  sleep_debt_hrs        double precision,
  valid                 boolean default true,         -- false = illegible self-report, excluded from analysis
  notes                 text,
  created_at            timestamptz not null default now()
);
create index if not exists idx_spec_sessions_chart on speculation_sessions(chart_id);

create table if not exists speculation_checkpoints (
  id                         uuid primary key default gen_random_uuid(),
  session_id                 uuid not null references speculation_sessions(id) on delete cascade,
  at_ts                      timestamptz not null,
  chip_balance               double precision not null,
  alcohol_units_cumulative   double precision,
  note                       text,                    -- drink / break / cash-out ...
  created_at                 timestamptz not null default now()
);
create index if not exists idx_spec_cp_session on speculation_checkpoints(session_id);

-- DERIVED: server-written only (never user-entered). One row per KP sub-lord
-- window; this is the analysis table for the study's §4 regression.
create table if not exists speculation_windows (
  id                uuid primary key default gen_random_uuid(),
  session_id        uuid not null references speculation_sessions(id) on delete cascade,
  chart_id          uuid not null references charts(id) on delete cascade,
  window_start      timestamptz not null,
  window_end        timestamptz not null,
  minutes           double precision,
  sub_lord          text,        -- Moon KP sub-lord (primary predictor)
  star_lord         text,
  sub_sub_lord      text,
  lahiri_sub_lord   text,        -- cross-check ayanamsa
  hora_lord         text,
  moon_sign         text,
  moon_nakshatra    text,
  md_lord           text,
  ad_lord           text,
  is_dasha_sub      boolean,     -- sub_lord == running mahadasha lord (H2)
  sub_polarity      text,        -- malefic / benefic
  net_units         double precision,   -- allocated P&L for this window
  net_per_min       double precision,
  created_at        timestamptz not null default now()
);
create index if not exists idx_spec_win_session on speculation_windows(session_id);
create index if not exists idx_spec_win_sublord on speculation_windows(sub_lord);

-- RLS: shadow research data. Only the owning user may write their own sessions;
-- reads for analysis go through the service role / an admin export endpoint.
alter table speculation_sessions    enable row level security;
alter table speculation_checkpoints enable row level security;
alter table speculation_windows     enable row level security;
-- (add policies to match your auth model; service-role bypasses RLS for the
--  server-side slicing + admin export.)
