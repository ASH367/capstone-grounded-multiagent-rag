# Repeat runs on cleaned facts (Milestone 2)

Three full pipeline runs on data/cases_v2_clean (22 cases): results/llm_runs_clean, llm_runs_clean_r3, llm_runs_clean_r4. Each run is a fresh Claude subagent per role; same prompts and retrieved passages.

| | Run A | Run B | Run C | Mean (of 22) | SD |
|---|---|---|---|---|---|
| Multi-agent correct | 18 | 17 | 15 | 16.7 (75.8%) | 1.5 |
| Single-agent correct | 19 | 20 | 17 | 18.7 (84.8%) | 1.5 |

- Single-agent is ahead or level in every run (by 1, 3 and 2 cases). Majority vote across runs: multi 17, single 19.
- 5 of 22 cases change prediction across runs. Citation validity was 100% (mechanical) for multi-agent in all three runs.
- Multi-agent never predicts PARTLY_COVERED for eagle_air_med while single-agent always does; the orchestrator tends to collapse to NOT_COVERED when a specialist says DOES_NOT_SUPPORT.
- Caveats: n=22 and a 2-case gap is about 1.3 SD, so this is not statistically significant. Runs are repeated samples of one model family, not independent systems. Conclusion supported: multi-agent shows no accuracy advantage over single-agent here; it may be slightly worse.
