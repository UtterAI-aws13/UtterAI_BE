# API 명세서

이 문서는 현재 백엔드 구현 방향에 맞춘 API 명세 초안이다.

## 기준

- 도메인 명칭은 `patients` 대신 `children`을 사용한다.
- URL과 권한 규칙은 현재 구현된 FastAPI 코드와 아키텍처 문서를 기준으로 맞춘다.
- 아직 미구현인 API도 이후 작업 범위를 명확히 하기 위해 함께 적어둔다.

---

## 1. Auth

### 구현 완료

| 상태 | 기능 | 사용자 | Method | URL | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 회원가입 | 전체 | POST | `/api/v1/auth/signup` | `email`, `password`, `name`, `role(optional)` | 회원가입 후 `access_token`, `refresh_token` 반환 |
| 구현됨 | 로그인 | 전체 | POST | `/api/v1/auth/login` | `email`, `password` | 로그인 후 `access_token`, `refresh_token` 반환 |
| 구현됨 | 내 정보 조회 | 로그인 사용자 | GET | `/api/v1/auth/me` | - | 현재 토큰 기준 사용자 정보 조회 |
| 구현됨 | 토큰 재발급 | 로그인 사용자 | POST | `/api/v1/auth/refresh` | `refresh_token` | refresh token 회전 후 새 토큰 쌍 반환 |
| 구현됨 | 로그아웃 | 로그인 사용자 | POST | `/api/v1/auth/logout` | - | 현재 사용자 기준 active refresh token 전체 revoke |

### 구현 메모

- `logout`은 stateless access token 자체를 즉시 폐기하지 않고, 서버에 저장된 active refresh token을 revoke하는 방식으로 동작한다.
- `refresh`는 기존 refresh token을 재사용하지 않고 회전(rotation)한다.

---

## 2. Users / Therapists

현재 사용자 관리 API는 구현 전이다. 문서상 `therapists`라는 이름을 쓰고 있었지만 실제 구현에서는 `users` 또는 `admin user management`로 재정리할 가능성이 높다.

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 사용자 목록 조회 | 관리자 | GET | `/api/v1/users` | `page`, `size`, `role`, `keyword` | - | 사용자 목록 조회 |
| 미구현 | 사용자 상세 조회 | 관리자 | GET | `/api/v1/users/{userId}` | - | - | 특정 사용자 상세 조회 |
| 미구현 | 사용자 생성 | 관리자 | POST | `/api/v1/users` | - | `name`, `email`, `role`, `password` | 사용자 계정 생성 |
| 미구현 | 사용자 수정 | 관리자 | PATCH | `/api/v1/users/{userId}` | - | `name`, `role`, `status` | 사용자 정보 수정 |
| 미구현 | 사용자 비활성화 | 관리자 | PATCH | `/api/v1/users/{userId}/deactivate` | - | - | 사용자 계정 비활성화 |

---

## 3. Children

`patients` 대신 `children` 도메인으로 정리한다.

### 구현 완료

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 아동 목록 조회 | 치료사, 관리자 | GET | `/api/v1/children` | - | - | 치료사는 본인 소유 아동만, 관리자는 전체 조회 |
| 구현됨 | 아동 상세 조회 | 치료사, 관리자 | GET | `/api/v1/children/{childId}` | - | - | 아동 기본 정보 조회 |
| 구현됨 | 아동 등록 | 치료사, 관리자 | POST | `/api/v1/children` | - | `name`, `birth_date`, `gender`, `memo`, `therapist_id(optional, admin only)` | 아동 정보 등록 |
| 구현됨 | 아동 정보 수정 | 치료사, 관리자 | PATCH | `/api/v1/children/{childId}` | - | `name`, `birth_date`, `gender`, `memo` | 아동 정보 수정 |
| 구현됨 | 아동 삭제 | 치료사, 관리자 | DELETE | `/api/v1/children/{childId}` | - | - | soft delete 처리 |

