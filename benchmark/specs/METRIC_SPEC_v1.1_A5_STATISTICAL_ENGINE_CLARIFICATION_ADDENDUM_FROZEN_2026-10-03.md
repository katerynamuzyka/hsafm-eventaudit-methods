# METRIC_SPEC_v1.1_A5_STATISTICAL_ENGINE_CLARIFICATION_ADDENDUM_FROZEN_2026-10-03

**Project:** HS-AFM / EventAudit Stage 3  
**Phase:** Stage 3A.5 — Metrics & Mechanical Verdicts  
**Status:** FROZEN ADDITIVE CLARIFICATION FOR IMPLEMENTATION  
**Parent authority:** `METRIC_SPEC_v1_FROZEN_2026-10-02.md`  
**Purpose:** resolve `SPEC_AMBIGUITY A5-01` without editing frozen v1 in place  
**Held-out execution:** NOT AUTHORIZED

## 1. Scope

This addendum resolves only the deterministic numerical implementation of
`METRIC_SPEC_v1`, §9, “Paired inferential engine”.

It does **not** change:

- any hypothesis definition H1A/H1B/H2–H7;
- any effect-size sign convention;
- any numerical margin or alpha threshold;
- any conditioning set;
- any baseline or generator behavior;
- any held-out authorization;
- any Stage 3B/3C scope.

The frozen resampling counts remain:

```text
bootstrap resamples = 10,000
random-sign permutations = 10,000
```

The resampling unit remains the latent case and paired method outputs are always
resampled together.

---

## 2. Canonical identifier tokens for the inferential seed expressions

Use the exact frozen Stage-3 contract SHA-256 hexadecimal string:

```text
frozen_contract_hash =
86ee65277b917ca513ffc1a5754748384240456172d883bff40c83d2804493d4
```

Encode it as the **64 lowercase ASCII hexadecimal characters shown above**.
Do not decode it to 32 raw hash bytes.

Use these exact ASCII `hypothesis_id` tokens:

```text
H1A
H1B
H2
H3
H4
H5
H6
H7
```

Use these exact ASCII `family_id` tokens:

```text
H1A -> F0
H1B -> F0b

H2 -> F1, F2, F3, or F4
H3 -> F1, F2, F3, or F4
H4 -> F1, F2, F3, or F4

H5 -> F0+F0b

H6 -> F1, F2, F3, or F4

H7 -> F6
```

No whitespace, separators, NUL bytes, prefixes, suffixes, locale-dependent
rendering, or alternate case are added to these tokens.

For hypotheses with more than one statistic (for example H1A hit and miss,
or H3 hit and miss), the same hypothesis/family resampling stream is reused for
all statistics in that hypothesis/family. This preserves pairing and does not
create post-hoc statistic-specific seeds.

---

## 3. Exact seed payloads

### 3.1 Bootstrap

The frozen expression remains:

```text
uint64(
    SHA256(
        frozen_contract_hash
        || "metric-bootstrap"
        || hypothesis_id
        || family_id
    )[0:16]
)
```

Operationally:

```python
payload = (
    frozen_contract_hash.encode("ascii")
    + b"metric-bootstrap"
    + hypothesis_id.encode("ascii")
    + family_id.encode("ascii")
)
digest = hashlib.sha256(payload).digest()
seed64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
```

The frozen notation `[0:16]` therefore means the first **16 hexadecimal
characters** of the lowercase SHA-256 hex digest, interpreted as an unsigned
base-16 integer. This is exactly equivalent to interpreting the first 8 raw
digest bytes as unsigned big-endian.

### 3.2 Random-sign permutation

The frozen expression remains:

```text
SHA256(
    frozen_contract_hash
    || "metric-permutation"
    || hypothesis_id
    || family_id
)
```

Use the same digest-to-seed rule:

```python
payload = (
    frozen_contract_hash.encode("ascii")
    + b"metric-permutation"
    + hypothesis_id.encode("ascii")
    + family_id.encode("ascii")
)
digest = hashlib.sha256(payload).digest()
seed64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
```

No additional hash round is applied.

---

## 4. RNG primitive

For both bootstrap and random-sign permutation use exactly:

```python
rng = np.random.Generator(np.random.PCG64(seed64))
```

Do not use:

- Python `random`;
- `np.random.RandomState`;
- another NumPy bit generator;
- a platform entropy source;
- an unseeded generator.

Bootstrap and permutation use separate seed payload tags and therefore separate
fresh `Generator(PCG64)` instances.

---

