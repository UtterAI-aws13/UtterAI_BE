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
- [x] Auth 도메인 1차 구현
- [ ] Child/Session CRUD 1차 구현

## Current Scope

이번 작업 범위는 다음까지다.

- [x] 회원가입 API 추가
- [x] 로그인 API 추가
- [x] 현재 사용자 조회 API 추가
- [x] 비밀번호 해싱 유틸 추가
- [x] JWT 생성/검증 유틸 추가
- [x] 사용자 조회/생성 repository 추가
- [ ] 실제 DB 연결 기반 수동 API 검증

## Next Recommended Steps

- [ ] refresh/logout 설계 및 구현
- [ ] 세션/아동 CRUD API 작성
- [ ] 권한 정책 모듈 구체화
- [ ] 테스트 프레임워크와 기본 테스트 추가
