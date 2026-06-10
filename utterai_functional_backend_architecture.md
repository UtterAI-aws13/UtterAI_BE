## UtterAI Functional Backend Architecture

---

## 1. 문서 목적

이 문서는 UtterAI 서비스에서 **AI 모델 처리 영역을 제외한 웹 동작용 기능 백엔드** 설계 문서이다.

AI 모델 추론, VAD, ASR, 화자 분리, RAG 처리, 지표 계산 로직은 별도 AI 서버 또는 AI 파이프라인에서 담당한다고 가정한다.

따라서 이 문서에서 다루는 백엔드는 다음 역할에 집중한다.

- 사용자 인증과 권한 관리
- 아동 프로필 관리
- 상담 세션 관리
- 음성 파일 업로드 관리
- AI 분석 요청 생성
- 분석 진행 상태 조회
- AI 분석 결과 저장 및 화면 제공
- 리포트 조회 및 다운로드
- 사용자 피드백 관리
- 관리자용 데이터 관리
- 웹 프론트엔드와 AI 시스템 사이의 연결 역할

---

## 2. 백엔드 범위 정의

### 2.1 백엔드가 담당하는 것

기능적 백엔드는 웹 서비스 운영에 필요한 API와 데이터를 관리한다.

| 구분 | 백엔드 담당 여부 | 설명 |
|---|---:|---|
| 회원가입 / 로그인 | O | 사용자 인증과 JWT 발급 |
| 아동 프로필 관리 | O | 치료사가 등록한 아동 정보 관리 |
| 상담 세션 관리 | O | 상담 회차, 날짜, 상태 관리 |
| 음성 업로드 URL 발급 | O | S3 Presigned URL 생성 |
| 업로드 완료 처리 | O | 업로드된 파일 검증 및 메타데이터 저장 |
| 분석 요청 생성 | O | AI 서버에 분석 요청을 보낼 Job 생성 |
| 분석 상태 조회 | O | 프론트엔드에 진행 상태 제공 |
| 분석 결과 조회 | O | AI 서버가 저장한 결과를 화면용으로 제공 |
| 리포트 다운로드 | O | PDF 또는 HTML 리포트 URL 제공 |
| 관리자 기능 | O | 사용자, 세션, 분석 상태 관리 |
| AI 모델 추론 | X | 별도 AI 서버 담당 |
| VAD / ASR / 화자 분리 | X | 별도 AI 서버 담당 |
| RAG 검색 및 LLM 호출 | X | 별도 AI 서버 또는 RAG 서버 담당 |
| 언어 지표 계산 | X | 별도 AI 서버 담당 |

---

### 2.2 백엔드의 핵심 역할

이 백엔드는 **웹 서비스의 상태 관리 서버**로 보면 된다.

즉, 사용자가 웹에서 어떤 동작을 했는지 저장하고, AI 시스템에 필요한 요청을 전달하며, AI 시스템이 만들어낸 결과를 다시 사용자 화면에 보여주는 역할을 한다.

```text
사용자 웹 화면
    |
    v
기능 백엔드
    |
    |-- 사용자 / 권한 관리
    |-- 아동 / 세션 관리
    |-- 파일 업로드 관리
    |-- 분석 요청 관리
    |-- 결과 조회 API 제공
    |
    v
AI 서버 또는 AI 파이프라인
```

---

## 3. 전체 웹 백엔드 아키텍처

### 3.1 논리 구조

```text
[Frontend Web/App]
        |
        v
[API Gateway or ALB]
        |
        v
[Backend API Server]
        |
        |-- [Aurora PostgreSQL]
        |-- [Amazon S3]
        |-- [Redis]
        |-- [SQS or EventBridge]
        |-- [AI Service API]
        |-- [CloudWatch Logs]
```

---

### 3.2 백엔드와 AI 영역 분리

백엔드와 AI 서버는 다음과 같이 분리한다.

```text
웹 기능 백엔드
    |
    | 1. 분석 요청 생성
    | 2. 분석 Job ID 발급
    | 3. AI 서버에 요청 전달
    | 4. 분석 상태 저장
    | 5. 결과 조회 API 제공
    v
AI 서버
    |
    | 1. 음성 파일 다운로드
    | 2. AI 모델 처리
    | 3. 분석 결과 생성
    | 4. 백엔드 Callback 또는 DB/S3 저장
```

기능 백엔드는 AI 모델을 직접 실행하지 않는다.

백엔드는 AI 서버를 다음 방식 중 하나로 호출할 수 있다.

| 방식 | 설명 | 추천 시점 |
|---|---|---|
| HTTP API 호출 | 백엔드가 AI 서버의 분석 API를 호출 | MVP |
| SQS 메시지 발행 | 백엔드가 분석 요청 메시지를 큐에 넣고 AI 서버가 소비 | 비동기 처리 고도화 |
| EventBridge 이벤트 발행 | 분석 요청 이벤트를 발행하고 여러 시스템이 구독 | 확장 단계 |

MVP에서는 **HTTP API 호출 또는 SQS 메시지 발행 방식**이 가장 현실적이다.

---

## 4. 주요 도메인 설계

---

## 4.1 Auth 도메인

### 기능 목적

Auth 도메인은 사용자의 로그인, 토큰 발급, 권한 검사를 담당한다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 회원가입 | 이메일, 비밀번호, 이름을 기반으로 사용자 생성 |
| 로그인 | 사용자 인증 후 Access Token과 Refresh Token 발급 |
| 토큰 재발급 | Refresh Token으로 Access Token 재발급 |
| 로그아웃 | Refresh Token 무효화 |
| 내 정보 조회 | 현재 로그인한 사용자 정보 반환 |

### 사용자 역할

| 역할 | 설명 |
|---|---|
| `ADMIN` | 전체 시스템 관리자 |
| `SLP` | 치료사 |
| `GUARDIAN` | 보호자 |
| `VIEWER` | 제한된 조회 사용자 |

### 동작 흐름

```text
1. 사용자가 이메일과 비밀번호 입력
2. 백엔드가 사용자 조회
3. 비밀번호 해시 검증
4. JWT Access Token 발급
5. Refresh Token 저장
6. 이후 요청에서 Authorization Header 검증
```

### API 예시

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/auth/signup` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/refresh` | 토큰 재발급 |
| POST | `/api/v1/auth/logout` | 로그아웃 |
| GET | `/api/v1/auth/me` | 내 정보 조회 |

---

## 4.2 User 도메인

### 기능 목적

User 도메인은 사용자 계정과 프로필 정보를 관리한다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 사용자 목록 조회 | 관리자용 사용자 목록 조회 |
| 사용자 상세 조회 | 특정 사용자 정보 조회 |
| 사용자 정보 수정 | 이름, 소속, 연락처 등 수정 |
| 사용자 비활성화 | 계정 사용 중지 |
| 권한 변경 | 관리자만 사용자 역할 변경 가능 |

### 권한 기준

일반 사용자는 자신의 정보만 수정할 수 있다.

관리자는 전체 사용자 정보를 조회하거나 권한을 변경할 수 있다.

---

## 4.3 Patient Profile 도메인

### 기능 목적

Patient Profile 도메인은 분석 대상 아동 정보를 관리한다.

치료사는 여러 아동 프로필을 등록할 수 있다.

### 저장 정보

| 필드 | 설명 |
|---|---|
| `child_id` | 아동 고유 ID |
| `therapist_id` | 담당 치료사 ID |
| `name` | 아동 이름 또는 별칭 |
| `birth_date` | 생년월일 |
| `gender` | 성별 |
| `memo` | 치료사 메모 |
| `created_at` | 생성일 |
| `updated_at` | 수정일 |

