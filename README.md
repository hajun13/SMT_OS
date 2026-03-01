# S.M.T DooDream OS - API + Web Console Bootstrap

`1.md`, `2.md` 요구사항을 기준으로 시작한 DDD 초기 구현이다.

## 구현 범위 (현재)

- DDD 4계층 구조
  - `domain`: 이벤트/등록/티켓/체크인 핵심 엔티티
  - `application`: 유스케이스
  - `infrastructure`: 인메모리 + PostgreSQL(Supabase) 저장소
  - `interfaces`: FastAPI 라우터 + 웹 UI
- 핵심 유스케이스
  - 행사 생성
  - 등록폼(필드) 구성/업데이트
  - 참가자 등록 + 티켓 발급
  - 단체등록(여러 참가자 일괄 등록)
  - CSV 업로드 등록 / CSV 내보내기(엑셀 호환)
  - 등록 시 필수 필드 검증
  - Assignment Engine(식사 슬롯/소그룹 설정, 자동 배정 실행, 결과 조회)
  - 설문 문항 설정/응답 수집/요약 리포트
  - Team OS(회의/회의노트/액션아이템/문서)
  - 토큰 체크인(중복 방지)
  - 참가자 목록 조회(필터)
  - 운영 대시보드 카운트(등록/체크인)
  - 공개 이벤트 조회(slug)
  - 공개 티켓 조회(개인정보 최소화)
- 웹 UI
  - `/` 소개 랜딩
  - `/console` 운영 콘솔
  - `/e/{slug}` 공개 행사 랜딩
  - `/e/{slug}/register` 공개 등록
  - `/e/{slug}/ticket` 공개 티켓 조회
  - 단색 중심 디자인 시스템(그라데이션 사용 없음)
  - 모바일 웹앱 최적화(`viewport-fit`, safe-area, 하단 고정 액션바, manifest)
  - 공개 등록 화면에서 등록폼 필드 동적 로딩
- 기본 역할 가드
  - 보호 라우트는 `x-role` 헤더 필요
- Supabase SQL 제공
  - `supabase/migrations/202602280001_mvp1_schema.sql`
  - `supabase/migrations/202602280002_mvp1_rls.sql`
  - `supabase/migrations/202602280003_mvp1_seed.sql`

## 실행

```bash
cd /Users/hajun/workspace/SMT_OS/claude-code-harness
uv run pytest
uv run uvicorn smt_os.main:app --reload
```

### Next.js 프론트엔드 실행 (`web/`)

```bash
cd /Users/hajun/workspace/SMT_OS/claude-code-harness/web
npm install
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run dev
```

- 권장 Node 버전: `22 LTS` (`v22.x`)
- `Node v25`에서는 `/_next/static/*` 404 같은 dev 자산 로딩 문제가 발생할 수 있음

- 프론트 주소: `http://127.0.0.1:3000`
- 백엔드 주소: `http://127.0.0.1:8000`
- UI 스택: Next.js(App Router) + Tailwind + shadcn/ui
- 주요 라우트:
  - `/`
  - `/admin` (운영자 관리자 콘솔)
  - `/field` (실 행사 현장 콘솔)
  - `/console` (레거시 호환, `/admin`으로 리다이렉트)
  - `/e/[slug]`
  - `/e/[slug]/register`
  - `/e/[slug]/ticket`

## Supabase 연결

1. `.env.example`를 참고해 `.env`에 실제 값을 채운다.
2. `STORAGE_BACKEND=postgres`로 설정한다.
3. 필수 키 4개를 모두 채운다.
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_DB_URL`
4. 앱 실행 전에 `supabase/migrations` SQL을 적용한다.
5. 부팅 시 위 키가 비어 있거나 `YOUR_*`, `your_project` 샘플값이면 서버가 즉시 에러를 내고 실행을 중단한다.

참고:
- `.env.local`은 선택 덮어쓰기 파일이다. 비워 두면 `.env` 값을 그대로 사용한다.
- Supabase 비밀번호에 특수문자가 있다면 `SUPABASE_DB_URL`에 URL 인코딩해서 넣어야 한다.
- 로컬 프론트(`:3000`)와 API(`:8000`)를 분리해서 실행하면 CORS가 필요하다. 기본 허용값은 `http://localhost:3000`, `http://127.0.0.1:3000`이며, 필요 시 `CORS_ALLOWED_ORIGINS`로 변경한다.

## 배포

- Vercel(프론트) + Render(백엔드) 배포 가이드:
  - `docs/deploy-vercel-render.md`

웹 화면:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/console`
- `http://127.0.0.1:8000/e/spring-festival-2026`

## API 요약

- `POST /api/events` (role: `org_admin`/`event_admin`)
- `GET /api/events` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `GET /api/public/events/{slug}` (public)
- `GET /api/public/events/{event_id}/registration-form` (public)
- `PUT /api/events/{event_id}/registration-form` (role: `org_admin`/`event_admin`)
- `POST /api/participants/register` (public)
- `POST /api/events/{event_id}/registrations/group` (role: `org_admin`/`event_admin`/`staff`)
- `POST /api/events/{event_id}/registrations/import-csv` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/events/{event_id}/registrations/export-csv` (role: `org_admin`/`event_admin`/`staff`)
- `PUT /api/events/{event_id}/meal-slots` (role: `org_admin`/`event_admin`/`staff`)
- `POST /api/events/{event_id}/assignments/meal/run` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/events/{event_id}/assignments/meal` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `PUT /api/events/{event_id}/groups` (role: `org_admin`/`event_admin`/`staff`)
- `POST /api/events/{event_id}/assignments/group/run` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/events/{event_id}/assignments/group` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `PUT /api/events/{event_id}/survey/questions` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/public/events/{event_id}/survey/questions` (public)
- `POST /api/public/events/{event_id}/survey/responses` (public)
- `GET /api/events/{event_id}/reports/summary` (role: `org_admin`/`event_admin`/`staff`)
- `POST /api/team/meetings` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/team/meetings` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `POST /api/team/meetings/{meeting_id}/notes` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/team/meetings/{meeting_id}/notes` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `POST /api/team/action-items` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/team/action-items` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `POST /api/team/documents` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/team/documents` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `GET /api/public/tickets/{token}` (public)
- `POST /api/checkins` (role: `org_admin`/`event_admin`/`staff`)
- `POST /api/checkins/by-participant` (role: `org_admin`/`event_admin`/`staff`)
- `GET /api/events/{event_id}/participants` (role: `org_admin`/`event_admin`/`staff`/`leader`)
- `GET /api/events/{event_id}/dashboard` (role: `org_admin`/`event_admin`/`staff`)

예시 헤더:

```text
x-role: staff
```

## 다음 구현 우선순위

1. 인메모리 저장소를 Supabase/PostgreSQL 리포지토리로 교체
2. `memberships` 연동 기반 실제 권한 검사(`x-role` 임시 헤더 제거)
3. 등록폼 버전 히스토리(`version` 증가)와 콘솔 UI 폼 빌더 추가
4. Supabase Auth JWT 기반 실권한 체계로 전환

## 스킬 반영 기록

- `/docs/skills-usage.md` 참고
