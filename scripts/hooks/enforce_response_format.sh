#!/usr/bin/env bash
set -euo pipefail

# Hook payload is not needed for this policy injector.
cat >/dev/null || true

cat <<'JSON'
{
  "continue": true,
  "systemMessage": "Response policy: 1) Update README when progress is significant and user-visible. 2) Explain outcomes in simple language with what improved or got worse. 3) After major results, brainstorm the next best stage with concrete actions."
}
JSON
