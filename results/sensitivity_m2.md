# Sensitivity analysis, held-out set (Milestone 2)

Three runs averaged. Liability-only partials = baptist_health_care, connecticut11, m-10-1884 (coverage denial undisputed; only liability reversed). Thin = <=2 facts (gr, ny).

```
== original orchestrator
All 18                                     n=18 multi   54%  single   61%
Drop liability-only partials (15)          n=15 multi   60%  single   73%
Drop thin cases, <=2 facts (16)            n=16 multi   56%  single   62%
Only cases with manual key (11)            n=11 multi   64%  single   70%
Drop liability-only AND thin (13)          n=13 multi   64%  single   77%
== per-component orchestrator
All 18                                     n=18 multi   41%  single   61%
Drop liability-only partials (15)          n=15 multi   49%  single   73%
Drop thin cases, <=2 facts (16)            n=16 multi   46%  single   62%
Only cases with manual key (11)            n=11 multi   52%  single   70%
Drop liability-only AND thin (13)          n=13 multi   56%  single   77%
domain snf              n=10 multi  57% single  63%
domain home_health      n=5 multi  53% single  60%
domain inpatient_rehab  n=3 multi  44% single  56%
ref COVERED         n=7 multi  62% single  67%
ref NOT_COVERED     n=5 multi  80% single  80%
ref PARTLY_COVERED  n=6 multi  22% single  39%
```

Reading: single-agent is at or above multi-agent in every subset (gap 6 to 13 points), so the ranking does not depend on the ambiguous or thin cases. Both systems do worst on PARTLY_COVERED (multi 22%, single 39%) and best on NOT_COVERED (80% both). Small n: treat as indicative.
