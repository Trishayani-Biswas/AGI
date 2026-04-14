#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PY_BIN=".venv/bin/python"
fi

HOST="127.0.0.1"
PORT="${WIKI_API_PORT:-8765}"

"$PY_BIN" scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 40 >/tmp/wiki_smoke_build_1.log
"$PY_BIN" scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 40 >/tmp/wiki_smoke_build_2.log
"$PY_BIN" scripts/lint_agi_wiki.py --wiki-dir wiki --report-path wiki/lint_report.md --fail-on-issues >/tmp/wiki_smoke_lint.log

"$PY_BIN" scripts/wiki_query_api.py --wiki-dir wiki --host "$HOST" --port "$PORT" >/tmp/wiki_smoke_api.log 2>&1 &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

HEALTH_JSON="$(curl --silent --fail --retry 15 --retry-all-errors --retry-delay 0 "http://${HOST}:${PORT}/health")"
QUERY_JSON="$(curl --silent --show-error --fail "http://${HOST}:${PORT}/query?q=curriculum%20robustness%20fail&top_k=3")"

HEALTH_JSON="$HEALTH_JSON" QUERY_JSON="$QUERY_JSON" "$PY_BIN" - <<'PY'
from __future__ import annotations

import json
import os

health = json.loads(os.environ["HEALTH_JSON"])
query = json.loads(os.environ["QUERY_JSON"])

if not health.get("ok"):
    raise SystemExit("Health endpoint did not return ok=true")

results = query.get("results")
if not isinstance(results, list):
    raise SystemExit("Query endpoint did not return results list")

if query.get("count", 0) < 1:
    raise SystemExit("Query endpoint returned no results")

print("Wiki smoke checks passed.")
PY
