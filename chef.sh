#!/usr/bin/env bash

# Example usages:
# ./chef.sh fetchif path/to/file.sv
# ./chef.sh --format markdown fetchif path/to/file.sv

set -euo pipefail

IMAGE_NAME=yehudats/chef:latest

# Build the image if it doesn't exist locally
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[chef.zsh] Docker image '$IMAGE_NAME' not found, building..."
  docker build -t "$IMAGE_NAME" .
fi

# Mount current repo into /app and run chef.py with all passed arguments.
# The Dockerfile ENTRYPOINT is ["python", "chef.py"], so args are appended directly.
docker run --rm \
  -v "$PWD":/app \
  -w /app \
  "$IMAGE_NAME" \
  "$@"

