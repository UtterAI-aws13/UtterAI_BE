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
| Audio Files | 구현됨 | presigned URL, complete, detail, delete 구현 완료. live S3/DB 검증만 남음 |
| Analysis Jobs | 구현됨 | 요청, 목록, 상세, 취소, progress callback 구현 완료. live 검증만 남음 |
| Transcripts | 구현됨 | result callback, 조회, 수정, bulk 수정, add/delete, confirm 구현 완료. live 검증만 남음 |
| Analysis Results | 부분 구현 | internal result callback 저장, detail/session/metrics 조회 구현 완료. transcript/speaker 전용 조회 미구현 |
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
- [x] `POST /api/v1/audio-files/presigned-url`
- [x] `POST /api/v1/audio-files`
- [x] `GET /api/v1/audio-files/{audioFileId}`
- [x] `DELETE /api/v1/audio-files/{audioFileId}`
- [x] `POST /api/v1/analysis-jobs`
- [x] `GET /api/v1/analysis-jobs`
- [x] `GET /api/v1/analysis-jobs/{jobId}`
- [x] `PATCH /api/v1/analysis-jobs/{jobId}/cancel`
- [x] `POST /api/v1/internal/analysis-jobs/{jobId}/progress`
- [x] `POST /api/v1/internal/analysis-results/callback`
- [x] `GET /api/v1/transcripts/{resultId}`
- [x] `GET /api/v1/sessions/{sessionId}/transcript`
- [x] `PATCH /api/v1/transcripts/{resultId}/segments/{segmentId}`
- [x] `PATCH /api/v1/transcripts/{resultId}/segments`
- [x] `POST /api/v1/transcripts/{resultId}/segments`
- [x] `DELETE /api/v1/transcripts/{resultId}/segments/{segmentId}`
- [x] `PATCH /api/v1/transcripts/{resultId}/confirm`
- [x] `GET /api/v1/analysis-results/{resultId}`
- [x] `GET /api/v1/sessions/{sessionId}/analysis-results`
- [x] `GET /api/v1/analysis-results/{resultId}/metrics`

## Remaining Near-Term APIs

- [ ] `GET /api/v1/analysis-results/{resultId}/transcripts`
- [ ] `GET /api/v1/analysis-results/{resultId}/speakers`
- [ ] `POST /api/v1/soap-notes/generate`
- [ ] `GET /api/v1/soap-notes`
- [ ] `GET /api/v1/soap-notes/{noteId}`

## Validation Status

- [ ] Auth API live validation against a real DB
- [ ] Children API live validation against a real DB
- [ ] Sessions API live validation against a real DB
- [ ] Audio Files API live validation against real DB/S3
- [ ] Analysis Jobs API live validation against real DB/AI callback mock
- [ ] Transcript/result callback live validation against real DB/callback mock
- [ ] Analysis result read APIs live validation against a real DB
- [ ] OpenAPI route list review against `API 명세서.md`
