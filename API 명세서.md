# API 명세서

이 문서는 현재 백엔드 구현 방향에 맞춘 API 명세이다.

## 기준

- 도메인 명칭은 `children` 대신 `patients`를 사용한다.
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

## 2. Users / SLPs

사용자 관리 API. Role은 `ADMIN`, `SLP` 두 가지만 존재한다.

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 사용자 목록 조회 | 관리자 | GET | `/api/v1/users` | `page`, `size`, `role`, `keyword` | - | 사용자 목록 조회 |
| 미구현 | 사용자 상세 조회 | 관리자 | GET | `/api/v1/users/{userId}` | - | - | 특정 사용자 상세 조회 |
| 미구현 | 사용자 생성 | 관리자 | POST | `/api/v1/users` | - | `name`, `email`, `role`, `password` | 사용자 계정 생성 |
| 미구현 | 사용자 수정 | 관리자 | PATCH | `/api/v1/users/{userId}` | - | `name`, `role`, `status` | 사용자 정보 수정 |
| 미구현 | 사용자 비활성화 | 관리자 | PATCH | `/api/v1/users/{userId}/deactivate` | - | - | 사용자 계정 비활성화 |

---

## 3. Patients

`children` 대신 `patients` 도메인으로 정리한다.

### 구현 완료

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 환자 목록 조회 | 치료사, 관리자 | GET | `/api/v1/patients` | - | - | 치료사는 본인 소유 환자만, 관리자는 전체 조회 |
| 구현됨 | 환자 상세 조회 | 치료사, 관리자 | GET | `/api/v1/patients/{patientId}` | - | - | 환자 기본 정보 조회 |
| 구현됨 | patient_ref_id로 환자 조회 | 치료사, 관리자 | GET | `/api/v1/patients/by-ref/{patientRefId}` | - | - | 세션의 `patient_ref_id` 기준으로 환자 정보 조회 |
| 구현됨 | 환자 등록 | 치료사, 관리자 | POST | `/api/v1/patients` | - | `name`, `birth_date`, `gender`, `memo`, `slp_id(optional, admin only)` | 환자 정보 등록 |
| 구현됨 | 환자 정보 수정 | 치료사, 관리자 | PATCH | `/api/v1/patients/{patientId}` | - | `name`, `birth_date`, `gender`, `memo` | 환자 정보 수정 |
| 구현됨 | 환자 삭제 | 치료사, 관리자 | DELETE | `/api/v1/patients/{patientId}` | - | - | soft delete 처리 |

---

## 4. Sessions

세션은 환자에 종속되지만, 생성/조회 동선의 단순화를 위해 `/sessions`를 기본 리소스로 둔다.

### 구현 완료

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 세션 생성 | 치료사, 관리자 | POST | `/api/v1/sessions` | - | `patient_ref_id`, `session_date`, `session_type`, `memo` | 특정 환자에 연결된 세션 생성 |
| 구현됨 | 세션 목록 조회 | 치료사, 관리자 | GET | `/api/v1/sessions` | `patient_ref_id(optional)` | - | 치료사는 본인 세션만, 관리자는 전체 조회 |
| 구현됨 | 세션 상세 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}` | - | - | 특정 세션 상세 조회 |
| 구현됨 | 세션 수정 | 치료사, 관리자 | PATCH | `/api/v1/sessions/{sessionId}` | - | `session_date`, `session_type`, `memo`, `status` | 세션 정보 수정 |
| 구현됨 | 세션 삭제 | 치료사, 관리자 | DELETE | `/api/v1/sessions/{sessionId}` | - | - | soft delete 처리 |

### 후속 예정

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 세션 요약 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/summary` | - | - | 업로드 상태, 분석 상태, 결과 요약 조회 |
| 구현됨 | 세션별 리포트 목록 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/reports` | - | - | 세션에 연결된 리포트 목록 조회 |
| 미구현 | 세션별 분석 결과 조회 | 치료사, 관리자, 공유 사용자 | GET | `/api/v1/sessions/{sessionId}/analysis-results` | - | - | 세션에 연결된 분석 결과 조회 |

---

## 5. Audio Files

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 음성 업로드 URL 발급 | 치료사, 관리자 | POST | `/api/v1/audio-files/presigned-url` | - | `file_name`, `content_type`, `session_id`, `file_size(optional)` | pending audio row 생성 후 S3 업로드용 presigned URL 발급 |
| 구현됨 | 음성 파일 등록 | 치료사, 관리자 | POST | `/api/v1/audio-files` | - | `session_id`, `object_key`, `actual_size_bytes(optional)` | 업로드 완료된 음성 메타데이터 확정 |
| 구현됨 | 음성 파일 조회 | 치료사, 관리자 | GET | `/api/v1/audio-files/{audioFileId}` | - | - | 음성 파일 메타데이터 조회 |
| 구현됨 | 음성 파일 삭제 | 치료사, 관리자 | DELETE | `/api/v1/audio-files/{audioFileId}` | - | - | 음성 파일 soft delete |

### 구현 메모

- presigned URL 발급 시 서버가 `audio_files`의 `PENDING_UPLOAD` row를 먼저 만든다.
- 업로드 완료 API는 `object_key` 기준으로 row를 찾아 `UPLOADED`로 상태 전이한다.
- 업로드 완료 시 세션 상태는 `AUDIO_UPLOADED`로 변경된다.

---

## 6. Analysis Jobs

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | AI 분석 요청 | 치료사, 관리자 | POST | `/api/v1/analysis-jobs` | - | `session_id`, `audio_file_id`, `template_id(optional)` | AI 분석 작업 생성 |
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
| 구현됨 | 내부 분석 결과 Callback | 내부 AI 시스템 | POST | `/api/v1/internal/analysis-results/callback` | - | 결과 payload | 분석 결과와 transcript/transcript_segments 저장 |
| 구현됨 | 전사 결과 조회 | 치료사, 관리자 | GET | `/api/v1/transcripts/{transcriptId}` | - | - | transcript_id 기준 전사 결과 조회 |
| 구현됨 | 세션 전사 결과 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/transcript` | - | - | 특정 세션의 전사 결과 조회 |
| 구현됨 | 전사 세그먼트 목록 조회 | 치료사, 관리자 | GET | `/api/v1/transcripts/{transcriptId}/segments` | - | - | 전사 세그먼트 목록 조회 |
| 구현됨 | 전사 세그먼트 수정 | 치료사, 관리자 | PATCH | `/api/v1/transcripts/{transcriptId}/segments/{segmentId}` | - | `text`, `speaker_role` | 특정 발화 구간 수정 |
| 구현됨 | 전사 세그먼트 일괄 수정 | 치료사, 관리자 | PATCH | `/api/v1/transcripts/{transcriptId}/segments` | - | `segments` | 여러 발화 구간 일괄 수정 |
| 구현됨 | 전사 결과 확정 | 치료사, 관리자 | POST | `/api/v1/transcripts/{transcriptId}/finalize` | - | - | 수정 완료 전사본 확정 |

