# METRIC_SPEC_v1.5_A5_H1_METHOD_PAIR_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — Metrics & Mechanical Verdicts  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `METRIC_SPEC_v1_FROZEN_2026-10-02.md`  
**Related additive authority:**
- `METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.2_A5_DESCRIPTIVE_SUMMARY_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.3_A5_DURATION_CONSTRUCTION_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`
- `METRIC_SPEC_v1.4_A5_H7_CORRECT_CENSORING_REPORT_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`

**Purpose:** resolve `SPEC_AMBIGUITY A5-05` without editing frozen v1/v1.1/v1.2/v1.3/v1.4 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope

This addendum resolves only the H1A/H1B method pair and signed paired differences.

It does **not** change:
- F0 or F0b construction;
- the common B5-eligible conditioning set;
- the frozen H1 equivalence margins;
- the frozen 90% paired bootstrap CI rule;
- the H1 mechanical verdict logic;
- H2–H7;
- any generator or baseline behavior;
- any held-out authorization.

## 2. Scientific role of H1

H1 is the clean/support-valid reference-equivalence control between:

```text
B6
```

and the frozen Aguet-inspired reference baseline:

```text
B5
```

This choice is fixed before any A5 implementation or benchmark result inspection.

`B5M` is **not** an H1 method. Its role is the support-masked B5 comparator used in H2 and in B6-vs-B5M contrasts.

## 3. H1A — F0 supported-reference equivalence

Conditioning set:

```text
F0 target boundaries
AND common B5-eligible subset
```

Method pair:

```text
A = B6
B = B5
```

Signed paired differences:

```text
D_miss_H1A = P_miss(B6) - P_miss(B5)
D_hit_H1A  = P_hit(B6)  - P_hit(B5)
```

The frozen symmetric equivalence margins remain:

```text
miss: [-0.03, +0.03]
hit:  [-0.05, +0.05]
```

Use the frozen paired 90% bootstrap CI for each signed difference.

Mechanical verdict remains exactly frozen v1:

- `SUPPORTED` only if both paired 90% CIs lie entirely within their corresponding equivalence intervals;
- `NOT_SUPPORTED` if either paired 90% CI lies entirely outside its corresponding equivalence interval;
- otherwise `INCONCLUSIVE`.

## 4. H1B — F0b supported-dropout equivalence

Conditioning set:

```text
F0b target boundaries
AND common B5-eligible subset
```

Use the **same method pair and sign convention** as H1A:

```text
D_miss_H1B = P_miss(B6) - P_miss(B5)
D_hit_H1B  = P_hit(B6)  - P_hit(B5)
```

Use the same frozen margins and mechanical verdict rules as H1A.

No B5M term enters H1B.

## 5. F0b-N / F0b-S descriptive subreports

F0b-N and F0b-S remain descriptive subreports only.

For each mechanism stratum, report at minimum the marginal three-way rates for B5 and B6:

```text
P_hit
P_miss
P_no_claim
```

If paired H1-style differences/CIs are emitted descriptively, they must use the same pair and sign:

```text
D_miss = P_miss(B6) - P_miss(B5)
D_hit  = P_hit(B6)  - P_hit(B5)
```

and the same paired 90% bootstrap machinery.

These descriptive subreports:
- do not create replacement hypotheses;
- do not create separate H1 verdicts;
- do not alter H1B's overall F0b verdict.

## 6. Pairing and conditioning

For H1A/H1B:
- pair by the same frozen latent case identity;
- resample the paired B6/B5 outputs together;
- use only the common B5-eligible subset already frozen by v1;
- do not condition on observed method success/failure after the fact;
- do not drop no-claim cases from the three-way rate denominator unless frozen v1 already requires a finite-claim conditional rate separately.

The H1 paired differences are differences of rates over the same paired conditioning set.

## 7. Required A5-05 development tests

At minimum test:

1. H1A pair is exactly `B6` vs `B5`;
2. H1B pair is exactly `B6` vs `B5`;
3. `B5M` is rejected if supplied as an H1 method;
4. `D_miss = P_miss(B6) - P_miss(B5)`;
5. `D_hit = P_hit(B6) - P_hit(B5)`;
6. reversing the method order changes the signed estimate and is therefore not accepted as canonical serialization;
7. H1A uses F0 only;
8. H1B uses F0b only;
9. both use the common B5-eligible subset;
10. H1A/H1B use paired 90% bootstrap CIs;
11. miss equivalence interval is exactly `[-0.03,+0.03]`;
12. hit equivalence interval is exactly `[-0.05,+0.05]`;
13. F0b-N and F0b-S descriptive differences, if emitted, use `B6-B5`;
14. F0b-N/S do not generate replacement H1 verdicts;
15. H1 implementation does not alter H2–H7 method-pair definitions.

## 8. A5-05 resolution state

```text
SPEC_AMBIGUITY_A5_05=RESOLVED

H1A_FAMILY=F0
H1B_FAMILY=F0b

H1_METHOD_A=B6
H1_METHOD_B=B5

H1_D_MISS=P_miss(B6)-P_miss(B5)
H1_D_HIT=P_hit(B6)-P_hit(B5)

H1_COMMON_SUBSET=B5_ELIGIBLE
H1_BOOTSTRAP_CI=90_percent_two_sided_paired

H1_MISS_EQUIVALENCE_MARGIN=plus_minus_0.03
H1_HIT_EQUIVALENCE_MARGIN=plus_minus_0.05

H1B_N_S_DESCRIPTIVE_PAIR=B6_vs_B5
H1B_N_S_REPLACEMENT_HYPOTHESES=NO

A5_SOURCE_EDIT_STARTED=NO
A5_TEST_EDIT_STARTED=NO

HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0

STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
```

## 9. Freeze rule

This file is additive authority for Stage 3A.5 implementation and must not be edited in place after its SHA-256 is recorded.

If another statistically or scientifically consequential implementation choice is not uniquely determined by frozen authority, coding must stop fail-closed as:

```text
SPEC_AMBIGUITY A5-XX
```

and return to Project Control before implementing that choice.