### 후속 예정

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 보호자 공유 권한 조회 | 치료사, 관리자 | GET | `/api/v1/children/{childId}/access-grants` | - | - | 아동 공유 권한 목록 조회 |
| 미구현 | 보호자 공유 권한 생성 | 치료사, 관리자 | POST | `/api/v1/children/{childId}/access-grants` | - | `granteeUserId`, `accessLevel`, `expiresAt(optional)` | 보호자/조회 사용자 공유 권한 생성 |
| 미구현 | 보호자 공유 권한 해제 | 치료사, 관리자 | DELETE | `/api/v1/children/{childId}/access-grants/{grantId}` | - | - | 공유 권한 해제 |

---

## 4. Sessions

세션은 아동에 종속되지만, 생성/조회 동선의 단순화를 위해 `/sessions`를 기본 리소스로 둔다.

### 구현 완료

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 세션 생성 | 치료사, 관리자 | POST | `/api/v1/sessions` | - | `child_id`, `session_date`, `session_type`, `memo` | 특정 아동에 연결된 세션 생성 |
| 구현됨 | 세션 목록 조회 | 치료사, 관리자 | GET | `/api/v1/sessions` | `child_id(optional)` | - | 치료사는 본인 세션만, 관리자는 전체 조회 |
| 구현됨 | 세션 상세 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}` | - | - | 특정 세션 상세 조회 |
| 구현됨 | 세션 수정 | 치료사, 관리자 | PATCH | `/api/v1/sessions/{sessionId}` | - | `session_date`, `session_type`, `memo`, `status` | 세션 정보 수정 |
| 구현됨 | 세션 삭제 | 치료사, 관리자 | DELETE | `/api/v1/sessions/{sessionId}` | - | - | soft delete 처리 |

### 후속 예정

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 세션 요약 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/summary` | - | - | 업로드 상태, 분석 상태, 결과 요약 조회 |
| 미구현 | 세션별 리포트 목록 | 치료사, 관리자, 공유 사용자 | GET | `/api/v1/sessions/{sessionId}/reports` | - | - | 세션에 연결된 리포트 목록 조회 |
| 미구현 | 세션별 분석 결과 조회 | 치료사, 관리자, 공유 사용자 | GET | `/api/v1/sessions/{sessionId}/analysis-results` | - | - | 세션에 연결된 분석 결과 조회 |

---

## 5. Audio Files

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 음성 업로드 URL 발급 | 치료사, 관리자 | POST | `/api/v1/audio-files/presigned-url` | - | `file_name`, `content_type`, `session_id`, `file_size(optional)` | pending audio row 생성 후 S3 업로드용 presigned URL 발급 |
| 구현됨 | 음성 파일 등록 | 치료사, 관리자 | POST | `/api/v1/audio-files` | - | `session_id`, `s3_key`, `duration_seconds(optional)` | 업로드 완료된 음성 메타데이터 확정 |
| 구현됨 | 음성 파일 조회 | 치료사, 관리자 | GET | `/api/v1/audio-files/{audioFileId}` | - | - | 음성 파일 메타데이터 조회 |
| 구현됨 | 음성 파일 삭제 | 치료사, 관리자 | DELETE | `/api/v1/audio-files/{audioFileId}` | - | - | 음성 파일 soft delete |

### 구현 메모

- presigned URL 발급 시 서버가 `audio_files`의 `PENDING` row를 먼저 만든다.
- 업로드 완료 API는 `s3_key` 기준으로 row를 찾아 `UPLOADED`로 상태 전이한다.
- 업로드 완료 시 세션 상태는 `AUDIO_UPLOADED`로 변경된다.

---

