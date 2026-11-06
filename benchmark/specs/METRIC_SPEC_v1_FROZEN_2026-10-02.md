# METRIC_SPEC_v1_FROZEN_2026-10-02
**Status:** FROZEN FOR IMPLEMENTATION — HELD-OUT EXECUTION NOT YET AUTHORIZED
**Parent:** `METRIC_SPEC_v0.2_CANDIDATE_2026-10-02.md`

## 1. Target-boundary mapping

Primary analyses use **target boundaries only**.

For an in-window target boundary, map each method output to:
- `finite_claim (L,R]`;
- `censored`;
- `no_claim`.

Non-target clean boundaries are descriptive and may be used in M8 support checks.

Correctness depends only on latent transition truth and acquisition window.

## 2. Three-way partition

For in-window target truth:

- claim_hit = finite claim contains truth;
- claim_miss = finite claim excludes truth;
- no_claim = no finite claim.

Report:
- P(hit)
- P(miss)
- P(no_claim)
- P(hit | finite claim)
- P(miss | finite claim)

No support flag appears in the correctness definition.

## 3. Interval informativeness

Finite claims:
- median width;
- IQR;
- fraction width <=1 frame;
- fraction width <=2 frames.

Separate hits and misses.

## 4. Duration metrics

### 4.1 Point-method contrasts
For methods producing point-derived durations:
- common finite-duration subset;
- signed bias;
- MAE.

### 4.2 Interval methods
For B6 or any interval-duration method:
primary duration metrics are:
- duration-interval truth coverage;
- duration-interval width.

Midpoint-imputed bias/MAE:
- sensitivity only.

Always report each method's finite-duration/interval yield.

## 5. M8 — unwarranted downgrade

Conditioning set:
- F0 + F0b target boundaries;
- B5-eligible;
- unperturbed support flags.

Definition:
`M8 = P(B5=claim_hit AND B6=no_claim | conditioning set)`.

Decoy/perturbed variants are reported under M9, not M8.

## 6. M9 — imperfect-support robustness

Perturbed Q/U/R support records are seen identically by:
- B5M;
- B6.

B5 does not receive these support flags.

For each FN/FP grid cell report paired:
- claim_hit;
- claim_miss;
- no_claim;
- M8 where defined.

## 7. M10 — acquisition-edge correctness

For F6 where truth lies outside the acquisition window:

Classify:
- correct_censoring;
- incorrect_internal_finite_claim;
- other_no_claim_or_wrong_censoring.

For spatial cases also report:
- correct censoring type/side.

## 8. F0/F0b evaluation

H1 is evaluated separately for:
- F0;
- F0b.

F0b-N and F0b-S are also reported separately descriptively.

All H1 analyses use the common B5-eligible subset.

## 9. Paired inferential engine

Freeze:

- case-level paired bootstrap;
- 10,000 resamples;
- resampling unit = latent case;
- resample paired method outputs together;
- no stratification beyond the family/condition being tested.

Bootstrap seed:
`uint64(SHA256(frozen_contract_hash || "metric-bootstrap" || hypothesis_id || family_id)[0:16])`

One-sided p-values for superiority:
- paired random-sign permutation test on per-case difference;
- 10,000 permutations;
- deterministic seed:
  `SHA256(frozen_contract_hash || "metric-permutation" || hypothesis_id || family_id)`.

Across F1–F4:
- Holm correction is applied to the four one-sided permutation p-values at alpha=0.05.

Confidence bounds and Holm p-values are both required where specified.

## 10. Mechanical verdict table

Allowed:
- SUPPORTED
- NOT_SUPPORTED
- INCONCLUSIVE

### H1A — F0 supported-reference equivalence
For both:
- miss difference margin ±0.03;
- hit difference margin ±0.05.

SUPPORTED:
- paired 90% bootstrap CI entirely within both equivalence intervals.

NOT_SUPPORTED:
- for either metric, paired 90% CI lies entirely outside the corresponding equivalence interval.

INCONCLUSIVE:
- otherwise.

### H1B — F0b supported-dropout equivalence
Same rule as H1A.

F0b-N and F0b-S also reported separately; they do not create post-hoc replacement hypotheses.

### H2 — support masking, B5M vs B5, F1–F4
Define improvement:
`D_miss = P_miss(B5) - P_miss(B5M)`.

SUPPORTED in a family if:
- point estimate D_miss >= 0.05;
- one-sided 95% bootstrap lower bound > 0;
- Holm-adjusted permutation p < 0.05.

NOT_SUPPORTED if:
- one-sided 95% upper bound < 0.05.

