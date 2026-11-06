# METRIC_SPEC v1.6 — A5 M9 / M10-H7 / undefined-set clarification addendum

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — DEVELOPMENT-ONLY Metrics & Mechanical Verdicts  
**Date:** 2026-10-03  
**Status:** FROZEN ADDITIVE CLARIFICATION  
**Held-out execution authorized:** NO

This addendum resolves only:

- `SPEC_AMBIGUITY A5-06` — M9 canonical population and paired report schema;
- `SPEC_AMBIGUITY A5-07` — M10/H7 F6 acquisition-edge population and censoring correctness mapping;
- `SPEC_AMBIGUITY A5-08` — representation and handling of legitimate empty/undefined metric sets.

It does **not** modify any frozen v1 scientific file in place. It does **not** change the accepted A3 generator, accepted A4 baselines, B6 scientific logic, the v1.1 statistical engine, the v1.2 descriptive conventions, the v1.3 duration construction, the v1.4 H7 supplemental CI rule, or the v1.5 H1 method pair/sign.

No held-out seed, case, output, Stage 3B material, or Stage 3C material is authorized by this addendum.

---

## 1. Binding upstream authority

The following existing authority remains binding:

- `METRIC_SPEC_v1_FROZEN_2026-10-02.md`
- `GENERATOR_SPEC_v1_FROZEN_2026-10-02.md`
- `GENERATOR_SPEC_v1.1_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.3_A5_DURATION_CONSTRUCTION_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.4_A5_H7_CORRECT_CENSORING_REPORT_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.5_A5_H1_METHOD_PAIR_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`

Relevant accepted SHA-256 anchors:

```text
METRIC_SPEC_v1_FROZEN_2026-10-02.md
c987dd8bd85089665017227b3017fb37ec40b1b4b0756ced31d6a097762fae26

GENERATOR_SPEC_v1_FROZEN_2026-10-02.md
ae7c769c0668481433608914eb58f780de2ef1e163294093e789b618e43d9bb9

GENERATOR_SPEC_v1.1_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
a51e48789c738fcefa24f8a476a99db085c823e107c066a023d81992549c1590

METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
79e27aba6cbfff2756e71acd8849c3333670c2bf61fe8fd2a521b34af72c6a5c

METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
da59b89c019907565c2334e8719c947e063968d71ce8fdc2bede0c76ab451c53

METRIC_SPEC_v1.3_A5_DURATION_CONSTRUCTION_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
cca3aadb824afc51e6d241bb9bf4d91499ab0fcf11d078cda016e30adff61393

METRIC_SPEC_v1.4_A5_H7_CORRECT_CENSORING_REPORT_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
93a99cbec253233b5301726fee60ddcddae650eb2a2281cf7460b2f2bf3aab58

METRIC_SPEC_v1.5_A5_H1_METHOD_PAIR_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md
b65201fa2b41e77241c4d7aa0f991f2eb3b3af7f6c6ed845880f73f51f094345
```

The user-local pre-v1.6 diagnostic reproduction is accepted as the provenance basis for issuing this clarification:

```text
A5_PREIMPLEMENTATION_GATE=PASS
A5_PRE_IMPLEMENTATION_SPEC_COMPLETENESS=FAIL
INDEPENDENT_BLOCKERS=3
SPEC_AMBIGUITY A5-06
SPEC_AMBIGUITY A5-07
SPEC_AMBIGUITY A5-08
A5_SOURCE_EDIT_STARTED=NO
A5_TEST_EDIT_STARTED=NO
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_MATERIAL_TOUCHED=NO
```

User-local diagnostic manifest SHA-256:

```text
bd51f95a601b1e5ebb534297038edb8fdbde495bb50a71d9cb257d8307626e27
```

---

# 2. Resolution of SPEC_AMBIGUITY A5-06 — canonical M9 population and report schema

## 2.1 Canonical base-family scope

The canonical M9 3×3 false-negative / false-positive support-error grid is computed on **F1, F2, F3, and F4 only**.

The report is emitted:

1. separately for each family `F1`, `F2`, `F3`, `F4`; and
2. as an optional pooled descriptive summary over `F1+F2+F3+F4`.

The pooled summary is descriptive only and must not replace any family-specific H6 quantity or Holm-controlled result.

