#!/usr/bin/env bash
# One command: single-agent vs multi-agent on the fair-test Council arms, plus the blind-guess floor.
#   export LLM_API_KEY=...            # your key
#   export LLM_BASE_URL=https://openrouter.ai/api/v1      # only if you use OpenRouter (same as your earlier runs)
#   bash scripts/run_fair_eval.sh                          # held-out, arms D_wide (primary) and A_strict (leak-controlled)
#   ARMS="D_wide" SETS="held dev" REPS=3 PROBE=1 bash scripts/run_fair_eval.sh
# Outputs: results/fair/<arm>_<set>/run*/resp_*.json and score.txt ; results/fair/probe_<arm>_<set>/ ; results/fair/score_*.json
set -euo pipefail
cd "$(dirname "$0")/.."
: "${LLM_API_KEY:?set LLM_API_KEY first}"
MODEL="${MODEL:-anthropic/claude-sonnet-5.5}"; BACKEND="${BACKEND:-openai}"
ARMS="${ARMS:-D_wide A_strict}"; SETS="${SETS:-held}"; REPS="${REPS:-1}"; PROBE="${PROBE:-1}"
export INDEX_DIR="${INDEX_DIR:-data/index_v3}"
for ARM in $ARMS; do for SET in $SETS; do
  CASES="data/cases_v4/${ARM}_${SET}"; BASE="results/fair/${ARM}_${SET}"; mkdir -p "$BASE"
  CASES_DIR="$CASES" RUN_DIR="$BASE/prompts" python3 -m rag.pipeline prepare
  for R in $(seq 1 "$REPS"); do
    OUT="$BASE/run$R"
    if [ -f "$OUT/resp_orch.json" ]; then echo "skip $OUT (done)"; continue; fi
    CASES_DIR="$CASES" RUN_DIR="$BASE/prompts" python3 -m rag.langgraph_app --backend "$BACKEND" --model "$MODEL" --out "$OUT"
  done
  python3 scripts/score_fair.py --arm "$ARM" --set "$SET" --runs $(ls -d "$BASE"/run*) | tee "$BASE/score.txt"
  if [ "$PROBE" = "1" ]; then python3 scripts/blind_probe.py --arm "$ARM" --set "$SET" --backend "$BACKEND" --model "$MODEL" | tee "$BASE/probe_score.txt"; fi
done; done
