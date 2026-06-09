# UtterAI_BE

언어치료 세션 관리, 오디오 업로드, AI 분석 요청, 결과 조회, 리포트 생성을 담당하는 FastAPI 백엔드 서비스.

## 역할 범위

| 담당 | 비담당 |
|---|---|
| 사용자 인증 / 권한 관리 | AI 모델 추론 (`UtterAI_AI`) |
| 아동 프로필 / 세션 관리 | 음성 STT / 화자 분리 / 지표 계산 |
| S3 presigned URL 발급 및 업로드 완료 처리 | 인프라 배포 정의 (`UtterAI_Infra`) |
| AI 분석 요청 생성 및 상태 추적 | 프론트엔드 (`UtterAI_FE`) |
| 분석 결과 / 전사 / SOAP 노트 / 리포트 API 제공 | |

## 기술 스택

- **Runtime**: Python 3.11+, FastAPI, Uvicorn (포트 8080)
- **ORM / DB**: SQLAlchemy 2.x, Alembic, PostgreSQL 16
- **Auth**: JWT (stateless access token + DB 저장 refresh token 회전)
- **Storage**: AWS S3 (boto3)
- **배포**: Docker → AWS ECR (ap-northeast-2)

## 로컬 개발 환경 구동

```bash
# 1. 환경 파일 생성
cp .env.example .env

# 2. Python 의존성 설치
python -m pip install -e ".[dev]"

# 3. PostgreSQL 실행 (Docker)
docker compose -f docker-compose.local.yml up -d

# 4. DB 마이그레이션
alembic upgrade head

# 5. 서버 실행
uvicorn app.main:app --reload
# Swagger: http://localhost:8000/docs
```

> Dockerfile 기준 포트는 **8080**이지만, 로컬 `--reload` 실행은 기본 8000 사용.

## API 구조

Base URL: `/api/v1`

| 도메인 | 엔드포인트 prefix | 구현 상태 |
|---|---|---|
| Auth | `/auth` | 완료 |
| Children | `/children` | 완료 |
| Sessions | `/sessions` | 완료 |
| Audio Files | `/audio-files` | 완료 |
| Analysis Jobs | `/analysis-jobs` | 완료 |
| Analysis Results | `/analysis-results` | 완료 |
| Transcripts | `/transcripts` | 완료 |
| SOAP Notes | `/soap-notes` | 완료 |
| Reports | `/reports` | 완료 |
| Templates | `/templates` | 완료 |
| AI 내부 콜백 | `/internal/analysis-jobs`, `/internal/analysis-results` | 완료 |
| Users (관리자) | `/users` | 미구현 |

전체 엔드포인트 목록과 요청/응답 형식은 `API 명세서.md` 참고.

## 세션 상태 머신

```
CREATED → AUDIO_UPLOADING → AUDIO_UPLOADED
       → ANALYSIS_REQUESTED → ANALYSIS_PROCESSING
       → ANALYSIS_COMPLETED → REPORT_READY
       (오류 시) → FAILED
```

## 환경 변수

`.env.example` 참고. 주요 항목:

| 변수 | 설명 |
|---|---|
| `DB_*` | PostgreSQL 접속 정보 |
| `JWT_SECRET_KEY` | JWT 서명 키 — 운영 시 반드시 교체 |
| `INTERNAL_CALLBACK_TOKEN` | AI 서비스 내부 통신 토큰 |
| `AI_SERVICE_BASE_URL` | AI 서비스 URL (비어있으면 dispatch 스킵) |
| `PUBLIC_API_BASE_URL` | AI 콜백이 사용할 이 서버의 공개 URL |
| `RAW_AUDIO_BUCKET` | S3 오디오 버킷 |
| `template_bucket` | S3 템플릿 버킷 |

## CI/CD

| 워크플로 | 트리거 | 동작 |
|---|---|---|
| `backend-ci.yaml` | PR 및 push (dev/main/feature/*) | pytest + Docker build 검증 |
| `backend-ecr-push.yaml` | push (dev/main) | ECR 이미지 push (`dev-{SHA}` / `prod-{SHA}`) |

GitHub Actions에 필요한 Variables: `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_BACKEND_REPOSITORY`

OIDC 기반 IAM Role assume 방식 사용 (장기 access key 없음).

## 관련 문서

| 문서 | 내용 |
|---|---|
| `API 명세서.md` | 전체 엔드포인트 요청/응답 명세 |
| `utterai_functional_backend_architecture.md` | 도메인 구조, 권한 규칙, 상태 전이 설계 |
| `LOCAL_DEV_SETUP.md` | 로컬 검증 절차 상세 |
| `CONTRIBUTING.md` | 브랜치 전략, 커밋 컨벤션, PR 규칙 |

## 브랜치 전략

- `main`: 운영 배포 기준
- `dev`: 기본 개발 브랜치
- `feature/<issue-number>-<name>`: 기능 개발
- `fix/<issue-number>-<name>`: 버그 수정
- `docs/<issue-number>-<name>`: 문서 작업

상세 규칙은 `CONTRIBUTING.md` 참고.
