-- Run with the Supabase SQL editor. Existing attendance_entries and RLS policies stay unchanged.
create table if not exists public.holiday_cache (
  year integer not null check (year between 2000 and 2100),
  holidays jsonb not null,
  expires_at timestamptz not null,
  updated_at timestamptz not null default now(),
  primary key (year)
);

alter table public.holiday_cache enable row level security;
-- There is intentionally no client policy: only the API, using the service-role key,
-- reads and writes the cache.
