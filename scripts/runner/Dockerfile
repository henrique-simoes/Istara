FROM node:20-bookworm

# The runner needs a Linux Docker CLI because tests/real_user_benchmark/run.mjs starts
# disposable donor/model/relay containers through the Docker API socket. Installing the CLI
# happens while building this disposable image; nothing is installed on the Mac Studio host,
# and no Docker daemon is started in this image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io ca-certificates git tar python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# The long-horizon API workload is Python-based. Keep its client dependency in this
# disposable image so the Mac Studio host never receives a Python package or virtualenv.
RUN python3 -m venv /opt/runner-venv \
    && /opt/runner-venv/bin/pip install --no-cache-dir "httpx==0.28.1"

WORKDIR /work