## 6. Analysis Jobs

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | AI 분석 요청 | 치료사, 관리자 | POST | `/api/v1/analysis-jobs` | - | `session_id`, `audio_file_id`, `analysis_template(optional)` | AI 분석 작업 생성 |
| 구현됨 | 분석 작업 목록 | 치료사, 관리자 | GET | `/api/v1/analysis-jobs` | `session_id(optional)`, `status(optional)` | - | 분석 작업 목록 조회 |
| 구현됨 | 분석 작업 상태 조회 | 치료사, 관리자 | GET | `/api/v1/analysis-jobs/{jobId}` | - | - | 분석 진행 상태 조회 |
| 구현됨 | 분석 작업 취소 | 치료사, 관리자 | PATCH | `/api/v1/analysis-jobs/{jobId}/cancel` | - | - | active 분석 작업 취소 |
| 구현됨 | 내부 진행률 Callback | 내부 AI 시스템 | POST | `/api/v1/internal/analysis-jobs/{jobId}/progress` | - | `status`, `progress`, `current_stage` | 진행 상태 업데이트 |
| 미구현 | 내부 결과 Callback | 내부 AI 시스템 | POST | `/api/v1/internal/analysis-results/callback` | - | 결과 payload | 분석 결과 수신 |

### 구현 메모

- 한 세션에는 동시에 active analysis job 하나만 허용한다.
- 생성 시 업로드 완료(`AUDIO_UPLOADED`)된 audio file만 분석 요청 가능하다.
- `internal progress callback`은 `X-Internal-Token` 인증이 필요하다.
- `result callback`은 transcript/result 저장 단계와 함께 구현 예정이다.

---

## 7. Transcripts

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 내부 분석 결과 Callback | 내부 AI 시스템 | POST | `/api/v1/internal/analysis-results/callback` | - | 결과 payload | 분석 결과와 transcript/speaker/utterance 저장 |
| 구현됨 | 전사 결과 조회 | 치료사, 관리자 | GET | `/api/v1/transcripts/{resultId}` | - | - | analysis result 기준 전사 결과 조회 |
| 구현됨 | 세션 전사 결과 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/transcript` | - | - | 특정 세션의 전사 결과 조회 |
| 구현됨 | 전사 문장 수정 | 치료사, 관리자 | PATCH | `/api/v1/transcripts/{resultId}/segments/{segmentId}` | - | `text`, `speaker_role`, `edit_reason(optional)` | 특정 발화 구간 수정 |
| 구현됨 | 전사 결과 일괄 수정 | 치료사, 관리자 | PATCH | `/api/v1/transcripts/{resultId}/segments` | - | `segments` | 여러 발화 구간 일괄 수정 |
| 구현됨 | 전사 구간 추가 | 치료사, 관리자 | POST | `/api/v1/transcripts/{resultId}/segments` | - | `speaker_label`, `speaker_role(optional)`, `start_time`, `end_time`, `text`, `edit_reason(optional)` | 누락된 구간 추가 |
| 구현됨 | 전사 구간 삭제 | 치료사, 관리자 | DELETE | `/api/v1/transcripts/{resultId}/segments/{segmentId}` | - | - | 잘못 생성된 구간 삭제 |
| 구현됨 | 전사 결과 확정 | 치료사, 관리자 | PATCH | `/api/v1/transcripts/{resultId}/confirm` | - | - | 수정 완료 전사본 확정 |

### 구현 메모

- transcript는 AI result callback 이후 생성된다.
- 저장 구조는 `analysis_results -> speakers -> utterances -> utterance_edit_history` 흐름이다.
- 수정 시 `original_text`는 유지하고, `edited_text`와 수정 이력을 별도로 관리한다.

---

## 8. Analysis Results

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 분석 결과 조회 | 치료사, 관리자 | GET | `/api/v1/analysis-results/{resultId}` | - | - | 전체 분석 결과 조회 |
| 구현됨 | 세션별 분석 결과 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/analysis-results` | - | - | 세션별 분석 결과 조회 |
| 미구현 | 전사 결과 조회 | 치료사, 관리자 | GET | `/api/v1/analysis-results/{resultId}/transcripts` | - | - | STT 전사 결과 조회 |
| 미구현 | 화자 분리 결과 조회 | 치료사, 관리자 | GET | `/api/v1/analysis-results/{resultId}/speakers` | - | - | 화자별 발화 구간 조회 |
| 구현됨 | 언어 지표 조회 | 치료사, 관리자 | GET | `/api/v1/analysis-results/{resultId}/metrics` | - | - | 저장된 metrics payload 조회 |

