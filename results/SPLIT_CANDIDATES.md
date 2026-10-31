# Split-unit candidates (draft for review, 2026-10-30) - NOTHING BUILT OR RUN YET

Rule: a decision is split only where the Council states its own coverage verdict for each part (beneficiary / stay / period). No label is invented.
Source: decision text in data/raw/text, DECISION/CONCLUSION paragraphs.

## A. Clean (explicit verdict per unit)
| decision | units | labels (Council) |
|---|---|---|
| twin_maples_health_care_case | stay Aug 1-11, 2009 / stay after Aug 11 | COVERED / NOT_COVERED ("skilled care ... covered" ; "remains liable for the noncovered costs ... after August 11") |
| prestige_homecare | B.K. / B.N. / F.P. | NOT_COVERED x3 ("not medically reasonable and necessary and are not covered") |
| m_10_1771 | E.K. PT / E.M. SNF / J.S. SNF | NOT_COVERED x3 ("PT ... not covered"; "SNF ... E.M. and J.S. were not covered") |
| roman_eagle_memorial_home | first stay 9/29-11/27/03 | NOT_COVERED (no skilled care, no certification) |

## B. Needs your call (label depends on a definition)
| decision | issue |
|---|---|
| roman_eagle second stay 12/11/03-1/6/04 | Council: skilled care AND physician certified, but provider (not Medicare) liable because notice/consent invalid. Criteria met = COVERED; payment outcome = not paid. Coverage-only key says COVERED. This is the one our system called "covered". |
| 11-1343 (3 beneficiaries x PT/OT/ST/SN, ~10 units) | Council text gives per-service reasoning but verdicts are scattered ("PT and ST not necessary" per beneficiary; "limited types of services found necessary" at the end). Needs a careful read of each beneficiary section before any label is written. |
| state_of_vt | 3 explicit COVERED windows (6/3-6/27, 8/15-8/30, 10/25-10/29/07); other windows not covered only by implication (ALJ stands). Facts are not separable by period. |
| m-11-1869 | COVERED Oct 3 2007-Mar 28 2008 and Jun 21-Sep 24 2008; gap in between implied not covered. Same facts-by-period problem. |
| case_excellenthomecare | 2 beneficiaries, Council adopts ALJ (NOT_COVERED both) but its discussion is generic for both. |

## C. Not splittable
ny (remand, no verdict) ; baptist_health_care (liability only) ; eagle_air_med, midwest_lifeteam (payment-limit on miles; already fail evidence floor) ; single-unit decisions (the rest).

## Rough count (honest)
Clean now: +5 units (twin +1, prestige +2, m_10_1771 +2) -> but 3 of the original cases already count as 1 each. If all of B is accepted: roughly +15-20 more, mostly NOT_COVERED, and units from one decision are clustered (not independent). Each unit must still pass the evidence floor (A>=60, D>=150 words) after facts are cut per unit - many may not.

---
## UPDATE 2026-10-30 22:5x - decisions made with user + 11-1343 read in full

Decision: roman_eagle second stay (12/11/03-1/6/04) labeled COVERED on the coverage-only key (skilled care + physician certification met; provider liable only because notice/consent invalid). First stay NOT_COVERED.

### 11-1343 units (Council's own verdict sentence per unit, read from the Discussion sections)
| unit | label | Council sentence (abridged) |
|---|---|---|
| D.E. OT (Oct 2009) | COVERED | "the Council concurs with the ALJ's finding that the OT services were medically reasonable and necessary" |
| D.E. PT | NOT_COVERED | "the record does not support a finding that the PT services were medically reasonable and necessary" |
| D.E. ST | NOT_COVERED | "the record does not support a finding that D.E. experienced significant progress to justify continued skilled speech therapy" |
| E.M. ST (Oct 2009) | COVERED | "the Council concurs with the ALJ that the ST services were medically reasonable and necessary" |
| E.M. PT | NOT_COVERED | "the record does not support a finding that the PT services were medically reasonable and necessary" |
| E.M. OT | NOT_COVERED | "continued teaching of repetitive exercises does not require the skills of therapist" ; OT "not medically reasonable and necessary" |
| J.M. SN (Aug 2009) | COVERED | "the SN services for dates of service at issue were skilled, and thus medically reasonable and necessary" |
| J.M. PT | NOT_COVERED | "a restorative nursing program would have been more appropriate than continued services by a skilled therapist" |
| J.M. OT | NOT_COVERED | "the Council concurs ... OT services were not medically reasonable and necessary" |
| J.M. ST | NOT_COVERED | "the record showed minimal progress" ; PT and ST "not medically reasonable and necessary" |
Physician-signature question was decided in the appellant's favor for all PT/ST/OT units (signed orders sufficient), so these units turn on medical necessity only. Total 10 units: 3 COVERED, 7 NOT_COVERED.

### Confirmed unit set so far (not yet built)
11-1343 x10 ; twin_maples x2 ; prestige_homecare x3 ; m_10_1771 x3 ; roman_eagle x2  => 20 units from 5 decisions (these 5 decisions currently count as 5 cases).
Labels: 5 COVERED (3 in 11-1343, twin Aug 1-11, roman stay 2), 15 NOT_COVERED. Still subject to the evidence floor per unit after facts are cut.
