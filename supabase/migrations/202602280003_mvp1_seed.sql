-- S.M.T DooDream OS seed

with inserted_org as (
  insert into orgs(name)
  values ('서중한합회 학생사역팀')
  on conflict do nothing
  returning id
), target_org as (
  select id from inserted_org
  union all
  select id from orgs where name = '서중한합회 학생사역팀' limit 1
)
insert into events(org_id, slug, title, template, venue, start_at, end_at, capacity, status)
select id, 'spring-festival-2026', '춘계 페스티벌 2026', 'day_event', '서울', '2026-05-16 09:00:00+09', '2026-05-16 19:00:00+09', 300, 'draft'
from target_org
on conflict (org_id, slug) do nothing;

with target_org as (
  select id from orgs where name = '서중한합회 학생사역팀' limit 1
)
insert into events(org_id, slug, title, template, venue, start_at, end_at, capacity, status)
select id, 'summer-camp-2026', '여름 캠프 2026', 'camp', '가평', '2026-08-01 10:00:00+09', '2026-08-03 16:00:00+09', 150, 'draft'
from target_org
on conflict (org_id, slug) do nothing;

insert into event_modules(event_id, seats, meals, groups, activities, lodging, buses)
select e.id,
  false,
  case when e.template = 'day_event' then true else true end,
  true,
  case when e.template = 'day_event' then true else false end,
  case when e.template = 'camp' then true else false end,
  case when e.template = 'camp' then true else false end
from events e
where e.slug in ('spring-festival-2026', 'summer-camp-2026')
on conflict (event_id) do nothing;