## 5. Canonical latent-case order before stochastic inference

Within the already frozen hypothesis/family/condition set:

1. join paired method outputs by the frozen latent-case identity;
2. verify one paired record per required method per latent case;
3. order latent cases deterministically by ascending frozen base latent
   `case_id` (lowercase 16-hex-character identity);
4. only then construct the paired case-level contribution vectors.

Materialized clean/support variants do not become extra resampling units.
Where a variant is evaluated, it remains linked to its frozen base latent case.

Input row order must not alter bootstrap or permutation results.

No semantic family/severity information is inferred from the opaque `case_id`;
the ID is used only for deterministic rejoining and ordering.

---

## 6. Bootstrap sampling primitive

Let `n` be the number of latent cases in the frozen conditioning set.

Generate the complete resampling index matrix with one NumPy call:

```python
bootstrap_index = rng.integers(
    low=0,
    high=n,
    size=(10000, n),
    dtype=np.int64,
    endpoint=False,
)
```

Each row is one paired case-level bootstrap resample.

The same row of indices is applied to every method/statistic participating in
that hypothesis/family comparison.

No additional stratification is introduced.

The inferential statistic is recomputed from each resampled case-level vector;
do not resample already aggregated summary statistics.

---

## 7. Bootstrap confidence-interval convention

Use the **percentile bootstrap** only.

Do not use:

- basic/reverse-percentile intervals;
- BCa;
- studentized intervals;
- normal-approximation intervals.

Quantiles are computed using:

```python
np.quantile(values, q, method="linear")
```

with bootstrap replicate statistics represented as `float64`.

### 7.1 Paired 90% two-sided CI

Use directly:

```text
lower = q(0.05)
upper = q(0.95)
```

### 7.2 One-sided 95% lower bound

Use directly:

```text
lower_95 = q(0.05)
```

### 7.3 One-sided 95% upper bound

Use directly:

```text
upper_95 = q(0.95)
```

One-sided bounds are computed directly from the bootstrap replicate
distribution. They are **not** obtained by taking one endpoint of a separately
constructed two-sided 95% interval.

No rounding is applied before mechanical verdict comparisons.

If the frozen target statistic is undefined for the conditioning set or a
bootstrap replicate, do not silently drop/replace that replicate. Stop
fail-closed as a new `SPEC_AMBIGUITY A5-XX` unless an already frozen rule
uniquely determines handling.

---

## 8. Random-sign permutation primitive

For the frozen one-sided superiority tests, let:

```text
d_i
```

be the paired per-latent-case difference using the sign convention already
defined by the corresponding hypothesis.

Retain **all** latent cases, including cases with:

```text
d_i = 0
```

Zeros remain zero and remain in the denominator.

Let:

```python
d = np.asarray(d, dtype=np.float64)
T_obs = np.mean(d, dtype=np.float64)
```

Generate the complete sign matrix with one NumPy call:

```python
bits = rng.integers(
    low=0,
    high=2,
    size=(10000, n),
    dtype=np.int8,
    endpoint=False,
)
signs = 2 * bits.astype(np.int8) - 1
```

Thus:

```text
bit 0 -> sign -1
bit 1 -> sign +1
```

A sign is drawn even for zero differences; multiplying by zero leaves the
case contribution zero while keeping the RNG draw schedule independent of the
number of ties.

For each permutation:

```python
T_perm = np.mean(signs * d[None, :], axis=1, dtype=np.float64)
```

The frozen one-sided alternative is improvement/superiority in the **positive**
direction of the hypothesis-defined difference.

---

## 9. Permutation tail and Monte-Carlo p-value

Count equality in the upper tail:

```python
b = np.count_nonzero(T_perm >= T_obs)
```

With exactly:

```text
B = 10000
```

use the add-one Monte-Carlo convention:

```python
p_raw = (b + 1) / (B + 1)
```

Therefore the minimum attainable raw Monte-Carlo p-value is:

```text
1 / 10001
```

Do not use:

```text
b / B
```

Do not use a strict `>` tail.

If all paired differences are zero, the rule above yields `p_raw = 1`.

Mechanical significance remains exactly the frozen comparison:

```text
p < 0.05
```

Thus `p == 0.05` is not significant.

---

## 10. Holm adjustment across F1–F4

Where frozen v1 requires Holm correction, the family set is exactly:

```text
F1, F2, F3, F4
```

with:

```text
m = 4
```

Start from the four raw one-sided permutation p-values.

Sort by:

```text
(raw_p ascending, family order F1 < F2 < F3 < F4)
```

The family order is only the deterministic tie-break/serialization order; it
does not change equal raw p-values.

For sorted raw values:

```text
p_(1) <= p_(2) <= p_(3) <= p_(4)
```

compute:

```python
a1 = 4 * p_(1)
a2 = 3 * p_(2)
a3 = 2 * p_(3)
a4 = 1 * p_(4)

holm_(1) = min(1.0, a1)
holm_(2) = min(1.0, max(holm_(1), a2))
holm_(3) = min(1.0, max(holm_(2), a3))
holm_(4) = min(1.0, max(holm_(3), a4))
```

Map the adjusted values back to the original family identities and serialize
reported family results in:

```text
F1, F2, F3, F4
```

order.

Do not round p-values before Holm adjustment or verdict comparison.

Mechanical significance remains:

```text
Holm-adjusted p < 0.05
```

---

## 11. Required deterministic seed test vectors

The following vectors are normative implementation tests.

### H1A / F0 bootstrap

```text
payload ASCII =
86ee65277b917ca513ffc1a5754748384240456172d883bff40c83d2804493d4metric-bootstrapH1AF0

first 16 SHA-256 hex characters =
6004488bf55bfdc4

seed64 =
6918734693502025156
```

### H2 / F1 bootstrap

```text
first 16 SHA-256 hex characters =
457de6e09ab7e409

seed64 =
5007412213048665097
```

### H2 / F1 permutation

```text
first 16 SHA-256 hex characters =
2fe1a4b25e69ac92

seed64 =
3450219875537628306
```

### H5 / F0+F0b bootstrap

```text
first 16 SHA-256 hex characters =
44642575ff15bd14

seed64 =
4928105080971181332
```

### H6 / F1 permutation

```text
first 16 SHA-256 hex characters =
f7c2b39f31f3593c

seed64 =
17853029369169271100
```

### H7 / F6 bootstrap

```text
first 16 SHA-256 hex characters =
29d6d012dee15ae0

seed64 =
3014825780038425312
```

Any mismatch with these vectors is an implementation failure.

---

## 12. Required A5-01 development tests

At minimum test:

1. exact seed vectors above;
2. same seed -> identical bootstrap index matrix;
3. same seed -> identical permutation sign matrix;
4. input-row permutation -> unchanged paired inference after canonical rejoin/order;
5. zero differences retained and `all-zero -> p=1`;
6. equality uses `T_perm >= T_obs`;
7. Monte-Carlo formula is `(b+1)/(10001)`;
8. 90% percentile CI uses `q=.05/.95`, `method="linear"`;
9. one-sided 95% lower/upper use direct `.05/.95` quantiles;
10. Holm tie handling and map-back to F1/F2/F3/F4;
11. `p == 0.05` does not satisfy frozen `p < 0.05`;
12. no truth/family metadata flows backward into baseline execution.

---

## 13. A5-01 resolution state

```text
SPEC_AMBIGUITY_A5_01=RESOLVED

A5_STAT_RNG=NumPy_Generator_PCG64
A5_BOOTSTRAP_RESAMPLES=10000
A5_PERMUTATIONS=10000

A5_BOOTSTRAP_CI=percentile
A5_QUANTILE_METHOD=linear

A5_90_TWO_SIDED=(q0.05,q0.95)
A5_95_ONE_SIDED_LOWER=q0.05
A5_95_ONE_SIDED_UPPER=q0.95

A5_RANDOM_SIGN_ZERO_TREATMENT=retain
A5_PERMUTATION_TAIL=>=
A5_MONTE_CARLO_P=(b+1)/(B+1)

A5_HOLM_FAMILY_ORDER=F1,F2,F3,F4
A5_HOLM_ALPHA_COMPARISON=<0.05

A5_SOURCE_EDIT_STARTED=NO

HELD_OUT_EXECUTION_AUTHORIZED=NO
HELD_OUT_SEEDS_GENERATED=0
HELD_OUT_CASES_GENERATED=0
SCIENTIFIC_HELDOUT_EXECUTION=0

STAGE3B_STARTED=NO
STAGE3C_STARTED=NO
```

---

## 14. Freeze rule

This file is additive authority for Stage 3A.5 implementation and must not be
edited in place after its SHA-256 is recorded.

If another statistically or scientifically consequential implementation choice
is not uniquely determined by frozen authority, coding must stop fail-closed as:

```text
SPEC_AMBIGUITY A5-XX
```

and return to Project Control before implementing that choice.
