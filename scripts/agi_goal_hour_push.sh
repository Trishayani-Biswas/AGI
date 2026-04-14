#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PY_BIN=".venv/bin/python"
fi

BUDGET_MINUTES="${BUDGET_MINUTES:-60}"
BUDGET_SECONDS=$((BUDGET_MINUTES * 60))
START_TS="$(date +%s)"
RUN_TAG="${RUN_TAG:-hour_$(date -u +%Y%m%d_%H%M%S)}"

COMMON_ARGS=(
  --generations 40
  --eval-days 900
  --max-population 220
  --world-difficulty 1.45
  --shock-prob 0.02
  --robustness-seeds 4
  --robustness-days 300
  --robustness-founders 24
  --checkpoint-every 10
)

NO_CURR_SEEDS=(11111 12121 13131 14141 15151)
CURR_SEEDS=(16161)

elapsed_seconds() {
  local now
  now="$(date +%s)"
  echo $((now - START_TS))
}

within_budget() {
  local elapsed
  elapsed="$(elapsed_seconds)"
  [[ "$elapsed" -lt "$BUDGET_SECONDS" ]]
}

run_one() {
  local mode="$1"
  local seed="$2"
  local output_dir="$3"

  echo ""
  echo "=== [$(date -u +"%Y-%m-%d %H:%M:%S UTC")] start mode=${mode} seed=${seed} out=${output_dir} ==="

  if [[ "$mode" == "curriculum" ]]; then
    "$PY_BIN" run_neat_training.py "${COMMON_ARGS[@]}" --curriculum --seed "$seed" --output-dir "$output_dir" --no-auto-memory-sync
  else
    "$PY_BIN" run_neat_training.py "${COMMON_ARGS[@]}" --seed "$seed" --output-dir "$output_dir" --no-auto-memory-sync
  fi

  echo "=== completed mode=${mode} seed=${seed} ==="
}

echo "AGI hour push started: budget_minutes=${BUDGET_MINUTES}"
echo "Run tag: ${RUN_TAG}"
echo "Goal: beat best robustness mean while preserving stability and min-score floor."

for seed in "${NO_CURR_SEEDS[@]}"; do
  if ! within_budget; then
    echo "Budget exhausted before next no-curriculum run."
    break
  fi
  run_one "no_curriculum" "$seed" "outputs/${RUN_TAG}_nocurr_${seed}"
done

for seed in "${CURR_SEEDS[@]}"; do
  if ! within_budget; then
    echo "Budget exhausted before next curriculum run."
    break
  fi
  run_one "curriculum" "$seed" "outputs/${RUN_TAG}_curr_${seed}"
done

echo ""
echo "=== post-batch analysis ==="
"$PY_BIN" scripts/compare_neat_runs.py --require-full-generations
"$PY_BIN" scripts/build_experiment_observatory.py
"$PY_BIN" scripts/agi_memory_autosync.py --sync-once --force --outputs-dir outputs --wiki-dir wiki --max-runs 40
"$PY_BIN" scripts/query_agi_wiki.py "best robustness mean shock tolerant" --wiki-dir wiki --top-k 5

echo ""
echo "AGI hour push finished in $(elapsed_seconds) seconds."