### 주요 기능

| 기능 | 설명 |
|---|---|
| 아동 등록 | 치료사가 새 아동 프로필 생성 |
| 아동 목록 조회 | 로그인한 치료사의 아동 목록 조회 |
| 아동 상세 조회 | 특정 아동의 상세 정보 조회 |
| 아동 정보 수정 | 아동 이름, 메모 등 수정 |
| 아동 삭제 | 아동 프로필 삭제 또는 비활성화 |

### 동작 흐름

```text
1. 치료사가 아동 등록 요청
2. 백엔드가 로그인 사용자 확인
3. slp_id와 patient 정보를 연결
4. patient_refs 테이블에 저장
5. 프론트엔드에 생성된 patient_ref_id 반환
```

---

## 4.4 Session 도메인

### 기능 목적

Session은 하나의 상담 또는 검사 회차를 의미한다.

예를 들어 한 아동이 특정 날짜에 진행한 상담 1회가 하나의 Session이 된다.

### Session이 필요한 이유

AI 분석은 음성 파일 하나만으로 끝나지 않는다.

음성 파일은 특정 아동, 특정 상담 회차, 특정 치료사와 연결되어야 한다.

그래서 백엔드는 분석의 기준 단위로 Session을 관리한다.

```text
Patient
  |
  v
Session
  |
  v
Audio File
  |
  v
Analysis Job
  |
  v
Analysis Result
```

### 주요 기능

| 기능 | 설명 |
|---|---|
| 세션 생성 | 상담 회차 생성 |
| 세션 목록 조회 | 아동별 또는 치료사별 세션 목록 조회 |
| 세션 상세 조회 | 상담 날짜, 상태, 파일, 분석 결과 요약 조회 |
| 세션 수정 | 상담 메모, 상담 유형 수정 |
| 세션 삭제 | 세션 삭제 또는 비활성화 |
| 세션 상태 관리 | 업로드 전, 분석 중, 완료 등 상태 관리 |

### 세션 상태

| 상태 | 설명 |
|---|---|
| `CREATED` | 세션만 생성됨 |
| `AUDIO_UPLOADING` | 음성 업로드 준비 중 |
| `AUDIO_UPLOADED` | 음성 업로드 완료 |
| `ANALYSIS_REQUESTED` | AI 분석 요청 완료 |
| `ANALYSIS_PROCESSING` | AI 분석 진행 중 |
| `ANALYSIS_COMPLETED` | 분석 완료 |
| `REPORT_READY` | 리포트 생성 완료 |
| `FAILED` | 처리 실패 |

---

## 4.5 Audio 도메인

### 기능 목적

Audio 도메인은 음성 파일 업로드와 파일 메타데이터를 관리한다.

백엔드는 파일을 직접 받지 않고, S3 Presigned URL을 발급한다.

### Presigned URL을 사용하는 이유

```text
사용자 브라우저
    |
    | 1. 업로드 URL 요청
    v
백엔드
    |
    | 2. Presigned URL 발급
    v
사용자 브라우저
    |
    | 3. S3로 직접 업로드
    v
S3
```

이 구조를 사용하면 다음 장점이 있다.

- 백엔드 서버가 대용량 파일을 직접 받지 않아도 된다.
- API 서버의 네트워크 부하가 줄어든다.
- S3에 안전하게 제한된 시간 동안만 업로드할 수 있다.
- 파일 저장 위치와 권한을 백엔드가 통제할 수 있다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 업로드 URL 발급 | S3 Presigned URL 생성 |
| 업로드 완료 처리 | S3 파일 존재 여부 확인 |
| 음성 파일 메타데이터 조회 | 파일명, 크기, 상태 조회 |
| 음성 파일 삭제 | S3 객체와 DB 메타데이터 삭제 |
| 다운로드 URL 발급 | 권한 있는 사용자에게만 다운로드 URL 제공 |

### 업로드 완료 처리 흐름

```text
1. 프론트엔드가 백엔드에 업로드 URL 요청
2. 백엔드가 audio_files row 생성
3. 백엔드가 S3 Presigned URL 반환
4. 프론트엔드가 S3에 직접 파일 업로드
5. 프론트엔드가 백엔드에 업로드 완료 API 호출
6. 백엔드가 S3 HeadObject로 파일 존재 여부 확인
7. audio_files 상태를 UPLOADED로 변경
8. session 상태를 AUDIO_UPLOADED로 변경
```

---

## 4.6 Analysis Job 도메인

### 기능 목적

Analysis Job은 AI 서버에 분석을 요청하고, 분석 상태를 추적하기 위한 작업 단위이다.

AI 처리는 별도 시스템에서 하지만, 사용자는 웹 화면에서 분석 상태를 확인해야 한다.

따라서 기능 백엔드는 Analysis Job을 반드시 관리해야 한다.

### 백엔드가 관리하는 정보

| 정보 | 설명 |
|---|---|
| `job_id` | 분석 작업 ID |
| `session_id` | 연결된 상담 세션 |
| `audio_id` | 분석 대상 음성 파일 |
| `status` | 분석 상태 |
| `progress` | 진행률 |
| `requested_at` | 분석 요청 시간 |
| `completed_at` | 분석 완료 시간 |
| `error_message` | 실패 사유 |
| `external_ai_job_id` | AI 서버에서 발급한 Job ID |

### 분석 요청 흐름

```text
1. 사용자가 분석 시작 버튼 클릭
2. 프론트엔드가 백엔드에 분석 요청
3. 백엔드가 세션과 음성 파일 상태 확인
4. analysis_jobs row 생성
5. AI 서버에 분석 요청 전달
6. AI 서버의 external_ai_job_id 저장
7. 세션 상태를 ANALYSIS_PROCESSING으로 변경
8. 프론트엔드는 주기적으로 상태 조회
```

### 분석 상태

| 상태 | 설명 |
|---|---|
| `REQUESTED` | 분석 요청 생성 |
| `QUEUED` | AI 서버 대기열에 등록 |
| `PROCESSING` | AI 서버 처리 중 |
| `COMPLETED` | 분석 완료 |
| `FAILED` | 분석 실패 |
| `CANCELLED` | 사용자가 취소 |
| `EXPIRED` | 오래된 작업 만료 |

---

## 4.7 Analysis Result 도메인

### 기능 목적

Analysis Result 도메인은 AI 서버가 만든 결과를 웹 화면에서 보여줄 수 있는 형태로 저장하고 제공한다.

백엔드는 분석을 직접 하지 않지만, 결과를 받아서 저장하고 조회 API를 제공한다.

### 결과 저장 방식

AI 서버의 분석 결과는 다음 방식 중 하나로 백엔드에 전달된다.

| 방식 | 설명 |
|---|---|
| Callback API | AI 서버가 백엔드의 결과 수신 API를 호출 |
| DB 저장 | AI 서버가 같은 DB에 결과 저장 |
| S3 저장 후 알림 | AI 서버가 결과 JSON을 S3에 저장하고 백엔드에 위치 전달 |
| Polling | 백엔드가 AI 서버에 주기적으로 결과 조회 |

MVP에서는 **Callback API** 또는 **S3 저장 후 Callback** 방식을 추천한다.

### Callback 흐름

```text
AI 서버
    |
    | POST /api/v1/internal/analysis-results/callback
    v
백엔드
    |
    | 1. Callback 인증 검증
    | 2. job_id 확인
    | 3. 결과 JSON 저장
    | 4. job 상태 COMPLETED 변경
    | 5. session 상태 ANALYSIS_COMPLETED 변경
```

### 저장 결과 예시

