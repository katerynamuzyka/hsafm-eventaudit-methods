# GENERATOR_SPEC_v1.1_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Control role:** Project Control II  
**Status:** APPROVED FOR STAGE 3A.3 DEVELOPMENT IMPLEMENTATION  
**Scope:** normative clarification of A3-01 through A3-05 only  
**Held-out execution:** NOT AUTHORIZED  
**Stage 3B / Stage 3C:** NOT AUTHORIZED  

## 1. Change-control status

The frozen file `GENERATOR_SPEC_v1_FROZEN_2026-10-02.md` remains byte-identical and must not be edited in place.

The Stage-3 v1 freeze requires a separately named version for any scientific-rule or mapping addition that can change benchmark behavior. This document therefore acts as the **v1.1 generator clarification addendum** for Stage 3A.3.

For A3 implementation, the effective generator authority is:

1. the existing frozen v1 scientific authority;
2. `STAGE3A3_IMPLEMENTATION_BRIEF_2026-10-03.md`;
3. this v1.1 clarification addendum.

This addendum has precedence **only** for the five underspecified items A3-01 through A3-05 below. It does not reopen or alter any other frozen v1 rule, threshold, family count, baseline rule, metric, or held-out restriction.

No held-out seed, case, manifest, serialization, execution, or unblinding is authorized by this document.

---

## 2. A3-01 — deterministic `above_frac` synthesis

### Normative rule

A3 uses a threshold-preserving record-level surrogate. It does **not** invent a pixel lattice or measured-pixel count.

For every method-visible frame:

```text
if measured_frac <= 0:
    above_frac = NaN
elif b5_peak < theta:
    above_frac = 0.0
else:
    above_frac = min_above_frac
```

With the frozen constants:

```text
theta = 1.0
min_above_frac = 0.05
```

Therefore, for any frame with measured support and `b5_peak >= theta`, the generated record has:

```text
above_frac = 0.05
```

exactly.

### Interpretation

- `above_frac` remains defined over measured support only.
- `measured_frac == 0` is the record-level surrogate for no measured pixels.
- This rule introduces no additional footprint-size, pixel-count, shape, or suprathreshold-area parameter.
- The rule preserves the frozen distinction:
  - `b5_peak < theta` → cannot be S;
  - `b5_peak >= theta`, no accepted component, valid support → satisfies the S threshold exactly.
- Noise is already applied to the scalar signal before this threshold-derived field is assigned.

No alternative graded mapping from `b5_peak` to `above_frac` is authorized in A3.

---

## 3. A3-02 — common-T0 accepted-detection construction

### 3.1 Clean template is constructed before family corruption

For each latent case, first construct a clean common-T0 template. Let `D` be the already selected inclusive accepted-frame span belonging to the case's frozen duration bin.

For an endpoint-targeted clean template with clean anchor `L0_clean`:

```text
accepted target-event T0 frames =
[L0_clean - D + 1, ..., L0_clean]
```

For an onset-targeted clean template:

```text
accepted target-event T0 frames =
[L0_clean, ..., L0_clean + D - 1]
```

On those clean accepted frames:

```text
t0_detection_state = existing A1 accepted-T0 representation
component_state = self
```

On all other clean-template frames, unless a frozen family rule explicitly overrides them:

```text
t0_detection_state = existing A1 non-accepted representation
component_state = none
```

The generator must use the already accepted A1 state representation/constants; it must not introduce a new public state vocabulary.

### 3.2 Default numerical/support state

Before a family-specific override:

- clean accepted target-event T0 frames use the frozen clean-present signal model;
- clean non-accepted frames use the frozen clean-absent signal model;
- support is valid:
  - `production_good = true`;
  - `secondary_qc_bad = false`;
  - `measured_frac = 1.0`;
  - `registration_supported = true`;
  - `movie_boundary = false`;
- `candidate_applied = false`.

Signal alone does **not** create or delete an accepted T0 detection. Accepted component ownership and `b5_peak` remain independent, as required by frozen v1.

### 3.3 What the duration bin constrains

The frozen duration bin constrains the **clean-template accepted-frame span `D`, before family corruption**.

Family corruption is then applied to that clean template.

The corrupted method-visible T0 span is allowed to differ from `D` only where the frozen family rules explicitly require or allow it. In particular:

- F1 X frames remove any target-event accepted T0 detection on those X frames;
- F2/F3/F4 presence-like constructions may contain the explicitly frozen accepted-self-component stratum despite failed support;
- F5 A/C interaction frames are competing/unowned components rather than accepted target-event self-components;
- F0b dropout frames have no accepted component as already frozen;
- F7 recurrence rules remain governed by their frozen family definition.

No other support flag may retroactively delete an already accepted T0 positive.

### 3.4 Method anchor

After all authorized family corruption has been applied, the common method anchor `L0` is derived from the **post-corruption method-visible accepted T0 detections**:

- endpoint: last accepted target-event T0 detection;
- onset: first accepted target-event T0 detection.

B1/B5/B5M/B6 consume that common post-corruption T0 identity/span. The clean anchor `L0_clean` and the pre-corruption span remain truth/construction-side only and are not exposed to methods.

---

## 4. A3-03 — exact F6 temporal-edge construction

### 4.1 Fixed raw movie and acquisition intervals

Raw movie frames remain:

```text
0..63
```

Use these deterministic acquisition-good intervals:

```text
FULL       = [0, 63]
LEFT_CUT   = [8, 63]
RIGHT_CUT  = [0, 55]
BOTH_CUT   = [8, 55]
```

Frames outside the applicable acquisition-good interval remain raw record rows but are marked:

```text
movie_boundary = true
```

and are not acquisition-good frames. To keep E isolated from lower-precedence evidence, those rows use neutral non-failure support fields:

```text
production_good = true
secondary_qc_bad = false
measured_frac = 1.0
registration_supported = true
component_state = none
t0_detection_state = non-accepted
b5_peak = 0.0
above_frac = 0.0
candidate_applied = false
```

`movie_boundary` has E precedence; the neutral values above must not be interpreted as observed support outside acquisition.

### 4.2 Internal control anchors

For non-target-side temporal controls use the symmetric internal anchors:

```text
endpoint internal anchor = 31
onset internal anchor    = 32
internal latent truth    = 31.5
```

These positions keep a maximum 20-frame clean accepted span and a 12-frame outward walk away from the opposite acquisition edge.

### 4.3 Construction table

| F6 edge type | Target side | first_good | last_good | post-corruption target anchor L0 | target latent truth | Expected temporal relation |
|---|---:|---:|---:|---:|---:|---|
| temporal-left | onset | 8 | 63 | 8 | 7.75 | target truth left of acquisition; immediate temporal censor |
| temporal-left | endpoint | 8 | 63 | 31 | 31.5 | target internal; left edge is non-target control |
| temporal-right | endpoint | 0 | 55 | 55 | 55.25 | target truth right of acquisition; immediate temporal censor |
| temporal-right | onset | 0 | 55 | 32 | 31.5 | target internal; right edge is non-target control |
| temporal-both | onset | 8 | 55 | 8 | 7.75 | target truth left of acquisition; immediate temporal censor |
| temporal-both | endpoint | 8 | 55 | 55 | 55.25 | target truth right of acquisition; immediate temporal censor |
| mixed temporal+spatial | onset | 8 | 63 | 8 | 7.75 | target-side temporal-left plus frozen spatial construction |
| mixed temporal+spatial | endpoint | 0 | 55 | 55 | 55.25 | target-side temporal-right plus frozen spatial construction |

For the four purely spatial F6 edge types (`spatial-top`, `spatial-bottom`, `spatial-left`, `spatial-right`) and `spatial-corner`, use `FULL = [0,63]` and the internal target anchors above; spatial behavior continues to be controlled by the frozen `edge_px` construction.

### 4.4 E placement

- If an endpoint target anchor equals `last_good`, B6 must take the already frozen **immediate temporal boundary** path before any outward code is consumed.
- If an onset target anchor equals `first_good`, B6 must take the same immediate path.
- For a non-immediate outward walk, the first raw frame outside `[first_good,last_good]` is an E frame by `movie_boundary = true`.
- No synthetic frame outside raw indices `0..63` is created.

This table intentionally preserves non-target temporal-edge controls. Metric M10's frozen wording “for F6 where truth lies outside the acquisition window” therefore applies to the target-side rows above, not automatically to every temporal-left/right cell.

---

## 5. A3-04 — exact F8 interaction-window construction

F8 is a one-frame, co-occurring interaction test. It does not introduce a new severity axis.

### 5.1 Placement

Use the standard internal anchors:

```text
endpoint L0 = 31
onset L0    = 32
```

The single F8 interaction frame is the **first outward raw frame**:

```text
endpoint: L0 + 1 = 32
onset:    L0 - 1 = 31
```

Interaction-window length:

```text
1 raw frame
```

The two immediately following outward frames are clean supported N frames. Thus, after the one interaction frame, the record contains at least two consecutive support-valid, no-component, below-threshold frames unless a separately authorized perturbation variant changes support.

### 5.2 Co-occurrence definitions

On the interaction frame:

#### X + U

```text
production_good = false
measured_frac = 0.25
secondary_qc_bad = false
registration_supported = true
component_state = none
target-event T0 detection = non-accepted
numerical mode = absence-like
```

#### Q + R

```text
production_good = true
secondary_qc_bad = true
measured_frac = 1.0
registration_supported = false
component_state = none
target-event T0 detection = non-accepted
numerical mode = absence-like
```