### 구현 메모

- transcript draft는 ML GPU Worker가 alignment 완료 후 `transcripts` + `transcript_segments` 테이블에 직접 저장한다. (SQS 파이프라인 내부 처리, BE callback 불필요)
- BE `POST /internal/analysis-results/callback`은 dev/test용 수동 ingest 경로로만 사용된다.
- 저장 구조는 `transcripts (헤더) → transcript_segments (발화 단위)` 이다.
- 수정 시 `original_text`는 유지하고 `text`를 덮어쓴다. `is_edited`, `edited_by`, `edited_at`으로 이력을 추적한다.

---

## 8. Analysis Results

> 별도 `analysis_results` 테이블은 현재 스키마에 존재하지 않는다. 분석 결과는 `transcripts`, `transcript_segments`, `language_metrics`, `reports` 테이블로 분리 보관된다. 아래 엔드포인트는 미구현이며 향후 필요 시 추가한다.

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | 세션별 분석 결과 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/analysis-results` | - | - | 세션별 분석 결과 요약 조회 |
| 미구현 | 언어 지표 조회 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/language-metrics` | - | - | `language_metrics` 테이블 조회 |

---

## 9. SOAP Notes

> 현재 `soap_notes` 테이블 및 관련 엔드포인트는 미구현이다. SOAP Note 초안은 LLM GPU Worker가 `reports` + `report_segments` 테이블에 직접 저장하는 방식으로 처리된다.

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 미구현 | SOAP Note 초안 생성 | 치료사, 관리자 | POST | `/api/v1/soap-notes/generate` | - | - | 별도 BE 엔드포인트 없이 LLM Worker가 직접 저장 |

---

## 10. Reports

| 상태 | 기능 | 사용자 | Method | URL | Query Param | Request Body | 설명 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 구현됨 | 리포트 목록 조회 | 치료사, 관리자 | GET | `/api/v1/reports` | `session_id(optional)`, `patient_ref_id(optional)` | - | 현재 사용자에게 보이는 리포트 목록을 조회한다. |
| 구현됨 | 리포트 상세 조회 | 치료사, 관리자 | GET | `/api/v1/reports/{reportId}` | - | - | 리포트 본문과 메타데이터를 조회한다. |
| 구현됨 | 리포트 세그먼트 목록 | 치료사, 관리자 | GET | `/api/v1/reports/{reportId}/segments` | - | - | SOAP 섹션 단위 세그먼트 목록 조회 |
| 구현됨 | 리포트 세그먼트 수정 | 치료사, 관리자 | PATCH | `/api/v1/reports/{reportId}/segments/{segmentId}` | - | `ai_content`, `content` 등 | 개별 SOAP 섹션 내용 수정 |
| 구현됨 | 리포트 상태 변경 | 치료사, 관리자 | PATCH | `/api/v1/reports/{reportId}/status` | - | `status` | 리포트 상태 전이 (`DRAFT` → `REVIEWING` → `APPROVED` → `FINALIZED`) |
| 구현됨 | 세션별 리포트 목록 | 치료사, 관리자 | GET | `/api/v1/sessions/{sessionId}/reports` | - | - | 세션에 연결된 리포트 목록 조회 |
| 미구현 | 리포트 생성 | 치료사, 관리자 | POST | `/api/v1/reports` | - | - | LLM Worker가 직접 저장하므로 BE 생성 엔드포인트 없음 |
| 미구현 | 리포트 다운로드 | 치료사, 관리자 | GET | `/api/v1/reports/{reportId}/download` | - | - | PDF 렌더링 후속 작업으로 남김 |

### 구현 메모

- 리포트 초안은 LLM GPU Worker가 S3 저장 후 `reports` + `report_segments` 테이블에 직접 기록한다.
- 리포트 상태 전이: `DRAFT` → `REVIEWING` → `APPROVED` → `FINALIZED`. `DELETED`는 soft delete.
- `report_segments`는 SOAP Note의 각 섹션(SUBJECTIVE / OBJECTIVE / ASSESSMENT / PLAN / CUSTOM)을 분리 저장한다.
- `ai_content`(AI 원본, 불변)와 `content`(치료사 편집본)를 컬럼으로 분리한다.
- 보호자/공유 사용자 대상 리포트 공개 정책과 PDF 렌더링은 미구현이다.
