# Stage 1: Builder — install deps with build tools
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git libmagic1 build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

# Stage 2: Runtime — lean image
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libmagic1 && rm -rf /var/lib/apt/lists/*
RUN useradd --system --no-create-home istara
COPY --from=builder /install /usr/local
COPY --from=builder /build .
RUN mkdir -p data/uploads data/projects data/lance_db data/backups data/channel_audio \
    && chown -R istara:istara data
USER istara
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/api/health"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
