# Held-out evaluation (18 cases, never used for tuning) - Milestone 2

Cases: data/cases_v3_heldout_clean (facts cleaned of adjudicator findings), index: data/index_v3 (adds MBPM ch.6 and ch.8).
Domains: SNF (ch.8), home health, inpatient rehab. Roles played by Claude subagents (file-based runs), three independent runs.
Majority-class baseline: 7/18 = 0.389. Reference labels mapped from outcomes (favorable/unfavorable/partial).

See per-run files results/heldout_r{1,2,3}/decisions.json (original orchestrator) and heldout_r{1,2,3}v2 (per-component orchestrator).
Caveats: 18 cases is small (one case = 5.6 points); thin-fact and liability-only "partial" labels are ambiguous; 10 of 21 pre-cleaning cases have no MBPM key (decision accuracy only).
