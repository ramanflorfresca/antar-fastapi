-- Circle (the two-sided People tab): invites, pairs, per-person sharing choice.
-- Run via Lovable (Lovable Cloud owns Supabase DDL). The backend uses the service role.
--
-- Consent model, in one paragraph: a pair row exists ONLY after the invitee has opened
-- the inviter's link, consented and entered their OWN birth details (their own chart).
-- Nothing in these tables stores the invitee's birth details, a decline, or anything
-- about a person who has not accepted. Antar never messages the invitee: the inviter
-- shares the link from their own phone.
--
-- Every code path in the backend fails open (logs once, serves an empty circle) when
-- these tables are missing, so this file can be run any time after the code ships.

-- ── invites ────────────────────────────────────────────────────────────────
create table if not exists public.circle_invites (
  id                 uuid primary key default gen_random_uuid(),
  inviter_chart_id   uuid not null references public.charts(id) on delete cascade,
  inviter_user_id    uuid,                          -- rate limit across the inviter's charts
  token_hash         text not null,                 -- sha256 hex of the raw code; the raw code is never stored
  relation_type      text not null,                 -- what the INVITEE is to the inviter (people_links relation key)
  position           integer,                       -- optional manual order in the inviter's circle
  invitee_first_name text,                          -- the name the INVITER typed; shown only to the inviter
  private_chart_id   uuid,                          -- optional: the inviter's private person this invite replaces on screen
  language           text,                          -- language of the landing page
  status             text not null default 'pending'
                     check (status in ('pending', 'accepted', 'declined', 'expired', 'cancelled')),
  resend_count       integer not null default 0,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  expires_at         timestamptz not null,
  accepted_chart_id  uuid references public.charts(id) on delete set null
);
create unique index if not exists circle_invites_token_hash_uq on public.circle_invites (token_hash);
create index if not exists circle_invites_inviter_idx on public.circle_invites (inviter_chart_id, status);
create index if not exists circle_invites_user_day_idx on public.circle_invites (inviter_user_id, created_at);
create index if not exists circle_invites_accepted_idx on public.circle_invites (accepted_chart_id)
  where accepted_chart_id is not null;

-- ── pairs ──────────────────────────────────────────────────────────────────
-- chart_a is the inviter's chart, chart_b the invitee's. A pair is deleted (not flagged)
-- when either side leaves, so nothing about the link outlives it.
create table if not exists public.circle_pairs (
  id                uuid primary key default gen_random_uuid(),
  chart_a           uuid not null references public.charts(id) on delete cascade,
  chart_b           uuid not null references public.charts(id) on delete cascade,
  invite_id         uuid references public.circle_invites(id) on delete set null,
  relation_a_to_b   text not null,                  -- what B is to A
  relation_b_to_a   text not null,                  -- what A is to B
  status            text not null default 'active' check (status in ('active')),
  created_at        timestamptz not null default now(),
  check (chart_a <> chart_b)
);
-- one active pair per two people, whichever way round they are stored
create unique index if not exists circle_pairs_unordered_uq on public.circle_pairs
  ((least(chart_a::text, chart_b::text)), (greatest(chart_a::text, chart_b::text)));
create index if not exists circle_pairs_a_idx on public.circle_pairs (chart_a);
create index if not exists circle_pairs_b_idx on public.circle_pairs (chart_b);

-- ── sharing ────────────────────────────────────────────────────────────────
-- chart_id's own choice about other_chart_id: "share my day with them". Default OFF.
create table if not exists public.circle_sharing (
  chart_id        uuid not null references public.charts(id) on delete cascade,
  other_chart_id  uuid not null references public.charts(id) on delete cascade,
  share_day       boolean not null default false,
  updated_at      timestamptz not null default now(),
  primary key (chart_id, other_chart_id)
);
create index if not exists circle_sharing_other_idx on public.circle_sharing (other_chart_id);

alter table public.circle_invites enable row level security;
alter table public.circle_pairs   enable row level security;
alter table public.circle_sharing enable row level security;
-- No policies: clients get no direct access; only the backend's service role.
