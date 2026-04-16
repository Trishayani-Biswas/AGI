#!/usr/bin/env bash

# If someone uses `source`, run this script in a child bash instead so we do
# not alter the current shell options/environment unexpectedly.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  bash "${BASH_SOURCE[0]}" "$@"
  return $?
fi

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing Python virtual environment at .venv." >&2
  echo "Create it with:" >&2
  echo "python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "scripts/experience_llm_vs_evolved.py" ]]; then
  echo "Missing script: scripts/experience_llm_vs_evolved.py" >&2
  exit 1
fi

.venv/bin/python scripts/experience_llm_vs_evolved.py "$@"
rc=$?

if [[ $rc -ne 0 ]]; then
  echo "Experience launcher exited with code $rc" >&2
  echo "Try debug:" >&2
  echo "  bash -x ./scripts/start_experience_env.sh --model deepseek-r1:1.5b --session-name exp_debug" >&2
  echo "Common fixes:" >&2
  echo "  1) Start model runtime: ollama serve" >&2
  echo "  2) Use plain command: bash ./scripts/start_experience_env.sh --model deepseek-r1:1.5b --session-name exp1" >&2
fi

exit "$rc"