M9 does not silently extend the canonical 3×3 grid to `F0`, `F0b`, `F5`, `F6`, `F7a`, `F7b`, or `F8`.

## 2.2 Canonical 3×3 grid

Use exactly the frozen support-perturbation rates:

```text
FN ∈ {0, 0.10, 0.25}
FP ∈ {0, 0.10, 0.25}
```

forming exactly nine cells.

Each cell contains one variant per eligible base latent case from the canonical F1–F4 population.

The `(FN=0, FP=0)` cell is the canonical unperturbed reference for that same latent-case population.

If the generator representation exposes both a base record and a separately materialized `(0,0)` perturbation record for the same latent case, the case is counted **once**, not twice. The canonical identity key is the frozen base latent `case_id`.

No support-perturbation cell is re-generated in A5. A5 consumes the already accepted deterministic A3 variant materialization.

## 2.3 Pairing unit

Within every M9 stratum, pairing is by the same frozen base latent `case_id`.

No case multiplication is permitted from:

- repeated method evaluation;
- multiple report fields;
- clean-twin aliases;
- decoy aliases;
- bootstrap/permutation expansion.

The M9 descriptive denominator is therefore a latent-case denominator, not an output-row denominator.

## 2.4 Canonical methods

For each canonical 3×3 cell, evaluate exactly:

```text
B5
B5M
B6
```

using the accepted A4 common interface.

For each method report the marginal three-way rates:

```text
P(claim_hit)
P(claim_miss)
P(no_claim)
```

with the full cell denominator.

These three probabilities must sum to one up to floating-point representation.

## 2.5 Canonical paired contrasts

For each outcome indicator

```text
Y ∈ {claim_hit, claim_miss, no_claim}
```

also report the paired mean indicator differences:

```text
D_Y(B6-B5)   = mean(I_B6(Y)  - I_B5(Y))
D_Y(B5M-B5)  = mean(I_B5M(Y) - I_B5(Y))
D_Y(B6-B5M)  = mean(I_B6(Y)  - I_B5M(Y))
```

on the same latent cases in that grid cell.

These M9 pairwise contrasts are descriptive unless an already frozen H6 rule explicitly consumes one of them. This addendum creates no new hypothesis, no new alpha level, and no new multiplicity family.

## 2.6 Clean twins

A clean twin is not an additional population member.

Where an accepted A3 variant object retains a clean-twin reference, use it only to establish the same-case comparison/provenance relationship.

For canonical M9 counting:

```text
clean twin == the same base latent case represented by the (0,0) reference condition
```

and is not appended as an additional tenth cell or additional replicate.

## 2.7 D1 / D2 / D3 decoy variants

The frozen decoy placements `D1`, `D2`, and `D3` are reported under M9 as **three separate descriptive decoy strata** on the same canonical F1–F4 base latent-case population wherever that decoy variant is defined by the accepted A3 generator.

They are **not** crossed with the 3×3 FN/FP grid.

Therefore M9 contains:

```text
nine support-error grid cells
plus
three separate decoy strata: D1, D2, D3
```

not a `9 × 3` or `9 × 4` factorial expansion.

For each decoy stratum, use the same method set and same report schema as §2.4–2.5:

```text
B5, B5M, B6
P(claim_hit), P(claim_miss), P(no_claim)
D_Y(B6-B5), D_Y(B5M-B5), D_Y(B6-B5M)
```

where defined.

## 2.8 M8 inside M9

The standalone frozen M8 definition is not redefined.

Within M9, the phrase `M8 where defined` means:

For each 3×3 support-error cell, on the subset satisfying the already frozen M8/B5-eligibility predicate, report the M8-style joint event rate

```text
P(B5=claim_hit AND B6=no_claim | frozen M8/B5-eligible subset of that M9 cell)
```

as an **M9 descriptive field**.

For clarity:

- this field does not create a new standalone M8 hypothesis;
- it does not change the original M8 conditioning rule;
- D1/D2/D3 decoy strata do not enter standalone M8;
- if the M8-eligible subset of a cell is empty, use the undefined-set rule in §4.

## 2.9 H6 separation

H6 remains exactly the already frozen F1–F4 inferential analysis.

M9 is the full descriptive robustness report surrounding H6.

Nothing in this addendum changes:

- H6 direction/sign;
- H6 bootstrap/permutation stream;
- H6 family tokens;
- H6 Holm rule;
- H6 mechanical verdict rule.

