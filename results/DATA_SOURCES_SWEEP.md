# Data source sweep (Oct 30, 2026)

Question: is there public data that gives (a) volume AND (b) enough case detail AND (c) Medicare coverage criteria, for checking coverage decisions against the Medicare Benefit Policy Manual (MBPM)?
Status key: VERIFIED = fetched or counted this session; PARTLY = seen in search results or page summary only; NOT VERIFIED = could not reach / not checked. Counts marked "user" were read by Ashish in a browser.
Method limits: the cloud workspace could not reach CourtListener, Harvard CAP, govinfo, Zenodo, GitHub or the Internet Archive from the shell; some pages were read through a page-summary tool, so numbers are as reported by that tool.

## A. Real cases, Medicare
| Source | What we found | Status | Verdict |
|---|---|---|---|
| HHS DAB Medicare Appeals Council decisions | Page states decisions are "selected for posting", not complete. 53 documents already in repo. Data.gov record lists license ODbL 1.0. | VERIFIED | Used. No more to mine here. |
| Older archived Council index pages (2004, 2009) | Internet Archive rate-limited; UNT archive blocks robots | NOT VERIFIED | Unknown; pre-2005 rules anyway |
| OMHA ALJ decisions | Appears to publish statistics only (decision statistics, receipts by procedure), no decision text | PARTLY | No |
| Federal court opinions (CourtListener) | Ashish's browser counts (strict queries): SNF 26, home health 18, inpatient rehab 2; many dated 1960s-1990s | user | Small, partly outdated rules |
| govinfo USCOURTS | Opinions from selected courts, mostly 2004 onward, PDFs; search API (POST /search, free key) | PARTLY | Same small population, newer slice |
| Harvard Caselaw Access Project | Could not read coverage page | NOT VERIFIED | Likely overlaps CourtListener |
| OIG audit reports | Web page gives category-level findings only (e.g. 39 of 100 sampled home health claims failed; homebound/skilled-need errors); full PDFs not reachable | PARTLY | Weak: no per-claim facts seen |
| Westlaw / Nexis Uni via RIT | RIT guide lists Westlaw Campus Research (on-campus access only) and Nexis Uni; RIT resources limited to academic use | PARTLY | Not usable at scale for an online student |
| PACER | Not checked (about 10 cents/page per earlier search) | NOT VERIFIED | Same small case population as court opinions |

## B. Real cases, not Medicare
| Source | What we found | Status | Verdict |
|---|---|---|---|
| California IMR (DMHC/CDI) | 19,245 decisions 2001-2016; 251 SNF, 59 home health; findings median about 1,040 chars; after removing conclusion sentences median about 77 words of facts (37 of 251 SNF cases have 150+ words); 71% of SNF upheld; license unchecked | VERIFIED (counts) | Volume, thin facts, commercial plans |
| HICRIC corpus (Gartner 2025) | NY + CA external appeal summaries (73,987 labeled, most labels model-generated, 1,000 hand-annotated); descriptions "relatively short"; corpus also holds Medicare LCD/NCD and CMS manuals; code public, permissive license | PARTLY | Precedent for using appeal summaries; no richer data |
| NY DFS external appeal database | One case page checked: structured fields only (plan, outcome, appeal type, age range), no narrative | VERIFIED (one page) | Weak |
| Oregon IRO decision report | Per case: metadata only (service name, outcome); redacted synopsis only on request; about 350-500 cases/year | PARTLY | No |
| Texas TDI IRO decisions | Two PDFs checked: workers' compensation, clinical-history section separate from analysis; criteria are proprietary guidelines (ODG etc.) | VERIFIED (two docs) | Wrong domain/criteria |
| NY OTDA Fair Hearing Decision Archive | OTDA page says decisions are published online, personal data removed; link, volume, structure not captured | PARTLY | Medicaid; needs a 1-minute browser check |
| Montana fair hearing decision search | Search by year/program/issue, decisions as PDFs; programs and volume not captured | PARTLY | Unknown |
| Kaggle "prior authorization" table (250,000 rows) | No clinical text; denial rate 35% for every service, age, race, provider; exact 162,500/87,500 split | VERIFIED | Rejected: synthetic noise |

## C. Real clinical notes (no coverage labels)
| Source | What we found | Status | Verdict |
|---|---|---|---|
| MIMIC-IV-Note | Credentialed. PhysioNet policy page: DUA prohibits sharing data with third parties including APIs; local LLMs recommended; cloud only if zero retention, no training, no human review is verified | VERIFIED (policy page) | Not feasible this term (credentialing + local-only models) |
| PMC-Patients | About 167k (v1) to 250k (v2) patient summaries from published case reports; CC BY-NC-SA 4.0; CSV 545 MB, JSON 837 MB; no coverage labels | PARTLY | Possible fact-rich source for checker validation; probe script written, not run |
| MTSamples | Public transcription samples; provenance/license unclear | NOT VERIFIED | Weak |
| n2c2 / i2b2 | Not checked | NOT VERIFIED | Needs data-use agreement anyway |

