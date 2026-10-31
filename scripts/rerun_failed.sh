#!/usr/bin/env bash
# One command: re-run ONLY the failed model calls (429 / broken JSON) with a hard spending cap, then rescore.
#   bash scripts/rerun_failed.sh            # asks for your key silently (not echoed, not saved, not in shell history)
#   MAX_USD=3 bash scripts/rerun_failed.sh  # change the cap (default 4)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${LLM_API_KEY:-}" ]; then read -r -s -p "OpenRouter key (input hidden): " LLM_API_KEY; echo; fi
export LLM_API_KEY LLM_BASE_URL="${LLM_BASE_URL:-https://openrouter.ai/api/v1}" MAX_USD="${MAX_USD:-4}" REDO=1 NOTES=0
python3 scripts/check_key.py || exit 1
echo "cap: \$${MAX_USD}  (the run stops itself above this; run the same command again to resume)"
bash scripts/run_final_eval.sh
echo; echo "true cost of this run (from the per-call log):"; python3 - <<'PY'
import glob, json
f = sorted(glob.glob("results/fair/usage_*.jsonl"))
if f:
    L = [json.loads(x) for x in open(f[-1])]; print(f"  {len(L)} calls, ${sum(x['usd'] for x in L):.2f}   ({f[-1]})")
PY
