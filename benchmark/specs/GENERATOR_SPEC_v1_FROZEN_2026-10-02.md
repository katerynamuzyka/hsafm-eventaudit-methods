# GENERATOR_SPEC_v1_FROZEN_2026-10-02
**Status:** FROZEN FOR IMPLEMENTATION — HELD-OUT EXECUTION NOT YET AUTHORIZED
**Role:** fully specifies the Stage-3B observation-record generator and closes BL-1.

## 1. Scope

This generator creates synthetic **observation records**, not photorealistic AFM images.

It is designed to test boundary semantics conditional on specified support/association information.

It does not test:
- segmentation accuracy;
- frame-QC classifier accuracy;
- registration-confidence classifier accuracy;
- biological truth classification.

Image-level practical validation is reserved for Stage 3C.

## 2. Common units

- time: raw frame index;
- latent time: continuous frame units;
- signal: normalized detector-threshold units, `theta = 1`;
- source support: fraction `[0,1]`;
- spatial edge: pixels relative to the frozen detector-excluded border.

Movie length:
- `n_frames = 64`.

## 3. Latent event-duration bins

Inclusive sampled detection-span classes:

- short: `4–6` accepted-frame span;
- medium: `7–12`;
- long: `13–20`.

Within every family cell, duration-bin allocation is exact as specified below.

These are benchmark design values, not fitted biological distributions.

## 4. Signal model

### 4.1 Clean present state
Peak footprint signal:
- Uniform `[1.4, 2.0] theta`.

### 4.2 Clean absent state
Peak footprint signal:
- Uniform `[0.0, 0.4] theta`.

### 4.3 Noise
Two fixed strata:
- `sigma = 0`;
- `sigma = 0.15 theta`.

Noise is zero-mean Gaussian and is applied before threshold-derived summary fields are calculated.

### 4.4 B5 scalar signal
`b5_peak` = normalized **peak footprint intensity**.

This is the scalar seen by B5/B5M.

### 4.5 Record-consistency rules

For every method-visible frame:

- `above_frac` is calculated over measured pixels only;
- if no measured pixels exist, `above_frac = NaN`;
- if `b5_peak < theta`, then `above_frac = 0`;
- an `S` frame requires:
  - sufficient source support;
  - no production/QC/registration exclusion;
  - no accepted overlapping component;
  - `b5_peak >= theta`;
  - `above_frac >= min_above_frac`;
- accepted component ownership is stored independently from `b5_peak`;
- unsupported/QC/registration-limited frames may still contain plausible numerical signal.

This ensures B5 and B6 read a coherent record.

## 5. Method-visible schema whitelist

Methods may access **only**:

- `case_id`
- `target_side`
- `frame`
- `time_frame_units`
- `t0_event_id`
- `t0_track_id`
- `t0_detection_state`
- `production_good`
- `secondary_qc_bad`
- `measured_frac`
- `registration_supported`
- `b5_peak`
- `above_frac`
- `component_state` in `{none,self,other,unowned}`
- `other_event_ids`
- `edge_px`
- `movie_boundary`
- `candidate_applied` (always false in Stage 3B)

Methods must not receive:
- family;
- severity;
- duration-bin label;
- corruption truth;
- latent transition time;
- clean-twin ID;
- perturbation-condition label;
- true event persistence;
- seed or semantic case index.

Structured case IDs are forbidden.

`case_id` is a hash-derived opaque identifier.

A static test must fail any method key access outside the whitelist.

## 6. Truth schema

Stored in a physically separate file:

- opaque case_id;
- family and stratum;
- target side;
- latent transition time;
- true event-presence trajectory;
- true corruption window;
- true support state;
- true assignment identity;
- duration bin;
- clean-twin mapping;
- seed metadata.

Method execution must pass with this truth file physically absent.

## 7. Case-ID generation

`case_id = first_16_hex(SHA256(seed_manifest_hash || "case" || global_case_index))`

Twin mapping exists only in the truth file.

Permutation of case ordering and case IDs must not change method outputs after rejoining by opaque ID.

## 8. Common inherited semantics

Primary fixed values:

- `min_measured_frac = 0.50`;
- `min_above_frac = 0.05`;
- `n_confirm = 2`;
- `lookahead_frames = 12`;
- `spatial_margin_px = 2`.

These are inherited semantics, not claimed optimal thresholds.

**The core Stage-3B benchmark does not test optimality of `min_measured_frac = 0.50`.**
No “best threshold” may be selected from Stage-3B.

## 9. F0 — supported reference

Grid:
- noise: 2;
- duration bin: 3.

Total cells:
- `2 × 3 = 6`.

