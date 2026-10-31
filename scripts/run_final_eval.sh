#!/usr/bin/env bash
# FINAL RUN (run once): multi-agent vs single-agent on the unit/case test sets, with the human-in-the-loop layer and the blind-probe floor.
#   export LLM_API_KEY=...            # your key (never paste it in chat)
#   export LLM_BASE_URL=https://openrouter.ai/api/v1
#   bash scripts/run_final_eval.sh                       # held-out first, then dev;  arms D_wide + A_strict
#   ARMS=A_strict SETS=final_held REPS=1 NOTES=1 bash scripts/run_final_eval.sh
# NOTES=1 also asks the model to write the reviewer note for each flagged case (costs a few extra calls).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${LLM_API_KEY:?set LLM_API_KEY first}"
: "${MAX_USD:?set a hard spending cap first, e.g.  export MAX_USD=4   (the run stops itself above it; rerun the same command to resume)}"
export MAX_USD LLM_USAGE_LOG="${LLM_USAGE_LOG:-results/fair/usage_$(date +%Y%m%d_%H%M%S).jsonl}"   # per-call true cost log
# REDO=1 : keep finished work, re-run ONLY cases whose saved responses contain an API error/fallback (429, broken JSON), then re-score. Probe resumes automatically.
MODEL="${MODEL:-anthropic/claude-sonnet-5.5}"; BACKEND="${BACKEND:-openai}"
ARMS="${ARMS:-D_wide A_strict}"; SETS="${SETS:-final_held final_dev}"; REPS="${REPS:-1}"; PROBE="${PROBE:-1}"; NOTES="${NOTES:-0}"
python3 scripts/check_key.py
export INDEX_DIR="${INDEX_DIR:-data/index_v3}"
for ARM in $ARMS; do for SET in $SETS; do
  CASES="data/cases_v4/${ARM}_${SET}"; BASE="results/fair/${ARM}_${SET}"; mkdir -p "$BASE"
  CASES_DIR="$CASES" RUN_DIR="$BASE/prompts" python3 -m rag.pipeline prepare
  for R in $(seq 1 "$REPS"); do
    OUT="$BASE/run$R"
    if [ ! -f "$OUT/resp_orch.json" ]; then CASES_DIR="$CASES" RUN_DIR="$BASE/prompts" python3 -m rag.langgraph_app --backend "$BACKEND" --model "$MODEL" --out "$OUT"
    elif [ "${REDO:-0}" = "1" ]; then CASES_DIR="$CASES" RUN_DIR="$BASE/prompts" python3 -m rag.langgraph_app --backend "$BACKEND" --model "$MODEL" --out "$OUT" --redo-errors
    else echo "skip model calls for $OUT (done)"; fi
    if [ "$NOTES" = "1" ]; then CASES_DIR="$CASES" RUN_DIR="$OUT" python3 -m rag.hitl --notes llm --backend "$BACKEND" --model "$MODEL"; else CASES_DIR="$CASES" RUN_DIR="$OUT" python3 -m rag.hitl; fi
  done
  if [ "$PROBE" = "1" ]; then python3 scripts/blind_probe_final.py --arm "$ARM" --set "$SET" --backend "$BACKEND" --model "$MODEL"; fi
  PR=""; [ "$PROBE" = "1" ] && PR="--probe results/fair/probe_${ARM}_${SET}"
  python3 scripts/score_final.py --arm "$ARM" --set "$SET" --runs $(ls -d "$BASE"/run*) $PR | tee "$BASE/final_score.txt"
done; done
