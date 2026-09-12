#!/usr/bin/env bash
# Build and run the JSX test suite in Chromium.
#
#   bash tests/js/run.sh            # every test file
#   bash tests/js/run.sh layer      # only files whose name contains "layer"
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d node_modules ]; then
  echo "installing test dependencies with bun..."
  bun install --silent
fi

bun harness/build.mjs "$@"
node harness/run.mjs