---

# 3. Resolution of SPEC_AMBIGUITY A5-07 — M10/H7 F6 population and censoring correctness

## 3.1 Acquisition-edge truth predicate

Define, for each F6 latent case, the frozen temporal acquisition interval:

```text
[FULL_left, FULL_right]
```

from the accepted generator record/specification.

Define:

```text
temporal_truth_outside =
    (T_truth < FULL_left) OR (T_truth > FULL_right)
```

using the frozen continuous latent transition time.

This predicate, not the textual temporal edge-type label alone, determines target-side temporal inclusion.

This preserves the v1.1 generator clarification that non-target temporal controls do not automatically enter M10/H7.

## 3.2 Pure spatial acquisition-edge predicate

For a purely spatial F6 case with frozen edge type in:

```text
spatial-top
spatial-bottom
spatial-left
spatial-right
spatial-corner
```

define:

```text
spatial_truth_outside = (edge_px < SPATIAL_MARGIN_PX)
```

using the accepted B6 spatial margin.

For the accepted A3 generator values and accepted A4 B6 implementation:

```text
SPATIAL_MARGIN_PX = 2
```

therefore the canonical pure-spatial acquisition-edge H7 cases are exactly the pure-spatial cases with:

```text
edge_px = 1
```

Pure-spatial `edge_px = 2` and `edge_px = 3` cases are internal spatial controls and do not enter the primary H7 conditioning set.

They may be reported descriptively under M10 as spatial-edge controls.

## 3.3 Canonical H7 conditioning set

The canonical paired H7 F6 conditioning set is the union:

```text
H7_SET =
    {F6 cases with temporal_truth_outside}
    UNION
    {pure-spatial F6 cases with spatial_truth_outside}
```

Each base latent case enters at most once.

This includes target-side mixed temporal+spatial cases whenever `temporal_truth_outside` is true.

It excludes:

- non-target temporal controls for which `temporal_truth_outside` is false;
- pure-spatial `edge_px >= 2` controls;
- all non-F6 families.

The exact same latent-case set is used for B5 and B6.

## 3.4 Mixed temporal+spatial precedence

For a mixed temporal+spatial F6 case:

- if `temporal_truth_outside == true`, the primary H7 truth class is **temporal acquisition-edge**;
- spatial attributes remain available only as descriptive substrata;
- the case is not duplicated into a second spatial H7 observation.

Thus the primary H7 pairing unit remains one latent case.

This temporal precedence is chosen because the frozen F6 construction already places the target truth outside the temporal acquisition interval in the mixed target-side cases.

## 3.5 Primary H7 incorrect-internal indicator

For every case in `H7_SET` and method `m ∈ {B5, B6}`, define:

```text
I_internal_m = 1  iff  outcome_m.status == "finite_claim"
I_internal_m = 0  otherwise
```

on this acquisition-edge truth population.

Thus:

- any finite internal boundary claim is an incorrect internal finite claim;
- `censored` is not an incorrect internal finite claim;
- `no_claim` is not an incorrect internal finite claim.

The already frozen primary H7 statistic remains:

```text
D_internal =
    P(I_internal_B6 = 1)
    -
    P(I_internal_B5 = 1)
```

with its already frozen inferential and mechanical-verdict rules unchanged.

## 3.6 Paired correct-censoring indicator used by v1.4

For every case in `H7_SET` and method `m ∈ {B5, B6}`, define the common paired correct-censoring indicator:

```text
C_m = 1  iff  outcome_m.status == "censored"
C_m = 0  otherwise
```

This common endpoint is deliberately based on the censoring decision itself because the accepted common `BaselineOutcome` interface does not expose a common censor-type/side field for both B5 and B6.

The v1.4 supplemental statistic therefore remains:

```text
d_correct(case) = C_B6 - C_B5
D_correct       = mean(d_correct)
```

with the already frozen v1.4 10,000-replicate paired 90% two-sided percentile bootstrap CI.

No type-specific requirement is inserted into `C_m`.

## 3.7 M10 three-way acquisition-edge report

For each method on `H7_SET`, report mutually exclusive outcome classes:

```text
correct_censoring
incorrect_internal_finite_claim
other_no_claim
```

where:

```text
correct_censoring              := status == "censored"
incorrect_internal_finite_claim := status == "finite_claim"
other_no_claim                 := status == "no_claim"
```

These classes exhaust the accepted common A4 output status vocabulary on the M10/H7 set.

If a method emits a status outside the accepted common interface vocabulary, that is an invariant failure, not an undefined-set condition.

## 3.8 Spatial type/side report — no invented side classifier

The frozen v1 request to report spatial censoring type/side is operationalized as a **truth-stratified descriptive report**, not as a newly invented side-prediction task.

For pure-spatial F6 cases:

### B6

Report:

```text
spatial_type_correct_B6 =
    1 iff
    outcome_B6.status == "censored"
    AND outcome_B6.b6_decision.boundary == "spatial"
```

and report its rate separately by the frozen truth stratum:

```text
spatial-top
spatial-bottom
spatial-left
spatial-right
spatial-corner
```

The stratum label is explicitly named `truth_spatial_side` or `truth_spatial_edge_type`.

Do **not** serialize a `predicted_spatial_side`, because accepted B6 does not emit one.

### B5

B5 has no accepted censor-type/side field.

Therefore do not fabricate a B5 spatial type/side classification.

For B5, report only its common outcome rates:

```text
P(censored)
P(finite_claim)
P(no_claim)
```

stratified by the same truth spatial edge type.

Any field that would require a B5 predicted spatial type or predicted spatial side must be represented as:

```text
status = "not_observable_from_accepted_method_output"
value  = null
```

and must not be imputed from truth.

## 3.9 Pure-spatial internal controls

Pure-spatial F6 cases with:

```text
edge_px ∈ {2, 3}
```

are not part of `H7_SET`.

They are descriptive M10 controls only.

For these controls report the same common outcome rates by edge type and edge_px, but do not include them in:

- `D_internal`;
- `P_correct_B5`;
- `P_correct_B6`;
- `D_correct`;
- any H7 bootstrap;
- the H7 mechanical verdict.

## 3.10 No duplicate mixed-case reporting in the H7 primary statistic

A mixed temporal+spatial case may appear in descriptive M10 substrata, but it contributes exactly one paired observation to the primary H7 set and is governed by the temporal precedence in §3.4.

---

# 4. Resolution of SPEC_AMBIGUITY A5-08 — empty/undefined metric sets

## 4.1 General serialization rule

A legitimate empty conditioning/subset is **not** a coding error.

Do not represent a legitimate undefined metric as:

```text
0
NaN
Infinity
missing key
silently dropped row
```

Every scalar metric that can become undefined must carry at least:

```text
status
n
value
```

where `value` is JSON `null` when undefined.

For ratio/proportion metrics also carry:

```text
numerator
denominator
```

when applicable.

For defined metrics:

```text
status = "defined"
value  = finite numeric value
```

## 4.2 Required undefined status vocabulary

Use exactly these status tokens where applicable:

```text
undefined_empty_conditioning_set
undefined_zero_finite_claims
undefined_empty_hit_subset
undefined_empty_miss_subset
undefined_empty_common_finite_duration_subset
undefined_inferential_target
not_observable_from_accepted_method_output
```

A more specific token above takes precedence over the generic
`undefined_empty_conditioning_set`.

## 4.3 Conditional finite-claim rates

For:

```text
P(hit | finite claim)
P(miss | finite claim)
```

if the number of finite claims is zero:

```text
status      = "undefined_zero_finite_claims"
denominator = 0
value       = null
```

Do not substitute zero.

If the denominator is positive and the numerator is zero, the defined value is exactly `0.0`.

## 4.4 Hit/miss interval-informativeness subsets

If the finite-hit interval subset is empty, all hit-only width summaries are undefined with:

```text
status = "undefined_empty_hit_subset"
n      = 0
```

and numeric summary fields:

```text
median
q1
q3
iqr
fraction_width_le_1
fraction_width_le_2
```

are `null`.

Use the analogous rule and status:

```text
undefined_empty_miss_subset
```

for an empty finite-miss interval subset.

No fallback to the combined finite-claim distribution is permitted.

## 4.5 Empty common finite-duration subset

If the already frozen common finite-duration intersection is empty:

```text
status = "undefined_empty_common_finite_duration_subset"
n      = 0
```

and the required common-subset:

```text
signed_bias
MAE
```

values are `null`.

