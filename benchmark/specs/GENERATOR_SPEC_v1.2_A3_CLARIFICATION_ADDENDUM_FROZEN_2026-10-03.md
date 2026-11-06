# GENERATOR_SPEC_v1.2_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Control role:** Project Control II  
**Status:** APPROVED FOR STAGE 3A.3 DEVELOPMENT IMPLEMENTATION  
**Scope:** normative clarification of `SPEC_AMBIGUITY A3-06` through `A3-13` only  
**Basis:** `STAGE3A3_SPEC_AMBIGUITY_AFTER_V1_1_2026-10-03.md`  
**Held-out execution:** NOT AUTHORIZED  
**Stage 3B / Stage 3C:** NOT AUTHORIZED  

## 1. Change-control status

The following authorities remain byte-identical and must not be edited in place:

- `BOUNDARY_CONSEQUENCE_BENCHMARK_CONTRACT_v1_FROZEN_2026-10-02.md`
- `GENERATOR_SPEC_v1_FROZEN_2026-10-02.md`
- `BASELINE_SPEC_v1_FROZEN_2026-10-02.md`
- `METRIC_SPEC_v1_FROZEN_2026-10-02.md`
- `GENERATOR_SPEC_v1.1_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`

This document is an additive **v1.2 generator clarification addendum**. It has precedence only for A3-06 through A3-13. It does not reopen A3-01 through A3-05 or any other frozen rule.

For Stage 3A.3 development implementation, the effective authority is:

1. the frozen v1 contract/spec set;
2. `STAGE3A3_IMPLEMENTATION_BRIEF_2026-10-03.md`;
3. the v1.1 A3 clarification addendum;
4. this v1.2 A3 clarification addendum.

No held-out seed, held-out case, held-out manifest, scientific held-out execution, Stage 3B, or Stage 3C is authorized.

---

## 2. A3-06 — exact accepted-span `D` selection within each duration bin

The frozen duration bins remain:

```text
short  = {4, 5, 6}
medium = {7, 8, 9, 10, 11, 12}
long   = {13, 14, 15, 16, 17, 18, 19, 20}
```

For every base latent case, select one integer `D` by a **discrete uniform draw over the integers in the assigned frozen duration bin**.

Implementation rule:

```python
rng = np.random.Generator(np.random.PCG64(case_seed))
D = int(rng.integers(bin_low, bin_high + 1))
```

This `D` draw is the **first case-level random draw** from the case RNG before any frame-level clean-present, clean-absent, support-severity, or Gaussian-noise draw.

Normative consequences:

- `D` is shared by every clean twin and every support-perturbation variant of that latent case.
- The frozen exact allocation to the three **duration bins** remains mandatory.
- There is **no additional exact balancing requirement among the integer values inside a bin**.
- No cycling by replicate index, midpoint substitution, or family-specific fixed `D` is authorized.
- The selected `D` is truth/construction-side only and is not exposed to methods.

---

## 3. A3-07 — default internal clean anchors and default latent-transition placement

Unless a family-specific rule below overrides them, use:

```text
raw movie frames: 0..63

endpoint L0_clean = 31
onset    L0_clean = 32
```

The default target latent-transition time is the midpoint between the clean target anchor and the first target-outward raw frame:

```text
endpoint: T_truth = L0_clean + 0.5 = 31.5
onset:    T_truth = L0_clean - 0.5 = 31.5
```

This default applies to:

- F0;
- F0b;
- F5;
- F7b target boundary;
- F8;
- F6 purely spatial cases and non-target temporal-control rows already assigned the internal anchor by v1.1.

Explicit exceptions:

- F1–F4: latent transition is determined from the corruption window exactly as frozen v1 plus A3-08 below.
- F6 target-side temporal cases: use the exact v1.1 A3-03 construction table.
- F7a: use the exact offset rule in A3-12 below.

The method-visible `L0` remains the **post-corruption** common-T0 anchor under v1.1 §3.4. `L0_clean` and `T_truth` remain truth/construction-side fields.

---

## 4. A3-08 — absolute F1–F4 corruption-window placement

Let severity length be:

```text
mild         s = 1
intermediate s = 2
severe       s = 3
```

Use the default internal clean anchors from A3-07.

### 4.1 Endpoint construction

For endpoint `L0_clean = L`:

#### transition-before-window

```text
w0 = L + 1
w1 = L + s
T_truth = w0 - 0.25
```

#### transition-inside-window

```text
w0 = L - floor((s - 1) / 2)
w1 = w0 + s - 1
T_truth = midpoint([w0, w1 + 1))
        = (w0 + w1 + 1) / 2
```

