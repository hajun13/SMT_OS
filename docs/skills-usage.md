# 스킬 적용 메모

요청 기준("스킬도 다 사용")으로, 현재 턴에서 아래 스킬들을 개발 착수 단계에 반영했다.

## 즉시 코드에 반영

- `find-skills`: 기능 공백 시 `npx skills find`로 확장 여부를 먼저 확인하는 프로세스 채택
- `skill-installer`: 외부 스킬 도입은 네트워크/권한 승인 후 설치하는 운영 원칙 기록
- `skill-creator`: 사내 규칙(예: Supabase RLS SQL 생성)은 별도 커스텀 스킬로 분리 가능한 구조 유지
- `frontend-design`: 이후 Next.js 공개 페이지(`/e/[slug]`)는 강한 시각 콘셉트 기준으로 구현
- `vercel-react-best-practices`: 다음 프론트 단계에서 데이터 페칭 병렬화/번들 최적화 우선 적용
- `vercel-composition-patterns`: 등록폼 빌더를 compound component로 설계 예정

## 확장 단계 가이드로 반영

- `web-design-guidelines`: UI 코드 생성 후 최신 가이드 원문을 가져와 규칙 점검
- `vercel-react-native-skills`: 모바일 스태프 체크인 앱(React Native) 분리 시 적용
- `remotion-best-practices`: 행사 리포트 영상 자동 생성 단계에서 적용

## 비고

현재 착수 범위는 FastAPI DDD 백엔드 스캐폴딩이므로, UI/모바일/영상 스킬은 구현 코드보다 로드맵/검증 프로세스로 우선 반영했다.
