# Work Progress

이 문서는 현재 구현 진행 범위와 다음 작업을 빠르게 확인하기 위한 체크리스트다.

## Current Phase

- [x] 프로젝트 방향 문서 정리
- [x] 협업 규칙과 PR/Issue 템플릿 추가
- [x] FastAPI 기본 스캐폴딩 구성
- [x] DB 연결/세션 관리 코드 추가
- [x] 공통 enum과 상태 규칙 코드화
- [x] Alembic 초기 설정 추가
- [x] 핵심 테이블 초기 마이그레이션 작성
- [ ] Auth 도메인 1차 구현
- [ ] Child/Session CRUD 1차 구현

## Current Scope

이번 작업 범위는 다음까지다.

- [x] `pyproject.toml` 추가
- [x] `app/` 패키지 구조 추가
- [x] 설정/DB/라우터 기본 코드 추가
- [x] `users`, `children`, `sessions`, `child_access_grants` 모델 추가
- [x] Alembic 환경 및 첫 마이그레이션 추가
- [x] 로컬 정적 검증 수행

## Next Recommended Steps

- [ ] 인증 도메인 상세 구현
- [ ] 세션/아동 CRUD API 작성
- [ ] 권한 정책 모듈 구체화
- [ ] 테스트 프레임워크와 기본 테스트 추가
