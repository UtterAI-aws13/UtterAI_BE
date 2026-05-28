# Work Progress

이 문서는 현재 구현 진행 범위와 다음 작업을 빠르게 확인하기 위한 체크리스트다.

세부 API 구현 상태는 `API_PROGRESS.md`에서 지속 추적한다.

## Current Phase

- [x] 프로젝트 방향 문서 정리
- [x] 협업 규칙과 PR/Issue 템플릿 추가
- [x] FastAPI 기본 스캐폴딩 구성
- [x] DB 연결/세션 관리 코드 추가
- [x] 공통 enum과 상태 규칙 코드화
- [x] Alembic 초기 설정 추가
- [x] 핵심 테이블 초기 마이그레이션 작성
- [x] Auth 도메인 1차 구현
- [x] Child/Session CRUD 1차 구현

## Current Scope

이번 작업 범위는 다음까지다.

- [x] session_id 기반 report repository 필터 추가
- [x] session-scoped report service 조회 추가
- [x] `GET /api/v1/sessions/{sessionId}/reports` API 추가
- [x] 세션 접근 권한 체크 재사용
- [x] API 명세서와 API 진행 추적 문서 갱신
- [ ] 실제 DB 기반 session-scoped report list 수동 검증

## Next Recommended Steps

- [ ] 권한 정책 모듈 구체화
- [ ] analysis-result transcript/speaker read API 보완
- [ ] analysis-results transcript read API 구현
- [ ] analysis-results speakers read API 구현
- [ ] 테스트 프레임워크와 기본 테스트 추가
