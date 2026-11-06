# METRIC_SPEC_v1.3_A5_DURATION_CONSTRUCTION_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — Metrics & Mechanical Verdicts  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `METRIC_SPEC_v1_FROZEN_2026-10-02.md`  
**Related additive authority:**
- `METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`

**Purpose:** resolve `SPEC_AMBIGUITY A5-03` without editing frozen v1/v1.1/v1.2 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope and interpretation

This addendum resolves only the construction of the §4 duration metrics from:

- one frozen target-boundary outcome for the case;
- the same case's common detector-defined T0 accepted detections;
- the frozen target latent transition truth.

It does not create an unobserved opposite latent transition.

Accordingly, Stage-3A.5 §4 durations are:

> **target-boundary-relative track durations measured from the opposite common-T0 accepted-detection reference.**

They are not a claim of full latent biological event lifetime when the opposite biological boundary is not generated as truth.

This addendum does **not** change:
- common T0;
- B1–B6 outputs;
- generator truth;
- hit/miss/no-claim correctness;
- any H1A/H1B/H2–H7 rule;
- any frozen statistical convention;
- any held-out authorization.

---

## 2. Common opposite-side reference

Let the case's method-visible records be the same fixed common-T0 records supplied to the baselines.

Define accepted target-event T0 rows exactly by the already frozen predicate:

```python
row["t0_detection_state"] == "accepted"
```

Support flags do not delete an accepted T0 detection for this reference.

Let:

```text
A = sorted raw-frame indices of accepted target-event T0 detections
```

The common opposite-side reference is method-independent:

### Endpoint-targeted case

```text
t_ref = min(A)
```

That is, the first accepted target-event T0 detection.

### Onset-targeted case

```text
t_ref = max(A)
```

That is, the last accepted target-event T0 detection.

`t_ref` is a sampled detection time in raw-frame units. It is **not** converted
into an additional detector-adjacent boundary interval and is **not** replaced
by `L0_clean`, `D`, or another construction-only field.

The same `t_ref` is used for every baseline evaluated on that case.

If no accepted target-event T0 detection exists, this is an invariant failure;
do not invent a duration reference.

---

## 3. Frozen target truth and true duration

Let:

```text
T_truth = truth_record["latent_transition_time"]
```

in continuous raw-frame units.

### Endpoint-targeted case

```text
true_duration = T_truth - t_ref
```

### Onset-targeted case

```text
true_duration = t_ref - T_truth
```

Thus time reversal gives the same duration convention.

Do **not** use:
- the duration-bin label itself;
- inclusive clean span `D`;
- `l0_clean`;
- `l0_method`;

as substitutes for `true_duration`.

Those fields may be used for construction/invariant checks only.

---

## 4. Point-derived duration methods

For A5 duration purposes, the point-derived boundary methods are:

```text
B1
B2a
B2b
B3
B4a
B5
B5M
```

`B4b` is not a case-level boundary method and has no case-level point duration.

`B6` is an interval-duration method and is not converted to a primary point
duration.

For a point-derived method, a finite point duration exists iff:

```text
BaselineOutcome.status == "finite_claim"
AND
BaselineOutcome.anchor_frame is not None
```

Let:

```text
k = BaselineOutcome.anchor_frame
```

The point-duration estimate is:

### Endpoint-targeted case

```text
estimated_duration_point = k - t_ref
```

### Onset-targeted case

```text
estimated_duration_point = t_ref - k
```

Do not use the midpoint of `(L,R]` for these point-derived methods.

Their detector-adjacent finite boundary interval remains available for the
separate boundary hit/miss analysis, but the point-duration consequence uses
the method's accepted T0 anchor `k`.

Do not add `+1` for inclusive accepted-frame count. §4 durations are elapsed
continuous frame-time differences, not B4b's separate inclusive sampled
duration `t`.

Zero or negative finite point-duration estimates, if produced by a legal
finite method output, are retained as errors; do not drop or clip them.

---

## 5. Common finite-duration subset for point-method bias/MAE

For any reported point-method duration contrast, first declare the set of
point methods being jointly contrasted.

The common finite-duration subset is exactly:

```text
cases in the already frozen analysis conditioning set
for which every point method in that declared contrast set
has a finite point duration under §4
and the common t_ref is valid
```