```json
{
  "jobId": "job_123",
  "sessionId": "session_123",
  "summary": {
    "totalUtterances": 42,
    "patientUtterances": 18,
    "slpUtterances": 24,
    "durationSeconds": 530
  },
  "transcriptS3Key": "results/session_123/transcript.json",
  "metricsS3Key": "results/session_123/metrics.json",
  "reportS3Key": "reports/session_123/report.pdf"
}
```

---

## 4.8 Transcript 도메인

### 기능 목적

Transcript 도메인은 AI 서버가 생성한 발화 텍스트를 웹 화면에서 조회하고 수정할 수 있게 한다.

AI가 만든 전사 결과는 항상 완벽하지 않으므로, 치료사가 화면에서 수정할 수 있어야 한다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 발화 목록 조회 | 세션별 발화 텍스트 조회 |
| 발화 수정 | 치료사가 오인식된 텍스트 수정 |
| 화자 역할 수정 | SPEAKER_00을 아동/치료사로 매핑 |
| 발화 삭제 | 잘못 생성된 발화 제거 |
| 발화 추가 | 누락된 발화 수동 추가 |

### 동작 흐름

```text
1. 사용자가 세션 분석 결과 화면 진입
2. 백엔드가 utterances 목록 조회
3. 프론트엔드가 타임라인 형태로 표시
4. 사용자가 잘못된 텍스트를 수정
5. 백엔드가 수정 이력을 저장
6. 수정된 텍스트가 리포트 재생성에 반영됨
```

### 수정 이력 관리

발화 수정은 원본과 수정본을 구분하는 것이 좋다.

| 필드 | 설명 |
|---|---|
| `original_text` | AI가 생성한 원본 텍스트 |
| `edited_text` | 사용자가 수정한 텍스트 |
| `edited_by` | 수정한 사용자 |
| `edited_at` | 수정 시간 |

---

## 4.9 Report 도메인

### 기능 목적

Report 도메인은 분석 결과를 사용자에게 보여주거나 다운로드할 수 있게 한다.

리포트 자체 생성 로직이 AI 서버에 있다면, 기능 백엔드는 리포트 파일의 메타데이터와 다운로드 권한만 관리한다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 리포트 목록 조회 | 세션별 리포트 목록 조회 |
| 리포트 상세 조회 | 리포트 요약 데이터 조회 |
| 리포트 다운로드 URL 발급 | S3 Presigned Download URL 발급 |
| 리포트 재생성 요청 | 수정된 발화 기준으로 AI 서버에 재생성 요청 |
| 리포트 공개 상태 변경 | 보호자 공유 여부 설정 |

### 다운로드 흐름

```text
1. 사용자가 리포트 다운로드 클릭
2. 백엔드가 사용자 권한 확인
3. reports 테이블에서 S3 Key 조회
4. S3 Presigned Download URL 발급
5. 프론트엔드가 해당 URL로 파일 다운로드
```

---

## 4.10 Dashboard 도메인

### 기능 목적

Dashboard 도메인은 웹 메인 화면에서 필요한 요약 데이터를 제공한다.

### 제공 데이터 예시

| 화면 | 필요 데이터 |
|---|---|
| 치료사 홈 | 담당 아동 수, 최근 세션, 분석 대기 건수 |
| 아동 상세 | 세션 목록, 최근 분석 결과, 리포트 목록 |
| 세션 상세 | 업로드 파일, 분석 상태, 결과 요약 |
| 관리자 홈 | 전체 사용자 수, 분석 실패 건수, 최근 가입자 |

### API 예시

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/dashboard/slp` | 치료사 대시보드 |
| GET | `/api/v1/dashboard/admin` | 관리자 대시보드 |
| GET | `/api/v1/patients/{patientId}/summary` | 아동 요약 |
| GET | `/api/v1/sessions/{sessionId}/summary` | 세션 요약 |

---

## 4.11 Notification 도메인

### 기능 목적

Notification 도메인은 사용자가 알아야 할 이벤트를 관리한다.

예를 들어 분석 완료, 분석 실패, 리포트 생성 완료 같은 알림을 제공한다.

### 알림 종류

| 알림 | 설명 |
|---|---|
| 분석 완료 | AI 분석이 완료됨 |
| 분석 실패 | 분석 중 오류 발생 |
| 리포트 준비 완료 | 다운로드 가능한 리포트 생성 |
| 공유 요청 | 보호자 또는 다른 사용자에게 공유됨 |
| 관리자 공지 | 시스템 공지 |

### 구현 방식

MVP에서는 알림 목록 조회 API만 구현해도 된다.

운영 단계에서는 WebSocket 또는 SSE를 사용할 수 있다.

```text
MVP:
프론트엔드가 알림 목록 API를 주기적으로 호출

확장:
WebSocket 또는 SSE로 실시간 알림 전송
```

---

## 4.12 Feedback 도메인

### 기능 목적

Feedback 도메인은 사용자가 분석 결과에 대해 남기는 의견을 관리한다.

AI 모델 개선은 별도 영역이지만, 기능 백엔드는 사용자의 피드백을 저장할 수 있어야 한다.

### 피드백 예시

| 피드백 유형 | 설명 |
|---|---|
| 전사 오류 | 음성 텍스트 변환 오류 |
| 화자 구분 오류 | 아동과 치료사 구분 오류 |
| 리포트 표현 오류 | 리포트 문장이 부정확함 |
| 기타 의견 | 자유 의견 |

### 주요 기능

| 기능 | 설명 |
|---|---|
| 피드백 등록 | 사용자가 분석 결과에 대한 피드백 작성 |
| 피드백 목록 조회 | 관리자 또는 치료사가 피드백 확인 |
| 피드백 상태 변경 | 확인 전, 처리 중, 처리 완료 |
| 피드백 메모 | 관리자 내부 메모 |

---

## 5. API 설계

---

## 5.1 Auth API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/auth/signup` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/refresh` | 토큰 재발급 |
| POST | `/api/v1/auth/logout` | 로그아웃 |
| GET | `/api/v1/auth/me` | 내 정보 조회 |

---

## 5.2 User API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/users/me` | 내 프로필 조회 |
| PATCH | `/api/v1/users/me` | 내 프로필 수정 |
| GET | `/api/v1/admin/users` | 사용자 목록 조회 |
| GET | `/api/v1/admin/users/{userId}` | 사용자 상세 조회 |
| PATCH | `/api/v1/admin/users/{userId}/role` | 사용자 권한 변경 |
| PATCH | `/api/v1/admin/users/{userId}/status` | 사용자 상태 변경 |

---

## 5.3 Patient API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/patients` | 아동 등록 |
| GET | `/api/v1/patients` | 아동 목록 조회 |
| GET | `/api/v1/patients/{patientId}` | 아동 상세 조회 |
| PATCH | `/api/v1/patients/{patientId}` | 아동 정보 수정 |
| DELETE | `/api/v1/patients/{patientId}` | 아동 삭제 |

---

## 5.4 Session API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/sessions` | 세션 생성 |
| GET | `/api/v1/sessions` | 세션 목록 조회 |
| GET | `/api/v1/sessions/{sessionId}` | 세션 상세 조회 |
| PATCH | `/api/v1/sessions/{sessionId}` | 세션 수정 |
| DELETE | `/api/v1/sessions/{sessionId}` | 세션 삭제 |

---

## 5.5 Audio API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/audio/upload-url` | 음성 업로드 URL 발급 |
| POST | `/api/v1/audio/{audioId}/complete` | 업로드 완료 처리 |
| GET | `/api/v1/audio/{audioId}` | 음성 파일 메타데이터 조회 |
| GET | `/api/v1/audio/{audioId}/download-url` | 음성 다운로드 URL 발급 |
| DELETE | `/api/v1/audio/{audioId}` | 음성 파일 삭제 |

