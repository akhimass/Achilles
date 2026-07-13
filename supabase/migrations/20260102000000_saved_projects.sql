-- Private, per-user saved projects.
--
-- Unlike the public demo graph (which uses a public-read RLS policy), these rows are NEVER
-- world-readable. Isolation is enforced by Row-Level Security keyed to the authenticated
-- user: a signed-in user can only read, write, and delete their OWN rows. There is no
-- policy that grants anon/other-user access, so cross-user reads are impossible even with
-- the public anon key.
--
-- Data flow (see AUTH_PLAN.md): the browser writes here directly via the Supabase client
-- under the user's session; the FastAPI backend and the language model never touch this
-- table, so the "never sent to the model, never leaves your control" guarantee holds.

create extension if not exists pgcrypto;

create table if not exists public.saved_projects (
  id          uuid primary key default gen_random_uuid(),
  owner       uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  kind        text not null default 'lineage',   -- what was saved (e.g. a BYO lineage result)
  payload     jsonb not null,                     -- the deterministic result the user chose to keep
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists saved_projects_owner_idx
  on public.saved_projects (owner, created_at desc);

alter table public.saved_projects enable row level security;

-- Owner-scoped policies. No public/anon access — the only way in is as the row's owner.
create policy "saved_projects: owner can select"
  on public.saved_projects for select using (auth.uid() = owner);

create policy "saved_projects: owner can insert"
  on public.saved_projects for insert with check (auth.uid() = owner);

create policy "saved_projects: owner can update"
  on public.saved_projects for update
  using (auth.uid() = owner) with check (auth.uid() = owner);

create policy "saved_projects: owner can delete"
  on public.saved_projects for delete using (auth.uid() = owner);

-- Keep updated_at fresh on edits.
create or replace function public.touch_updated_at()
  returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists saved_projects_touch on public.saved_projects;
create trigger saved_projects_touch
  before update on public.saved_projects
  for each row execute function public.touch_updated_at();