---

## 9. SOAP Notes

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | SOAP Note 초안 생성 | 치료사, 관리자 | POST | `/api/v1/soap-notes/generate` | - | `sessionId`, `transcriptId`, `clinicalAnalysisJobId(optional)` | 분석 결과 기반 초안 생성 |
| 구현됨 | SOAP Note 목록 조회 | 치료사, 관리자 | GET | `/api/v1/soap-notes` | `sessionId(optional)`, `childId(optional)` | - | SOAP Note 목록 조회 |
| 구현됨 | SOAP Note 상세 조회 | 치료사, 관리자 | GET | `/api/v1/soap-notes/{noteId}` | - | - | SOAP Note 상세 조회 |
| 구현됨 | SOAP Note 수정 | 치료사, 관리자 | PATCH | `/api/v1/soap-notes/{noteId}` | - | `subjective`, `objective`, `assessment`, `plan` | mutable SOAP Note 수정 |
| 구현됨 | SOAP Note 저장 | 치료사, 관리자 | PATCH | `/api/v1/soap-notes/{noteId}/save` | - | - | 수정본 저장 |
| 구현됨 | SOAP Note 확정 | 치료사, 관리자 | PATCH | `/api/v1/soap-notes/{noteId}/finalize` | - | - | 최종 확정 |
| 구현됨 | SOAP Note 삭제 | 치료사, 관리자 | DELETE | `/api/v1/soap-notes/{noteId}` | - | - | SOAP Note soft delete |

### 구현 메모

- SOAP draft 생성 전 transcript 전체가 `confirmed` 상태여야 한다.
- 현재 draft 생성은 backend-local 텍스트 조합 방식이며, 이후 LLM 기반 고도화가 가능하다.
- `FINALIZED` 상태의 SOAP Note는 수정할 수 없다.

---

## 10. Reports

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 리포트 생성 | 치료사, 관리자 | POST | `/api/v1/reports` | - | `sessionId`, `resultId`, `templateType` | finalized SOAP Note와 분석 결과를 기준으로 리포트를 생성한다. |
| 구현됨 | 리포트 목록 조회 | 치료사, 관리자 | GET | `/api/v1/reports` | `childId(optional)` | - | 현재 사용자에게 보이는 리포트 목록을 조회한다. |
| 구현됨 | 리포트 상세 조회 | 치료사, 관리자 | GET | `/api/v1/reports/{reportId}` | - | - | 리포트 본문과 메타데이터를 조회한다. |
| 구현됨 | 리포트 수정 | 치료사, 관리자 | PATCH | `/api/v1/reports/{reportId}` | - | `title`, `content`, `memo` | 생성된 리포트의 제목, 본문, 메모를 수동 수정한다. |
| 구현됨 | 리포트 다운로드 | 치료사, 관리자 | GET | `/api/v1/reports/{reportId}/download` | - | - | MVP에서는 텍스트 첨부파일 다운로드를 제공하고 PDF 렌더링은 후속 작업으로 남긴다. |

### 구현 메모

- 리포트 생성 전 세션에는 최소 1개의 `FINALIZED` SOAP Note가 있어야 한다.
- 리포트 생성이 완료되면 세션 상태를 `REPORT_READY`로 올린다.
- soft delete된 리포트는 수정할 수 없다.
- 보호자/공유 사용자 대상 리포트 공개 정책과 PDF 렌더링 파이프라인은 아직 구현하지 않았다.
