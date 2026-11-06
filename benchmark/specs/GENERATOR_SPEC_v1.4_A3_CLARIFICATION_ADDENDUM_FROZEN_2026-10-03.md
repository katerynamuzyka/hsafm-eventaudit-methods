# GENERATOR_SPEC_v1.4_A3_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Control role:** Project Control II  
**Status:** APPROVED FOR STAGE 3A.3 DEVELOPMENT IMPLEMENTATION  
**Scope:** normative clarification of `SPEC_AMBIGUITY A3-23` only  
**Basis:** `STAGE3A3_SPEC_AMBIGUITY_AFTER_V1_3_2026-10-03.md`  
**Held-out execution:** NOT AUTHORIZED  
**Stage 3B / Stage 3C:** NOT AUTHORIZED  

## 1. Change-control status

Frozen v1 authority and A3 clarification addenda v1.1, v1.2 and v1.3 remain byte-identical.

This document is an additive **v1.4 A3 clarification addendum**. It has precedence only for A3-23. It does not reopen A3-01 through A3-22 and does not change any scientific threshold, family count, baseline rule, metric rule, or held-out authorization.

For F1–F4, duration bin is **not** an additional crossed cell factor. The frozen grid remains exactly:

```text
3 transition positions × 2 numerical modes × 3 severities = 18 cells
```

with:

```text
endpoint = 12 cases/cell
onset    = 6 cases/cell
```

The duration bin is assigned deterministically from the existing zero-based replicate index within each frozen 18-cell stratum.

---

## 2. A3-23 — exact F1–F4 replicate-to-duration mapping

Apply the following mapping independently to every F1, F2, F3 and F4 frozen cell.

The replicate index resets to zero inside each cell.

### 2.1 Endpoint: replicates `r = 0..11`

Noise assignment and duration bin are jointly fixed as:

| r | sigma | duration bin |
|---:|:---:|:---:|
| 0 | 0 | short |
| 1 | 0 | medium |
| 2 | 0 | long |
| 3 | 0 | short |
| 4 | 0 | medium |
| 5 | 0 | long |
| 6 | 0.15 theta | short |
| 7 | 0.15 theta | medium |
| 8 | 0.15 theta | long |
| 9 | 0.15 theta | short |
| 10 | 0.15 theta | medium |
| 11 | 0.15 theta | long |

Equivalent deterministic formula:

```python
if 0 <= r <= 5:
    sigma = 0.0
    j = r
elif 6 <= r <= 11:
    sigma = 0.15 * theta
    j = r - 6
else:
    raise GeneratorInvariantError

duration_bin = ("short", "medium", "long")[j % 3]
```

Therefore, within every endpoint F1–F4 cell:

```text
short / medium / long = 4 / 4 / 4
```

and within each noise stratum:

```text
short / medium / long = 2 / 2 / 2
```

### 2.2 Onset: replicates `r = 0..5`

Noise assignment and duration bin are jointly fixed as:

| r | sigma | duration bin |
|---:|:---:|:---:|
| 0 | 0 | short |
| 1 | 0 | medium |
| 2 | 0 | long |
| 3 | 0.15 theta | long |
| 4 | 0.15 theta | short |
| 5 | 0.15 theta | medium |

Equivalent deterministic formula:

```python
if 0 <= r <= 2:
    sigma = 0.0
    duration_bin = ("short", "medium", "long")[r]
elif 3 <= r <= 5:
    sigma = 0.15 * theta
    duration_bin = ("long", "short", "medium")[r - 3]
else:
    raise GeneratorInvariantError
```

Therefore, within every onset F1–F4 cell:

```text
short / medium / long = 2 / 2 / 2
```

and within each noise stratum:

```text
short / medium / long = 1 / 1 / 1
```

No other duration interleaving is authorized.

---

## 3. Relationship to v1.3 presence-like self/no-self allocation

The v1.3 A3-20 self/no-self rules remain unchanged.

### 3.1 Endpoint presence-like F2/F3/F4

Within each endpoint noise stratum, let local replicate index be `j = 0..5`.

v1.3 self state remains:

```text
j = 0,1,2 -> accepted-self
j = 3,4,5 -> no-self
```

Under the v1.4 duration mapping:

```text
j = 0 -> short  + self
j = 1 -> medium + self
j = 2 -> long   + self
j = 3 -> short  + no-self
j = 4 -> medium + no-self
j = 5 -> long   + no-self
```

Thus every endpoint `noise × duration` stratum contains exactly:

```text
1 self + 1 no-self
```

### 3.2 Onset presence-like F2/F3/F4

The v1.3 onset self state remains:

For `sigma = 0`:

```text
local j = 0,1 -> accepted-self
local j = 2   -> no-self
```

For `sigma = 0.15 theta`:

```text
local j = 0   -> accepted-self
local j = 1,2 -> no-self
```

Combined with the v1.4 duration mapping, the six onset replicates are:

| r | sigma | duration | self state |
|---:|:---:|:---:|:---:|
| 0 | 0 | short | self |
| 1 | 0 | medium | self |
| 2 | 0 | long | no-self |
| 3 | 0.15 theta | long | self |
| 4 | 0.15 theta | short | no-self |
| 5 | 0.15 theta | medium | no-self |

Therefore, after pooling the two noise strata, every onset duration bin contains exactly:

```text
1 self + 1 no-self
```

while each noise stratum still contains exactly one short, one medium and one long case.

This is the intended non-confounded joint allocation.

---

## 4. Interaction with `D`

After `duration_bin` is assigned by this addendum, select `D` exactly as already frozen by v1.2 A3-06:

```text
short  -> D drawn uniformly from {4,5,6}
medium -> D drawn uniformly from {7,8,9,10,11,12}
long   -> D drawn uniformly from {13,14,15,16,17,18,19,20}
```

The v1.2 requirement remains unchanged:

- `D` is the first case-level PCG64 draw;
- there is no exact balancing among integer `D` values inside a duration bin;
- twins and perturbation variants reuse the same base `D`.

The v1.4 mapping only determines the duration-bin label from the existing within-cell replicate index.

---

## 5. Enumeration invariant

Do not create new duration-crossed cells and do not reorder the canonical F1–F4 cell grid.

For each already enumerated frozen cell:

1. enumerate the existing replicate index `r`;
2. assign `sigma` and `duration_bin` using §2;
3. apply the already frozen/v1.3 self/no-self rule where applicable;
4. draw `D` under v1.2;
5. continue the cumulative generator authority.

Therefore the frozen latent count remains exactly:

```text
18 cells × (12 endpoint + 6 onset) = 324 latent cases per F1/F2/F3/F4 family
```

No duration-bin multiplication of the family count is permitted.

---

## 6. Required A3 tests added by v1.4

Before A3 returns to Project Control, add deterministic tests proving at least:

1. every endpoint F1–F4 cell has exactly `4 short / 4 medium / 4 long`;
2. each endpoint noise stratum has exactly `2 short / 2 medium / 2 long`;
3. every onset F1–F4 cell has exactly `2 short / 2 medium / 2 long`;
4. each onset noise stratum has exactly `1 short / 1 medium / 1 long`;
5. endpoint presence-like F2/F3/F4 has exactly `1 self + 1 no-self` within each `noise × duration` stratum;
6. onset presence-like F2/F3/F4 has exactly `1 self + 1 no-self` within each duration bin after pooling the two noise strata;
7. the exact endpoint and onset replicate tables in §2 are reproduced byte-for-byte by the canonical enumeration;
8. F1–F4 remain exactly 324 latent cases per family;
9. no duration-crossed 54-cell interpretation is created;
10. inherited A1/A2 tests and all v1.1–v1.3 clarification tests remain PASS;
11. no held-out seed/case/manifest/serialization/execution path is created.

---

## 7. Development provenance

Retain the existing v1.1, v1.2 and v1.3 clarification hash fields unchanged.

Add:

```text
generator_clarification_v1_4_sha256 =
<SHA-256 of this v1.4 addendum>
```

Do not modify the frozen v1 contract hash, generator-spec hash, or their seed formulas.

Any future held-out authorization must explicitly name and hash this v1.4 addendum, or a later cumulative frozen generator specification that supersedes it, before held-out generation can be permitted.

---

## 8. Authorization state after this addendum

```text
STAGE3A3_ENTRY_GATE=PASS
A3_01_TO_A3_22_RESOLVED=YES
A3_23_RESOLVED=YES
FROZEN_V1_FILES_CHANGED=NO
V1_1_ADDENDUM_CHANGED=NO
V1_2_ADDENDUM_CHANGED=NO
V1_3_ADDENDUM_CHANGED=NO
A3_DEVELOPMENT_CODING_MAY_RESUME=YES
HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0
STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
NEXT=RESUME_STAGE3A3_DEVELOPMENT_ONLY
```

If implementation encounters another unresolved choice that can alter latent truth, duration assignment, clean/post-corruption T0 span, numerical evidence, support-perturbation exposure, variant identity, decoy placement, family behavior, or downstream method behavior, fail closed and return a new `SPEC_AMBIGUITY` to Project Control.