#### transition-after-window

```text
w1 = L - 1
w0 = L - s
T_truth = w1 + 1.25
```

With `L=31`, these endpoint truth times stay in the detector-adjacent interval `(31,32]`.

### 4.2 Onset construction: exact raw-frame time reverse

For onset `L0_clean = L`:

#### transition-before-window

```text
w0 = L - s
w1 = L - 1
T_truth = w1 + 0.25
```

#### transition-inside-window

```text
w1 = L + floor((s - 1) / 2)
w0 = w1 - s + 1
T_truth = (w0 + w1 - 1) / 2
```

#### transition-after-window

```text
w0 = L + 1
w1 = L + s
T_truth = w0 - 1.25
```

This is the exact raw-frame time reverse of the endpoint construction under frame reversal `f -> 63-f`, with endpoint anchor 31 mapping to onset anchor 32.

### 4.3 Corruption application

Apply the frozen family-specific F1/F2/F3/F4 state to **every raw frame `w0..w1` inclusive**.

Then:

- F1 X frames remove target-event accepted T0 detections on those frames;
- F2/F3/F4 do not delete an already accepted target T0 detection merely because Q/U/R support fails;
- the already frozen presence-like accepted-self stratum may place/retain accepted target T0 detections on its corrupted frames;
- the clean twin uses the same `D`, `L0_clean`, `T_truth`, window coordinates and all non-corruption random draws, but does not apply the corruption state.

After corruption, recompute method-visible `L0` exactly as required by v1.1 §3.4.

No other absolute window placement is authorized.

---

## 5. A3-09 — F0/F0b target-outward construction

### 5.1 F0 supported reference

F0 is the unmodified clean template.

For target-outward frames, including the complete B5/B5M 5-frame target buffer and the complete B6 12-frame raw lookahead where those frames exist:

```text
target-event T0 detection = non-accepted
component_state = none
support axes = valid
numerical state = frozen clean-absent model
candidate_applied = false
```

`above_frac` is then derived by v1.1 A3-01.

No extra F0 target-outward mechanism state is inserted.

### 5.2 F0b mechanism extent

F0b modifies **exactly one raw frame**: the first target-outward frame.

```text
endpoint mechanism frame = L0_clean + 1 = 32
onset mechanism frame    = L0_clean - 1 = 31
```

On that one frame:

- support axes are valid;
- target-event T0 detection is non-accepted;
- `component_state = none`;
- F0b-N obeys the frozen below-threshold / `N` constraints;
- F0b-S obeys the frozen suprathreshold-unaccepted / `S` constraints;
- `candidate_applied = false`.

Beginning with the second target-outward frame, the record reverts to the F0 clean-reference construction.

Therefore the F0b mechanism persistence is:

```text
1 raw frame exactly
```

The target latent-transition time remains the A3-07 default midpoint unless another already frozen rule explicitly applies.

---

## 6. A3-10 — F5 competing-candidate extent and numerical signal

The primary F5 competing candidate occupies **exactly one raw frame**, the first target-outward frame:

```text
endpoint: L0_clean + 1 = 32
onset:    L0_clean - 1 = 31
```

On that frame:

### A ownership

```text
target-event T0 detection = non-accepted
component_state = other
other_event_ids = exactly one opaque competing retained-event ID
support axes = valid
numerical state = frozen clean-present signal model
candidate_applied = false
```

### C ownership

```text
target-event T0 detection = non-accepted
component_state = unowned
other_event_ids = empty
support axes = valid
numerical state = frozen clean-present signal model
candidate_applied = false
```

For both A and C:

- use the cell's already frozen noise stratum;
- apply Gaussian noise before threshold-derived fields;
- derive `above_frac` by v1.1 A3-01;
- the overlap-fraction factor `0.25 / 0.50 / 0.75` remains generator/truth-side construction and does not create a new method-visible field.

Beginning with the second target-outward frame, revert to the F0 clean-reference construction.

No multi-frame F5 candidate persistence is authorized in A3.

---

## 7. A3-11 — exact F7b true-absence / same-site-recurrence construction

Let the frozen sampled true-absence length be:

```text
A in {1, 2, 3} raw frames
```

Use the default internal anchors and default target truth time from A3-07.

The recurrent same-site event is a **different retained event identity** from the target event.

It uses one opaque recurrent event ID that is constant across all of its accepted recurrence frames.

### 7.1 Endpoint-targeted F7b

Target event:

```text
target clean accepted span ends at L0_clean = 31
target latent endpoint truth = 31.5
```

True-absence frames:

```text
L0_clean + 1 .. L0_clean + A
```

On every true-absence frame:

