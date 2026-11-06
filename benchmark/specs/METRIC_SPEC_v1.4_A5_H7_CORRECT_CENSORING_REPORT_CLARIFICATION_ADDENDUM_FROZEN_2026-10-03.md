# METRIC_SPEC_v1.4_A5_H7_CORRECT_CENSORING_REPORT_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — Metrics & Mechanical Verdicts  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `METRIC_SPEC_v1_FROZEN_2026-10-02.md`  
**Related additive authority:**
- `METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.3_A5_DURATION_CONSTRUCTION_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`

**Purpose:** resolve `SPEC_AMBIGUITY A5-04` without editing frozen v1/v1.1/v1.2/v1.3 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope

This addendum resolves only the supplemental H7 requirement:

> report correct-censoring rates with paired CIs.

It does **not** change:

- the primary H7 statistic;
- the H7 non-inferiority margin;
- the H7 mechanical verdict;
- the M10 correctness categories;
- the F6 conditioning set;
- any bootstrap RNG/CI convention;
- any generator or baseline behavior;
- any held-out authorization.

The primary H7 statistic remains exactly:

```text
D_internal =
P_incorrect_internal(B6) - P_incorrect_internal(B5)
```

and its already-frozen one-sided non-inferiority decision remains unchanged.

---

## 2. H7 conditioning set

Use exactly the same paired F6 latent cases used for the frozen H7 analysis.

For each such latent case and each method `m in {B5, B6}`, define the already-frozen M10/H7 correct-censoring indicator:

```text
C_m(i) = 1  if method m is classified as correct censoring
         0  otherwise
```

Do not redefine correct censoring in this addendum.

The same latent-case set is used for B5 and B6, preserving pairing.

---

## 3. Marginal correct-censoring rates

Report the two method-specific point estimates:

```text
P_correct_B5 = mean(C_B5)
P_correct_B6 = mean(C_B6)
```

These are descriptive point estimates.

Do **not** attach separate marginal confidence intervals to these two rates for the frozen H7 supplemental report.

This avoids presenting unpaired marginal uncertainty where the frozen text specifically requests paired CIs.

---

## 4. Paired correct-censoring contrast

Define the paired case-level difference:

```text
d_correct(i) = C_B6(i) - C_B5(i)
```

and the aggregate paired contrast:

```text
D_correct =
P_correct_B6 - P_correct_B5
=
mean(d_correct)
```

The method order/sign is therefore frozen as:

```text
B6 - B5
```

Interpretation:

```text
D_correct > 0  -> higher correct-censoring rate for B6
D_correct = 0  -> equal correct-censoring rates
D_correct < 0  -> lower correct-censoring rate for B6
```

No sign reversal is permitted.

---

## 5. Paired confidence interval for D_correct

Use the v1.1 paired case-level bootstrap engine with exactly:

```text
10,000 resamples
```

and the already-frozen hypothesis/family seed machinery.

For the supplemental H7 correct-censoring contrast, use the same H7/F6 bootstrap stream as the primary H7 paired bootstrap quantities.

For each bootstrap resample, compute:

```text
D_correct* =
mean(C_B6* - C_B5*)
```

using the same resampled latent-case indices for both methods.

Report a **90% two-sided percentile bootstrap confidence interval**:

```text
lower = q(0.05)
upper = q(0.95)
```

with the v1.1 convention:

```python
np.quantile(values, q, method="linear")
```

Do not use:
- a 95% one-sided bound;
- a 95% two-sided interval;
- separate unpaired marginal-rate bootstrap intervals.

No rounding is applied before serialization or interpretation.

---

## 6. Relationship to the H7 verdict

The supplemental correct-censoring report is **descriptive only**.

It must report:

```text
P_correct_B5
P_correct_B6
D_correct = P_correct_B6 - P_correct_B5
D_correct_90CI = [q0.05, q0.95]
```

It must **not**:

- create a second H7 pass/fail criterion;
- modify the frozen `D_internal` non-inferiority verdict;
- override `SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE`;
- introduce a new alpha threshold;
- be Holm-adjusted;
- trigger permutation testing.

The only H7 mechanical verdict remains the one already frozen for `D_internal`.

---

## 7. Temporal/spatial reporting

If the existing frozen M10/H7 reporting structure already separates temporal and spatial F6 censoring summaries, retain those descriptive strata.

However:

- the canonical H7 supplemental `D_correct` above is computed on the exact overall paired H7 conditioning set;
- no additional stratum-specific hypothesis or verdict is created;
- stratum-specific correct-censoring values, if emitted, are descriptive only.

Do not invent new strata solely for this addendum.

---

## 8. Empty/undefined conditioning set

If the frozen H7 conditioning set is empty, or if the already-frozen upstream classification makes the requested H7 correct-censoring statistic undefined, do not silently substitute:

```text
0
NaN
empty CI
```

or drop the field.

Stop fail-closed as a new:

```text
SPEC_AMBIGUITY A5-XX
```

unless existing authority uniquely determines the representation.

---

## 9. Required A5-04 development tests

At minimum test:

1. `C_B5` and `C_B6` use the existing M10/H7 correct-censoring classification;
2. marginal rates are `mean(C_B5)` and `mean(C_B6)`;
3. `D_correct = P_correct_B6 - P_correct_B5`;
4. case-level paired difference is `C_B6 - C_B5`;
5. positive `D_correct` means B6 has higher correct-censoring rate;
6. the same latent-case indices are applied to B5 and B6 in every bootstrap resample;
7. exactly 10,000 paired bootstrap resamples are used;
8. the H7/F6 bootstrap stream is reused;
9. CI is exactly 90% two-sided percentile: q0.05/q0.95;
10. quantiles use `method="linear"`;
11. marginal B5/B6 rates have point estimates only in the canonical supplemental report;
12. no permutation p-value is generated for `D_correct`;
13. no Holm adjustment is generated for `D_correct`;
14. `D_correct` and its CI do not alter the primary H7 `D_internal` mechanical verdict;
15. input row order does not alter the paired H7 correct-censoring report after canonical rejoin/order.

---

## 10. A5-04 resolution state

```text
SPEC_AMBIGUITY_A5_04=RESOLVED

H7_PRIMARY_STATISTIC=
P_incorrect_internal(B6)-P_incorrect_internal(B5)

H7_PRIMARY_VERDICT_CHANGED=NO

H7_CORRECT_CENSOR_B5=
P_correct_censor(B5)

H7_CORRECT_CENSOR_B6=
P_correct_censor(B6)

H7_CORRECT_CENSOR_PAIRED_STATISTIC=
P_correct_censor(B6)-P_correct_censor(B5)

H7_CORRECT_CENSOR_SIGN=B6-B5

H7_CORRECT_CENSOR_CI=90_percent_two_sided_percentile_bootstrap
H7_CORRECT_CENSOR_CI_LOWER=q0.05
H7_CORRECT_CENSOR_CI_UPPER=q0.95
H7_CORRECT_CENSOR_QUANTILE_METHOD=linear

H7_CORRECT_CENSOR_MARGINAL_CI=NO
H7_CORRECT_CENSOR_PERMUTATION=NO
H7_CORRECT_CENSOR_HOLM=NO
H7_CORRECT_CENSOR_AFFECTS_VERDICT=NO

A5_SOURCE_EDIT_STARTED=NO
A5_TEST_EDIT_STARTED=NO

HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0

STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
```

---

## 11. Freeze rule

This file is additive authority for Stage 3A.5 implementation and must not be edited in place after its SHA-256 is recorded.

If another statistically or scientifically consequential implementation choice is not uniquely determined by frozen authority, coding must stop fail-closed as:

```text
SPEC_AMBIGUITY A5-XX
```

and return to Project Control before implementing that choice.
