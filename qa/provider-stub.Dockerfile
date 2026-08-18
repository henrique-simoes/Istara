# Tiny, non-model provider contract adapter for disposable QA only.
FROM python:3.12-slim

WORKDIR /app
COPY qa/scripts/provider_stub.py /app/provider_stub.py
USER 65532:65532
EXPOSE 11434
ENTRYPOINT ["python", "/app/provider_stub.py"]
