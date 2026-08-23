# syntax=docker/dockerfile:1
# Build context is the REPOSITORY ROOT (see docker-compose*.yml) so the Pi
# runtime worker can ship inside the image (CF-SPEC-1: deployed testing
# instances run the Pi agentic loop against configured cloud endpoints).
# Stage 1: Builder — python deps + pi-runtime node deps
FROM python:3.12-slim AS builder
WORKDIR /build
ARG INSTALL_WHISPER=true
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git libmagic1 build-essential nodejs npm && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN if [ "$INSTALL_WHISPER" = "true" ]; then \
        pip install --no-cache-dir --prefix=/install -r backend/requirements.txt; \
    else \
        sed '/^openai-whisper/d' backend/requirements.txt > /tmp/requirements-no-whisper.txt \
        && pip install --no-cache-dir --prefix=/install -r /tmp/requirements-no-whisper.txt; \
    fi
COPY pi-runtime ./pi-runtime
RUN cd pi-runtime && npm ci --omit=dev --ignore-scripts
COPY backend ./backend

# Stage 2: Runtime — lean image
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git libmagic1 nodejs && rm -rf /var/lib/apt/lists/*
RUN useradd --system --no-create-home istara
COPY --from=builder /install /usr/local
COPY --from=builder /build/backend .
COPY --from=builder /build/pi-runtime ./pi-runtime
RUN mkdir -p data/uploads data/projects data/lance_db data/backups data/channel_audio \
    && chown -R istara:istara data
USER istara
EXPOSE 8000
ENV PI_RUNTIME_ROOT=/app
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/api/health"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
