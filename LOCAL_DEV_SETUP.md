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

1. `POST /api/v1/auth/signup`
2. `POST /api/v1/auth/login`
3. `POST /api/v1/children`
4. `POST /api/v1/sessions`
5. `POST /api/v1/audio-files/presigned-url`
6. `POST /api/v1/audio-files`
7. `POST /api/v1/analysis-jobs`
8. `POST /api/v1/internal/analysis-jobs/{jobId}/progress`
9. `POST /api/v1/internal/analysis-results/callback`
10. `GET /api/v1/transcripts/{resultId}`
11. `PATCH /api/v1/transcripts/{resultId}/confirm`
12. `POST /api/v1/soap-notes/generate`
13. `PATCH /api/v1/soap-notes/{noteId}/finalize`
14. `POST /api/v1/reports`

## 4. What You Need To Prepare

실제 워크플로 검증 전 아래 항목은 직접 준비해야 한다.

- 사용할 로컬 `.env`
- S3를 붙일지, 아니면 presigned URL 단계만 형식 검증할지 결정
- AI callback에 보낼 샘플 payload
- 최소 2개 계정
  - `THERAPIST`
  - `ADMIN`
- transcript/soap/report까지 이어볼 하나의 기준 세션

## 5. Minimum Test Data To Prepare

추천 기준 데이터는 다음 정도면 충분하다.

- therapist 계정 1개
- admin 계정 1개
- child 1명
- session 1개
- audio file 1개
- analysis job 1개
- analysis result callback payload 1개
  - speakers 2명 이상
  - utterances 3개 이상

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
- AI 서버는 아직 mock/callback 수동 호출 기준이다.
- 현재 저장소에는 자동 시드 스크립트가 없다.
- 실제 통합 검증 기록은 아직 남아 있지 않다.
