-- S.M.T DooDream OS MVP-1 schema

create extension if not exists pgcrypto;

create table if not exists orgs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  phone text,
  created_at timestamptz not null default now()
);

do $$ begin
  create type role_type as enum ('org_admin','event_admin','staff','leader','participant');
exception when duplicate_object then null; end $$;

create table if not exists memberships (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  event_id uuid null,
  user_id uuid not null references auth.users(id) on delete cascade,
  role role_type not null,
  created_at timestamptz not null default now(),
  unique(org_id, event_id, user_id, role)
);

do $$ begin
  create type event_template as enum ('day_event','camp');
exception when duplicate_object then null; end $$;

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  slug text not null,
  title text not null,
  template event_template not null,
  venue text,
  start_at timestamptz not null,
  end_at timestamptz not null,
  capacity int not null default 0,
  is_public boolean not null default true,
  status text not null default 'draft',
  created_at timestamptz not null default now(),
  unique(org_id, slug)
);

create table if not exists event_modules (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  seats boolean not null default false,
  meals boolean not null default false,
  groups boolean not null default true,
  activities boolean not null default false,
  lodging boolean not null default false,
  buses boolean not null default false,
  created_at timestamptz not null default now(),
  unique(event_id)
);

create table if not exists registration_forms (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  version int not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique(event_id, version)
);

do $$ begin
  create type field_type as enum ('text','textarea','select','multi_select','checkbox','date','phone');
exception when duplicate_object then null; end $$;

create table if not exists form_fields (
  id uuid primary key default gen_random_uuid(),
  form_id uuid not null references registration_forms(id) on delete cascade,
  key text not null,
  label text not null,
  type field_type not null,
  required boolean not null default false,
  options jsonb not null default '[]'::jsonb,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  unique(form_id, key)
);

do $$ begin
  create type registration_kind as enum ('individual','group');
exception when duplicate_object then null; end $$;

create table if not exists registrations (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  kind registration_kind not null,
  applicant_name text not null,
  applicant_phone text,
  applicant_email text,
  group_name text,
  status text not null default 'submitted',
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists participants (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  registration_id uuid not null references registrations(id) on delete cascade,
  name text not null,
  gender text,
  grade text,
  church_or_school text,
  phone text,
  email text,
  answers jsonb not null default '{}'::jsonb,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table if not exists tickets (
  id uuid primary key default gen_random_uuid(),
  participant_id uuid not null references participants(id) on delete cascade,
  token text not null,
  status text not null default 'issued',
  created_at timestamptz not null default now(),
  unique(token),
  unique(participant_id)
);

do $$ begin
  create type checkin_type as enum ('entry','meal','activity','session');
exception when duplicate_object then null; end $$;

create table if not exists checkins (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  participant_id uuid not null references participants(id) on delete cascade,
  type checkin_type not null,
  meta jsonb not null default '{}'::jsonb,
  created_by uuid null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists meetings (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  title text not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists meeting_notes (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null references meetings(id) on delete cascade,
  content text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists action_items (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  event_id uuid null references events(id) on delete cascade,
  title text not null,
  owner_user_id uuid references auth.users(id),
  department text,
  due_at timestamptz,
  status text not null default 'open',
  created_at timestamptz not null default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references orgs(id) on delete cascade,
  event_id uuid null references events(id) on delete cascade,
  title text not null,
  kind text not null default 'doc',
  content text,
  version int not null default 1,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_memberships_user on memberships(user_id);
create index if not exists idx_memberships_org_event on memberships(org_id, event_id);
create index if not exists idx_events_org on events(org_id);
create index if not exists idx_registrations_event on registrations(event_id);
create index if not exists idx_participants_event on participants(event_id);
create index if not exists idx_checkins_event_type on checkins(event_id, type);
