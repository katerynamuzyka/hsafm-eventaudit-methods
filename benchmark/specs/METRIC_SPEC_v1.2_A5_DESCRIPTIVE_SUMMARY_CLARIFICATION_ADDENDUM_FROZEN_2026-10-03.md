# METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — Metrics & Mechanical Verdicts  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `METRIC_SPEC_v1_FROZEN_2026-10-02.md`  
**Related additive authority:** `METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`  
**Purpose:** resolve `SPEC_AMBIGUITY A5-02` without editing frozen v1 or v1.1 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope

This addendum resolves only:

1. the deterministic empirical-quantile convention for descriptive A5 summaries;
2. the sign and aggregation convention for descriptive signed duration bias and MAE.

It does **not** change:

- target-boundary hit/miss/no-claim definitions;
- conditioning sets;
- interval-width definitions;
- finite-duration subset definitions;
- any H1A/H1B/H2–H7 hypothesis;
- any frozen margin, alpha threshold, bootstrap count, permutation count, or verdict rule;
- any generator, T0, or B1–B6 semantics;
- any held-out authorization.

`METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
continues to govern the paired inferential engine.

---

## 2. Descriptive empirical quantiles

For **all A5 descriptive empirical quantiles** computed from a finite sample, use:

```python
np.quantile(values, q, method="linear")
```

with the input converted to `float64`.

This includes, where requested by frozen v1:

```text
median = q(0.50)
Q1     = q(0.25)
Q3     = q(0.75)
IQR    = Q3 - Q1
```

Therefore interval-informativeness summaries are computed exactly as:

```python
widths = np.asarray(widths, dtype=np.float64)

median_width = np.quantile(widths, 0.50, method="linear")
q1_width     = np.quantile(widths, 0.25, method="linear")
q3_width     = np.quantile(widths, 0.75, method="linear")
iqr_width    = q3_width - q1_width
```

The same descriptive quantile convention applies to any other A5 descriptive
median/quartile explicitly required by frozen v1.

Do not use another Hyndman-Fan/NumPy quantile method (`lower`, `higher`,
`midpoint`, `nearest`, etc.).

Do not round widths or quantiles before computing the IQR or before reporting
threshold-derived fractions.

This clarification does not alter v1.1's bootstrap percentile rule; it makes
the same `method="linear"` interpolation convention explicit for descriptive
empirical quantiles as well.

---

## 3. Signed duration error convention

For every finite case in a duration-summary conditioning set, define the signed
duration error as:

```text
error_i = estimated_duration_i - true_duration_i
```

Interpretation:

```text
positive error  -> duration overestimation
negative error  -> duration underestimation
zero            -> exact duration
```

The descriptive signed duration bias is the arithmetic mean of the case-level
signed errors:

```python
errors = np.asarray(estimated_duration, dtype=np.float64) \
       - np.asarray(true_duration, dtype=np.float64)

bias = np.mean(errors, dtype=np.float64)
```

Thus:

```text
BIAS = mean(estimate - truth)
```

Do not reverse the subtraction order.

---

## 4. Mean absolute error convention

For the same already-frozen common finite-duration subset:

```python
mae = np.mean(np.abs(errors), dtype=np.float64)
```

Thus:

```text
MAE = mean(abs(estimate - truth))
```

Bias and MAE must use the **same case subset** required by frozen v1 for that
duration comparison.

No case may be added or removed because of the sign or magnitude of its error.

---

## 5. Midpoint-imputed interval sensitivity

Where frozen v1 requests midpoint-imputed interval bias/MAE as a sensitivity
analysis, define the imputed duration estimate exactly from the already-frozen
interval midpoint construction, then apply the same signed-error convention:

```text
midpoint_error_i =
midpoint_imputed_duration_i - true_duration_i
```

and:

```text
midpoint_bias = mean(midpoint_error_i)
midpoint_MAE  = mean(abs(midpoint_error_i))
```

This remains a sensitivity analysis only and does not replace the primary
interval coverage/width analysis.

This addendum does not redefine how the interval midpoint itself is formed; if
that construction is not uniquely frozen by existing authority, coding must
fail closed as a new `SPEC_AMBIGUITY A5-XX`.

---

## 6. Fractions and rates

This clarification does not change fraction/rate definitions.

For interval informativeness:

```text
fraction_width_le_1 =
count(width <= 1 frame) / number_of_finite_claim_widths

fraction_width_le_2 =
count(width <= 2 frames) / number_of_finite_claim_widths
```

Use exact numerical comparisons to the already-frozen width values; do not
round widths before thresholding.

Hits and misses remain summarized separately where frozen v1 requires that
separation.

---

## 7. Empty or undefined descriptive sets

This addendum does **not** invent a new policy for an empty conditioning set or
an otherwise undefined requested metric.

If frozen v1 plus existing accepted authority does not uniquely determine the
representation/handling of an empty or undefined descriptive set, coding must
stop fail-closed as a new:

```text
SPEC_AMBIGUITY A5-XX
```

rather than silently using `0`, `NaN`, dropping the metric, or another fallback.

---

## 8. Required A5-02 development tests

At minimum add exact tests for:

1. descriptive median uses `np.quantile(..., 0.50, method="linear")`;
2. Q1 uses `q=0.25`, `method="linear"`;
3. Q3 uses `q=0.75`, `method="linear"`;
4. `IQR = Q3 - Q1`;
5. a sample where `linear` differs from `lower`/`higher`, proving the convention;
6. signed error is `estimate - truth`;
7. positive bias means overestimation;
8. negative bias means underestimation;
9. `bias = mean(estimate - truth)`;
10. `MAE = mean(abs(estimate - truth))`;
11. bias and MAE use the same frozen finite subset;
12. midpoint-sensitivity signed bias uses `midpoint_estimate - truth`;
13. width fractions use `<= 1` and `<= 2` without pre-rounding;
14. hit and miss interval-informativeness summaries remain separate.

---

## 9. A5-02 resolution state

```text
SPEC_AMBIGUITY_A5_02=RESOLVED

A5_DESCRIPTIVE_QUANTILE_METHOD=linear
A5_DESCRIPTIVE_MEDIAN=q0.50
A5_DESCRIPTIVE_Q1=q0.25
A5_DESCRIPTIVE_Q3=q0.75
A5_DESCRIPTIVE_IQR=Q3-Q1

A5_DURATION_SIGNED_ERROR=estimate-truth
A5_DURATION_BIAS=mean(estimate-truth)
A5_DURATION_MAE=mean(abs(estimate-truth))

A5_MIDPOINT_SENSITIVITY_SIGNED_ERROR=midpoint_estimate-truth

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

## 10. Freeze rule

This file is additive authority for Stage 3A.5 implementation and must not be
edited in place after its SHA-256 is recorded.

If another statistically or scientifically consequential implementation choice
is not uniquely determined by frozen authority, coding must stop fail-closed as:

```text
SPEC_AMBIGUITY A5-XX
```

and return to Project Control before implementing that choice.