No case is removed because its duration error is large, zero, or negative.

For the default Stage-3 core point-duration table, the declared point-method set is:

```text
{B1, B2a, B2b, B3, B4a, B5, B5M}
```

and the common finite-duration subset is the intersection across all seven.

If a separately frozen hypothesis/report explicitly names a smaller point-method
comparison, use the intersection of exactly that named set and state the set in
the output.

Bias and MAE on that common subset use the v1.2 convention:

```text
error = estimate - truth
bias  = mean(error)
MAE   = mean(abs(error))
```

---

## 6. Finite point-duration yield

For each point method separately:

```text
finite_point_duration_yield =
number of cases with finite point duration
/
number of cases in the already frozen duration-analysis conditioning set
with valid common t_ref
```

The common-subset restriction used for bias/MAE does not replace per-method
yield reporting.

A target `censored` or `no_claim` output has no finite point duration.

---

## 7. Interval-duration construction

For an interval-duration method with frozen target finite claim:

```text
T_target ∈ (L, R]
```

use the same case-level `t_ref`.

### 7.1 Endpoint-targeted case

Because:

```text
duration = T_target - t_ref
```

the duration interval is:

```text
(L - t_ref, R - t_ref]
```

Define numeric bounds:

```text
duration_lower = L - t_ref
duration_upper = R - t_ref
```

with:

```text
lower_open  = True
upper_closed = True
```

### 7.2 Onset-targeted case

Because:

```text
duration = t_ref - T_target
```

the transformed duration interval is:

```text
[t_ref - R, t_ref - L)
```

Define numeric bounds:

```text
duration_lower = t_ref - R
duration_upper = t_ref - L
```

with:

```text
lower_closed = True
upper_open   = True
```

The reversal of endpoint closure is intentional and follows exactly from the
monotone-decreasing transformation.

In both target directions:

```text
duration_interval_width = duration_upper - duration_lower = R - L
```

Do not round bounds before coverage or width calculations.

---

## 8. Duration-interval truth coverage

### Endpoint-targeted

Coverage is:

```text
duration_lower < true_duration <= duration_upper
```

Equivalently:

```text
L < T_truth <= R
```

### Onset-targeted

Coverage is:

```text
duration_lower <= true_duration < duration_upper
```

Equivalently, because the original target boundary claim remains `(L,R]`:

```text
L < T_truth <= R
```

The transformed interval's open/closed endpoints must therefore be respected;
do not replace either target direction by a fully closed interval solely for
convenience.

---

## 9. Midpoint-imputed interval duration sensitivity

For a finite target boundary interval `(L,R]`, define the target-boundary
midpoint numerically as:

```text
M = (L + R) / 2
```

The midpoint-imputed duration is:

### Endpoint-targeted

```text
estimated_duration_midpoint = M - t_ref
```

### Onset-targeted

```text
estimated_duration_midpoint = t_ref - M
```

Equivalently in either direction:

```text
estimated_duration_midpoint =
(duration_lower + duration_upper) / 2
```

This point estimate is **sensitivity only**, exactly as frozen v1 requires.

Its bias/MAE use the v1.2 sign convention:

```text
midpoint_error = midpoint_estimate - true_duration
```

No midpoint is created for censored or no-claim outputs.

---

## 10. Interval finite eligibility and yield

A finite duration interval exists iff:

```text
BaselineOutcome.status == "finite_claim"
AND
left_frame is not None
AND
right_frame is not None
AND
t_ref is valid
```

For B6, primary duration coverage/width are evaluated on B6's finite duration
intervals only.

For a target outcome:

```text
status == "censored"
```

there is no finite duration interval.

For:

```text
status == "no_claim"
```

there is no finite duration interval.

Neither is midpoint-imputed.

For each interval method:

```text
finite_duration_interval_yield =
number of finite duration intervals
/
number of cases in the already frozen duration-analysis conditioning set
with valid common t_ref
```

Do not silently convert censoring to a finite bound for §4 interval coverage.

This addendum does not change the separate M10 acquisition-censoring analysis.

---

## 11. Truth isolation / execution ordering

