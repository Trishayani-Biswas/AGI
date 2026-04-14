#!/usr/bin/env bash
set -euo pipefail

# Hook payload is not required for this async sync trigger.
cat >/dev/null || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PY_BIN=".venv/bin/python"
fi

if [[ -f "scripts/agi_memory_autosync.py" ]]; then
  # Async trigger keeps hooks responsive while lock-based sync avoids overlap.
  ("$PY_BIN" scripts/agi_memory_autosync.py --sync-once --outputs-dir outputs --wiki-dir wiki --max-runs 40 >/tmp/agi_memory_autosync_hook.log 2>&1 &) || true
fi

cat <<'JSON'
{
  "continue": true
}
JSON