```text
target-event T0 detection = non-accepted
component_state = none
other_event_ids = empty
support axes = valid
numerical state = frozen clean-absent model
candidate_applied = false
```

The recurrent event begins at:

```text
R0 = L0_clean + A + 1
```

and persists on the same nominal K0 site through the remaining target-outward acquisition-good frames.

On every recurrent-event frame:

```text
target-event T0 detection = non-accepted
component_state = other
other_event_ids = [same opaque recurrent event ID]
support axes = valid
numerical state = frozen clean-present model
candidate_applied = false
```

The recurrent event is not added to the target event's T0 accepted span.

### 7.2 Onset-targeted F7b: exact time reverse

Target event:

```text
target clean accepted span begins at L0_clean = 32
target latent onset truth = 31.5
```

True-absence frames:

```text
L0_clean - A .. L0_clean - 1
```

The distinct same-site predecessor/recurrent-counterpart event occupies the target-outward frames before the absence:

```text
... .. L0_clean - A - 1
```

through the first acquisition-good frame.

On those counterpart-event frames:

```text
target-event T0 detection = non-accepted
component_state = other
other_event_ids = [same opaque counterpart event ID]
support axes = valid
numerical state = frozen clean-present model
candidate_applied = false
```

The `A` absence frames use the same clean-absent / no-component state specified above.

The target event itself begins at `L0_clean` and uses the v1.1 clean accepted-span construction.

### 7.3 Identity and signal semantics

For both target sides:

- recurrent/counterpart event ID is distinct from the target `t0_event_id`;
- the same nominal K0 site is truth-side geometry, not a new public method field;
- recurrence/counterpart signal uses the frozen clean-present distribution and the case's frozen noise stratum;
- absence signal uses the frozen clean-absent distribution and the same noise stratum;
- `above_frac` follows v1.1 A3-01;
- the frozen F7b noise split remains endpoint 12/12 and onset 6/6 per absence-length × duration cell.

This construction intentionally yields target-outward evidence of the form:

```text
endpoint: N-like absence frames -> A-type same-site recurrence
onset:    time-reversed N-like absence frames -> A-type prior counterpart
```

subject to the realized numerical threshold field on the clean-absent frames.

---

## 8. A3-12 — exact F7a offset mapping and noise allocation

Use:

```text
endpoint L0_clean = 31
onset    L0_clean = 32
```

For offset:

```text
delta in {0.25, 0.50, 0.75}
```

freeze latent truth as:

```text
endpoint: T_truth = L0_clean + delta
onset:    T_truth = L0_clean - delta
```

Thus the `delta = 0.50` stratum coincides with the default internal midpoint truth from A3-07.

Within every offset × duration-bin cell, noise is split exactly:

```text
endpoint: 6 cases sigma=0
          6 cases sigma=0.15 theta

onset:    3 cases sigma=0
          3 cases sigma=0.15 theta
```

No random or global-only F7a noise allocation is authorized.

---

## 9. A3-13 — FP eligibility and deterministic decoy tie-breaking

### 9.1 False-positive support eligibility

Construct the FP candidate pool from the **unperturbed truth/base record**, before applying either FN or FP transforms.

A raw frame is FP-eligible iff all are true:

```text
movie_boundary == false
production_good == true
secondary_qc_bad == false
measured_frac >= 0.50
registration_supported == true
```

Component and signal state do not restrict FP eligibility.

Therefore supported frames remain FP-eligible even when they contain:

- an accepted target self-component;
- `component_state = other`;
- `component_state = unowned`;
- suprathreshold signal.

True X/Q/U/R frames are not FP-eligible.

The FN pool and FP pool are defined independently from the unperturbed truth/base record and are therefore disjoint by true support state. A frame made apparently supported by an FN transform does **not** become FP-eligible in the same perturbation variant.

The already frozen v1.1 count rule and `Q -> U -> R` FP phase remain unchanged.

### 9.2 D1 midpoint tie

For D1:

1. take the first and last accepted target-event T0 frames in the record to which the decoy is applied;
2. define their arithmetic midpoint;
3. choose the accepted target-event T0 frame with minimum absolute distance to that midpoint.

If two accepted frames are equidistant, choose the one **toward the target anchor**:

```text
endpoint: larger raw-frame index
onset:    smaller raw-frame index
```

This is the exact target-side time-reversal-symmetric tie rule.

### 9.3 D2 edge-adjustment ordering

The nominal D2 position remains:

```text
endpoint: L0 + 3
onset:    L0 - 3
```

If deterministic inward adjustment is required to preserve the frozen “inside the 5-frame target-side B5 buffer” category, search target-side offsets in this exact order:

```text
3, 2, 4, 1, 5
```

For endpoint add the offset; for onset subtract it.

The first frame satisfying the already required D2 eligibility/category constraints is used.

No frame outside target-side offsets 1..5 may be substituted for D2.

### 9.4 D3 nearest-far-frame tie

For D3, eligible frames must satisfy:

- the FP/support-valid predicate in §9.1;
- `abs(frame - L0) >= 8`.

Search increasing distance:

```text
d = 8, 9, 10, ...
```

At each distance inspect the **target-outward** candidate first, then the target-inward candidate:

```text
endpoint: L0 + d, then L0 - d
onset:    L0 - d, then L0 + d
```

The first in-movie eligible frame is D3.

Thus an equidistant D3 tie is always resolved target-outward first.

### 9.5 No category-breaking fallback

If no eligible frame exists under the applicable D1/D2/D3 category-preserving rule, generation must fail closed with a deterministic generator-invariant error.

Do not silently substitute a frame from another decoy category.

Decoy adjustment metadata remains truth-only.

---

## 10. Required A3 tests added by v1.2

Before A3 can return to Project Control, add deterministic tests proving at least:

1. `D` is an integer inside the assigned bin, is drawn first from the PCG64 case RNG, and is reused by twins/perturbation variants.
2. No exact within-bin integer balancing is asserted beyond the frozen bin-level case allocation.
3. Default anchors are endpoint 31 / onset 32 and default truth is 31.5.
4. Every F1–F4 severity × transition-position cell has the exact endpoint/onset `w0,w1,T_truth` from §4.
5. F1 corruption can change post-corruption `L0` only through removal of accepted T0 detections on X frames; v1.1 post-corruption anchor recomputation remains in force.
6. F0b modifies exactly one first-outward frame and then reverts to F0.
7. F5 A/C occupies exactly one first-outward frame and uses clean-present numerical signal.
8. F7b absence frames are exactly 1/2/3, recurrence/counterpart identity differs from the target, and endpoint/onset constructions are exact time reverses.
9. F7a truth offsets use `+delta` endpoint / `-delta` onset and noise is exactly 6/6 or 3/3 per cell.
10. FP eligibility is computed from the unperturbed true support record and includes supported component-bearing frames.
11. Simultaneous FN and FP transforms use disjoint truth-defined pools; FN-cleared frames never enter the FP pool.
12. D1 ties resolve toward the target anchor.
13. D2 adjustment order is exactly `3,2,4,1,5`.
14. D3 ties resolve target-outward first at the smallest eligible distance >=8.
15. Missing category-preserving decoy resolution fails closed.
16. All inherited A1/A2 tests remain PASS.
17. All v1.1 A3-01…A3-05 tests remain PASS.
18. No held-out path, seed, case, manifest, serialization or execution is created.

---

## 11. Development seed-manifest provenance

Retain the v1.1 manifest requirement unchanged:

```text
generator_clarification_sha256 = a51e48789c738fcefa24f8a476a99db085c823e107c066a023d81992549c1590
```

and add one additional field:

```text
generator_clarification_v1_2_sha256 = <SHA-256 of this v1.2 addendum>
```

Do not replace the frozen v1 contract hash or v1 generator-spec hash in the existing seed formulas.

Any later held-out authorization must explicitly name and hash both clarification addenda, or a separately frozen cumulative generator-spec version that supersedes them, before any held-out seed/case generation is permitted.

---

## 12. Authorization state after this addendum

```text
STAGE3A3_ENTRY_GATE=PASS
A3_01_RESOLVED=YES
A3_02_RESOLVED=YES
A3_03_RESOLVED=YES
A3_04_RESOLVED=YES
A3_05_RESOLVED=YES
A3_06_RESOLVED=YES
A3_07_RESOLVED=YES
A3_08_RESOLVED=YES
A3_09_RESOLVED=YES
A3_10_RESOLVED=YES
A3_11_RESOLVED=YES
A3_12_RESOLVED=YES
A3_13_RESOLVED=YES
FROZEN_V1_FILES_CHANGED=NO
V1_1_ADDENDUM_CHANGED=NO
A3_DEVELOPMENT_CODING_MAY_RESUME=YES
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0
STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
NEXT=RESUME_STAGE3A3_DEVELOPMENT_ONLY
```

If implementation encounters any additional choice that can alter latent truth, clean or post-corruption T0 span, family behavior, method-visible evidence, decoy placement, support-perturbation exposure, or downstream method behavior, it remains fail-closed and must return a new `SPEC_AMBIGUITY` to Project Control rather than infer a rule.