The opposite reference `t_ref` is computed only from the same method-visible
common-T0 records and does not require the truth file.

Baseline execution remains:

```text
method-visible records
    -> fixed B1–B6 outputs
```

Only after outputs are fixed may A5 join:

```text
fixed outputs + t_ref + truth_record["latent_transition_time"]
    -> duration scoring
```

Truth must not flow backward into:
- accepted-T0 selection;
- `t_ref`;
- baseline execution;
- relinking;
- claim generation.

---

## 12. Worked symmetry check

For a clean four-detection span:

### Endpoint target

```text
accepted frames = 28,29,30,31
t_ref = 28
T_truth = 31.5
target claim = (31,32]
```

Then:

```text
true_duration = 3.5
point anchor duration = 31 - 28 = 3
duration interval = (3,4]
midpoint duration = 3.5
```

### Onset target

```text
accepted frames = 32,33,34,35
t_ref = 35
T_truth = 31.5
target claim = (31,32]
```

Then:

```text
true_duration = 3.5
point anchor duration = 35 - 32 = 3
duration interval = [3,4)
midpoint duration = 3.5
```

The endpoint/onset constructions are exact time reverses.

---

## 13. Required A5-03 development tests

At minimum test:

1. endpoint `t_ref = first accepted T0 frame`;
2. onset `t_ref = last accepted T0 frame`;
3. Q/U/R on an accepted row do not remove it from `t_ref`;
4. endpoint true duration = `T_truth - t_ref`;
5. onset true duration = `t_ref - T_truth`;
6. point methods use `anchor_frame`, not finite-claim midpoint;
7. no `+1` inclusive-count correction is added;
8. default point-method common subset is intersection across
   `B1/B2a/B2b/B3/B4a/B5/B5M`;
9. censored/no-claim point outputs have no finite point duration;
10. endpoint interval transforms `(L,R] -> (L-ref,R-ref]`;
11. onset interval transforms `(L,R] -> [ref-R,ref-L)`;
12. endpoint and onset truth-coverage endpoint inequalities are exact;
13. interval width equals `R-L`;
14. midpoint duration equals the arithmetic midpoint of duration bounds;
15. censored/no-claim interval outputs are not midpoint-imputed;
16. per-method finite yield uses the full frozen conditioning-set denominator,
    not the common bias/MAE subset;
17. zero/negative finite duration estimates are retained, not clipped/dropped;
18. endpoint/onset clean four-detection worked examples in §12 reproduce exactly;
19. truth-file absence still permits construction of `t_ref` and all baseline
    outputs before scoring.

---

## 14. A5-03 resolution state

```text
SPEC_AMBIGUITY_A5_03=RESOLVED

A5_DURATION_REFERENCE=opposite_common_T0_accepted_edge

ENDPOINT_REFERENCE=min_accepted_frame
ONSET_REFERENCE=max_accepted_frame

A5_TRUE_DURATION_ENDPOINT=T_truth-t_ref
A5_TRUE_DURATION_ONSET=t_ref-T_truth

A5_POINT_DURATION_ENDPOINT=anchor_frame-t_ref
A5_POINT_DURATION_ONSET=t_ref-anchor_frame
A5_POINT_DURATION_INCLUSIVE_PLUS_ONE=NO

A5_DEFAULT_POINT_COMMON_SUBSET=
intersection(B1,B2a,B2b,B3,B4a,B5,B5M finite durations)

A5_ENDPOINT_DURATION_INTERVAL=(L-t_ref,R-t_ref]
A5_ONSET_DURATION_INTERVAL=[t_ref-R,t_ref-L)

A5_MIDPOINT_DURATION_ENDPOINT=((L+R)/2)-t_ref
A5_MIDPOINT_DURATION_ONSET=t_ref-((L+R)/2)

A5_CENSORED_FINITE_DURATION=NO
A5_NOCLAIM_FINITE_DURATION=NO

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

## 15. Freeze rule

This file is additive authority for Stage 3A.5 implementation and must not be
edited in place after its SHA-256 is recorded.

If another statistically or scientifically consequential implementation choice
is not uniquely determined by frozen authority, coding must stop fail-closed as:

```text
SPEC_AMBIGUITY A5-XX
```

and return to Project Control before implementing that choice.
