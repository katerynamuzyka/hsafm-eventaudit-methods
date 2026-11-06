# GENERATOR_SPEC_v1.3_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Control role:** Project Control II  
**Status:** APPROVED FOR STAGE 3A.3 DEVELOPMENT IMPLEMENTATION  
**Scope:** normative clarification of `SPEC_AMBIGUITY A3-14` through `A3-22` only  
**Basis:** `STAGE3A3_SPEC_AMBIGUITY_AFTER_V1_2_2026-10-03.md`  
**Held-out execution:** NOT AUTHORIZED  
**Stage 3B / Stage 3C:** NOT AUTHORIZED  

## 1. Change-control status

The frozen v1 authority and both earlier A3 clarification addenda remain byte-identical and must not be edited in place.

This document is an additive **v1.3 A3 clarification addendum**. It has precedence only for A3-14 through A3-22. It does not reopen A3-01 through A3-13 and does not change any frozen scientific threshold, family count, baseline rule, metric rule, or held-out authorization.

For Stage 3A.3 development implementation, the effective generator authority is:

1. frozen v1 contract/spec authority;
2. `STAGE3A3_IMPLEMENTATION_BRIEF_2026-10-03.md`;
3. `GENERATOR_SPEC_v1.1_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`;
4. `GENERATOR_SPEC_v1.2_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03.md`;
5. this v1.3 addendum.

No held-out seed, held-out case, held-out manifest, scientific held-out execution, Stage 3B, or Stage 3C is authorized.

---

## 2. Canonical byte and child-seed conventions used by this addendum

For all new child-seed rules below:

```python
case_seed_bytes = int(case_seed).to_bytes(8, byteorder="big", signed=False)
```

A SHA-256 digest converted to a PCG64 seed uses:

```python
seed64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
rng = np.random.Generator(np.random.PCG64(seed64))
```

All textual tags introduced by this addendum are encoded as ASCII exactly as written.

No locale-dependent formatting is permitted.

---

## 3. A3-14 — support-perturbation child seed and deterministic sampling

The frozen formula remains:

```text
SHA256(case_seed || "support-perturb" || fn_rate || fp_rate)
```

### 3.1 Exact hash input

Render the four concatenated fields as:

```text
case_seed:
    exactly 8 unsigned big-endian bytes

literal tag:
    ASCII bytes b"support-perturb"

fn_rate token:
    0    -> ASCII b"0"
    0.10 -> ASCII b"0.10"
    0.25 -> ASCII b"0.25"

fp_rate token:
    same canonical tokens
```

No separators, whitespace, prefixes, signs, scientific notation, or trailing zero changes are added.

Thus:

```python
payload = (
    case_seed_bytes
    + b"support-perturb"
    + fn_rate_token
    + fp_rate_token
)
digest = hashlib.sha256(payload).digest()
support_seed = int.from_bytes(digest[:8], "big", signed=False)
support_rng = np.random.Generator(np.random.PCG64(support_seed))
```

### 3.2 Eligible-pool ordering

Before sampling:

```text
FN pool = unique eligible raw-frame indices sorted ascending
FP pool = unique eligible raw-frame indices sorted ascending
```

Eligibility itself remains as frozen by v1.1/v1.2.

### 3.3 Exact without-replacement primitive and call order

Use exactly two `Generator.permutation` calls, in this order:

```python
fn_order = support_rng.permutation(
    np.asarray(fn_pool_sorted, dtype=np.int64)
)
fp_order = support_rng.permutation(
    np.asarray(fp_pool_sorted, dtype=np.int64)
)
```

The calls are made in FN-then-FP order even when `n_select == 0`.

Selection is:

```python
fn_selected = sorted(int(x) for x in fn_order[:n_fn])
fp_selected = sorted(int(x) for x in fp_order[:n_fp])
```

The ascending re-sort after selection is canonical.

FP perturbation types are then assigned to `fp_selected` in the already frozen:

