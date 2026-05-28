# UtterAI_BE

UtterAI backend repository.

현재 저장소는 기능 백엔드 설계 문서와 협업 규칙을 우선 관리한다.

## Current Scope

- 기능 백엔드 아키텍처 문서 관리
- API 명세 문서 관리
- 이슈/PR 템플릿 관리
- 이후 FastAPI 기반 백엔드 구현 반영

## Main Documents

- `utterai_functional_backend_architecture.md`
- `API 명세서.md`
- `API_PROGRESS.md`

## Implementation Reference

구현 시 다음 두 문서를 함께 기준으로 사용한다.

- `utterai_functional_backend_architecture.md`
  - 도메인 구조, 상태 전이, 권한/보안/운영 규칙 기준
- `API 명세서.md`
  - 엔드포인트 범위, URL, 요청/응답 형태의 초안 기준
- `API_PROGRESS.md`
  - 현재 구현 완료 API와 남은 API의 추적 기준

구현 중 두 문서가 충돌하면 아키텍처 문서의 도메인/권한 규칙을 우선하고, API 명세서는 그에 맞춰 갱신한다.

## Branch Strategy

- `dev`: 기본 개발 브랜치
- 기능 작업은 `feature/*`
- 버그 수정은 `fix/*`
- 문서 작업은 `docs/*`

상세 규칙은 `CONTRIBUTING.md`를 따른다.
