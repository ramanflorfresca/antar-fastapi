-- Brief 2 — Prompt Registry. Run in Supabase SQL Editor BEFORE deploying
-- the registry code (runtime falls back to hardcoded prompts until then).
create extension if not exists pgcrypto;

create table if not exists llm_prompts (
  id          uuid primary key default gen_random_uuid(),
  surface     text not null,
  body        text not null,
  version     int  not null default 1,
  status      text not null check (status in ('draft','live','archived')),
  updated_by  text,
  updated_at  timestamptz default now(),
  unique (surface, status, version)
);

-- exactly one live + at most one draft per surface
create unique index if not exists llm_prompts_one_live
  on llm_prompts(surface) where status = 'live';
create unique index if not exists llm_prompts_one_draft
  on llm_prompts(surface) where status = 'draft';
