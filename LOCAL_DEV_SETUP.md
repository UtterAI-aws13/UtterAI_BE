# Local Dev Setup

이 문서는 UtterAI 백엔드를 실제 PostgreSQL에 연결해서 로컬에서 검증하기 위한 최소 절차를 정리한다.

## 1. Prerequisites

- Python `3.11+`
- Docker Desktop
- Git

## 2. First-Time Setup

1. 예시 환경 파일 복사

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

2. Python 의존성 설치

```bash
python -m pip install -e ".[dev]"
```

3. 로컬 PostgreSQL 실행

```bash
docker compose -f docker-compose.local.yml up -d
```

4. DB 마이그레이션 적용

```bash
alembic upgrade head
```

5. API 서버 실행

```bash
uvicorn app.main:app --reload
# Swagger: http://localhost:8000/docs
```

## 3. Recommended Verification Order

다음 순서로 검증하면 상태 전이와 권한 흐름을 빠르게 확인할 수 있다.

**BE만 검증 (AI Worker 없이)**

1. `POST /api/v1/auth/signup`
2. `POST /api/v1/auth/login`
3. `POST /api/v1/sessions`
4. `POST /api/v1/audio-files/presigned-url`
5. `PUT <presigned-url>` (S3 직접 업로드)
6. `POST /api/v1/audio-files/{audioFileId}/complete`
7. `POST /api/v1/analysis-jobs` → SQS 발행 (`.env`에 `SQS_AUDIO_PREPROCESS_QUEUE_URL` 필요)

**AI Worker 포함 E2E 검증** (step 7 이후)

```bash
# UtterAI_AI 레포에서 별도 터미널로 실행
python scripts/run_cpu_worker.py    # SQS 폴링 시작
python scripts/run_ml_gpu_worker.py # GPU inference 큐 폴링 시작
```

8. CPU Worker가 음성 전처리 + VAD 수행 → `utterai-dev-raw-audio/intermediate/...` 저장
9. ML GPU Worker가 화자분리 + STT + alignment 수행 → `transcripts` / `transcript_segments` RDS 저장, `analysis_jobs.status = COMPLETED`
10. `GET /api/v1/sessions/{sessionId}/transcript`
11. `PATCH /api/v1/transcripts/{transcriptId}/segments/{segmentId}`
12. `PATCH /api/v1/transcripts/{transcriptId}/finalize`
13. `GET /api/v1/reports`
14. `GET /api/v1/reports/{reportId}/segments`
15. `PATCH /api/v1/reports/{reportId}/segments/{segmentId}`

> AI Worker 설정은 `UtterAI_AI/LOCAL_DEV_SETUP.md` 참고.

## 4. What You Need To Prepare

실제 워크플로 검증 전 아래 항목은 직접 준비해야 한다.

- 사용할 로컬 `.env` (`SQS_AUDIO_PREPROCESS_QUEUE_URL` 포함)
- S3를 붙일지, 아니면 presigned URL 단계만 형식 검증할지 결정
- 최소 2개 계정
  - `SLP`
  - `ADMIN`
- transcript/report까지 이어볼 하나의 기준 세션

## 5. Minimum Test Data To Prepare

추천 기준 데이터는 다음 정도면 충분하다.

- SLP 계정 1개
- admin 계정 1개
- patient 1명
- session 1개
- audio file 1개 (실제 음성 파일, 10초 이상 권장)
- analysis job 1개

## 6. Next After Setup

세팅이 끝나면 다음 순서로 진행하는 것이 맞다.

1. happy-path 수동 검증
2. 권한 실패 케이스 검증
3. soft delete 이후 접근 차단 검증
4. finalized 리소스 수정 차단 검증
5. callback 재전송 시 동작 확인
6. `pytest` 기반 API 테스트 추가

## 7. Known Gaps

- 실제 S3 object 존재 검증까지 하려면 AWS 자격 증명이 필요하다.
- 현재 저장소에는 자동 시드 스크립트가 없다.
- AI Worker 취소 처리: `analysis_jobs.status = CANCELLED`로 업데이트해도 이미 SQS에 들어간 메시지는 Worker가 끝까지 처리한다. Worker가 스테이지 시작 전 DB 상태를 확인하는 로직이 아직 없다.
- transcript → report 연결 흐름은 LLM GPU Worker 구현 완료 후 검증 가능하다.
