# BOUNDARY_CONSEQUENCE_BENCHMARK_CONTRACT_v1_FROZEN_2026-10-02
**Status:** FROZEN FOR IMPLEMENTATION — HELD-OUT EXECUTION NOT YET AUTHORIZED
**Parent:** v0.5  
**Purpose:** close BL-1 through BL-5 from the final targeted review.

## 1. Scope

Stage 3B core is an observation-record benchmark of boundary semantics conditional on measurement-support information.

It is not end-to-end validation of:
- QC detection;
- registration-confidence detection;
- segmentation;
- biological-state classification.

Practical HS-AFM improvement claims require Stage 3C.

## 2. Core question

> Given common detector-defined T0 tracks, does support-conditioned boundary interpretation reduce incorrect finite temporal claims without merely replacing them with excessive no-claims?

## 3. Frozen predecessor provenance

Stage 2 remains frozen and closed.

Stage-3 design does not modify:
- Stage-1 FAIL;
- Stage-1B PASS;
- Stage-2 outputs;
- frozen external detector tracks.

## 4. Generator

Fully specified by:
`GENERATOR_SPEC_v1_FROZEN_2026-10-02.md`.

Core:
- 64 raw frames;
- K0 only;
- fixed signal/support semantics;
- exact family grids;
- exact corruption severities;
- exact method-visible whitelist;
- exact support-flag perturbation mechanism.

The 0.50 source-support threshold is inherited and is **not claimed optimal**.

## 5. Core families

Primary:
- F0
- F0b
- F1
- F2
- F3
- F4
- F5
- F6
- F7b

Reference/secondary:
- F7a
- F8

F0b explicitly contains:
- supported below-threshold N pathway;
- supported suprathreshold-unaccepted S pathway.

## 6. Common T0

Primary B1/B3/B4/B5/B5M/B6 consume common T0 event identities.

B2a/B2b are alternate gap-handling comparators.

No primary B5/B5M/B6 contrast relinks T0.

## 7. Baselines

Fully specified by:
`BASELINE_SPEC_v1_FROZEN_2026-10-02.md`.

B5:
- Aguet-inspired post-processing baseline;
- target-side full 5-frame buffer;
- minimum 5 accepted T0 detections;
- finite claim remains detector-adjacent `(t_L0,t_L0+1]`.

B5M:
- all 5 target-side buffer frames support-valid;
- otherwise no_claim:partial_support;
- supported within-track max only.

B6:
- exact frozen code/class behavior;
- additive non-exclusive assignment retention on R frames;
- exact temporal/spatial rules;
- mandatory image→record conformance suite.

## 8. BL-4 closure

Direct frozen-source inspection establishes:

- frozen `evidence.py` does **not** export assignment-overlap fields on an R frame because it returns R before component overlap;
- E inside `_classify()` → boundary_censored;
- lookahead exhaustion → unresolved;
- anchor at first/last good frame → immediate temporal boundary_censored;
- spatial override occurs before interval writing, so spatially overridden rows do not retain SVN/OBS interval fields.

Therefore:
- code/class/interval conformance is exact to frozen `evidence.py`;
- assignment retention on R is a declared additive Stage-3 extension validated against frozen v0.2.2 invariant #6;
- additive evidence cannot change code or class.

## 9. Metrics

Fully specified by:
`METRIC_SPEC_v1_FROZEN_2026-10-02.md`.

Correctness is latent-truth anchored.

No support flag defines correctness.

Primary outputs:
- claim_hit;
- claim_miss;
- no_claim;
- interval informativeness;
- duration interval coverage/width;
- imperfect-support robustness;
- acquisition-censoring correctness.

Mechanical SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE rules are frozen before held-out execution.

## 10. Sample size

Core:
- 9 families × 324 = 2916 latent cases;
- 216 end-targeted/family;
- 108 onset-targeted/family.

Reference:
- F7a = 162.

Secondary interactions:
- F8 = 216.

No runtime fallback.

Matched twins and support perturbations reuse latent units and are not counted as biological replicates.

## 11. Truth isolation

Method-visible fields are whitelisted.

Methods receive no:
- family;
- severity;
- truth time;
- twin mapping;
- perturbation label;
- structured case ID.

Required:
- truth-file-absent test;
- forbidden-key test;
- hashed IDs;
- permutation invariance.

## 12. Imperfect-support claim boundary

Support flags are generated from known synthetic corruption and therefore remain oracle-like inputs in the clean core.

The mandatory FN/FP perturbation arm quantifies sensitivity to incorrect support information.

Therefore Stage-3B supports only a conditional claim:

> given support information of specified quality, support-conditioned boundary handling changes the trade-off between incorrect finite claims, decisive coverage and unresolved/censored boundaries.

## 13. Population consequence arm

Removed from the core v1 unblinding.

Any population duration/survival consequence analysis is separately preregistered and frozen as:

`STAGE3B_POPULATION_CONSEQUENCE_ANNEX_v1`.

It must be frozen before that arm runs.

It may still appear in Paper 1 if completed under its own frozen annex.

## 14. Stage 3C

Required before any practical HS-AFM improvement claim.

To prevent post-hoc design:
- Stage 3C contract must be frozen **before Stage-3B core held-out unblinding**;
- Stage 3C may be coded later, but its scientific design cannot be changed in response to 3B held-out results.

Stage 3C must:
- use real AFM backgrounds/artifact contexts;
- inject known events;
- run frozen image-level EventAudit evidence logic;
- compute support diagnostics through actual diagnostic machinery rather than truth flags;
- compare B5/B5M/B6 under the separately frozen design.

## 15. Development / held-out firewall

Before held-out seed creation:
- contract/spec hashes fixed;
- generator source/spec fixed;
- baselines/metrics fixed;
- conformance suite PASS;
- construction invariants PASS.

One held-out unblinding writes all core method outputs and mechanical verdict inputs before inspection.

Implementation bug after unblinding:
- must reproduce independently on development/hand fixtures;
- all affected outputs rerun;
- original outputs retained;
- any scientific-rule change creates a new version.

## 16. Literature positioning

- B5 is not full cmeAnalysis reproduction.
- Exact Loerke Text-S1 algebra remains on citation hold.
- u-track3D wording remains conservative: the paper describes no export of alternative assignments.
- Stage 3 does not claim to invent the existence of every interval field; frozen evidence.py already exports some endpoint intervals.

## 17. Freeze status

The final targeted review and subsequent Project-Control close-out established that no further open-ended review is required after:
- BL-1 to BL-4 are filled;
- BL-5 is filled or formally deferred;
- one read-only frozen evidence.py check closes BL-4.

v1 freeze closes those items by:
- generator spec;
- baseline spec;
- metric spec;
- BL-4 direct source note;
- formal population-arm deferral.

Project-Control mechanical close-out was completed before this freeze. Exact hashes are recorded in the Stage-3 frozen manifest and freeze record.

Production implementation may begin only under this frozen specification; held-out execution still requires a separate Project-Control authorization.

---
**Freeze rule:** Any scientific-rule, threshold, family, metric, margin, or mapping change after this freeze requires a new version. This file must not be edited in place.
