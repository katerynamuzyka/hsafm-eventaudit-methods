# BASELINE_SPEC_v1_FROZEN_2026-10-02
**Status:** FROZEN FOR IMPLEMENTATION — HELD-OUT EXECUTION NOT YET AUTHORIZED
**Parent:** `BASELINE_SPEC_v0.2_CANDIDATE_2026-10-02.md`

## 1. T0

Primary B1/B3/B4/B5/B5M/B6 consume common frozen detector-defined T0 event identities.

B2a/B2b are explicit alternate gap-handling comparators.

## 2. Time convention

Store continuous latent time separately from sampled frame index.

A sampled finite boundary claim is represented as `(L,R]`.

## 3. B1

End:
- last accepted T0 detection at frame k;
- finite claim `(t_k, t_{k+1}]` if next raw frame exists;
- otherwise right-censored.

Start is the time reverse.

## 4. B2a / B2b

- B2a bridges 1 missing usable detection.
- B2b bridges 2.

After bridging, the boundary claim is:
`(t_k, t_{k+1}]`
at the last accepted detection of the bridged event.

Excluded X frames remain on time axis and do not count as usable misses.

## 5. B3

At internal boundaries:
- same finite claim mapping as B1.

At temporal or spatial acquisition boundary:
- censor.

Internal support failure is not acquisition censoring.

## 6. B4a

`complete` =
- not temporally censored;
- not spatially/FOV censored.

At internal boundaries:
- B1 mapping.

## 7. B4b finite-window reference

Population-reference / sanity baseline only.

Use:
`p_complete(t) = (N - t + 1) / N`

with inclusive sampled duration t.

Unbuffered:
- `N = n`.

Buffered Aguet-style reference:
- `N = n - b_start - b_end`.

Exact Loerke Text-S1 algebra remains on citation hold.

## 8. B5 — Aguet-inspired buffer-validation on common T0

Exact label:
`Aguet-inspired buffer-validation post-processing baseline on common detector-defined tracks`.

Not a cmeAnalysis reproduction.

### 8.1 Minimum length
Minimum:
- 5 accepted T0 detections in the track.

If fewer:
- `no_claim:min_length`
for all B5/B5M hypothesis mappings.

H1 equivalence is evaluated on the common B5-eligible subset.

### 8.2 Target-side buffer
Boundary-level B5 validates the **target side only**:
- endpoint uses post buffer;
- onset uses pre buffer.

Required target-side buffer:
- all 5 raw buffer frames exist in movie.

Track-level both-side completeness is reserved for the separately frozen population annex.

### 8.3 Signal rule
B5 reads `b5_peak`.

Boundary validation requires:
- at least 2 consecutive buffer frames with `b5_peak < theta`;
- maximum of the full 5-frame target buffer < maximum `b5_peak` among accepted T0 detections in the track.

If passed, B5 does **not** widen the detector span.

Mapped finite claim:
- endpoint: `(t_L0, t_L0+1]`;
- onset: time reverse.

This is the frozen Stage-3 mapping of Aguet-style buffer validation.

### 8.4 B5 partial cases
If target-side 5-frame buffer cannot be calculated:
- acquisition edge → censored;
- otherwise `no_claim:partial`.

### 8.5 Explicit omissions relative to full cmeAnalysis
Core record-level B5 omits:
- u-track relinking;
- cmeAnalysis merge/split topology;
- gap-vs-sequential split logic (inert under the K0 core and common-T0 design);
- gap-structure validity rule;
- cohort-percentile filtering;
- compound-track simplification;
- Anderson–Darling residual-fit test;
- channel-specific intensity fitting/normalisation.

These omissions are explicit and prevent a false software-equivalence claim.

## 9. B5M — support-masked Aguet-inspired comparator

Same T0, minimum length, target-side 5-frame buffer and B5 signal rule.

### 9.1 Buffer support requirement
**All 5 target-side buffer frames must be support-valid.**

A buffer frame is support-valid only if:
- production_good = true;
- secondary_qc_bad = false;
- measured_frac >= 0.50;
- registration_supported = true.

Otherwise:
- `no_claim:partial_support`.

The 2-consecutive below-threshold test is never run on a subset of the 5-frame buffer.

### 9.2 Track maximum
For B5M:
- within-track maximum is calculated from accepted T0 detections whose own support state is valid.

If no supported accepted T0 detection exists:
- `no_claim:partial_support`.

### 9.3 Claim mapping
If validation passes:
- same mapped finite claim as B5:
  `(t_L0, t_L0+1]`
  or time reverse for onset.

