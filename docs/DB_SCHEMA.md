# UtterAI BE — DB Schema 설계 문서

> **기준**: `entities.py` 기반 (`app/models/entities.py`)  
> **DB**: PostgreSQL (RDS) — BE 전용 (AI DB는 별도 `rag_chunks` 테이블)  
> **마지막 마이그레이션**: `20260610_0013_remove_approval_history`

---

## 전체 테이블 목록

| 테이블 | 설명 |
|---|---|
| `users` | SLP/관리자 계정 |
| `refresh_tokens` | JWT refresh token 저장 |
| `patient_refs` | 온프레미스 환자 DB와의 연결 참조 키 |
| `sessions` | 치료 세션 |
| `audio_files` | 세션 음성 파일 메타데이터 (S3 presigned upload) |
| `analysis_jobs` | AI 분석 파이프라인 작업 |
| `transcripts` | 분석 결과 스크립트 헤더 |
| `transcript_segments` | 스크립트 발화 단위 |
| `language_metrics` | 언어 지표 (MLU, TTR, NTW, NDW 등) |
| `templates` | SLP가 업로드한 리포트 템플릿 파일 |
| `reports` | AI 생성 리포트 헤더 |
| `report_segments` | 리포트 SOAP 섹션 단위 |

---

## 테이블 상세

### `users`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 로그인 이메일 |
| `password_hash` | TEXT | NOT NULL | bcrypt 해시 |
| `name` | VARCHAR(100) | NOT NULL | 표시 이름 |
| `role` | ENUM(user_role) | NOT NULL | `ADMIN`, `SLP` |
| `status` | ENUM(user_status) | NOT NULL, default `ACTIVE` | `ACTIVE`, `INACTIVE` |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, server_default | |

---

### `refresh_tokens`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users(id) ON DELETE CASCADE | |
| `token_hash` | VARCHAR(255) | UNIQUE, NOT NULL | SHA-256 해시 |
| `expires_at` | TIMESTAMPTZ | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `revoked_at` | TIMESTAMPTZ | nullable | revoke 시점 |

---

### `patient_refs`

> 온프레미스 환자 DB와의 브릿지. 클라우드에서는 UUID만 보유하며, 실제 환자 정보는 온프레미스 DB에 있음.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | 클라우드 측 환자 참조 키 |
| `created_at` | TIMESTAMPTZ | NOT NULL | 참조 생성 시점 |

---

### `sessions`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `patient_ref_id` | UUID | FK → patient_refs(id) ON DELETE RESTRICT | |
| `slp_id` | UUID | FK → users(id) ON DELETE RESTRICT | 담당 치료사 |
| `session_date` | DATE | NOT NULL | 세션 날짜 |
| `session_type` | VARCHAR(100) | nullable | 세션 유형 (예: 언어치료) |
| `session_goal` | TEXT | nullable | 세션 목표 |
| `memo` | TEXT | nullable | 메모 |
| `status` | ENUM(session_status) | NOT NULL, default `CREATED` | 아래 상태 전이 참조 |
| `completed_at` | TIMESTAMPTZ | nullable | 세션 완료 시점 |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, server_default | |

**session_status 전이:**
```
CREATED → AUDIO_UPLOADING → AUDIO_UPLOADED
         → ANALYSIS_REQUESTED → ANALYSIS_PROCESSING
         → ANALYSIS_COMPLETED → REPORT_READY
         → FAILED / DELETED
```

---

### `audio_files`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `created_by_slp_id` | UUID | FK → users(id) ON DELETE RESTRICT | |
| `object_key` | TEXT | UNIQUE, NOT NULL | S3 object key (`raw-audio/{slp_id}/{session_id}/...`) |
| `original_filename` | TEXT | NOT NULL | 원본 파일명 |
| `content_type` | VARCHAR(100) | nullable | MIME 타입 (예: `audio/wav`) |
| `actual_size_bytes` | BIGINT | nullable | 업로드 완료 후 실제 파일 크기 |
| `presigned_expires_at` | TIMESTAMPTZ | nullable | presigned URL 만료 시각 |
| `uploaded_at` | TIMESTAMPTZ | nullable | S3 업로드 완료 시각 |
| `status` | ENUM(audio_file_status) | NOT NULL, default `PENDING_UPLOAD` | `PENDING_UPLOAD`, `UPLOADED`, `FAILED`, `EXPIRED`, `DELETED` |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**업로드 흐름:**
1. `POST /audio-files/presigned-url` → `PENDING_UPLOAD` 행 생성, presigned PUT URL 반환
2. 클라이언트 → S3 직접 PUT
3. `POST /audio-files` (complete) → S3 존재 확인 후 `UPLOADED`로 전환

