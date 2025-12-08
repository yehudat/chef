#!/usr/bin/env zsh

# Example usage:
# ./test.zsh            # runs all unit tests in tests/ directory

set -euo pipefail

IMAGE_NAME=yehudats/chef:latest

# Build the image if it doesn't exist locally
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[chef.zsh] Docker image '$IMAGE_NAME' not found, building..."
  docker build -t "$IMAGE_NAME" .
fi

docker run --rm \
  -v "$PWD":/app \
  -w /app \
  "$IMAGE_NAME" \
  python -m unittest discover -s tests