B5M does not retain an interval across unsupported frames.

### 9.4 Decoy note
A predeclared D2 false support failure at anchor ±3 may invalidate B5M's 5-frame buffer after B6 has already achieved 2-N confirmation.

This is an explicit part of the C2 `B5M vs B6` bundle.

## 10. B6 — frozen-code-conformant record implementation

### 10.1 Non-exclusive evidence axes
Retain:
- production status;
- secondary QC;
- measured/source support;
- registration support;
- component/ownership state;
- suprathreshold signal;
- competing IDs;
- temporal boundary;
- spatial edge.

Final code/class is separate.

### 10.2 Exact frozen decision precedence
`E > X > Q > U > R > A > C > S > N`

### 10.3 Exact walk
- X/Q/U: gap=true; N-run=0; continue;
- R: `registration_limited`;
- A/C:
  - no prior X/Q/U gap → `assignment_ambiguous`;
  - prior gap → `candidate_reappearance`;
- S: `unresolved`;
- N: increment consecutive run;
- n_confirm=2:
  - no prior gap → `source_valid_negative`;
  - prior gap → `observability_limited`;
- E reached in walk → `boundary_censored`;
- lookahead exhausted with no decisive outcome → `unresolved`.

Raw-frame lookahead:
- 12 raw frame indices.

### 10.4 Immediate temporal boundary
Before the outward walk:
- endpoint anchor == last good frame → immediate temporal `boundary_censored`;
- onset anchor == first good frame → immediate temporal `boundary_censored`.

### 10.5 Spatial/FOV rule
Method-visible field:
- `edge_px`: distance in px from anchor footprint to detector-excluded border.

Evaluate on the anchor footprint as in frozen code.

If:
`edge_px < spatial_margin_px (=2)`

mark spatial boundary.

After provisional class:
override to `boundary_censored` only if provisional class is:
- source_valid_negative;
- observability_limited;
- unresolved.

Do not override:
- registration_limited;
- assignment_ambiguous;
- candidate_reappearance.

Frozen interval fields are absent after this spatial override.

### 10.6 Positive T0 detections
Do not delete/relink already accepted T0 positives because of support state.

### 10.7 Conformance target per field

**Exact equality with frozen `audit/evidence.py`:**
- per-frame decision code;
- final class;
- temporal-boundary behavior;
- spatial override behavior;
- interval fields when frozen code emits them.

**Declared additive Stage-3 extension:**
- retain competing/content evidence on an R-coded frame according to the frozen v0.2.2 invariant-#6 rule.

Frozen `audit/evidence.py` returns R before component overlap is computed and therefore does not itself export those overlap fields on R.

The additive fields:
- must never alter code/class;
- are validated against frozen axes-v0.2.2 invariant semantics.

## 11. Mandatory conformance suite

Records for conformance fixtures must be derived from the image fixtures' frozen observer quantities by a frozen extraction rule, not hand-written independently.

Required groups:

1. clean supported N confirmation;
2. X gap;
3. Q modifier;
4. U support loss;
5. R limitation;
6. A overlap;
7. C overlap;
8. S suprathreshold-unaccepted;
9. immediate temporal anchor censoring;
10. E reached after:
   - 0 N;
   - 1 N;
   - X/Q/U gap;
11. lookahead exhaustion:
   - 12 X/Q/U;
   - alternating X,N pattern;
12. N-run reset:
   - N,X,N,N → observability_limited with interval from second N run;
13. threshold boundaries:
   - measured_frac exactly 0.50;
   - above_frac exactly 0.05;
   - edge_px = 1,2,3;
14. spatial override crossed with every provisional class;
15. co-occurrences:
   - U∧C;
   - Q∧A;
   - X∧component evidence;
   - R∧A;
16. interval fields after spatial override;
17. onset-side time reversals of every applicable fixture.

Conformance checks:
- exact code/class equality with frozen evidence.py;
- exact interval equality where frozen code emits intervals;
- additive assignment retention checked against the v0.2.2 invariant and required not to alter code/class.

Any conformance failure is a hard pre-execution stop.

## 12. Primary contrasts
- C1 B5 vs B5M
- C2 B5M vs B6
- C3 B5 vs B6

Do not attribute C2 to one internal mechanism without a separately frozen ablation.

---
**Freeze rule:** Any scientific-rule, threshold, family, metric, margin, or mapping change after this freeze requires a new version. This file must not be edited in place.
