# syntax=docker/dockerfile:1
# One image for every Vyom OS process: the API (default), vyom-migrate,
# vyom-admin, vyom-seed-demo and the vyom-weekly-sweep job.
# Pin the base image by digest in CI (python:3.12-slim@sha256:...).
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv && /opt/venv/bin/pip install .

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    VYOM_MIGRATIONS_DIR=/app/migrations
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin vyom
COPY --from=build /opt/venv /opt/venv
COPY migrations /app/migrations
WORKDIR /app
USER 10001:10001
EXPOSE 8000
CMD ["vyom-os-api"]