```text
Q, U, R, Q, U, R, ...
```

order.

No `choice`, Python `random`, set iteration, dictionary iteration, or implementation-dependent pool order is authorized.

---

## 4. A3-15 — complete deterministic case-randomness schedule

### 4.1 Base case RNG

The v1.2 rule remains unchanged:

```python
base_rng = np.random.Generator(np.random.PCG64(case_seed))
D = int(base_rng.integers(bin_low, bin_high + 1))
```

`D` is the first and **only** stochastic value drawn from `base_rng`.

After `D`, do not consume `base_rng` again.

### 4.2 Purpose-specific frame child streams

All remaining stochastic numerical values use independent purpose-specific child streams derived directly from `case_seed`.

For raw frame `f` in `0..63`, define:

```python
frame_token = f"{f:02d}".encode("ascii")

payload = (
    case_seed_bytes
    + b"\x00a3-purpose\x00"
    + purpose_tag
    + b"\x00"
    + frame_token
)
child_seed = int.from_bytes(
    hashlib.sha256(payload).digest()[:8],
    "big",
    signed=False,
)
rng = np.random.Generator(np.random.PCG64(child_seed))
```

Authorized `purpose_tag` values are exactly:

```text
b"signal-present"
b"signal-absent"
b"noise-z"
b"f2-measured"
```

### 4.3 Signal and noise draws

For every raw frame, the canonical potential draws are:

```python
present_base = rng_present.uniform(1.4, 2.0)
absent_base  = rng_absent.uniform(0.0, 0.4)
z            = rng_noise.standard_normal()
```

All are represented as `numpy.float64`.

The previously frozen semantic rule decides whether a frame uses the present or absent base draw.

Observed scalar signal is:

```python
b5_peak = base_signal + sigma * z
```

with no clipping or rounding before storage.

`above_frac` is then derived exactly by v1.1 A3-01.

### 4.4 F1/F3/F4 numerical modes

On F1/F3/F4 corrupted frames:

```text
presence-like -> use that frame's signal-present child draw
absence-like  -> use that frame's signal-absent child draw
```

The same frame's `noise-z` draw is used in either mode.

Outside the corrupted window, the clean case and its clean twin use the same frame child values.

### 4.5 F2 measured support

For each F2 corrupted raw frame, use that frame's `f2-measured` child stream and exactly one:

```python
rng_f2.uniform(low, high)
```

draw with the frozen severity interval:

```text
mild:         [0.40, 0.49]
intermediate: [0.20, 0.39]
severe:       [0.00, 0.19]
```

The generated value is stored as `numpy.float64` without rounding.

F2 presence-like/absence-like numerical signal uses the same signal/noise rule as §4.4.

### 4.6 Other families

F5 and F7b clean-present/clean-absent states use the same frame-local `signal-present`, `signal-absent`, and `noise-z` streams.

F6 and F8 use the same frame-local signal/noise streams wherever their already frozen state calls for present-like or absent-like numerical signal.

F0b mechanism frames are the sole exception and use the conditional stream specified in A3-18 below.

### 4.7 Clean twins and variants

A clean twin and every support-perturbation variant reuse:

- the same `case_seed`;
- the same `D`;
- the same purpose-specific child values.

A support perturbation may alter only the support fields already authorized by frozen v1/v1.1/v1.2. It must not redraw signal, noise, component state, `D`, or truth.

Because random values are keyed by purpose and raw frame, iteration order over frames, families, rows, twins, or variants must not change generated numerical values.

---

## 5. A3-16 — exact `true_event_presence_trajectory`

The trajectory contains exactly 64 booleans in raw-frame order `0..63`.

For target-event truth only:

### Endpoint-targeted case

```python
true_event_presence_trajectory[f] = bool(f < T_truth)
```

### Onset-targeted case

```python
true_event_presence_trajectory[f] = bool(f > T_truth)
```

The strict inequalities are normative.

Consequences:

- a transition exactly at an integer frame belongs to neither the endpoint-present sample at that integer nor the onset-present sample at the time-reversed integer;
- movie-boundary/support state does not alter latent presence truth;
- F1–F6, F7a and F8 use the same predicate with their already frozen `T_truth`.

### F7b exception/identity rule

For F7b, the same predicate is used for the **target event identity only**.

The same-site recurrent/counterpart retained event is a distinct identity and does not set the target event's presence trajectory to `true`.

Therefore:

- endpoint F7b target presence becomes false at/after its target endpoint according to `f < T_truth`;
- onset F7b target presence becomes true only according to `f > T_truth`;
- the separately frozen 1/2/3-frame true-absence and recurrent/counterpart assignment are recorded in their existing truth fields and must not be folded into target-event presence.

---

## 6. A3-17 — canonical A3 `t0_detection_state`

For records emitted by the Stage 3A.3 generator, the only authorized values are exactly:

```text
accepted
not_accepted
```

The canonical accepted-state predicate is exactly:

```python
row["t0_detection_state"] == "accepted"
```

Everything else is non-accepted.

The generator must not emit:

```text
accepted_anchor
observer_frame
```

or any other adapter/example vocabulary in `t0_detection_state`.

This clarification is generator-local. It does not rewrite accepted A1 adapter tests or historical example strings; A3 generation must normalize its own output to the two values above.

---

## 7. A3-18 — exact F0b-N / F0b-S numerical sampling

F0b mechanism-frame signal is generated by conditional rejection sampling from the corresponding frozen clean signal model plus the cell's frozen Gaussian-noise stratum.

### 7.1 Dedicated mechanism child stream

For the single F0b mechanism raw frame `f`, use:

```python
purpose_tag = (
    b"f0b-N" if mechanism == "N"
    else b"f0b-S"
)

payload = (
    case_seed_bytes
    + b"\x00a3-purpose\x00"
    + purpose_tag
    + b"\x00"
    + f"{f:02d}".encode("ascii")
)
seed64 = int.from_bytes(
    hashlib.sha256(payload).digest()[:8],
    "big",
    signed=False,
)
rng = np.random.Generator(np.random.PCG64(seed64))
```

### 7.2 F0b-N

Repeat sequentially from this one dedicated RNG:

```python
base = rng.uniform(0.0, 0.4)
z = rng.standard_normal()
candidate = base + sigma * z
```

Accept the first candidate satisfying:

```text
candidate < 1.0
```

Set:

```text
b5_peak = candidate
above_frac = 0.0
```

### 7.3 F0b-S

Repeat sequentially:

```python
base = rng.uniform(1.4, 2.0)
z = rng.standard_normal()
candidate = base + sigma * z
```

Accept the first candidate satisfying:

```text
candidate >= 1.0
```

Set:

```text
b5_peak = candidate
above_frac = 0.05
```

No clipping, threshold pinning, post-hoc replacement, or draw from the opposite clean distribution is authorized.

For `sigma = 0`, the first draw necessarily satisfies the mechanism threshold.

All non-mechanism F0b frames remain governed by F0/v1.2 A3-09 and the generic A3-15 frame child streams.

---

## 8. A3-19 — deterministic F6 noise and spatial-edge allocation

Define `r` as the zero-based replicate index **within one `(edge_type, duration_bin, target_side)` allocation**.

The replicate index resets to `0` independently for every such allocation.

### 8.1 Noise

Endpoint has 8 cases per cell:

```text
r = 0,1,2,3 -> sigma = 0
r = 4,5,6,7 -> sigma = 0.15 theta
```

Onset has 4 cases per cell:

```text
r = 0,1 -> sigma = 0
r = 2,3 -> sigma = 0.15 theta
```

This satisfies the frozen global family/target-side balance and fixes the exact placement.

### 8.2 `edge_px` for spatial and mixed F6 cases

For each spatial or mixed `(edge_type, duration_bin, target_side)` allocation:

```python
edge_px = 1 + (r % 3)
```

Thus:

```text
endpoint r=0..7: 1,2,3,1,2,3,1,2
onset    r=0..3: 1,2,3,1
```

The cycle resets independently for each target side and each edge-type × duration-bin cell.

Purely temporal F6 cases use the non-spatial default from A3-21 below.

---

## 9. A3-20 — onset accepted-self allocation for F2/F3/F4 presence-like cells

Apply this rule independently in every F2/F3/F4 **presence-like** cell.

### Endpoint

The already frozen 3/3 split within each noise stratum is implemented with zero-based replicate `r=0..5`:

```text
r = 0,1,2 -> accepted target T0 self-component
r = 3,4,5 -> no accepted self-component
```

### Onset

Each noise stratum has zero-based replicate `r=0..2`.

For `sigma = 0`:

```text
r = 0,1 -> accepted target T0 self-component
r = 2   -> no accepted self-component
```

For `sigma = 0.15 theta`:

```text
r = 0   -> accepted target T0 self-component
r = 1,2 -> no accepted self-component
```

Therefore each onset presence-like cell is exactly:

```text
3 accepted-self
3 no-self
```

while retaining the already frozen 3/3 noise split.

For accepted-self cases, apply the already frozen/v1.1 rule that Q/U/R failure does not retroactively delete the accepted T0 positive.

---

## 10. A3-21 — default non-spatial `edge_px`

The default non-spatial value is exactly:

```text
edge_px = 3
```

It is constant across all 64 raw rows of the case unless the case is an F6 spatial or mixed construction with an explicitly assigned `edge_px`.

Scope of default `edge_px = 3`:

- F0;
- F0b;
- F1;
- F2;
- F3;
- F4;
- F5;
- F7a;
- F7b;
- F8;
- F6 temporal-left;
- F6 temporal-right;
- F6 temporal-both.

For F6 spatial-top/bottom/left/right/corner and mixed temporal+spatial, use A3-19.

No frame-wise random `edge_px` is permitted.

---

## 11. A3-22 — clean-twin / perturbation-variant `case_id`

### 11.1 Base latent case

The base observation record retains the already frozen base:

```text
case_id = first_16_hex(
    SHA256(seed_manifest_hash || "case" || global_case_index)
)
```

This formula is not modified by v1.3.

### 11.2 Variants receive distinct opaque IDs

A materialized clean twin or support-perturbation variant must **not** reuse the base method-visible `case_id`.

Let:

```python
base_case_id_bytes = bytes.fromhex(base_case_id)
```

where `base_case_id` is the frozen 16-lowercase-hex-character ID.

Construct:

```python
variant_payload = (
    base_case_id_bytes
    + b"\x00variant\x00"
    + variant_descriptor
)
variant_case_id = hashlib.sha256(
    variant_payload
).hexdigest()[:16]
```

The emitted ID is lowercase hexadecimal and remains opaque.

### 11.3 Canonical variant descriptors

Clean twin:

```text
b"clean"
```

Support-perturbation variant:

```python
(
    b"support\x00fn="
    + fn_rate_token
    + b"\x00fp="
    + fp_rate_token
)
```

If a support-perturbation variant of a clean twin is explicitly materialized by the existing benchmark design:

```python
(
    b"clean-support\x00fn="
    + fn_rate_token
    + b"\x00fp="
    + fp_rate_token
)
```

No other descriptor is authorized without Project-Control clarification.

A separately materialized `fn=0, fp=0` support-grid member receives its own support-variant ID; it does not silently alias the base record.

### 11.4 Truth-only mapping and latent counts

Truth/provenance must retain the mapping from every variant ID to its base latent unit.

Variant materialization does **not** increase latent-case counts.

Method-visible records contain only their own opaque `case_id`; they do not receive:

- base global index;
- variant descriptor;
- clean-twin label;
- support-perturbation label.

### 11.5 Collision invariant