Per family total:
- 216 endpoint-targeted;
- 108 onset-targeted.

Allocation:
- endpoint: 36/cell;
- onset: 18/cell.

All relevant support axes are valid.

## 10. F0b — supported detector dropout

Mechanisms:

### F0b-N
- support valid;
- no accepted component;
- `b5_peak < theta`;
- `above_frac = 0`;
- frozen code expectation: `N`.

### F0b-S
- support valid;
- no accepted component;
- `b5_peak >= theta`;
- `above_frac >= 0.05`;
- frozen code expectation: `S`;
- **B5 sees the same `b5_peak >= theta`**, so H1 is not forced in B6's favor by inconsistent signal definitions.

Grid:
- mechanism: 2;
- noise: 2;
- duration bin: 3.

Cells:
- `12`.

Allocation:
- endpoint: 18/cell;
- onset: 9/cell.

## 11. F1–F4 common 18-cell grid

Factors:
- latent transition position relative to corrupted window:
  - before;
  - inside;
  - after;
- numerical value mode on corrupted frames:
  - absence-like;
  - presence-like;
- severity:
  - mild;
  - intermediate;
  - severe.

Cells:
- `3 × 2 × 3 = 18`.

Allocation:
- endpoint: 12/cell;
- onset: 6/cell.

Noise is nested exactly within every cell:
- endpoint: 6 at sigma=0 and 6 at sigma=0.15;
- onset: 3 and 3.

Every corrupted case has a matched clean twin sharing latent truth and non-corruption random draws.

### Transition timing relative to the corruption window

Let the contiguous corruption window be raw frames `w0..w1`.

For endpoint targets:
- before: latent transition at `w0 - 0.25`;
- inside: latent transition at midpoint of `[w0,w1+1)`;
- after: latent transition at `w1 + 1.25`.

For onset targets use the time-reversed construction.

## 12. F1 — production-excluded gap

Severity:
- mild = 1 consecutive X frame;
- intermediate = 2;
- severe = 3.

X is exact:
- imperfect-support perturbations never flip production exclusion.

Numerical array values may still be generated for bookkeeping, but:
- production_good = false;
- no T0 accepted detection is generated on X frames.

## 13. F2 — local source-support loss

Severity:

- mild:
  - 1 corrupted frame;
  - `measured_frac ~ Uniform[0.40,0.49]`;
- intermediate:
  - 2 consecutive frames;
  - `measured_frac ~ Uniform[0.20,0.39]`;
- severe:
  - 3 consecutive frames;
  - `measured_frac ~ Uniform[0.00,0.19]`.

All primary F2 corrupted frames are below the fixed 0.50 support threshold.

Presence-like F2 numerical mode:
- half have no accepted self-component;
- half contain a T0 accepted self-component despite poor source support.

This split is balanced within each presence-like cell:
- endpoint: 3/3 within each noise stratum;
- onset: balanced globally within cell, counts differ by at most 1 where required.

T0 positives are not retroactively deleted by B6.

## 14. F3 — secondary-QC / scan degradation

Severity:
- mild = 1 consecutive Q frame;
- intermediate = 2;
- severe = 3.

Production status remains good.

Presence-like numerical mode:
- half no accepted self-component;
- half T0 accepted self-component.

The benchmark assumes the Q flag is supplied; it does not validate the QC detector.

## 15. F4 — registration limitation

Severity:
- mild = 1 consecutive registration-limited frame;
- intermediate = 2;
- severe = 3.

Production/QC/source support remain otherwise valid.

Presence-like numerical mode:
- half no accepted self-component;
- half T0 accepted self-component.

The benchmark assumes the R support signal is supplied; it does not validate the registration-confidence detector.

## 16. F5 — competing assignment

Support axes remain valid.

Geometry factor:
- overlap fraction = 0.25;
- 0.50;
- 0.75.

Ownership factor:
- `A`: accepted component owned by another retained event;
- `C`: accepted component present but no confirmed other-event owner.

Duration bin:
- 3.

Grid:
- `3 × 2 × 3 = 18`.

Allocation:
- endpoint: 12/cell;
- onset: 6/cell.

Noise nested:
- endpoint 6/6;
- onset 3/3.

Competing candidate begins on the first outward frame for the primary F5 construction.

## 17. F6 — temporal / spatial acquisition censoring

Nine edge types:

1. temporal-left;
2. temporal-right;
3. temporal-both;
4. spatial-top;
5. spatial-bottom;
6. spatial-left;
7. spatial-right;
8. spatial-corner;
9. mixed temporal+spatial.

Cross with 3 duration bins:
- 27 cells.

Allocation:
- endpoint: 8/cell;
- onset: 4/cell.

