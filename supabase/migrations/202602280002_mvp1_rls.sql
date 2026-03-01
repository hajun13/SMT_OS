-- S.M.T DooDream OS MVP-1 RLS

create or replace function public.is_member(
  p_org_id uuid,
  p_event_id uuid,
  p_roles role_type[] default null
)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from memberships m
    where m.user_id = auth.uid()
      and m.org_id = p_org_id
      and (
        m.event_id is null
        or p_event_id is null
        or m.event_id = p_event_id
      )
      and (
        p_roles is null
        or m.role = any(p_roles)
      )
  );
$$;

revoke all on function public.is_member(uuid, uuid, role_type[]) from public;
grant execute on function public.is_member(uuid, uuid, role_type[]) to authenticated;

create or replace view public_events as
select id, org_id, slug, title, template, venue, start_at, end_at, capacity, status
from events
where is_public = true;

grant select on public_events to anon, authenticated;

alter table memberships enable row level security;
alter table events enable row level security;
alter table registrations enable row level security;
alter table participants enable row level security;
alter table tickets enable row level security;
alter table checkins enable row level security;
alter table meetings enable row level security;
alter table meeting_notes enable row level security;
alter table action_items enable row level security;
alter table documents enable row level security;

create policy memberships_select_org_admin
on memberships for select
using (is_member(org_id, event_id, array['org_admin']::role_type[]));

create policy memberships_write_org_admin
on memberships for all
using (is_member(org_id, event_id, array['org_admin']::role_type[]))
with check (is_member(org_id, event_id, array['org_admin']::role_type[]));

create policy events_public_select
on events for select
using (is_public = true or is_member(org_id, id, array['org_admin','event_admin','staff','leader']::role_type[]));

create policy events_admin_write
on events for all
using (is_member(org_id, id, array['org_admin','event_admin']::role_type[]))
with check (is_member(org_id, id, array['org_admin','event_admin']::role_type[]));

create policy registrations_staff_rw
on registrations for all
using (
  exists (
    select 1 from events e
    where e.id = registrations.event_id
      and is_member(e.org_id, registrations.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
)
with check (
  exists (
    select 1 from events e
    where e.id = registrations.event_id
      and is_member(e.org_id, registrations.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
);

create policy participants_staff_rw
on participants for all
using (
  exists (
    select 1 from events e
    where e.id = participants.event_id
      and is_member(e.org_id, participants.event_id, array['org_admin','event_admin','staff','leader']::role_type[])
  )
)
with check (
  exists (
    select 1 from events e
    where e.id = participants.event_id
      and is_member(e.org_id, participants.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
);

create policy tickets_staff_rw
on tickets for all
using (
  exists (
    select 1
    from participants p
    join events e on e.id = p.event_id
    where p.id = tickets.participant_id
      and is_member(e.org_id, p.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
)
with check (
  exists (
    select 1
    from participants p
    join events e on e.id = p.event_id
    where p.id = tickets.participant_id
      and is_member(e.org_id, p.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
);

create policy checkins_staff_rw
on checkins for all
using (
  exists (
    select 1 from events e
    where e.id = checkins.event_id
      and is_member(e.org_id, checkins.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
)
with check (
  exists (
    select 1 from events e
    where e.id = checkins.event_id
      and is_member(e.org_id, checkins.event_id, array['org_admin','event_admin','staff']::role_type[])
  )
);

create policy meetings_org_read
on meetings for select
using (is_member(org_id, null, null));

create policy meetings_org_write
on meetings for all
using (is_member(org_id, null, array['org_admin','event_admin','staff']::role_type[]))
with check (is_member(org_id, null, array['org_admin','event_admin','staff']::role_type[]));

create policy meeting_notes_org_read
on meeting_notes for select
using (
  exists (
    select 1 from meetings m
    where m.id = meeting_notes.meeting_id
      and is_member(m.org_id, null, null)
  )
);

create policy meeting_notes_org_write
on meeting_notes for all
using (
  exists (
    select 1 from meetings m
    where m.id = meeting_notes.meeting_id
      and is_member(m.org_id, null, array['org_admin','event_admin','staff']::role_type[])
  )
)
with check (
  exists (
    select 1 from meetings m
    where m.id = meeting_notes.meeting_id
      and is_member(m.org_id, null, array['org_admin','event_admin','staff']::role_type[])
  )
);

create policy action_items_org_read
on action_items for select
using (is_member(org_id, event_id, null));

create policy action_items_org_write
on action_items for all
using (is_member(org_id, event_id, array['org_admin','event_admin','staff']::role_type[]))
with check (is_member(org_id, event_id, array['org_admin','event_admin','staff']::role_type[]));

create policy documents_org_read
on documents for select
using (is_member(org_id, event_id, null));

create policy documents_org_write
on documents for all
using (is_member(org_id, event_id, array['org_admin','event_admin','staff']::role_type[]))
with check (is_member(org_id, event_id, array['org_admin','event_admin','staff']::role_type[]));
