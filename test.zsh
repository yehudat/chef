#!/usr/bin/env zsh

# Example usage:
# ./test.zsh              # runs full regression (all tests)
# ./test.zsh regression   # runs full regression (all tests)
# ./test.zsh sanity       # runs sanity tests only (one per suite, fast)

set -euo pipefail

IMAGE_NAME=yehudats/chef:latest
MODE=${1:-regression}

# Build the image if it doesn't exist locally
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[test.zsh] Docker image '$IMAGE_NAME' not found, building..."
  docker build -t "$IMAGE_NAME" .
fi

# Sanity tests: one representative test per suite (excluding integration)
SANITY_TESTS=(
  tests.test_chef.TestChefCLI.test_no_arguments_prints_help_and_returns_nonzero
  tests.test_genesis2.TestGenesis2Strategy.test_extract_imports
  tests.test_genesis2_preprocess.TestGenesis2Preprocess.test_dbg_and_var_removed_import_preserved
  tests.test_nested_structs.TestNestedStructParsing.test_simple_struct_iter_fields
  tests.test_nested_structs.TestNestedStructRendering.test_simple_struct_rendering
  tests.test_parser.TestSVParser.test_parse_struct
  tests.test_slang_backend.TestSlangBackendCleanDirection.test_clean_direction_plain_output
)

case "$MODE" in
  sanity)
    echo "[test.zsh] Running sanity tests (${#SANITY_TESTS[@]} tests)..."
    docker run --rm \
      -v "$PWD":/app \
      -w /app \
      "$IMAGE_NAME" \
      python -m unittest ${SANITY_TESTS[@]}
    ;;
  regression|*)
    echo "[test.zsh] Running full regression..."
    docker run --rm \
      -v "$PWD":/app \
      -w /app \
      "$IMAGE_NAME" \
      python -m unittest discover -s tests
    ;;
esac

