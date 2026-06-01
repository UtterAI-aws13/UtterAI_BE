# Backend CI와 ECR Push 설정 기록

## 1. 변경 목적

`UtterAI_BE` 저장소에 FastAPI Backend를 검증하고 Docker image를 ECR에 업로드할 수 있는 초기 GitHub Actions 흐름을 추가했다.

초기 목표는 다음과 같다.

- Pull Request에서 Python 의존성 설치, app import, pytest, Docker build를 검증한다.
- `dev` 브랜치 push 시 `dev-{short_sha}` tag로 backend image를 ECR에 push한다.
- `main` 브랜치 push 시 `prod-{short_sha}` tag로 backend image를 ECR에 push한다.
- AWS credential은 장기 access key 대신 GitHub OIDC + IAM Role Assume 방식을 사용한다.
- 실제 AWS account ID나 secret은 코드에 하드코딩하지 않는다.

## 2. 추가한 파일

```text
.dockerignore
Dockerfile
.github/workflows/backend-ci.yaml
.github/workflows/backend-ecr-push.yaml
tests/test_health.py
BACKEND_CI_ECR_SETUP.md
```

## 3. 파일별 역할

### `.dockerignore`

Docker build context에 포함하지 않을 파일을 정의한다.

포함 제외 대상:

- `.git`
- `.github`
- Python cache
- virtual environment
- `.env`
- IDE/OS 파일

이미지에 secret 또는 불필요한 개발 파일이 들어가지 않도록 하기 위한 설정이다.

### `Dockerfile`

FastAPI Backend를 container image로 만들기 위한 초기 Dockerfile이다.

현재 동작:

1. `python:3.11-slim` base image 사용
2. `/app` 디렉토리에서 실행
3. `pyproject.toml`, `README.md`, `alembic.ini`, `app/`, `alembic/` 복사
4. `python -m pip install .`로 운영 의존성 설치
5. `uvicorn app.main:app --host 0.0.0.0 --port 8000`으로 실행

주의:

- DB migration은 container 시작 시 자동 실행하지 않는다.
- Alembic migration은 별도 job 또는 배포 절차에서 다루는 것이 안전하다.
- 운영 image에는 `pytest` 같은 dev dependency를 설치하지 않는다.

### `.github/workflows/backend-ci.yaml`

Pull Request와 push에서 Backend 기본 검증을 수행한다.

검증 내용:

1. Python 3.11 설정
2. `python -m pip install -e ".[dev]"`
3. FastAPI app import 확인
4. `pytest`
5. `docker build -t utterai-backend:ci .`

실행 조건:

- `dev`, `main` 대상 Pull Request
- `dev`, `main`, `feature/**` push
- Backend 코드, Alembic, 테스트, Dockerfile, workflow 변경 시 실행

### `.github/workflows/backend-ecr-push.yaml`

`dev` 또는 `main` 브랜치에 push되면 Docker image를 ECR에 push한다.

tag 전략:

```text
dev branch  -> dev-{short_sha}
main branch -> prod-{short_sha}
```

예시:

```text
utterai-backend:dev-a1b2c3d
utterai-backend:prod-a1b2c3d
```

이 workflow는 GitHub Environment를 사용한다.

- `dev` branch는 `dev` environment 사용
- `main` branch는 `prod` environment 사용

prod environment에는 GitHub Required reviewers를 설정해 manual approval을 걸 수 있다.

### `tests/test_health.py`

DB 연결 없이 FastAPI app이 정상적으로 생성되고 `/health` endpoint가 응답하는지 확인하는 최소 smoke test다.

초기 CI가 의미 있게 통과하기 위한 가장 작은 테스트로 추가했다.

### `.gitignore`

로컬에서 `pip install -e ".[dev]"`를 실행하면 `utterai_be.egg-info/` 같은 metadata 디렉토리가 생길 수 있다.

해당 파일은 소스 코드가 아니므로 Git에 올라가지 않도록 `*.egg-info/`를 ignore 대상에 추가했다.

### `app/models/entities.py`

