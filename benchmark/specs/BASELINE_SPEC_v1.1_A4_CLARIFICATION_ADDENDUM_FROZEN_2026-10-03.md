# BASELINE_SPEC_v1.1_A4_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.4 — benchmark baselines  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `BASELINE_SPEC_v1_FROZEN_2026-10-02.md`  
**Purpose:** resolve `SPEC_AMBIGUITY A4-01` without editing frozen v1 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope

This addendum resolves only the operational meaning of **B2a/B2b “missing usable detection”** for non-accepted Q/U/R frames.

It does not change:
- common T0 semantics;
- B1, B3, B4a, B4b, B5, B5M, or B6 scientific rules;
- A3 generator semantics;
- any metric, hypothesis, statistical, or held-out rule.

## 2. A4-01 decision — B2 usable-miss predicate

For B2a/B2b, scan the existing raw-frame sequence in target-time order.

An existing raw frame contributes **one B2 missing usable detection** iff:

```text
production_good == true
AND
t0_detection_state != accepted
```

The following support states do **not** exclude a production-good non-accepted frame from the B2 miss count:

```text
secondary_qc_bad == true          # Q
measured_frac < 0.50              # U
registration_supported == false  # R
```

Therefore:

```text
Q treatment = COUNT
U treatment = COUNT
R treatment = COUNT
```

A production-excluded frame:

```text
production_good == false          # X
```

does not contribute to the B2 usable-miss count.

Therefore:

```text
X treatment = SKIP
```

X remains on the raw time axis exactly as frozen v1 requires.

## 3. Accepted detections

A frame with:

```text
t0_detection_state == accepted
```

is an accepted T0 detection for B2 gap handling.

Q/U/R support flags do not retroactively invalidate an already accepted T0 detection for B2.

This preserves B2a/B2b as alternate detector-gap comparators rather than support-conditioned baselines.

## 4. Gap budget and X interposition

B2a permits at most:

```text
1
```

counted missing usable detection between accepted detections of the bridged event.

B2b permits at most:

```text
2
```

counted missing usable detections.

Production-excluded X frames may lie between those frames without consuming the B2 gap budget.

Example:

```text
accepted -> nonaccepted production-good -> X -> accepted
```

contains one B2 missing usable detection and is bridgeable by B2a.

Example:

```text
accepted -> Q/nonaccepted -> U/nonaccepted -> accepted
```

contains two B2 missing usable detections and is bridgeable by B2b but not B2a.

## 5. Time direction

The predicate and gap-budget rule apply identically to endpoint and onset.

Onset is the exact time-reversed construction of endpoint.

## 6. Boundary claim

This clarification does not change frozen B2 claim mapping.

After bridging, the finite boundary claim remains:

```text
(t_k, t_{k+1}]
```

at the last accepted detection of the bridged event, with onset handled by exact time reversal.

Acquisition-boundary behavior remains governed by the already frozen baseline/time-axis rules. Non-existent frames are never counted as misses.

## 7. Rationale / architecture preservation

Frozen v1 explicitly identifies B2a/B2b as alternate **gap-handling comparators** and explicitly excludes only X from the usable-miss count.

Frozen v1 separately introduces a full support-valid predicate for B5M and support-conditioned evidence logic for B6.

Using Q/U/R to skip B2 misses would silently introduce support-conditioned behavior into B2 that is not part of its frozen role.

Accordingly, A4-01 freezes the narrow production-usable interpretation:

```text
production-good non-accepted frame = COUNT
production-excluded X frame        = SKIP
```

## 8. Implementation constraints

A4 implementation must add explicit development tests covering at least:

```text
accepted -> Q/nonaccepted -> accepted
accepted -> U/nonaccepted -> accepted
accepted -> R/nonaccepted -> accepted
accepted -> X -> accepted
accepted -> Q/nonaccepted -> U/nonaccepted -> accepted
accepted -> nonaccepted -> X -> nonaccepted -> accepted
```

for B2a/B2b as applicable, plus endpoint/onset time reversal.

No truth field may be used by B2.

## 9. Authorization state

```text
SPEC_AMBIGUITY_A4_01=RESOLVED
B2_Q_TREATMENT=COUNT
B2_U_TREATMENT=COUNT
B2_R_TREATMENT=COUNT
B2_X_TREATMENT=SKIP

A4_SOURCE_EDITS_AUTHORIZED=YES_DEVELOPMENT_ONLY
A5_AUTHORIZED=NO

HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0

STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
```

## 10. Freeze rule

This file is additive authority for Stage 3A.4 implementation and must not be edited in place after its SHA-256 is recorded.

Any further consequential ambiguity must fail closed as a new:

```text
SPEC_AMBIGUITY A4-XX
```

and return to Project Control before implementation.
