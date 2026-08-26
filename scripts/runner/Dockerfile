FROM node:20-bookworm

# The runner needs a Linux Docker CLI because tests/real_user_benchmark/run.mjs starts
# disposable donor/model/relay containers through the Docker API socket. Installing the CLI
# happens while building this disposable image; nothing is installed on the Mac Studio host,
# and no Docker daemon is started in this image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io ca-certificates git tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
