-- Prompt Registry schema (Brief 2 + console-landing brief: language column).
-- Run in Supabase SQL Editor BEFORE the seed. Idempotent.
create extension if not exists pgcrypto;

create table if not exists llm_prompts (
  id          uuid primary key default gen_random_uuid(),
  surface     text not null,
  language    text not null default 'en' check (language in ('en','es','pt')),
  body        text not null,
  version     int  not null default 1,
  status      text not null check (status in ('draft','live','archived')),
  updated_by  text,
  updated_at  timestamptz default now(),
  unique (surface, language, status, version)
);

-- safety for any pre-language install (no-ops on fresh create)
alter table llm_prompts add column if not exists language text not null default 'en';
drop index if exists llm_prompts_one_live;
drop index if exists llm_prompts_one_draft;

-- exactly one live + at most one draft per (surface, language)
create unique index if not exists llm_prompts_one_live
  on llm_prompts(surface, language) where status = 'live';
create unique index if not exists llm_prompts_one_draft
  on llm_prompts(surface, language) where status = 'draft';
