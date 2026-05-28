# Contributing

## Branch Rules

- 기본 개발 브랜치는 `dev`다.
- 새 작업은 `dev`에서 분기한다.
- 브랜치 네이밍 규칙:
  - `feature/<issue-number>-<short-name>`
  - `fix/<issue-number>-<short-name>`
  - `docs/<issue-number>-<short-name>`
  - `chore/<issue-number>-<short-name>`

예시:

- `feature/12-auth-login`
- `fix/21-audio-upload-timeout`
- `docs/03-architecture-update`

## Commit Rules

- 커밋 메시지는 짧고 목적이 분명해야 한다.
- 권장 prefix:
  - `feat:`
  - `fix:`
  - `docs:`
  - `refactor:`
  - `test:`
  - `chore:`

예시:

- `feat: add child access grant model`
- `docs: expand backend architecture operations rules`

## Issue Rules

- 작업 시작 전 이슈를 먼저 만든다.
- 하나의 이슈는 하나의 목적에 집중한다.
- 이슈에는 배경, 목표, 완료 조건을 반드시 적는다.
- 구현 이슈는 가능하면 API, DB, 권한 영향 범위를 명시한다.

## Pull Request Rules

- PR base는 기본적으로 `dev`다.
- PR 하나에는 하나의 논리적 변경만 담는다.
- 초안 상태에서는 `Draft PR`을 사용한다.
- PR 본문에는 변경 내용, 테스트 결과, 영향 범위, 리뷰 포인트를 적는다.
- UI/API/DB 변경이 있으면 관련 예시나 스키마 변경점을 포함한다.
- 머지 전 최소 1회 이상 셀프 리뷰를 수행한다.

## Review Checklist

- 요구사항과 실제 변경 범위가 일치하는가
- 권한/보안/멱등성/트랜잭션 처리가 빠지지 않았는가
- 상태 전이 규칙을 위반하지 않는가
- 로그에 민감 정보가 남지 않는가
- 테스트 또는 수동 검증 결과가 있는가