---

### `analysis_jobs`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `audio_file_id` | UUID | FK → audio_files(id) ON DELETE RESTRICT | |
| `status` | ENUM(analysis_job_status) | NOT NULL, default `PENDING` | 아래 파이프라인 단계 참조 |
| `pipeline_stage` | VARCHAR(255) | nullable | 현재 파이프라인 단계 문자열 |
| `error_code` | VARCHAR(100) | nullable | 에러 코드 |
| `error_message` | TEXT | nullable | 에러 상세 메시지 |
| `retry_count` | INTEGER | NOT NULL, default 0 | 재시도 횟수 |
| `started_at` | TIMESTAMPTZ | nullable | 파이프라인 시작 시각 |
| `completed_at` | TIMESTAMPTZ | nullable | 완료/실패 시각 |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**analysis_job_status (파이프라인 단계):**
```
PENDING → DOWNLOADING → PREPROCESSING
        → RUNNING_VAD → RUNNING_DIARIZATION → RUNNING_ASR → ALIGNING
        → CALCULATING_METRICS → RUNNING_RAG → GENERATING_REPORT → SAVING_RESULT
        → COMPLETED
        → FAILED / CANCELLED / RETRYING
```

---

### `transcripts`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `audio_file_id` | UUID | FK → audio_files(id) ON DELETE RESTRICT | |
| `job_id` | UUID | FK → analysis_jobs(id) ON DELETE RESTRICT | |
| `status` | ENUM(transcript_status) | NOT NULL, default `DRAFT` | `DRAFT`, `EDITING`, `REVIEWED`, `FINALIZED` |
| `raw_draft_s3_key` | TEXT | nullable | AI 생성 원본 스크립트 S3 키 |
| `final_s3_key` | TEXT | nullable | 검토 완료 최종본 S3 키 |
| `finalized_by` | UUID | FK → users(id) ON DELETE SET NULL, nullable | |
| `finalized_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, server_default | |

---

### `transcript_segments`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `transcript_id` | UUID | FK → transcripts(id) ON DELETE CASCADE | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `segment_index` | INTEGER | NOT NULL | 발화 순서 (0-based) |
| `speaker_label` | VARCHAR(50) | nullable | 다이어라이제이션 레이블 (예: `SPEAKER_00`) |
| `speaker_role` | ENUM(speaker_role) | NOT NULL, default `UNKNOWN` | `PATIENT`, `SLP`, `GUARDIAN`, `UNKNOWN` |
| `start_ms` | INTEGER | nullable | 발화 시작 (밀리초) |
| `end_ms` | INTEGER | nullable | 발화 종료 (밀리초) |
| `original_text` | TEXT | nullable | ASR 원본 텍스트 |
| `text` | TEXT | nullable | 현재 텍스트 (치료사 편집 반영) |
| `confidence` | FLOAT | nullable | ASR 신뢰도 (0~1) |
| `is_edited` | BOOLEAN | NOT NULL, default false | 치료사 편집 여부 |
| `edited_by` | UUID | FK → users(id) ON DELETE SET NULL, nullable | |
| `edited_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

