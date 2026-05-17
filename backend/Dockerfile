# syntax=docker/dockerfile:1.6
#
# Production image for the Data Fuel FastAPI backend.
#
# Stage 1 (builder)  — installs runtime deps into an isolated /opt/venv so the
# final image carries only the resolved packages, not pip metadata or build
# tooling. No dev extras (pytest, mypy, ruff) reach the runtime image.
#
# Stage 2 (runtime)  — slim base, non-root user, virtualenv on PATH, app code
# copied verbatim. Healthcheck wired to /api/v1/health.

ARG PYTHON_VERSION=3.12

# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies. Copying only pyproject.toml first means the
# layer cache only invalidates when dependencies actually change.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && pip install .

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="datafuel-backend" \
      org.opencontainers.image.description="Data Fuel FastAPI backend (MITECO + ML)" \
      org.opencontainers.image.source="https://github.com/JoanOliver04/Data_Fuel" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY scripts ./scripts

# Non-root execution. Empty data/ and artifacts/ directories will be backed
# by named volumes at runtime (see docker-compose.yml).
RUN useradd --create-home --uid 1000 datafuel \
    && mkdir -p data artifacts \
    && chown -R datafuel:datafuel /app

USER datafuel

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; \
sys.exit(0) if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).getcode() == 200 else sys.exit(1)" \
    || exit 1

# Single worker keeps the in-process model_loader singleton coherent and
# bounded memory; scale horizontally via multiple containers, not workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
