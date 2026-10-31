# Synthetic case options and recommended plan (2026-10-30)

Anchor: PROBLEM_STATEMENT.md / spec v2. Synthetic data is the LAST resort and needs professor approval (Homan, Monday). Real data stays the headline: ~40 Council cases + CMS vignettes (37 cards pending labels). Synthetic is reported separately, never blended into one accuracy number.

## 1. What exists (all verified from primary pages this session unless marked)
| Option | What it is | License / access | Fit for Medicare SNF/HH/IRF |
|---|---|---|---|
| K-NHIB (JMIR 2026;28:e95877) | 222 synthetic reimbursement cases, 74 eligible / 74 ineligible / 74 undeterminable; each criterion marked met / not met / unevaluable and the label follows by rule; near-miss design (1-2 conditions off); 3 experts + independent UR nurse reviewed all cases, agreement 95% (211/222), kappa 0.93 | Repo seo-see/K-NHIB live; data CC BY 4.0, code MIT; Zenodo 10.5281/zenodo.20563360 v1.0.0 (verified) | Data unusable (Korean gynecologic oncology). METHOD and prompt/eval pipeline are the template. Its finding: models under-abstain, undeterminable recall 44.6-70.3% (Sonnet 4.6: 52.7%) |
| DeVisE (arXiv 2506.15339) | Single-variable counterfactual edits of real notes with diff checks; 5% LLM-extraction error found by manual check | Code MIT (repo live); data needs MIMIC credentials | Precedent for "change one thing, check the output moves" |
| CLINMT (arXiv 2607.22984) | Metamorphic testing: pairs with expected direction fixed in advance | No code/data release stated | Precedent only |
| SynthMedic (Zenodo 17127130) | Synthetic discharge summaries, 1.9 MB | CC BY 4.0 | No coverage criteria or outcomes |
| SynGP500 | 500 Australian GP notes, GPT-5, one GP reviewed | CC BY-NC-SA | Wrong domain |
| Longitudinal synthetic notes pipeline (arXiv 2606.26879) | Synthea UK demographics + GPT-4o; Silver release 70 patients, no clinician review | License not stated | No coverage criteria |
| Synthea | Structured synthetic patients | Open source | No narratives of skilled need or functional status; no Medicare coverage outcomes |
| Aegis, chi-Bench, 45 PA scenarios (arXiv 2603.29366) | Small synthetic PA/denial sets | Mixed / unstated | Small, wrong shape (from earlier sweep, PARTLY verified) |
Bottom line: no ready-made validated synthetic set exists for Medicare SNF / home health / IRF coverage that I could find. The reusable thing is the K-NHIB construction method, with published validation numbers to cite.

## 2. Recommended build (K-NHIB method on our own criteria trees)
- Source of truth for the rules: data/criteria/trees.json (MBPM ch.7/8/1). Leaves: SNF 10, home health 8, IRF 6.
- Matched triplets: for each of 20 base cases per domain (60 total), one ELIGIBLE parent (all leaves met), one NEAR-MISS INELIGIBLE twin (1-2 leaves explicitly not met), one UNDETERMINABLE twin (1-2 leaves not stated, none violated). 60 x 3 = 180 cases, labels by three-valued AND/OR logic, so the answer is known by construction.
- Narratives written as facts only (same style as Council case summaries), no rule vocabulary, no verdict words.
- Writer model from a different vendor than the model under test (avoid self-preference).
- Validation (what replaces K-NHIB's clinicians): (a) round-trip: a second, different model reads only the narrative and labels each leaf met / not met / not stated; keep a case only if all leaves match the intended states; (b) leakage scan for verdict words; (c) you spot-check 30 random cases (15-20 min, one HTML sheet) and we report agreement; (d) anchor check: compare single vs multi accuracy on synthetic vs on real Council + CMS cases; if ranking and rough level agree, that supports validity.
- Cost: ~180 writer calls + ~1,500 validator leaf calls + 2 systems x 180 runs. Cheap.

## 3. What 180 synthetic + ~78 real can prove (exact McNemar test, simulated)
| Claim | Needs | We have |
|---|---|---|
| Multi vs single decision accuracy, 10-pt gap | ~155-230 paired cases (power 0.76 at 155 with 20% discordance; 0.87 at 200) | ~258 combined, but synthetic and real reported separately: synthetic alone ~180 detects ~10-12 pts; real 78 alone detects only ~15-20 pts (power 0.72 at 15 pts) |
| Accuracy interval | n=78: +/-9.6 pts; n=200: +/-6.0 pts (at 75%) | |
| Missing-information behavior | 60 undeterminable cases give 60 abstention trials; matches fact-removal test and K-NHIB's finding | yes |
| Groundedness / hallucination | claim-level: 180 cases x 5-8 claims = 900+ claims; mechanical citation check plus human-labeled sample | yes |
| Latency | any run set | yes |
| Mechanism ("uses the criterion") | twin flips: one leaf changed, decision must change | yes, from triplets |

## 4. Honest limits (must go in the writeup)
- Gold labels come from the same MBPM criteria the systems retrieve, and the criteria trees are also the structure of the tree method: report the tree method on synthetic separately or exclude it. Multi-agent and single-agent never see the tree, so their comparison is fair.
- Clean, structured fact patterns overestimate real-world accuracy (K-NHIB states this). Synthetic = mechanism and power; Council + CMS = headline accuracy.
- Round-trip validation catches generator drift, not wrong rules. A person (you) still checks a sample.
- Needs written professor approval before use. One-line ask: "Real data first (about 78 labeled cases); synthetic cases built by the published K-NHIB method from CMS criteria, validated by round-trip and spot-check, reported separately and disclosed as synthetic."

## 5. Next steps if approved
1. Write rag/synth_cases.py (state sampler + Kleene logic + writer prompt + round-trip validator).
2. Pilot 3 triplets per domain (27 cases), inspect, then scale to 60 triplets.
3. Run single vs multi on CASES_DIR=synthetic, INDEX_DIR=data/index_v3_noex.