### `language_metrics`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `job_id` | UUID | FK → analysis_jobs(id) ON DELETE RESTRICT | |
| `target_speaker` | ENUM(target_speaker) | NOT NULL | `PATIENT`, `SLP`, `ALL` |
| `total_utterances` | INTEGER | nullable | 총 발화 수 |
| `ntw` | INTEGER | nullable | 총 낱말 수 |
| `ndw` | INTEGER | nullable | 다른 낱말 수 |
| `ttr` | FLOAT | nullable | 어휘 다양도 (NDW/NTW) |
| `mlu_morpheme` | FLOAT | nullable | 평균 발화 길이 (형태소 기준) |
| `avg_response_latency_sec` | FLOAT | nullable | 평균 반응 지연 시간 (초) |
| `max_response_latency_sec` | FLOAT | nullable | 최대 반응 지연 시간 (초) |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

### `templates`

> SLP가 직접 업로드한 리포트 템플릿 파일. 분석 요청 시 AI에 함께 전달되어 리포트 생성 형식을 지정한다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `owner_id` | UUID | FK → users(id) ON DELETE RESTRICT, nullable | null = 시스템 기본 템플릿 |
| `name` | VARCHAR(255) | NOT NULL | 템플릿 표시 이름 |
| `description` | TEXT | nullable | 템플릿 설명 |
| `template_type` | ENUM(template_type) | NOT NULL | `SOAP_NOTE`, `CUSTOM` |
| `sections_json` | JSONB | nullable | 섹션 구조 정의 (파일 없이 구조만 지정할 경우) |
| `file_s3_key` | TEXT | nullable | 업로드된 템플릿 파일 S3 키 |
| `file_original_name` | VARCHAR(500) | nullable | 업로드 원본 파일명 |
| `is_system` | BOOLEAN | NOT NULL, default false | 시스템 기본 제공 여부 (SLP 소유 아님) |
| `use_count` | INTEGER | NOT NULL, default 0 | 분석 요청에 사용된 횟수 |
| `status` | ENUM(template_status) | NOT NULL, default `ACTIVE` | `ACTIVE`, `DELETED` |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, server_default | |

**사용 흐름**: SLP가 파일 업로드 → S3 저장 후 `file_s3_key` 기록 → 분석 요청 시 `template_id` 지정 → AI 서버가 해당 파일을 참조해 리포트 생성

---

### `reports`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `session_id` | UUID | FK → sessions(id) ON DELETE RESTRICT | |
| `job_id` | UUID | FK → analysis_jobs(id) ON DELETE RESTRICT | |
| `template_id` | UUID | FK → templates(id) ON DELETE SET NULL, nullable | 생성에 사용된 템플릿 |
| `status` | ENUM(report_status) | NOT NULL, default `DRAFT` | `DRAFT`, `REVIEWING`, `APPROVED`, `FINALIZED`, `DELETED` |
| `model_used` | VARCHAR(255) | nullable | Bedrock 모델 ID (예: `claude-sonnet-4-6`) |
| `clinical_flags` | JSONB | nullable | AI가 탐지한 임상 플래그 목록 |
| `evidence_chunk_ids` | JSONB | nullable | RAG에서 참조한 chunk ID 목록 |
| `requires_human_review` | BOOLEAN | NOT NULL, default true | 인간 검토 필요 여부 |
| `s3_key` | TEXT | nullable | 최종 리포트 S3 키 |
| `generated_at` | TIMESTAMPTZ | nullable | AI 생성 시각 |
| `updated_at` | TIMESTAMPTZ | NOT NULL | 마지막 수정 시각 |

---

### `report_segments`