Before writing a materialized development set, all emitted base and variant `case_id` values must be unique.

Any collision is a deterministic hard failure; do not append semantic suffixes or silently regenerate IDs.

---

## 12. Required A3 tests added by v1.3

Before A3 can return to Project Control, deterministic tests must prove at least:

1. support child hash payload uses exactly 8-byte big-endian `case_seed`, the canonical rate tokens, and no separators;
2. digest-to-PCG64 conversion uses the first 8 digest bytes as unsigned big-endian;
3. FN and FP pools are ascending unique raw-frame indices;
4. support selection uses `Generator.permutation` in FN-then-FP order and the selected results are re-sorted ascending;
5. `D` is the only draw from the base case RNG;
6. all post-`D` signal/noise/F2 randomness is frame-and-purpose keyed and invariant to row iteration order;
7. clean twins and perturbation variants reuse identical non-corruption child values;
8. endpoint target truth is exactly `f < T_truth`; onset target truth is exactly `f > T_truth`;
9. F7b recurrent/counterpart identity does not set target-event presence true;
10. A3 emits only `accepted` / `not_accepted`, with exact accepted predicate equality to `accepted`;
11. F0b-N rejection sampling always returns `<1.0`; F0b-S always returns `>=1.0`; no clipping is used;
12. F6 noise assignment follows the exact replicate ranges in §8.1;
13. F6 spatial/mixed `edge_px` cycles exactly `1+(r%3)` and resets per cell/target side;
14. F2/F3/F4 onset presence-like self/none allocation is exactly 2/1 at sigma 0 and 1/2 at sigma 0.15;
15. default non-spatial `edge_px` is exactly 3 in all scoped families;
16. clean twins and support variants have distinct opaque IDs but map to one base latent unit in truth;
17. variant IDs are deterministic and collision-checked;
18. all inherited A1/A2 tests remain PASS;
19. all v1.1/v1.2 A3 clarification tests remain PASS;
20. no held-out seed/case/manifest/serialization/execution path is created.

---

## 13. Development provenance

Retain the existing clarification fields unchanged:

```text
generator_clarification_sha256 =
a51e48789c738fcefa24f8a476a99db085c823e107c066a023d81992549c1590

generator_clarification_v1_2_sha256 =
38700c1c5e9e39e5d40539e10793d72ca8765e117f78d615fe395e66f5d04a00
```

Add:

```text
generator_clarification_v1_3_sha256 =
<SHA-256 of this v1.3 addendum>
```

Do not modify the frozen v1 contract hash, generator-spec hash, or their existing seed formulas.

Any later held-out authorization must explicitly name and hash v1.1, v1.2 and v1.3, or a separately frozen cumulative generator specification that supersedes them, before any held-out seed/case generation is permitted.

---

## 14. Authorization state after this addendum

```text
STAGE3A3_ENTRY_GATE=PASS
A3_01_TO_A3_13_RESOLVED=YES
A3_14_RESOLVED=YES
A3_15_RESOLVED=YES
A3_16_RESOLVED=YES
A3_17_RESOLVED=YES
A3_18_RESOLVED=YES
A3_19_RESOLVED=YES
A3_20_RESOLVED=YES
A3_21_RESOLVED=YES
A3_22_RESOLVED=YES
FROZEN_V1_FILES_CHANGED=NO
V1_1_ADDENDUM_CHANGED=NO
V1_2_ADDENDUM_CHANGED=NO
A3_DEVELOPMENT_CODING_MAY_RESUME=YES
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0
STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
NEXT=RESUME_STAGE3A3_DEVELOPMENT_ONLY
```

If implementation encounters any additional choice that can alter latent truth, clean/post-corruption T0 span, method-visible numerical evidence, support-perturbation exposure, variant identity, decoy placement, family behavior, or downstream method behavior, it remains fail-closed and must return a new `SPEC_AMBIGUITY` to Project Control rather than infer a rule.