## D. Published synthetic / benchmark sets
| Source | What we found | Status | Verdict |
|---|---|---|---|
| K-NHIB (JMIR 2026, Korean anticancer reimbursement) | 222 synthetic cases built from public national insurance guidelines, 74 regimens, case outcomes derived from per-condition states (met / not met / unevaluable); accuracy 77.9-88.7% across six LLMs; recall on "undeterminable" cases only 44.6-70.3%; paper says data will be on GitHub (seo-see/K-NHIB) and Zenodo (doi 10.5281/zenodo.20563360) | PARTLY (page summary; links not reachable) | Closest published method precedent; Korean policy, release unconfirmed |
| 45 physician-validated PA scenarios (arXiv 2603.29366) | Synthetic, letters by 3 models; release not stated | PARTLY | Precedent only |
| chi-Bench (2026) | Synthetic simulator, 50 patients, 75 tasks incl. PA/UM; license not stated; repo not opened | PARTLY | Agent-tool benchmark, wrong shape |
| Aegis (GitHub) | 50+20 synthetic composite denial cases; Apache 2.0 repo, dataset license unstated | PARTLY | Small |
| MAX-EVAL-11 | ICD-11 coding benchmark, not PA | VERIFIED | Irrelevant |

## E. In-repo
| Source | What we found | Status | Verdict |
|---|---|---|---|
| CMS-authored EXAMPLE vignettes in MBPM ch.7/8/10 | 90 unique EXAMPLE blocks; 38 have at least 15 words of scenario plus a conclusion sentence (32 ch.7, 4 ch.8, 2 ch.10); regex guess: 30 covered / 8 not. Candidates in data/cms_vignettes/candidates.json | VERIFIED (counts) | Authoritative, public, about 38 items, skewed to home health; not volume. Index must exclude them when testing. |

## Bottom line
No public source found that combines volume, case detail and Medicare criteria. Largest real source in scope is California IMR (volume, thin). Richest real text is PMC-Patients or MIMIC-IV-Note (no coverage labels; MIMIC not feasible). Published precedent for criterion-based synthetic cases exists (K-NHIB, 45-scenario study, chi-Bench, Aegis, HICRIC).

## Still open (needs the user's browser or Mac)
1. Run scripts/pmc_patients_probe.py.
2. Open the K-NHIB Zenodo record and GitHub repo: is the data live?
3. Find the NY OTDA Fair Hearing Decision Archive: how many Medicaid home care / nursing facility decisions, and are findings of fact separate from conclusions?

## F. Synthetic options (2026-10-30)
See results/SYNTHETIC_PLAN.md. K-NHIB repo and Zenodo record verified live (CC BY 4.0 data, MIT code); paper reports expert validation kappa 0.93. No ready-made Medicare SNF/HH/IRF synthetic set found.

## G. California IMR full file (user upload, 2026-10-30)
File: independent-medical-review-imr-determinations-trends.csv (85 MB, not in repo; do not commit). DMHC Independent Medical Review determinations, 42,749 rows, 2001-2026, 22,445 overturned / 20,304 upheld. Columns: ReferenceID, ReportYear, DiagnosisCategory/SubCategory, TreatmentCategory/SubCategory, Determination, Type, AgeRange, PatientGender, IMRType, DaysToReview, DaysToAdopt, Findings. License: CC-BY per the data.gov catalog entry (DMHC's own conditions-of-use page not opened). Supersedes the 310-row subset (data/raw/ca_imr/ca_imr_snf_hh.csv, older category names).
| Slice | n | Overturned / Upheld |
|---|---|---|
| TreatmentCategory "Rehab/Svcs SNF Inpt" | 521 | 128 / 393 |
| "Home Health Care" | 153 | 72 / 81 |
| "Transportation" (ambulance) | 65 | 35 / 30 |
| Acute rehab found by text, outside SNF category | 147 | 37 / 110 |
| Any of the above by category or text | 1,193 | 393 / 800 (706 from 2016 on) |
Fit: 2016+ rows have "Case Summary / Findings / Final Result / Credentials" structure. In the 1,193 relevant rows only 2% mention Medicare, 48% "skilled", 26% daily / 5-7 days a week, 1% homebound, 1% three-day stay: these are commercial medical-necessity decisions, not Medicare coverage decisions. Case-specific sentences without evaluative wording: median about 5 per case (SNF 6, home health 4, transport 5; rough heuristic), same thinness as Council cases. Generic reviewer criteria text sits inside the narrative and must be stripped. SNF slice is 75% upheld, so majority baseline is 75% (use balanced accuracy).
Verdict: real, labeled, public, large enough for paired comparison (about 150-200 balanced cases gives roughly 0.76-0.87 power for a 10-point gap, simulated). Not a test of Medicare criteria. Needs facts-only extraction plus leak audit (rag/imr_prep.py, column names must be updated to this file).