> 리포트의 SOAP 섹션 단위. AI가 생성한 `ai_content`와 치료사 편집 `content`를 분리 보관.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `report_id` | UUID | FK → reports(id) ON DELETE CASCADE | |
| `segment_type` | ENUM(report_segment_type) | NOT NULL | `SUBJECTIVE`, `OBJECTIVE`, `ASSESSMENT`, `PLAN`, `CUSTOM` |
| `segment_index` | INTEGER | NOT NULL | 섹션 순서 (0-based) |
| `title` | VARCHAR(255) | nullable | 섹션 제목 |
| `ai_content` | TEXT | nullable | AI 생성 원본 내용 (불변) |
| `content` | TEXT | nullable | 현재 내용 (치료사 편집 가능) |
| `is_edited` | BOOLEAN | NOT NULL, default false | 치료사 편집 여부 |
| `edited_by` | UUID | FK → users(id) ON DELETE SET NULL, nullable | |
| `edited_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

## AI DB (`UtterAI_AI`)

AI 서버 전용 DB. BE RDS와 분리된 PostgreSQL + pgvector.

### `rag_chunks`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | |
| `source_type` | VARCHAR(100) | NOT NULL | 원문 출처 유형 (예: `clinical_guideline`) |
| `source_ref` | TEXT | nullable | 원문 참조 경로 |
| `chunk_text` | TEXT | NOT NULL | 청크 원문 |
| `embedding` | VECTOR(1024) | NOT NULL | 임베딩 벡터 (pgvector) |
| `metadata_json` | JSONB | nullable | 추가 메타데이터 |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

## 주요 Enum 값

| Enum | 값 |
|---|---|
| `user_role` | `ADMIN`, `SLP` |
| `user_status` | `ACTIVE`, `INACTIVE` |
| `session_status` | `CREATED`, `AUDIO_UPLOADING`, `AUDIO_UPLOADED`, `ANALYSIS_REQUESTED`, `ANALYSIS_PROCESSING`, `ANALYSIS_COMPLETED`, `REPORT_READY`, `FAILED`, `DELETED` |
| `audio_file_status` | `PENDING_UPLOAD`, `UPLOADED`, `FAILED`, `EXPIRED`, `DELETED` |
| `analysis_job_status` | `PENDING`, `DOWNLOADING`, `PREPROCESSING`, `RUNNING_VAD`, `RUNNING_DIARIZATION`, `RUNNING_ASR`, `ALIGNING`, `CALCULATING_METRICS`, `RUNNING_RAG`, `GENERATING_REPORT`, `SAVING_RESULT`, `COMPLETED`, `FAILED`, `RETRYING`, `CANCELLED` |
| `target_speaker` | `PATIENT`, `SLP`, `ALL` |
| `speaker_role` | `PATIENT`, `SLP`, `GUARDIAN`, `UNKNOWN` |
| `transcript_status` | `DRAFT`, `EDITING`, `REVIEWED`, `FINALIZED` |
| `template_type` | `SOAP_NOTE`, `CUSTOM` |
| `template_status` | `ACTIVE`, `DELETED` |
| `report_status` | `DRAFT`, `REVIEWING`, `APPROVED`, `FINALIZED`, `DELETED` |
| `report_segment_type` | `SUBJECTIVE`, `OBJECTIVE`, `ASSESSMENT`, `PLAN`, `CUSTOM` |

---

## 설계 결정 사항

| 항목 | 결정 | 이유 |
|---|---|---|
| `patient_refs` 분리 | 온프레미스 환자 DB와 클라우드 분리 | 실제 환자 정보는 온프레미스에만 보관 |
| `s3_bucket` 제거 | `object_key`만 저장, bucket은 config에서 관리 | 버킷은 환경별 설정값, DB에 중복 보관 불필요 |
| `report_segments` 분리 | SOAP 섹션별 편집 가능하게 | 섹션 단위 AI 원본 보존 + SLP 편집 이력 추적 |
| `language_metrics` 별도 테이블 | AI worker 기록, report 생성 시 읽음 | SOAP Objective 섹션 데이터 소스 |
| `organizations` 제거 | 단일 기관 운영 | 불필요한 복잡도 제거 |
| `audit_log` 제거 | 즉시 사용 계획 없음 | 필요 시 추후 추가 |
| `model_used` VARCHAR | Bedrock 모델 ID 하나만 저장 | 파이프라인 전체 모델 버전은 AI 서버 책임 |
| `templates` 파일 업로드 방식 | SLP가 직접 파일 업로드, AI가 참조 | 구조화된 JSON 대신 SLP 소유 파일로 리포트 형식 지정 |
| `VIEWER` 역할 제거 | 사용자 역할을 ADMIN/SLP만 유지 | 보호자는 앱에 직접 접근하지 않음 |
| `patient_access_grants` 미구현 | 보호자 공유 권한 테이블 없음 | 보호자 공유는 리포트 파일 전달 또는 공유 링크로 처리 |
