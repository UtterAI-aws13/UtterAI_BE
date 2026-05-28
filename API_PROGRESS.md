# API Progress

이 문서는 API 구현 진행 상황을 지속적으로 추적하기 위한 체크리스트다.

## Rules

- 각 도메인은 `구현됨`, `부분 구현`, `미구현` 중 하나로 관리한다.
- 코드가 먼저 바뀌면 이 문서와 `API 명세서.md`를 같은 작업에서 같이 갱신한다.
- 실제 DB 또는 통합 환경에서 검증이 끝난 항목은 별도 검증 체크를 남긴다.

## Domain Status

| Domain | Status | Notes |
| --- | --- | --- |
| Auth | 구현됨 | `signup`, `login`, `me`, `refresh`, `logout` 구현 완료. live DB 검증만 남음 |
| Users/Admin | 미구현 | 관리자 사용자 관리 API 없음 |
| Children | 구현됨 | CRUD 및 therapist/admin 접근 제어 구현 완료 |
| Sessions | 구현됨 | CRUD 및 therapist/admin 접근 제어 구현 완료 |
| Audio Files | 미구현 | 업로드 URL, 등록, 조회, 삭제 미구현 |
| Analysis Jobs | 미구현 | 요청, 상태 조회, callback 미구현 |
| Transcripts | 미구현 | 조회/수정 미구현 |
| Analysis Results | 미구현 | 조회 계열 미구현 |
| SOAP Notes | 미구현 | 생성/수정/확정 미구현 |
| Reports | 미구현 | 생성/조회/다운로드 미구현 |

## Implemented APIs

- [x] `POST /api/v1/auth/signup`
- [x] `POST /api/v1/auth/login`
- [x] `GET /api/v1/auth/me`
- [x] `POST /api/v1/auth/refresh`
- [x] `POST /api/v1/auth/logout`
- [x] `POST /api/v1/children`
- [x] `GET /api/v1/children`
- [x] `GET /api/v1/children/{childId}`
- [x] `PATCH /api/v1/children/{childId}`
- [x] `DELETE /api/v1/children/{childId}`
- [x] `POST /api/v1/sessions`
- [x] `GET /api/v1/sessions`
- [x] `GET /api/v1/sessions/{sessionId}`
- [x] `PATCH /api/v1/sessions/{sessionId}`
- [x] `DELETE /api/v1/sessions/{sessionId}`

## Remaining Near-Term APIs

- [ ] `POST /api/v1/audio-files/presigned-url`
- [ ] `POST /api/v1/audio-files`
- [ ] `GET /api/v1/audio-files/{audioFileId}`
- [ ] `DELETE /api/v1/audio-files/{audioFileId}`
- [ ] `POST /api/v1/analysis-jobs`
- [ ] `GET /api/v1/analysis-jobs`
- [ ] `GET /api/v1/analysis-jobs/{jobId}`
- [ ] `PATCH /api/v1/analysis-jobs/{jobId}/cancel`

## Validation Status

- [ ] Auth API live validation against a real DB
- [ ] Children API live validation against a real DB
- [ ] Sessions API live validation against a real DB
- [ ] OpenAPI route list review against `API 명세서.md`