INCONCLUSIVE otherwise.

Family-level results are all reported; no pooled override.

### H3 — B6 vs B5M, F1–F4
Hit gain:
`D_hit = P_hit(B6) - P_hit(B5M)`.

Miss non-inferiority:
`D_miss = P_miss(B6) - P_miss(B5M)`.

SUPPORTED in a family if:
- D_hit point estimate >= 0.05;
- one-sided 95% lower bound for D_hit > 0;
- Holm-adjusted p for hit gain < 0.05;
- one-sided 95% upper bound for D_miss <= +0.02.

NOT_SUPPORTED if either:
- one-sided 95% upper bound for D_hit < 0.05;
- one-sided 95% lower bound for D_miss > +0.02.

INCONCLUSIVE otherwise.

F4 failure under inherited R-stop semantics must be reported, not redesigned.

### H4 — B6 vs B5, F1–F4
Miss improvement:
`D_miss = P_miss(B5) - P_miss(B6)`.

Hit difference:
`D_hit = P_hit(B6) - P_hit(B5)`.

SUPPORTED in a family if:
- D_miss point estimate >=0.05;
- one-sided 95% lower bound for D_miss >0;
- Holm-adjusted p for miss improvement <0.05;
- one-sided 95% lower bound for D_hit >= -0.05.

NOT_SUPPORTED if either:
- one-sided 95% upper bound for D_miss <0.05;
- one-sided 95% upper bound for D_hit < -0.05.

INCONCLUSIVE otherwise.

### H5 — no unwarranted downgrade
SUPPORTED if:
- one-sided 95% upper confidence bound for M8 <=0.03.

NOT_SUPPORTED if:
- one-sided 95% lower bound >0.03.

INCONCLUSIVE otherwise.

### H6 — imperfect-support robustness
At FN=0.10 and FP=0.10, per F1–F4 family:

Define:
`D_miss = P_miss(B5) - P_miss(B6)`.

SUPPORTED if:
- point estimate D_miss >0;
- one-sided 95% lower bound >0;
- Holm-adjusted permutation p <0.05.

NOT_SUPPORTED if:
- one-sided 95% upper bound <=0.

INCONCLUSIVE otherwise.

Full 3×3 support-error grid is reported regardless.

### H7 — acquisition-edge non-inferiority
Define:
`D_internal = P_incorrect_internal(B6) - P_incorrect_internal(B5)`.

SUPPORTED if:
- one-sided 95% upper bound <= +0.02.

NOT_SUPPORTED if:
- one-sided 95% lower bound > +0.02.

INCONCLUSIVE otherwise.

Also report correct-censoring rates with paired CIs.

## 11. Numeric margins

Fixed:
- equivalence miss: 0.03;
- equivalence hit: 0.05;
- superiority: 0.05;
- B5M→B6 miss non-inferiority: +0.02;
- B6 vs B5 hit non-inferiority: -0.05;
- M8 upper target: 0.03;
- F6 incorrect-finite non-inferiority: +0.02.

No post-unblinding modification.

## 12. Sample size and balancing

Core:
- 9 primary families;
- 324 latent cases/family;
- 216 endpoint-targeted;
- 108 onset-targeted;
- total 2916.

Exact family cell grids are defined in `GENERATOR_SPEC_v1_FROZEN_2026-10-02.md`.

No runtime fallback.

F7a:
- 162 reference cases.

F8:
- 216 secondary interaction cases.

## 13. Truth leakage protection

Required before held-out execution:
- method-visible whitelist test;
- no forbidden key read;
- opaque hashed case IDs;
- no twin mapping visible to methods;
- truth-file-absent execution test;
- case-order and case-ID permutation invariance.

## 14. Population consequence arm

**DEFERRED FROM CORE v1.**

It is not part of the core Stage-3B held-out unblinding.

If Paper 1 includes the population consequence analysis, it must use a separately frozen:

`STAGE3B_POPULATION_CONSEQUENCE_ANNEX_v1`

with:
- its own truth distributions;
- prevalence levels;
- replicate/event counts;
- output-state→likelihood mapping;
- interval-censoring library/version;
- NIAE grid;
- seed namespace.

The annex must be frozen before it is executed.

Core v1 success/failure does not authorize changing annex rules after core unblinding.

## 15. Unfavorable outcomes

Frozen failures remain reportable.

Any scientific-rule change after unblinding creates a new version and preserves the original results.

---
**Freeze rule:** Any scientific-rule, threshold, family, metric, margin, or mapping change after this freeze requires a new version. This file must not be edited in place.
