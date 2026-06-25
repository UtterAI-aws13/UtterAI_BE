# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.5.30 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY app ./app
COPY alembic ./alembic

EXPOSE 8080

RUN adduser --disabled-password --uid 1000 appuser
USER 1000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