---

## 5.6 Analysis Job API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/analysis-jobs` | 분석 요청 생성 |
| GET | `/api/v1/analysis-jobs/{jobId}` | 분석 상태 조회 |
| POST | `/api/v1/analysis-jobs/{jobId}/cancel` | 분석 취소 |
| POST | `/api/v1/analysis-jobs/{jobId}/retry` | 분석 재시도 |
| GET | `/api/v1/sessions/{sessionId}/analysis-job` | 세션 기준 분석 작업 조회 |

---

## 5.7 Analysis Result API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/sessions/{sessionId}/analysis-result` | 분석 결과 조회 |
| GET | `/api/v1/sessions/{sessionId}/metrics` | 분석 지표 조회 |
| GET | `/api/v1/sessions/{sessionId}/interpretation` | AI 해석 결과 조회 |
| POST | `/api/v1/internal/analysis-results/callback` | AI 서버 결과 수신 |

---

## 5.8 Transcript API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/sessions/{sessionId}/utterances` | 발화 목록 조회 |
| PATCH | `/api/v1/utterances/{utteranceId}` | 발화 텍스트 수정 |
| DELETE | `/api/v1/utterances/{utteranceId}` | 발화 삭제 |
| POST | `/api/v1/sessions/{sessionId}/utterances` | 발화 수동 추가 |
| PATCH | `/api/v1/sessions/{sessionId}/speakers` | 화자 역할 수정 |

---

## 5.9 Report API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/sessions/{sessionId}/reports` | 세션 리포트 목록 조회 |
| GET | `/api/v1/reports/{reportId}` | 리포트 상세 조회 |
| GET | `/api/v1/reports/{reportId}/download-url` | 리포트 다운로드 URL 발급 |
| POST | `/api/v1/reports/{reportId}/regenerate` | 리포트 재생성 요청 |
| PATCH | `/api/v1/reports/{reportId}/visibility` | 리포트 공개 상태 변경 |

---

## 5.10 Dashboard API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/dashboard/slp` | 치료사 대시보드 |
| GET | `/api/v1/dashboard/admin` | 관리자 대시보드 |
| GET | `/api/v1/patients/{patientId}/summary` | 아동 요약 정보 |
| GET | `/api/v1/sessions/{sessionId}/summary` | 세션 요약 정보 |

---

## 5.11 Notification API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/notifications` | 내 알림 목록 조회 |
| PATCH | `/api/v1/notifications/{notificationId}/read` | 알림 읽음 처리 |
| PATCH | `/api/v1/notifications/read-all` | 전체 읽음 처리 |

---

## 5.12 Feedback API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/feedbacks` | 피드백 등록 |
| GET | `/api/v1/feedbacks` | 내 피드백 목록 조회 |
| GET | `/api/v1/admin/feedbacks` | 관리자 피드백 목록 조회 |
| PATCH | `/api/v1/admin/feedbacks/{feedbackId}/status` | 피드백 처리 상태 변경 |

---

## 6. 주요 기능 동작 상세

---

## 6.1 아동 등록 기능

### 목적

치료사가 분석 대상 아동을 등록한다.

### 동작 순서

```text
1. 치료사가 아동 등록 화면에서 정보 입력
2. 프론트엔드가 POST /patients 호출
3. 백엔드가 JWT 검증
4. 사용자 역할이 SLP인지 확인
5. patient_refs 테이블에 저장
6. 생성된 patient_ref_id 반환
```

### 요청 예시

```json
{
  "name": "김OO",
  "birthDate": "2020-03-15",
  "gender": "MALE",
  "memo": "초기 상담 대상"
}
```

### 응답 예시

```json
{
  "patientId": "patient_123",
  "name": "김OO",
  "birthDate": "2020-03-15",
  "gender": "MALE",
  "createdAt": "2026-05-28T10:00:00+09:00"
}
```

---

## 6.2 세션 생성 기능

### 목적

특정 아동에 대한 상담 회차를 생성한다.

### 동작 순서

```text
1. 치료사가 아동 상세 화면에서 새 세션 생성
2. 백엔드가 patient_ref_id 접근 권한 확인
3. sessions 테이블에 세션 생성
4. session 상태를 CREATED로 저장
5. 생성된 session_id 반환
```

### 요청 예시

```json
{
  "patientId": "patient_123",
  "sessionDate": "2026-05-28",
  "sessionType": "LANGUAGE_ASSESSMENT",
  "memo": "첫 번째 녹음 세션"
}
```

---

## 6.3 음성 업로드 기능

### 목적

상담 세션에 연결할 음성 파일을 업로드한다.

### 동작 순서

```text
1. 프론트엔드가 업로드할 파일 정보를 백엔드에 전달
2. 백엔드가 파일 확장자와 크기 검증
3. 백엔드가 S3 Object Key 생성
4. audio_files 테이블에 PENDING 상태로 저장
5. S3 Presigned URL 발급
6. 프론트엔드가 S3에 직접 업로드
7. 업로드 완료 후 백엔드에 complete 호출
8. 백엔드가 S3 파일 존재 확인
9. audio_files 상태를 UPLOADED로 변경
10. session 상태를 AUDIO_UPLOADED로 변경
```

### Object Key 예시

```text
raw-audio/{slpId}/{patientId}/{sessionId}/{audioId}.wav
```

사용자가 입력한 파일명을 그대로 S3 Key에 쓰지 않고, 백엔드가 생성한 ID 기반 경로를 사용한다.

---

## 6.4 분석 요청 기능

### 목적

업로드된 음성 파일을 AI 서버가 분석하도록 요청한다.

### 동작 순서

```text
1. 사용자가 분석 시작 버튼 클릭
2. 백엔드가 session_id 기준으로 음성 업로드 완료 여부 확인
3. 기존 진행 중인 analysis_job이 있는지 확인
4. analysis_jobs 테이블에 REQUESTED 상태로 저장
5. AI 서버에 분석 요청
6. AI 서버에서 받은 external_ai_job_id 저장
7. analysis_jobs 상태를 QUEUED 또는 PROCESSING으로 변경
8. 프론트엔드에 job_id 반환
```

### AI 서버 요청 예시

```json
{
  "jobId": "job_123",
  "sessionId": "session_123",
  "audioId": "audio_123",
  "audioS3Key": "raw-audio/slp/patient/session/audio.wav",
  "callbackUrl": "https://api.utterai.com/api/v1/internal/analysis-results/callback"
}
```

기능 백엔드는 AI 서버에 요청을 보낼 뿐, 직접 모델을 실행하지 않는다.

---

## 6.5 분석 상태 조회 기능

### 목적

사용자가 웹 화면에서 분석 진행 상황을 확인할 수 있게 한다.

### 동작 방식

프론트엔드는 일정 간격으로 상태 조회 API를 호출한다.

```text
1. 프론트엔드가 GET /analysis-jobs/{jobId} 호출
2. 백엔드가 analysis_jobs 테이블 조회
3. status, progress, current_stage 반환
4. COMPLETED이면 결과 조회 버튼 활성화
5. FAILED이면 재시도 버튼 표시
```

### 응답 예시

```json
{
  "jobId": "job_123",
  "status": "PROCESSING",
  "progress": 65,
  "currentStage": "AI 분석 진행 중",
  "startedAt": "2026-05-28T10:00:00+09:00",
  "updatedAt": "2026-05-28T10:03:12+09:00"
}
```

---

## 6.6 분석 결과 수신 기능

### 목적

AI 서버가 분석을 완료하면 기능 백엔드에 결과를 전달한다.

### 동작 순서

