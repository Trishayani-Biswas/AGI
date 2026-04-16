#!/usr/bin/env bash

# If someone uses `source`, run this script in a child bash instead so we do
# not alter the current shell options/environment unexpectedly.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  bash "${BASH_SOURCE[0]}" "$@"
  return $?
fi

set -uo pipefail

fail() {
  echo "$1" >&2
  exit 1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing Python virtual environment at .venv." >&2
  echo "Create it with:" >&2
  echo "python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "scripts/live_model_chat.py" ]]; then
  fail "Missing chat script: scripts/live_model_chat.py"
fi

.venv/bin/python scripts/live_model_chat.py "$@"
rc=$?

if [[ $rc -ne 0 ]]; then
  echo "Chat launcher exited with code $rc" >&2
  echo "Debug command:" >&2
  echo "  bash -x ./scripts/start_chat_env.sh --model deepseek-r1:1.5b --session-name debug1" >&2
  echo "Common fixes:" >&2
  echo "  1) Start model runtime: ollama serve" >&2
  echo "  2) Avoid pasting markdown links into terminal" >&2
  echo "  3) Use plain command: bash ./scripts/start_chat_env.sh --model deepseek-r1:1.5b --session-name test1" >&2
fi

exit "$rc"