For spatial/mixed cases:
- `edge_px` cycles through 1, 2, 3 as evenly as possible within each edge-type × duration cell;
- `edge_px < 2` is spatially censored under frozen semantics;
- `edge_px = 2` is exactly on the non-censored threshold;
- `edge_px = 3` is outside the margin.

Noise is balanced globally within family and target side.

## 18. F7b — brief true absence / same-site recurrence

True latent absence length:
- 1 frame;
- 2 frames;
- 3 frames.

Cross with 3 duration bins:
- 9 cells.

Allocation:
- endpoint: 24/cell;
- onset: 12/cell.

Noise:
- endpoint 12/12;
- onset 6/6.

The recurrence is at the same nominal site in K0.

## 19. F7a — sub-frame reference set

Separately labelled reference, not part of the 2916 core.

Offsets:
- 0.25;
- 0.50;
- 0.75 frame.

Cross duration bins:
- 9 cells.

Fixed count:
- 108 endpoint;
- 54 onset;
- total = 162.

Allocation:
- 12 endpoint/cell;
- 6 onset/cell.

## 20. F8 — predefined combined-support interactions

Secondary, separately labelled.

Combinations:
1. X + U;
2. Q + R;
3. U + A;
4. U + C.

Cross duration bins:
- 12 cells.

Fixed count:
- 144 endpoint;
- 72 onset;
- total = 216.

Allocation:
- 12 endpoint/cell;
- 6 onset/cell.

F8 results cannot change primary Stage-3B rules after unblinding.

## 21. Decoy support-failure placements

Predeclared decoy positions:

- D1 mid-event:
  - accepted frame nearest the event-span midpoint;
- D2 post-decision / inside-B5-buffer:
  - endpoint: `L0 + 3`;
  - onset: `L0 - 3`;
  - chosen because B6 may already have a 2-N confirmation while B5/B5M still inspect a 5-frame buffer;
- D3 far supported frame:
  - nearest eligible supported frame at least 8 raw frames from the target anchor.

If a specified decoy position is outside the movie, move inward to the nearest eligible frame while preserving its category; the deterministic adjustment is recorded in truth only.

The D2 asymmetry is explicitly part of the C2 bundle and is not attributed to a single B6 mechanism.

## 22. Imperfect-support perturbation mechanism

X is never perturbed.

Perturbable support axes:
- Q;
- U;
- R.

Rates:
- false negative: 0, 0.10, 0.25;
- false positive: 0, 0.10, 0.25.

### False negatives
Among truly failed Q/U/R frames, choose the preregistered fraction without replacement.

Apply:
- Q: clear secondary_qc_bad;
- U: replace measured_frac by 0.75;
- R: set registration_supported = true.

Numerical signal and component state remain unchanged.

### False positives
Among truly supported eligible frames, choose the preregistered fraction without replacement.

Assign perturbation type Q/U/R in deterministic round-robin balance.

Apply:
- Q: secondary_qc_bad = true;
- U: measured_frac = 0.25;
- R: registration_supported = false.

Numerical signal and component state remain unchanged.

### Visibility across methods
- B5 receives none of these support flags;
- B5M and B6 receive the identically perturbed support record.

Perturbation labels remain truth-only.

## 23. Presence-like junk after latent end

Restore as a predeclared B6-failure stratum.

For F2/F3/F4 presence-like cases:
- half no accepted self-component;
- half accepted T0 self-component.

This tests the frozen v1 decision not to delete already accepted T0 positives.

Report this stratum separately.

## 24. Seed derivation

Development:
`uint64(SHA256(contract_hash || "dev" || case_index)[0:16])`

Held-out:
`uint64(SHA256(contract_hash || "heldout" || case_index)[0:16])`

Perturbation grids derive child seeds from:
`SHA256(case_seed || "support-perturb" || fn_rate || fp_rate)`.

No held-out seed is generated until the frozen contract/spec hashes exist.

## 25. Generator invariants before held-out execution

Must PASS:

- exact family/cell counts;
- exact endpoint/onset counts;
- method-visible whitelist;
- no truth labels in method-visible schema;
- clean twin shares latent truth;
- F0b-S has `b5_peak >= theta` and no accepted component;
- F2 all primary corrupted measured_frac < 0.50;
- X never perturbed;
- support perturbations leave numerical signal/component state unchanged;
- hashed IDs contain no semantic structure;
- case-order/ID permutation leaves method outputs unchanged;
- method modules execute with truth file absent.

---
**Freeze rule:** Any scientific-rule, threshold, family, metric, margin, or mapping change after this freeze requires a new version. This file must not be edited in place.