#### U + A

```text
production_good = true
secondary_qc_bad = false
measured_frac = 0.25
registration_supported = true
component_state = other
other_event_ids = exactly one opaque competing event ID
target-event T0 detection = non-accepted
numerical mode = presence-like
```

#### U + C

```text
production_good = true
secondary_qc_bad = false
measured_frac = 0.25
registration_supported = true
component_state = unowned
other_event_ids = empty
target-event T0 detection = non-accepted
numerical mode = presence-like
```

`candidate_applied = false` throughout.

The interaction conditions are genuinely simultaneous on the same raw frame; sequential placement is not authorized.

### 5.3 F8 noise allocation

The common two frozen noise strata are retained without creating a new F8 cell factor:

- endpoint: 6 cases at `sigma = 0` and 6 at `sigma = 0.15 theta` within each combination × duration cell;
- onset: 3 and 3 within each combination × duration cell.

This preserves the already frozen 12 endpoint / 6 onset allocation per F8 cell.

---

## 6. A3-05 — imperfect-support fraction-to-count rule

For each FN or FP selection step, let:

```text
N = number of eligible unique raw frames
r = requested rate in {0, 0.10, 0.25}
```

The selected-frame count is:

```text
n_select = floor(r * N + 0.5)
```

with the natural bounds:

```text
0 <= n_select <= N
```

Therefore exact half ties round **up**, not to even.

Examples:

```text
N=5, r=0.10 -> 1
N=2, r=0.25 -> 1
N=1, r=0.25 -> 0
N=0          -> 0
```

Selection is without replacement using the already authorized deterministic child seed.

### 6.1 FN unit

FN eligibility is counted by **unique raw frame**, not by support-axis instance.

If an FN-selected frame contains more than one true perturbable support failure, all true Q/U/R failures on that selected frame are cleared by the already frozen transforms. Example: an F8 `Q+R` frame selected for FN has both Q and R cleared.

X is never perturbable.

### 6.2 FP round-robin phase

After FP frame indices are selected without replacement, sort the selected raw frame indices in ascending order and assign perturbation type:

```text
Q, U, R, Q, U, R, ...
```

starting with Q.

This fixes the phase of the already frozen deterministic round-robin rule. The numerical signal and component state remain unchanged.

---

## 7. Required A3 tests added by this clarification

Before A3 can return to Project Control, add deterministic tests proving at least:

1. `above_frac` mapping exactly follows A3-01, including `measured_frac == 0`, subthreshold, and exact-threshold cases;
2. duration-bin span is measured on the pre-corruption clean T0 template;
3. post-corruption L0 is recomputed from common accepted T0 detections;
4. F1 X can remove accepted T0 detections but Q/U/R alone do not retroactively delete them;
5. all F6 table rows have the exact `first_good`, `last_good`, L0, truth time and immediate/non-immediate temporal behavior above;
6. F6 non-target temporal controls do not become target temporal censoring solely because the opposite movie edge exists;
7. F8 uses exactly one co-occurring interaction frame at the first outward frame;
8. F8 X+U, Q+R, U+A and U+C encode the exact simultaneous fields above;
9. F8 noise is 6/6 endpoint and 3/3 onset per combination × duration cell;
10. FN/FP selection count uses `floor(r*N + 0.5)`;
11. FP round-robin begins Q→U→R after ascending-frame sorting;
12. multi-axis FN operates on unique frames and clears all true perturbable failures on a selected frame;
13. inherited A1/A2 tests remain PASS;
14. no held-out seed/case path is created or executed.

---

## 8. Provenance and seed-manifest requirement

Do not modify the original frozen v1 hashes or manifest.

The A3 development seed manifest must add one field:

```text
generator_clarification_sha256 = <SHA-256 of this addendum>
```

alongside the already required frozen contract and generator-spec hashes.

The frozen development case-seed formula continues to use the unchanged frozen benchmark `contract_hash` exactly as specified. This addendum does not redefine that formula.

Any future held-out authorization must explicitly name and hash this addendum (or a later superseding generator-spec version) before a held-out seed or case may be generated.

---

## 9. Authorization state after this addendum

```text
STAGE3A3_ENTRY_GATE=PASS
A3_01_RESOLVED=YES
A3_02_RESOLVED=YES
A3_03_RESOLVED=YES
A3_04_RESOLVED=YES
A3_05_RESOLVED=YES
FROZEN_V1_FILES_CHANGED=NO
A3_DEVELOPMENT_CODING_MAY_RESUME=YES
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
NEXT=RESUME_STAGE3A3_DEVELOPMENT_ONLY
```

If implementation encounters any additional choice that can alter family membership, truth, T0 span, method-visible evidence, downstream method behavior, or perturbation exposure, it remains fail-closed and must return a new `SPEC_AMBIGUITY` to Project Control rather than infer a rule.
