-- sql_event_convergence.sql
-- Event Engine Rebuild (Rao three-stage convergence, Cowork brief 2026-06-10)
-- Run in the Supabase SQL Editor. Additive only — no destructive changes.

-- ── 1. event_engine_config: convergence tunables ────────────────────────────
-- promise_floor          : Stage-1 minimum promise score (default 2.0 in code)
-- required_locks         : convergence gate override (default: 3 painful, 2 benign)
-- double_transit_enabled : Stage-3 on/off per event type
alter table event_engine_config
  add column if not exists promise_floor numeric,
  add column if not exists required_locks integer,
  add column if not exists double_transit_enabled boolean default true;

comment on column event_engine_config.promise_floor is
  'Stage-1 promise minimum (code default 2.0). Raise to silence weakly-promised event types.';
comment on column event_engine_config.required_locks is
  'Convergence gate override. Code default: 3 for painful events, 2 for benign.';
comment on column event_engine_config.double_transit_enabled is
  'Stage-3 K.N. Rao double transit on/off per event type.';

-- ── 2. Fixture protection: ground-truth charts must be un-deletable ─────────
-- Two ground-truth charts were already lost to cleanup; never again.
alter table charts add column if not exists protected boolean default false;

-- [fixture-identity 2026-06-11] re-pointed to the REAL charts: the brief's
-- 4e68bd94 was Raman's own birth data mislabeled; 9dff84f7 had ZZ-placeholder
-- coords. Originals left unprotected (and deletable) on purpose.
update charts set protected = true where id in (
  'e3a3dac7-cb91-468c-b9fe-51ff74ef1217',  -- Harleen  (Gemini, 1975-01-08, Kuwait) — regression fixture
  '20a4c417-053a-4822-9561-85584e2b8e95',  -- Shashi   (Libra,  1970-11-02, IN)     — regression fixture
  'a4c9d57b-fb9c-4890-8fe7-4a9904f515ed',  -- Raman    (Capricorn) — 10-event ground truth
  'a2b1178f-17e5-4321-b5c2-2eb7c684385d'   -- Rishipal (Sagittarius) — 5-event out-of-sample set
);

create or replace function block_protected_chart_delete()
returns trigger language plpgsql as $$
begin
  if old.protected then
    raise exception 'chart % is a protected regression fixture — deletion blocked. Unset charts.protected first if truly intended.', old.id;
  end if;
  return old;
end $$;

drop trigger if exists trg_block_protected_chart_delete on charts;
create trigger trg_block_protected_chart_delete
  before delete on charts
  for each row execute function block_protected_chart_delete();

-- Also protect their dasha_periods rows from chart-cascade-free wipes:
create or replace function block_protected_dasha_delete()
returns trigger language plpgsql as $$
begin
  if exists (select 1 from charts c where c.id = old.chart_id and c.protected) then
    raise exception 'dasha_periods rows for protected chart % — deletion blocked.', old.chart_id;
  end if;
  return old;
end $$;

drop trigger if exists trg_block_protected_dasha_delete on dasha_periods;
create trigger trg_block_protected_dasha_delete
  before delete on dasha_periods
  for each row execute function block_protected_dasha_delete();

-- ── 3. Verify ────────────────────────────────────────────────────────────────
-- select id, first_name, protected from charts where protected;
-- select event_type, promise_floor, required_locks, double_transit_enabled
--   from event_engine_config;
