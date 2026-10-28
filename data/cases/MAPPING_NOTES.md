# How real decisions became case files

Sources: 14 public, name-redacted Texas Department of Insurance IRO decisions on facet / medial branch block /
radiofrequency procedures (URL in each case's `source.url`) + 1 open-access PMC case report.

Rules
- Only facts the decision states are recorded. Not stated or redacted -> `null` -> the pipeline reports UNKNOWN.
- The IRO outcome (upheld/overturned) is stored as `reference_outcome` and never given to the pipeline.
- Facts were read from the PDFs with LLM assistance (WebFetch summaries), not hand-copied. Verify any specific value
  against `source.url` before quoting it.

Annotator mapping choices (judgement calls)
- "x/10" pain values are treated as a numeric rating scale (NRS); ranges ("4-6/10") are left null.
- Any sedation / anesthesia / MAC mention maps to a non-"none" sedation value (type of sedation is rarely specified).
- "radiculopathy present = yes" maps to untreated_radiculopathy = True (treatment status is rarely stated).
- Any non-facet finding listed in the decision (e.g. disc herniation) is recorded in `non_facet_pathology`.
- Levels that are redacted are `null`.

Limits
- The reviewers applied ODG/ACOEM guidelines, NOT Medicare LCD L38765, so the outcome is an external reference, not an
  LCD ground truth.
- Case files are summaries of the decision text, not the original medical records.