```text
1. AI 서버가 분석 완료
2. AI 서버가 결과 JSON 또는 결과 S3 Key를 백엔드 Callback API로 전달
3. 백엔드가 내부 인증 토큰 검증
4. job_id 존재 여부 확인
5. analysis_results 테이블에 결과 저장
6. utterances, metrics, reports 메타데이터 저장
7. analysis_jobs 상태를 COMPLETED로 변경
8. sessions 상태를 ANALYSIS_COMPLETED 또는 REPORT_READY로 변경
9. 사용자 알림 생성
```

### Callback 요청 예시

```json
{
  "jobId": "job_123",
  "status": "COMPLETED",
  "result": {
    "summary": {
      "totalUtterances": 42,
      "patientUtterances": 18,
      "durationSeconds": 530
    },
    "transcriptS3Key": "results/session_123/transcript.json",
    "metricsS3Key": "results/session_123/metrics.json",
    "reportS3Key": "reports/session_123/report.pdf"
  }
}
```

---

## 6.7 결과 조회 기능

### 목적

분석 완료 후 사용자가 결과 화면에서 데이터를 확인한다.

### 화면 구성 예시

| 화면 영역 | 백엔드 제공 데이터 |
|---|---|
| 세션 요약 | 상담 날짜, 음성 길이, 분석 상태 |
| 발화 타임라인 | 화자, 시작 시간, 종료 시간, 텍스트 |
| 분석 지표 | 발화 수, 발화 비율, MLU, TTR 등 |
| AI 해석 | AI 서버가 생성한 요약/해석 |
| 리포트 | PDF 다운로드 링크 |

### 동작 순서

```text
1. 사용자가 결과 화면 진입
2. 프론트엔드가 세션 상세 API 호출
3. 프론트엔드가 분석 결과 API 호출
4. 프론트엔드가 발화 목록 API 호출
5. 프론트엔드가 리포트 목록 API 호출
6. 백엔드는 DB와 S3 Key를 기반으로 화면용 데이터 반환
```

---

## 6.8 발화 수정 기능

### 목적

AI 전사 결과가 틀렸을 때 치료사가 직접 수정할 수 있게 한다.

### 동작 순서

```text
1. 치료사가 발화 텍스트 수정
2. 프론트엔드가 PATCH /utterances/{utteranceId} 호출
3. 백엔드가 해당 세션 접근 권한 확인
4. original_text는 유지
5. edited_text에 수정본 저장
6. 수정 이력 저장
7. 리포트 재생성 필요 상태로 변경
```

### 요청 예시

```json
{
  "editedText": "자동차 가지고 놀았어요."
}
```

---

## 6.9 리포트 다운로드 기능

### 목적

분석 완료된 리포트를 PDF로 다운로드한다.

### 동작 순서

```text
1. 사용자가 리포트 다운로드 클릭
2. 프론트엔드가 다운로드 URL 요청
3. 백엔드가 사용자 권한 확인
4. reports 테이블에서 report_s3_key 조회
5. S3 Presigned Download URL 생성
6. 프론트엔드가 URL을 통해 파일 다운로드
```

---

## 6.10 리포트 재생성 요청 기능

### 목적

사용자가 발화 텍스트나 화자 역할을 수정한 뒤, 수정된 내용을 기준으로 리포트를 다시 만들도록 AI 서버에 요청한다.

### 동작 순서

```text
1. 사용자가 리포트 재생성 클릭
2. 백엔드가 수정된 utterances와 speaker mapping 확인
3. report 상태를 REGENERATING으로 변경
4. AI 서버에 리포트 재생성 요청
5. AI 서버가 새 리포트 생성 후 Callback
6. 백엔드가 새 report_s3_key 저장
7. report 상태를 READY로 변경
```

---

## 7. 데이터베이스 설계

---

## 7.1 users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.2 patient_refs

> 온프레미스 환자 DB와의 브릿지. 실제 환자 정보는 온프레미스에 보관하고, 클라우드에서는 참조 UUID만 관리한다.

```sql
CREATE TABLE patient_refs (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL
);
```

---

## 7.3 sessions

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    patient_ref_id UUID NOT NULL REFERENCES patient_refs(id),
    slp_id UUID NOT NULL REFERENCES users(id),
    session_date DATE NOT NULL,
    session_type VARCHAR(100),
    session_goal TEXT,
    memo TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

## 7.4 audio_files

```sql
CREATE TABLE audio_files (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    original_file_name TEXT NOT NULL,
    content_type VARCHAR(100),
    file_size BIGINT,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key TEXT NOT NULL,
    duration_seconds NUMERIC(10, 2),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.5 analysis_jobs

```sql
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    audio_id UUID NOT NULL REFERENCES audio_files(id),
    external_ai_job_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'REQUESTED',
    progress INT NOT NULL DEFAULT 0,
    current_stage VARCHAR(255),
    error_code VARCHAR(100),
    error_message TEXT,
    requested_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.6 analysis_results

```sql
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES analysis_jobs(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    summary_json JSONB,
    metrics_json JSONB,
    interpretation_text TEXT,
    transcript_s3_key TEXT,
    metrics_s3_key TEXT,
    raw_result_s3_key TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.7 speakers

```sql
CREATE TABLE speakers (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    speaker_label VARCHAR(50) NOT NULL,
    speaker_role VARCHAR(50),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.8 utterances

```sql
CREATE TABLE utterances (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    speaker_id UUID REFERENCES speakers(id),
    speaker_label VARCHAR(50),
    start_time NUMERIC(10, 2),
    end_time NUMERIC(10, 2),
    original_text TEXT,
    edited_text TEXT,
    confidence NUMERIC(5, 4),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.9 reports

```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id),
    job_id UUID REFERENCES analysis_jobs(id),
    report_type VARCHAR(50) NOT NULL,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'READY',
    visibility VARCHAR(50) NOT NULL DEFAULT 'PRIVATE',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.10 notifications

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL
);
```

---

## 7.11 feedbacks

```sql
CREATE TABLE feedbacks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID REFERENCES sessions(id),
    job_id UUID REFERENCES analysis_jobs(id),
    feedback_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    admin_memo TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## 7.12 patient_access_grants

보호자 공유 권한은 환자 단위로 관리하고, 세션/결과/리포트 접근 권한은 환자 공유 권한에서 파생시키는 것을 기본으로 한다.

```sql
CREATE TABLE patient_access_grants (
    id UUID PRIMARY KEY,
    patient_ref_id UUID NOT NULL REFERENCES patient_refs(id),
    grantee_user_id UUID NOT NULL REFERENCES users(id),
    granted_by_user_id UUID NOT NULL REFERENCES users(id),
    access_level VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    UNIQUE (patient_ref_id, grantee_user_id)
);
```

`access_level`은 MVP에서 다음 두 단계만 두는 것이 안전하다.

| access_level | 설명 |
|---|---|
| `VIEW_RESULT` | 결과/리포트/세션 조회만 가능 |
| `VIEW_AND_DOWNLOAD` | 조회 + 리포트 다운로드 가능 |

---

## 7.13 utterance_edit_history

발화 수정은 `utterances` 테이블에 최신본을 유지하고, 별도 이력 테이블에 변경 내역을 append-only로 저장하는 방식을 권장한다.

```sql
CREATE TABLE utterance_edit_history (
    id UUID PRIMARY KEY,
    utterance_id UUID NOT NULL REFERENCES utterances(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    edited_by UUID NOT NULL REFERENCES users(id),
    previous_text TEXT,
    new_text TEXT,
    previous_speaker_role VARCHAR(50),
    new_speaker_role VARCHAR(50),
    edit_reason TEXT,
    created_at TIMESTAMP NOT NULL
);
```

---

