# Vercel + Render 배포 가이드

## 0) 사전 상태

- GitHub 원격: `https://github.com/chacha95/claude-code-harness.git`
- 프론트: `web/` (Next.js)
- 백엔드: 루트 (`FastAPI + uv`)

## 1) GitHub 반영

```bash
cd /Users/hajun/workspace/SMT_OS/claude-code-harness
git add .
git commit -m "chore: production deployment setup for vercel and render"
git push origin main
```

## 2) Render(백엔드) 배포

1. Render 대시보드 -> `New` -> `Blueprint`
2. GitHub repo 선택: `chacha95/claude-code-harness`
3. `render.yaml` 인식 확인 후 생성
4. 환경변수 입력

필수 환경변수:

- `STORAGE_BACKEND=postgres`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (반드시 service_role secret)
- `SUPABASE_DB_URL` (pooler 연결 문자열 권장)
- `SUPERADMIN_EMAIL`
- `SUPERADMIN_PASSWORD`
- `SUPERADMIN_NAME`
- `SUPERADMIN_TEAM`
- `CORS_ALLOWED_ORIGINS`

`CORS_ALLOWED_ORIGINS` 예시:

```text
https://your-app.vercel.app,https://your-domain.com
```

배포 후 확인:

- `GET https://<render-domain>/health` -> `{"status":"ok"...}`

## 3) Vercel(프론트) 배포

1. Vercel 대시보드 -> `New Project`
2. GitHub repo `chacha95/claude-code-harness` import
3. `Root Directory`를 `web`로 설정
4. Environment Variable 설정:

```text
NEXT_PUBLIC_API_BASE=https://<render-domain>
```

5. Deploy

## 4) CORS 최종 확정

Vercel URL 확정 후 Render 환경변수 `CORS_ALLOWED_ORIGINS`에 정확한 프론트 도메인을 넣고 재배포.

## 5) 운영 점검 체크리스트

1. `/login` 슈퍼계정 로그인
2. 사역팀 회원가입 + 승인
3. 팀장 지정/해제
4. 행사 생성/삭제(팀장 권한)
5. 참가자 등록/티켓 조회
6. 지도교사 환불 요청 -> 관리자(팀장) 승인
7. 홈 `/about/team` 조직도 및 사진 노출 확인