This does not make each method's already defined finite-duration yield undefined. Finite-duration yield remains computed on its already frozen full conditioning denominator when that denominator is non-empty.

## 4.6 Empty M8-eligible subset inside an M9 cell

If the frozen M8/B5-eligible subset of an M9 grid cell is empty:

```text
status      = "undefined_empty_conditioning_set"
denominator = 0
value       = null
```

for the M9 `m8_joint_rate` field.

The other full-cell M9 three-way rates remain defined if the full cell denominator is positive.

## 4.7 Empty H7 set or undefined paired H7 target

If the canonical H7 conditioning set is empty, or a required H7 paired target is legitimately undefined after applying this addendum:

- do not run a bootstrap/permutation for that undefined target;
- emit the relevant estimate/CI fields as `null`;
- emit `status = "undefined_inferential_target"`;
- set the affected mechanical verdict to:

```text
INCONCLUSIVE
```

with an explicit machine-readable reason.

This is not a `SUPPORTED` or `NOT_SUPPORTED` result.

## 4.8 Undefined hypothesis-family target generally

For any H1–H7 target that is legitimately undefined because its frozen conditioning set is empty:

```text
estimate = null
CI       = null
p_value  = null     # if a p-value is required
verdict  = "INCONCLUSIVE"
status   = "undefined_inferential_target"
```

Do not manufacture bootstrap replicates from an empty array.

Do not treat an undefined target as zero effect.

## 4.9 Holm-controlled F1–F4 families

Where an already frozen hypothesis requires Holm correction across the four families `F1–F4`:

- if all four raw p-values are defined, apply the already frozen Holm procedure unchanged;
- if one or more of the four required raw p-values is undefined, do not silently reduce `m` below 4;
- retain any individually defined raw p-values for transparency;
- set all Holm-adjusted p-values for that four-family hypothesis block to `null`;
- set the affected Holm-controlled hypothesis block verdict to `INCONCLUSIVE`;
- emit `status = "undefined_inferential_target"` and identify the undefined family/families.

This preserves the frozen multiplicity family instead of changing it post hoc.

## 4.10 Legitimate emptiness versus invariant failure

The structured undefined rules above apply only to a scientifically legitimate empty subset produced by already frozen conditioning.

The following remain hard failures:

- missing required case identifiers;
- malformed or duplicate pairing identities;
- impossible accepted status vocabulary;
- missing truth required by a metric that should exist;
- disagreement between supposedly paired latent-case keys;
- failure of accepted A3/A4 invariants;
- missing required frozen authority file;
- hash mismatch against frozen authority.

Such conditions must not be converted into an `undefined_*` metric.

---

# 5. Mechanical consequences of this clarification

This addendum resolves:

```text
SPEC_AMBIGUITY_A5_06=RESOLVED
SPEC_AMBIGUITY_A5_07=RESOLVED
SPEC_AMBIGUITY_A5_08=RESOLVED
```

subject to exact-byte admission of this file into canonical `00_CONTEXT_UPLOAD` and a post-v1.6 read-only completeness review.

It does not itself authorize the first A5 source/test edit until that post-v1.6 gate reports no remaining consequential specification ambiguity.

---

# 6. Required post-v1.6 gate

Before any A5 source or test edit:

1. verify the exact SHA-256 of this addendum;
2. copy it unchanged into canonical `00_CONTEXT_UPLOAD`;
3. re-run the inherited static contract preflight;
4. verify accepted A4 source/test identities remain exact;
5. verify `HELD_OUT_EXECUTION_AUTHORIZED=NO`;
6. perform a **v1.6-aware** read-only specification completeness review.

The pre-v1.6 completeness/blocker scripts are archival evidence and must not be used unchanged as the post-v1.6 decision engine if they have a hard-coded authority list ending at v1.5 or hard-coded A5-06/A5-07/A5-08 blockers.

No A5 implementation may begin unless the v1.6-aware review returns:

```text
A5_PRE_IMPLEMENTATION_SPEC_COMPLETENESS=PASS
```

If a new consequential ambiguity is found, stop fail-closed as a new `SPEC_AMBIGUITY A5-XX`.

---

# 7. Firewall

```text
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0
STAGE3B_AUTHORIZED=NO
STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
```

This addendum is DEVELOPMENT-ONLY authority for Stage 3A.5.