## 7.14 callback_event_receipts

AI Callback의 멱등 처리를 위해 수신 이벤트 자체를 기록한다.

```sql
CREATE TABLE callback_event_receipts (
    id UUID PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    job_id UUID REFERENCES analysis_jobs(id),
    payload_hash VARCHAR(255) NOT NULL,
    received_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'RECEIVED',
    UNIQUE (source, event_id)
);
```

---

## 7.15 idempotency_keys

사용자 요청 중 재시도 가능성이 높은 쓰기 API는 idempotency key를 받는 것이 좋다.

```sql
CREATE TABLE idempotency_keys (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id),
    route_key VARCHAR(255) NOT NULL,
    request_hash VARCHAR(255) NOT NULL,
    response_status INT,
    response_body JSONB,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE (idempotency_key, route_key)
);
```

---

## 8. 백엔드 프로젝트 구조

FastAPI 기준으로 다음과 같이 구성할 수 있다.

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── permissions.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── auth_router.py
│   │       ├── user_router.py
│   │       ├── patient_router.py
│   │       ├── session_router.py
│   │       ├── audio_router.py
│   │       ├── analysis_router.py
│   │       ├── transcript_router.py
│   │       ├── report_router.py
│   │       ├── dashboard_router.py
│   │       ├── notification_router.py
│   │       └── feedback_router.py
│   │
│   ├── domains/
│   │   ├── auth/
│   │   ├── user/
│   │   ├── patient/
│   │   ├── session/
│   │   ├── audio/
│   │   ├── analysis/
│   │   ├── transcript/
│   │   ├── report/
│   │   ├── dashboard/
│   │   ├── notification/
│   │   └── feedback/
│   │
│   ├── infrastructure/
│   │   ├── db/
│   │   ├── s3/
│   │   ├── redis/
│   │   ├── sqs/
│   │   └── ai_client/
│   │
│   └── schemas/
│       ├── auth_schema.py
│       ├── patient_schema.py
│       ├── session_schema.py
│       ├── audio_schema.py
│       ├── analysis_schema.py
│       ├── report_schema.py
│       └── common_schema.py
│
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
└── README.md
```

---

## 9. 계층별 역할

### 9.1 Router

Router는 HTTP 요청과 응답을 담당한다.

주요 역할은 다음과 같다.

- URL 매핑
- Request Body 검증
- Query Parameter 검증
- 로그인 사용자 추출
- Service 호출
- Response 반환

Router에는 복잡한 비즈니스 로직을 넣지 않는다.

---

### 9.2 Service

Service는 실제 서비스 로직을 담당한다.

예를 들어 분석 요청 Service는 다음 일을 한다.

```text
1. 사용자 권한 확인
2. 세션 존재 여부 확인
3. 음성 업로드 완료 여부 확인
4. 기존 분석 작업 중복 여부 확인
5. analysis_job 생성
6. AI 서버 호출
7. 상태 업데이트
```

---

### 9.3 Repository

Repository는 DB 접근을 담당한다.

주요 역할은 다음과 같다.

- 데이터 생성
- 데이터 조회
- 데이터 수정
- 데이터 삭제
- 조건 검색
- 트랜잭션 처리

---

### 9.4 Infrastructure

Infrastructure 계층은 외부 서비스 연동을 담당한다.

| 모듈 | 역할 |
|---|---|
| `s3_client.py` | Presigned URL 생성, HeadObject 확인 |
| `redis_client.py` | 캐시, Rate Limit |
| `sqs_client.py` | 분석 요청 메시지 발행 |
| `ai_client.py` | AI 서버 HTTP API 호출 |
| `db_session.py` | DB 연결 세션 관리 |

---

## 10. AI 서버 연동 방식

AI 모델은 별도 서버로 분리되어 있으므로, 기능 백엔드는 AI 서버와 약속된 API만 사용한다.

### 10.1 분석 요청 API

백엔드가 AI 서버로 요청한다.

```http
POST /internal/ai/analysis-jobs
Content-Type: application/json
X-Internal-Token: {internal_token}
```

요청 Body는 다음과 같다.

```json
{
  "jobId": "job_123",
  "sessionId": "session_123",
  "audioS3Bucket": "utterai-raw-audio",
  "audioS3Key": "raw-audio/slp/patient/session/audio.wav",
  "callbackUrl": "https://api.utterai.com/api/v1/internal/analysis-results/callback"
}
```

---

### 10.2 분석 결과 Callback API

AI 서버가 백엔드로 결과를 보낸다.

```http
POST /api/v1/internal/analysis-results/callback
Content-Type: application/json
X-Internal-Token: {internal_token}
```

결과 Body는 다음과 같다.

```json
{
  "jobId": "job_123",
  "status": "COMPLETED",
  "progress": 100,
  "summary": {
    "totalUtterances": 42,
    "patientUtterances": 18
  },
  "resultFiles": {
    "transcriptS3Key": "results/session_123/transcript.json",
    "metricsS3Key": "results/session_123/metrics.json",
    "reportS3Key": "reports/session_123/report.pdf"
  }
}
```

---

### 10.3 상태 업데이트 Callback API

AI 서버가 중간 진행률을 백엔드에 보낼 수 있다.

```http
POST /api/v1/internal/analysis-jobs/{jobId}/progress
Content-Type: application/json
X-Internal-Token: {internal_token}
```

```json
{
  "status": "PROCESSING",
  "progress": 45,
  "currentStage": "음성 분석 중"
}
```

이 구조를 사용하면 프론트엔드는 AI 서버를 직접 알 필요 없이 백엔드만 바라보면 된다.

---

### 10.4 AI Callback 인증 방식

MVP에서는 `X-Internal-Token` 기반 인증으로 시작할 수 있지만, 운영 단계까지 고려하면 다음 규칙을 같이 두는 것이 안전하다.

```text
1. 모든 Callback 요청은 HTTPS만 허용
2. X-Internal-Token 값 검증
3. X-Event-Id 헤더를 필수로 받아 중복 수신 방지
4. X-Signature 헤더에 HMAC-SHA256 서명 추가
5. X-Timestamp 헤더가 현재 시각 기준 5분 이내인지 확인
6. event_id 기준으로 callback_event_receipts 테이블에 선기록
7. 이미 처리된 event_id면 200 OK 반환 후 본 처리 생략
```

권장 헤더는 다음과 같다.

```http
X-Internal-Token: {internal_token}
X-Event-Id: evt_20260528_0001
X-Timestamp: 2026-05-28T10:15:00+09:00
X-Signature: sha256={hmac_signature}
```

서명 원문은 다음처럼 고정한다.

```text
{timestamp}.{raw_request_body}
```

이 규칙을 사용하면 재전송, 지연 도착, 위변조를 동시에 방어할 수 있다.

---

## 11. 권한 설계

### 11.1 기본 권한 규칙

| 리소스 | 접근 가능한 사용자 |
|---|---|
| 내 프로필 | 본인 |
| 아동 프로필 | 담당 치료사, 관리자 |
| 세션 | 담당 치료사, 관리자, 공유받은 보호자 |
| 음성 파일 | 담당 치료사, 관리자 |
| 분석 결과 | 담당 치료사, 관리자, 공유받은 보호자 |
| 리포트 | 담당 치료사, 관리자, 공유받은 보호자 |
| 관리자 API | 관리자만 가능 |

---

### 11.2 권한 체크 예시

세션 상세 조회 시 다음을 확인한다.

```text
1. JWT에서 user_id 추출
2. session_id로 세션 조회
3. 세션의 therapist_id와 user_id 비교
4. 같으면 접근 허용
5. 관리자라면 접근 허용
6. 공유 권한이 있으면 접근 허용
7. 아니면 403 Forbidden 반환
```

---

### 11.3 공유 권한 모델

공유는 `세션 단위`가 아니라 `아동 단위`를 기본으로 한다.

이유는 다음과 같다.

- 보호자는 특정 아동의 여러 세션을 연속적으로 봐야 한다.
- 세션별로 권한을 따로 주면 운영 복잡도가 불필요하게 커진다.
- 세션, 결과, 리포트 권한을 하나의 기준으로 묶기 쉽다.

공유 규칙은 다음과 같이 정의한다.

```text
1. 공유 생성 주체는 담당 치료사 또는 관리자
2. 공유 대상은 GUARDIAN 또는 VIEWER 역할 사용자
3. 공유 기준은 patient_ref_id
4. 공유가 ACTIVE이면 해당 patient의 session/result/report 조회 가능
5. download는 access_level이 VIEW_AND_DOWNLOAD일 때만 허용
6. revoke 또는 expires_at 경과 시 즉시 접근 차단
7. audio 원본 다운로드는 공유 대상에게 기본적으로 허용하지 않음
```

권한 판단 우선순위는 다음과 같다.

```text
ADMIN
-> 세션 담당 SLP
-> ACTIVE patient_access_grants 보유 사용자
-> 그 외 거부
```

---

### 11.4 Soft Delete 기준

MVP에서는 물리 삭제보다 soft delete를 기본으로 하고, 외부 저장소 정리는 비동기 후처리로 분리한다.

soft delete 대상은 다음과 같다.

| 리소스 | 삭제 방식 | 이유 |
|---|---|---|
| users | `status=INACTIVE` | 감사 추적과 토큰/세션 연계 유지 |
| patient_refs | `status=DELETED` | 세션/결과 참조 보존 필요 |
| sessions | `status=DELETED` | 분석/리포트 이력 보존 필요 |
| audio_files | `status=DELETED` | 분석 재현성 추적 필요 |
| child_access_grants | `status=REVOKED` | 권한 변경 감사 필요 |
| reports | `status=DELETED` | 배포 이력과 재생성 이력 보존 |

물리 삭제를 허용해도 되는 대상은 다음과 같다.

- 만료된 `idempotency_keys`
- 장기 보관 정책이 끝난 `callback_event_receipts`
- 읽음 처리 후 보존 기간이 지난 `notifications`

soft delete 공통 규칙은 다음과 같다.

```text
1. 외부 API 기본 조회에서는 deleted 리소스를 제외
2. 관리자 감사 조회 API에서만 deleted 포함 조회 가능
3. unique key 충돌 방지를 위해 status만으로 재사용 판단하지 않음
4. S3 객체 삭제는 DB soft delete 이후 비동기 작업으로 처리
5. delete 요청 시 참조 중인 하위 리소스는 cascade soft delete 또는 접근 차단 정책을 명시
```

---

### 11.5 세션/잡 상태 전이 규칙

상태 전이는 임의 업데이트가 아니라 허용된 경로만 통과해야 한다.

세션 상태 전이는 다음을 기준으로 한다.

| 현재 상태 | 허용 다음 상태 | 설명 |
|---|---|---|
| `CREATED` | `AUDIO_UPLOADING`, `DELETED` | 세션 생성 직후 |
| `AUDIO_UPLOADING` | `AUDIO_UPLOADED`, `FAILED`, `DELETED` | 업로드 중 |
| `AUDIO_UPLOADED` | `ANALYSIS_REQUESTED`, `DELETED` | 업로드 완료 |
| `ANALYSIS_REQUESTED` | `ANALYSIS_PROCESSING`, `FAILED` | AI 요청 직후 |
| `ANALYSIS_PROCESSING` | `ANALYSIS_COMPLETED`, `FAILED` | 분석 진행 중 |
| `ANALYSIS_COMPLETED` | `REPORT_READY`, `FAILED` | 결과 저장 완료 |
| `REPORT_READY` | `REPORT_READY`, `FAILED` | 최종 안정 상태 |
| `FAILED` | `AUDIO_UPLOADED`, `ANALYSIS_REQUESTED`, `DELETED` | 재시도 가능 |
| `DELETED` | 없음 | 종료 상태 |

analysis job 상태 전이는 다음을 기준으로 한다.

| 현재 상태 | 허용 다음 상태 | 설명 |
|---|---|---|
| `REQUESTED` | `QUEUED`, `PROCESSING`, `FAILED`, `CANCELLED` | 백엔드 생성 직후 |
| `QUEUED` | `PROCESSING`, `FAILED`, `CANCELLED`, `EXPIRED` | AI 대기열 |
| `PROCESSING` | `COMPLETED`, `FAILED`, `CANCELLED`, `EXPIRED` | AI 처리 중 |
| `COMPLETED` | 없음 | 종료 상태 |
| `FAILED` | `REQUESTED` | 새 재처리 job 생성 전 논리적 재시도 표시용 |
| `CANCELLED` | 없음 | 종료 상태 |
| `EXPIRED` | 없음 | 종료 상태 |

추가 규칙은 다음과 같다.

```text
1. 하나의 session에는 동시에 ACTIVE한 analysis job 1개만 허용
2. COMPLETED job은 수정하지 않고 immutable 취급
3. 재처리는 기존 job 상태를 되돌리지 않고 새 job을 생성
4. session.status는 대표 job의 상태를 요약해 반영
5. callback으로 status가 역행하는 업데이트는 무시
```

---

### 11.6 수정 이력 저장 기준

발화 수정은 별도 이력 테이블 분리를 권장한다.

기준은 다음과 같다.

```text
1. utterances에는 현재 화면에 보여줄 최신 상태 저장
2. utterance_edit_history에는 모든 변경 이벤트 append-only 저장
3. original_text는 최초 AI 결과를 유지하고 overwrite하지 않음
4. edited_text는 최신 사용자 수정본만 유지
5. speaker_role 수정도 동일하게 이력 테이블에 기록
6. report 재생성은 최신 utterances 기준으로 수행
```

이 구조가 필요한 이유는 다음과 같다.

- 화면 조회는 빠르게 유지할 수 있다.
- 감사 로그와 되돌리기 기능을 확장하기 쉽다.
- AI 원본과 사용자 편집본을 명확히 분리할 수 있다.

---

### 11.7 재처리와 멱등성

재처리와 중복 요청은 반드시 분리해서 다뤄야 한다.

`재처리`는 사용자의 명시적 의도이고, `멱등성`은 같은 요청의 중복 실행 방지이다.

규칙은 다음과 같다.

```text
1. 분석 재처리는 기존 job 재사용이 아니라 새 analysis_job 생성
2. 같은 session에 대해 완료되지 않은 job이 있으면 새 분석 요청 거절
3. POST /analysis-jobs 요청은 Idempotency-Key 헤더를 지원
4. 같은 key + 같은 request_hash면 기존 응답 재사용
5. 같은 key + 다른 request_hash면 409 Conflict 반환
6. AI callback은 event_id 기준으로 멱등 처리
7. S3 업로드 완료 API는 동일 audio_id에 대해 여러 번 호출돼도 최종 상태만 보장
```

권장 멱등 적용 대상은 다음과 같다.

- 회원가입
- 세션 생성
- 업로드 완료 처리
- 분석 요청 생성
- 리포트 재생성 요청
- AI callback 수신

---

### 11.8 트랜잭션 경계

DB 트랜잭션은 짧게 유지하고, 외부 네트워크 호출은 트랜잭션 밖으로 빼는 것이 원칙이다.

핵심 경계는 다음과 같다.

| 작업 | 같은 DB 트랜잭션으로 묶을 범위 | 트랜잭션 밖에서 할 일 |
|---|---|---|
| 환자 등록 | patient_refs row 생성 | 없음 |
| 세션 생성 | session row 생성 | 없음 |
| 업로드 URL 발급 | audio_files row 생성 | S3 presigned URL 생성 |
| 업로드 완료 처리 | audio_files 상태 변경 + session 상태 변경 | S3 HeadObject 호출 |
| 분석 요청 생성 | 중복 job 검사 + job row 생성 + session 상태 변경 | AI 서버 호출 |
| 결과 callback 처리 | receipt 기록 + job 상태 변경 + result 저장 + session 상태 변경 + notification 생성 | 필요 시 결과 파일 S3 존재 검증 |
| 발화 수정 | utterances 최신본 갱신 + edit_history append + report 상태 변경 | AI 재생성 호출 |
| 리포트 재생성 요청 | report 상태 변경 + 재생성 job/event 기록 | AI 서버 호출 |

분석 요청과 callback 처리에는 outbox 성격의 보강 규칙을 둔다.

```text
1. DB commit 전에 AI 서버를 먼저 호출하지 않음
2. AI 호출 실패 시 DB 상태는 REQUESTED 또는 RETRY_PENDING처럼 복구 가능한 상태 유지
3. callback 수신 시 receipt를 먼저 기록한 뒤 본 처리
4. 본 처리 중 실패하면 receipt.status=FAILED로 남기고 재처리 가능하게 함
5. 외부 호출 결과를 기다리며 DB row lock을 오래 잡지 않음
```

---

## 12. 보안 설계

### 12.1 인증

모든 사용자 API는 JWT 인증을 사용한다.

```http
Authorization: Bearer {access_token}
```

내부 AI 서버 Callback API는 별도의 내부 토큰을 사용한다.

```http
X-Internal-Token: {internal_token}
```

운영 환경에서는 내부 토큰을 Secrets Manager에 저장한다.

---

### 12.2 S3 보안

S3 Bucket은 Public Access를 차단한다.

파일 접근은 백엔드가 발급한 Presigned URL을 통해서만 가능하게 한다.

권장 설정은 다음과 같다.

```text
1. S3 Public Access Block 활성화
2. Bucket Policy에서 직접 public 접근 차단
3. Presigned URL 만료 시간 짧게 설정
4. 사용자 입력 파일명을 S3 Key로 직접 사용하지 않기
5. 파일 다운로드 전 백엔드 권한 검사
```

---

### 12.3 로그 보안

로그에 남기지 말아야 할 정보는 다음과 같다.

```text
1. JWT 토큰
2. 비밀번호
3. 원본 음성 다운로드 URL
4. 아동 이름과 생년월일
5. 전체 전사 텍스트
6. 보호자 연락처
```

로그에는 다음처럼 식별자와 상태 중심으로 남긴다.

```json
{
  "event": "analysis_job_requested",
  "jobId": "job_123",
  "sessionId": "session_123",
  "userId": "user_123",
  "status": "REQUESTED"
}
```

---

## 13. 운영 모니터링

### 13.1 API 지표

| 지표 | 설명 |
|---|---|
| Request Count | 전체 API 요청 수 |
| Error Rate | 4xx, 5xx 비율 |
| p95 Latency | 상위 95% 응답 시간 |
| p99 Latency | 상위 99% 응답 시간 |
| Login Failure Count | 로그인 실패 횟수 |
| Upload URL Issue Count | 업로드 URL 발급 횟수 |
| Analysis Request Count | 분석 요청 횟수 |

---

### 13.2 비즈니스 지표

| 지표 | 설명 |
|---|---|
| Daily Active SLPs | 일간 활성 SLP 수 |
| Created Sessions | 생성된 상담 세션 수 |
| Uploaded Audio Count | 업로드된 음성 파일 수 |
| Completed Analysis Count | 완료된 분석 수 |
| Failed Analysis Count | 실패한 분석 수 |
| Report Download Count | 리포트 다운로드 수 |

---

### 13.3 알람 기준 예시

| 상황 | 알람 조건 |
|---|---|
| API 장애 | 5xx 비율 5분 동안 5% 이상 |
| DB 장애 | DB Connection Error 증가 |
| AI 연동 실패 | AI 서버 요청 실패율 증가 |
| 분석 실패 증가 | FAILED 상태 Job 급증 |
| 업로드 실패 증가 | S3 HeadObject 실패 증가 |

---

## 14. MVP 구현 순서

### 14.1 1단계: 기본 사용자 기능

```text
1. FastAPI 프로젝트 생성
2. DB 연결
3. User 모델 생성
4. 회원가입 구현
5. 로그인 구현
6. JWT 인증 구현
```

---

### 14.2 2단계: 아동과 세션 관리

```text
1. patient_refs 테이블 생성
2. sessions 테이블 생성
3. 환자 CRUD API 구현
4. 세션 CRUD API 구현
5. 권한 체크 구현
```

---

### 14.3 3단계: 음성 업로드 관리

```text
1. audio_files 테이블 생성
2. S3 Presigned URL 발급 구현
3. 업로드 완료 API 구현
4. S3 HeadObject 검증 구현
5. 세션 상태 변경 구현
```

---

### 14.4 4단계: 분석 요청 관리

```text
1. analysis_jobs 테이블 생성
2. 분석 요청 API 구현
3. AI 서버 호출 Client 구현
4. 분석 상태 조회 API 구현
5. 분석 실패 / 재시도 / 취소 API 구현
```

---

### 14.5 5단계: 결과 조회와 리포트

```text
1. analysis_results 테이블 생성
2. AI Callback API 구현
3. utterances 저장 구조 구현
4. 결과 조회 API 구현
5. reports 테이블 생성
6. 리포트 다운로드 URL 발급 구현
```

---

### 14.6 6단계: 운영 기능

```text
1. 알림 기능 구현
2. 피드백 기능 구현
3. 관리자 사용자 관리 구현
4. 관리자 분석 상태 조회 구현
5. 로그와 모니터링 지표 추가
```

---

## 15. 최종 정리

이 백엔드는 AI 모델을 직접 실행하지 않는다.

대신 웹 서비스가 정상적으로 동작하기 위한 다음 기능을 담당한다.

```text
1. 사용자를 인증한다.
2. 아동과 상담 세션을 관리한다.
3. 음성 파일 업로드를 안전하게 처리한다.
4. AI 서버에 분석 요청을 전달한다.
5. 분석 진행 상태를 저장하고 제공한다.
6. AI 서버가 만든 결과를 저장한다.
7. 프론트엔드가 결과를 조회할 수 있게 API를 제공한다.
8. 리포트 파일을 안전하게 다운로드할 수 있게 한다.
9. 사용자 피드백과 알림을 관리한다.
10. 관리자 기능과 운영 모니터링을 제공한다.
```

즉, 기능 백엔드는 UtterAI의 **서비스 제어 서버**이다.

AI 서버가 실제 분석 엔진이라면, 기능 백엔드는 사용자 화면, 데이터 상태, 파일 저장소, 분석 요청, 결과 제공을 연결하는 중심 API 서버라고 볼 수 있다.

MVP에서는 다음 순서로 구현하는 것이 가장 좋다.

```text
Auth
  -> Patient
  -> Session
  -> Audio Upload
  -> Analysis Job
  -> AI Callback
  -> Result View
  -> Report Download
  -> Feedback / Admin
```

이 구조로 나누면 AI 모델 개발과 웹 백엔드 개발을 독립적으로 진행할 수 있고, 이후 EKS 환경에서도 API 서버와 AI 서버를 별도 Node Group 또는 별도 서비스로 확장하기 쉽다.