CI 테스트 중 FastAPI app import 단계에서 `AnalysisResult.summary_json`, `AnalysisResult.metrics_json` 컬럼의 SQLAlchemy 타입 오류가 발견되었다.

Alembic migration은 두 컬럼을 PostgreSQL `JSONB`로 생성하고 있었으므로 ORM 모델도 `JSONB` 타입을 명시하도록 맞췄다.

```text
summary_json -> JSONB
metrics_json -> JSONB
```

이 수정은 CI를 통과시키기 위한 모델 타입 정합성 수정이며, API 비즈니스 로직은 변경하지 않았다.

## 4. GitHub Variables 설정

GitHub repository 또는 environment variables에 다음 값을 설정해야 한다.

```text
AWS_REGION
AWS_ROLE_ARN
ECR_BACKEND_REPOSITORY
```

예시:

```text
AWS_REGION=ap-northeast-2
AWS_ROLE_ARN=arn:aws:iam::{AWS_ACCOUNT_ID}:role/{GITHUB_ACTIONS_ROLE_NAME}
ECR_BACKEND_REPOSITORY=utterai-backend
```

주의:

- 실제 AWS account ID는 코드에 하드코딩하지 않는다.
- `AWS_ROLE_ARN`은 GitHub OIDC로 assume 가능한 IAM Role이어야 한다.
- ECR repository는 사전에 AWS에 생성되어 있어야 한다.

## 5. 필요한 AWS 권한

GitHub Actions가 assume하는 IAM Role에는 최소한 다음 권한이 필요하다.

```text
ecr:GetAuthorizationToken
ecr:BatchCheckLayerAvailability
ecr:InitiateLayerUpload
ecr:UploadLayerPart
ecr:CompleteLayerUpload
ecr:PutImage
ecr:DescribeRepositories
ecr:BatchGetImage
sts:GetCallerIdentity
```

권장 방식:

- GitHub OIDC Provider 생성
- `dev` branch와 `main` branch 조건을 trust policy에 반영
- 장기 AWS access key를 GitHub Secrets에 저장하지 않음

## 6. GitHub Environments 설정

GitHub repository settings에서 다음 environment를 만든다.

```text
dev
prod
```

권장 설정:

```text
dev
- allowed branch: dev
- required reviewer: 없음

prod
- allowed branch: main
- required reviewer: 있음
```

이렇게 설정하면 `main` push 후 ECR push 전에 prod approval을 걸 수 있다.

## 7. 현재 포함하지 않은 것

이번 설정에는 다음을 포함하지 않았다.

- Alembic migration을 실제 PostgreSQL에 적용하는 integration test
- ECR push 이후 Helm `values-dev.yaml` image tag 자동 갱신
- Argo CD Application sync
- prod SemVer tag(`prod-v0.1.0`) 발행
- DB migration 배포 전략

이유:

- 현재 목표는 Backend image build와 ECR push까지의 최소 경로를 먼저 만드는 것이다.
- 실제 Kubernetes 배포는 Helm/Argo CD 구조가 준비된 뒤 연결한다.

## 8. 다음 단계

권장 다음 작업은 다음과 같다.

1. PR에서 `Backend CI`가 통과하는지 확인한다.
2. `dev` branch merge 후 `Backend ECR Push`가 `dev-{short_sha}` tag로 image를 push하는지 확인한다.
3. ECR에서 image tag를 확인한다.
4. Helm chart의 `values-dev.yaml` image tag update workflow를 추가한다.
5. Argo CD dev Application을 연결한다.
6. prod는 GitHub Environment manual approval 이후에만 push되도록 확인한다.

## 9. 로컬 검증 결과

로컬에서 확인한 결과는 다음과 같다.

```text
python3 -m pytest
-> 1 passed
```

Docker build는 Docker Desktop daemon이 실행 중이지 않아 로컬에서 완료하지 못했다.

```text
docker build -t utterai-backend:ci .
-> Cannot connect to the Docker daemon
```

GitHub Actions의 Ubuntu runner에서는 Docker daemon이 제공되므로 PR에서 `Backend CI`의 Docker build step으로 다시 검증해야 한다.
