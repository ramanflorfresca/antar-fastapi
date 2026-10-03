-- Accuracy board snapshots (outcome loop week 3). One row per nightly run; the
-- `board` jsonb holds the full board (engines × topic, final answers,
-- calibration, check-in health, trend, decoy baselines). Totals only — no
-- person, chart or question is stored here. Run via Lovable.
create table if not exists public.accuracy_board_snapshots (
  id                   uuid primary key default gen_random_uuid(),
  computed_at          timestamptz not null default now(),
  claims               integer not null default 0,
  answered             integer not null default 0,
  baselines_available  boolean not null default false,
  board                jsonb not null
);
create index if not exists accuracy_board_snapshots_at_idx
  on public.accuracy_board_snapshots (computed_at desc);
alter table public.accuracy_board_snapshots enable row level security;
-- No policies: backend service role only.
