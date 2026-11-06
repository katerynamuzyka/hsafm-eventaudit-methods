"""Development-only Stage-3A.5 metrics and mechanical verdicts.

This module consumes *already fixed* A4 ``BaselineOutcome`` objects.  It never
runs or relinks a baseline.  Truth and family/condition labels enter only in
this scoring/reporting layer, after method outputs have been fixed.

Binding authority is ``METRIC_SPEC_v1`` plus frozen A5 clarification addenda
v1.1-v1.6.  Held-out execution, Stage 3B/3C, and the population-consequence arm
are intentionally absent.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

from .benchmark_baselines import BaselineOutcome
from .baselines import SPATIAL_MARGIN_PX
from .boundary_record import validate_method_visible_record
from .truth_record import validate_truth_record


FROZEN_CONTRACT_HASH = "86ee65277b917ca513ffc1a5754748384240456172d883bff40c83d2804493d4"
BOOTSTRAP_RESAMPLES = 10_000
PERMUTATIONS = 10_000
ALPHA = 0.05

CLAIM_HIT = "claim_hit"
CLAIM_MISS = "claim_miss"
NO_CLAIM = "no_claim"
THREE_WAY_CATEGORIES = (CLAIM_HIT, CLAIM_MISS, NO_CLAIM)

SUPPORTED = "SUPPORTED"
NOT_SUPPORTED = "NOT_SUPPORTED"
INCONCLUSIVE = "INCONCLUSIVE"
VERDICTS = frozenset({SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE})

DEFINED = "defined"
UNDEFINED_EMPTY = "undefined_empty_conditioning_set"
UNDEFINED_ZERO_FINITE = "undefined_zero_finite_claims"
UNDEFINED_EMPTY_HIT = "undefined_empty_hit_subset"
UNDEFINED_EMPTY_MISS = "undefined_empty_miss_subset"
UNDEFINED_EMPTY_COMMON_DURATION = "undefined_empty_common_finite_duration_subset"
UNDEFINED_INFERENTIAL = "undefined_inferential_target"
NOT_OBSERVABLE = "not_observable_from_accepted_method_output"

POINT_DURATION_METHODS = ("B1", "B2a", "B2b", "B3", "B4a", "B5", "B5M")
M9_METHODS = ("B5", "B5M", "B6")
M9_FAMILIES = ("F1", "F2", "F3", "F4")
M9_RATES = (0.0, 0.10, 0.25)
M9_DECOYS = ("D1", "D2", "D3")
HOLM_FAMILIES = ("F1", "F2", "F3", "F4")
PURE_SPATIAL_EDGE_TYPES = frozenset(
    {"spatial-top", "spatial-bottom", "spatial-left", "spatial-right", "spatial-corner"}
)
ACCEPTED_OUTPUT_STATUSES = frozenset({"finite_claim", "censored", "no_claim"})
_CASE_ID_RE = re.compile(r"^[0-9a-f]{16}$")

HYPOTHESIS_FAMILY_TOKENS: Mapping[str, frozenset[str]] = {
    "H1A": frozenset({"F0"}),
    "H1B": frozenset({"F0b"}),
    "H2": frozenset(HOLM_FAMILIES),
    "H3": frozenset(HOLM_FAMILIES),
    "H4": frozenset(HOLM_FAMILIES),
    "H5": frozenset({"F0+F0b"}),
    "H6": frozenset(HOLM_FAMILIES),
    "H7": frozenset({"F6"}),
}


class MetricInvariantError(RuntimeError):
    """Raised when accepted A3/A4 invariants or required pairing are violated."""


@dataclass(frozen=True)
class BoundaryScore:
    """One truth-joined target-boundary score from an already fixed method output."""

    case_id: str
    method: str
    family: str
    stratum: str
    target_side: str
    truth_time: float
    output_status: str
    category: str
    left_frame: int | None
    right_frame: int | None
    width: float | None

    @property
    def hit(self) -> int:
        return int(self.category == CLAIM_HIT)

    @property
    def miss(self) -> int:
        return int(self.category == CLAIM_MISS)

    @property
    def no_claim(self) -> int:
        return int(self.category == NO_CLAIM)

    @property
    def finite_claim(self) -> int:
        return int(self.output_status == "finite_claim")


@dataclass(frozen=True)
class ScoredCase:
    """A5-normalized case holding only fixed outcomes plus post-hoc scoring metadata.

    ``base_case_id`` is the frozen latent pairing identity.  For an unperturbed
    base case it normally equals ``case_id``; support/decoy variants keep their
    emitted ``case_id`` while pairing by ``base_case_id``.
    """

    base_case_id: str
    case_id: str
    family: str
    stratum: str
    target_side: str
    truth_time: float
    outcomes: Mapping[str, BaselineOutcome]
    scores: Mapping[str, BoundaryScore]
    b5_eligible: bool
    variant_kind: str = "base"  # base | support | decoy
    fn_rate: float | None = None
    fp_rate: float | None = None
    decoy: str | None = None
    full_left: int | None = None
    full_right: int | None = None
    edge_type: str | None = None
    edge_px: int | None = None


@dataclass(frozen=True)
class DurationCase:
    """Per-case Stage-3A.5 duration construction after outputs are fixed."""

    case_id: str
    target_side: str
    t_ref: int
    true_duration: float
    point_durations: Mapping[str, float | None]
    interval_durations: Mapping[str, Mapping[str, Any] | None]


# ---------------------------------------------------------------------------
# Structured scalar/summary serialization (v1.6)
# ---------------------------------------------------------------------------


def _scalar(
    *,
    status: str,
    n: int,
    value: float | None,
    numerator: int | None = None,
    denominator: int | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status, "n": int(n), "value": value}
    if numerator is not None:
        out["numerator"] = int(numerator)
    if denominator is not None:
        out["denominator"] = int(denominator)
    return out


def _defined_ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator <= 0:
        raise MetricInvariantError("defined ratio requires a positive denominator")
    return _scalar(
        status=DEFINED,
        n=denominator,
        value=float(numerator / denominator),
        numerator=numerator,
        denominator=denominator,
    )


def _undefined_ratio(status: str, denominator: int = 0) -> dict[str, Any]:
    return _scalar(status=status, n=0, value=None, numerator=0, denominator=denominator)


def _undefined_inferential(reason: str, *, families: Sequence[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": UNDEFINED_INFERENTIAL,
        "n": 0,
        "estimate": None,
        "ci90": None,
        "lower95": None,
        "upper95": None,
        "p_raw": None,
        "p_holm": None,
        "verdict": INCONCLUSIVE,
        "reason": reason,
    }
    if families is not None:
        out["undefined_families"] = list(families)
    return out


# ---------------------------------------------------------------------------
# Truth join and target-boundary scoring
# ---------------------------------------------------------------------------


def _validate_case_id(case_id: str) -> None:
    if not isinstance(case_id, str) or _CASE_ID_RE.fullmatch(case_id) is None:
        raise MetricInvariantError("case_id must be the frozen lowercase 16-hex identity")


def _truth_by_case(truth_records: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for record in truth_records:
        validate_truth_record(record)
        case_id = str(record["case_id"]).lower()
        _validate_case_id(case_id)
        if case_id in out:
            raise MetricInvariantError(f"duplicate truth case_id {case_id}")
        out[case_id] = record
    return out


def score_target_boundary(outcome: BaselineOutcome, truth_record: Mapping[str, Any]) -> BoundaryScore:
    """Score one fixed target-boundary output using the frozen ``(L,R]`` rule.

    Both ``censored`` and method ``no_claim`` outputs enter the three-way target
    partition as ``no_claim`` because neither is a finite claim.  The original
    output status is retained separately for M10/H7.
    """

    validate_truth_record(truth_record)
    if not isinstance(outcome, BaselineOutcome):
        raise MetricInvariantError("A5 scoring requires an accepted BaselineOutcome")
    case_id = str(outcome.case_id).lower()
    truth_case_id = str(truth_record["case_id"]).lower()
    _validate_case_id(case_id)
    if case_id != truth_case_id:
        raise MetricInvariantError("fixed output and truth case_id disagree")
    if outcome.target_side != truth_record["target_side"]:
        raise MetricInvariantError("fixed output and truth target_side disagree")
    if outcome.status not in ACCEPTED_OUTPUT_STATUSES:
        raise MetricInvariantError(f"unexpected accepted output status {outcome.status!r}")

    truth_time = float(truth_record["latent_transition_time"])
    if outcome.status == "finite_claim":
        if outcome.left_frame is None or outcome.right_frame is None:
            raise MetricInvariantError("finite output is missing frozen interval endpoints")
        left = int(outcome.left_frame)
        right = int(outcome.right_frame)
        if not left < right:
            raise MetricInvariantError("finite output must satisfy L < R")
        category = CLAIM_HIT if left < truth_time <= right else CLAIM_MISS
        width: float | None = float(right - left)
    else:
        left = None
        right = None
        width = None
        category = NO_CLAIM

    return BoundaryScore(
        case_id=case_id,
        method=str(outcome.method),
        family=str(truth_record["family"]),
        stratum=str(truth_record["stratum"]),
        target_side=str(truth_record["target_side"]),
        truth_time=truth_time,
        output_status=str(outcome.status),
        category=category,
        left_frame=left,
        right_frame=right,
        width=width,
    )


def score_fixed_outputs(
    method_outputs: Iterable[BaselineOutcome],
    truth_records: Iterable[Mapping[str, Any]],
) -> tuple[BoundaryScore, ...]:
    """Join already-fixed method outputs to truth by opaque case identity.

    Input row order does not affect the returned canonical ``(case_id, method)``
    ordering.  No baseline function is called here.
    """

    truth = _truth_by_case(truth_records)
    seen: set[tuple[str, str]] = set()
    scores: list[BoundaryScore] = []
    for outcome in method_outputs:
        if not isinstance(outcome, BaselineOutcome):
            raise MetricInvariantError("method_outputs must contain BaselineOutcome objects")
        case_id = str(outcome.case_id).lower()
        key = (case_id, str(outcome.method))
        if key in seen:
            raise MetricInvariantError(f"duplicate fixed method output {key}")
        seen.add(key)
        if case_id not in truth:
            raise MetricInvariantError(f"fixed output lacks truth record for {case_id}")
        scores.append(score_target_boundary(outcome, truth[case_id]))
    return tuple(sorted(scores, key=lambda s: (s.case_id, s.method)))


def three_way_summary(scores: Sequence[BoundaryScore]) -> dict[str, Any]:
    """Frozen target-boundary hit/miss/no-claim summary for one condition/method."""

    n = len(scores)
    if n == 0:
        return {
            "n": 0,
            "p_hit": _undefined_ratio(UNDEFINED_EMPTY),
            "p_miss": _undefined_ratio(UNDEFINED_EMPTY),
            "p_no_claim": _undefined_ratio(UNDEFINED_EMPTY),
            "p_hit_given_finite": _undefined_ratio(UNDEFINED_ZERO_FINITE),
            "p_miss_given_finite": _undefined_ratio(UNDEFINED_ZERO_FINITE),
        }
    hits = sum(s.hit for s in scores)
    misses = sum(s.miss for s in scores)
    no_claim = sum(s.no_claim for s in scores)
    if hits + misses + no_claim != n:
        raise MetricInvariantError("three-way partition does not exhaust conditioning set")
    finite = hits + misses
    if finite == 0:
        p_hit_finite = _undefined_ratio(UNDEFINED_ZERO_FINITE)
        p_miss_finite = _undefined_ratio(UNDEFINED_ZERO_FINITE)
    else:
        p_hit_finite = _defined_ratio(hits, finite)
        p_miss_finite = _defined_ratio(misses, finite)
    return {
        "n": n,
        "p_hit": _defined_ratio(hits, n),
        "p_miss": _defined_ratio(misses, n),
        "p_no_claim": _defined_ratio(no_claim, n),
        "p_hit_given_finite": p_hit_finite,
        "p_miss_given_finite": p_miss_finite,
    }


def _width_summary(widths: Sequence[float], empty_status: str) -> dict[str, Any]:
    values = np.asarray(widths, dtype=np.float64)
    if values.size == 0:
        return {
            "status": empty_status,
            "n": 0,
            "median": None,
            "q1": None,
            "q3": None,
            "iqr": None,
            "fraction_width_le_1": None,
            "fraction_width_le_2": None,
        }
    if not np.all(np.isfinite(values)):
        raise MetricInvariantError("interval widths must be finite")
    q1 = float(np.quantile(values, 0.25, method="linear"))
    q3 = float(np.quantile(values, 0.75, method="linear"))
    return {
        "status": DEFINED,
        "n": int(values.size),
        "median": float(np.quantile(values, 0.50, method="linear")),
        "q1": q1,
        "q3": q3,
        "iqr": float(q3 - q1),
        "fraction_width_le_1": float(np.mean(values <= 1.0, dtype=np.float64)),
        "fraction_width_le_2": float(np.mean(values <= 2.0, dtype=np.float64)),
    }


def interval_informativeness(scores: Sequence[BoundaryScore]) -> dict[str, Any]:
    """Finite-claim width summaries, separated exactly into hit and miss subsets."""

    hit_widths = [float(s.width) for s in scores if s.category == CLAIM_HIT and s.width is not None]
    miss_widths = [float(s.width) for s in scores if s.category == CLAIM_MISS and s.width is not None]
    return {
        "hit": _width_summary(hit_widths, UNDEFINED_EMPTY_HIT),
        "miss": _width_summary(miss_widths, UNDEFINED_EMPTY_MISS),
    }


def compute_metrics(
    method_outputs: Iterable[BaselineOutcome],
    truth_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compute boundary-scoring summaries from already-fixed outputs.

    This public replacement for the A0 stub intentionally performs no baseline
    execution.  Duration/M8-M10/hypothesis helpers below require their additional
    frozen conditioning metadata and are therefore exposed explicitly rather
    than guessed here.
    """

    scores = score_fixed_outputs(method_outputs, truth_records)
    methods = sorted({s.method for s in scores})
    by_method: dict[str, Any] = {}
    for method in methods:
        subset = tuple(s for s in scores if s.method == method)
        by_method[method] = {
            "three_way": three_way_summary(subset),
            "interval_informativeness": interval_informativeness(subset),
        }
    return {"scores": scores, "by_method": by_method}


# ---------------------------------------------------------------------------
# A5 duration construction (v1.2-v1.3)
# ---------------------------------------------------------------------------


def common_t0_reference(
    method_records: Sequence[Mapping[str, Any]],
    *,
    target_side: str | None = None,
) -> int:
    """Return the method-independent opposite-side reference ``t_ref``.

    Endpoint uses the *first* accepted target-event T0 frame; onset uses the
    *last*.  Q/U/R support flags do not remove an already accepted detection.
    """

    if isinstance(method_records, (str, bytes)) or not isinstance(method_records, Sequence) or not method_records:
        raise MetricInvariantError("duration reference requires non-empty method-visible records")
    validated: list[Mapping[str, Any]] = []
    for row in method_records:
        validate_method_visible_record(row)
        validated.append(row)
    case_ids = {str(r["case_id"]).lower() for r in validated}
    sides = {str(r["target_side"]) for r in validated}
    event_ids = {str(r["t0_event_id"]) for r in validated}
    track_ids = {str(r["t0_track_id"]) for r in validated}
    frames = [int(r["frame"]) for r in validated]
    if len(case_ids) != 1 or len(sides) != 1:
        raise MetricInvariantError("duration reference records mix case identity or target side")
    if len(event_ids) != 1 or len(track_ids) != 1:
        raise MetricInvariantError("duration reference records mix common-T0 event/track identities")
    if len(frames) != len(set(frames)):
        raise MetricInvariantError("duration reference records contain duplicate raw-frame indices")
    side = next(iter(sides)) if target_side is None else str(target_side)
    if side not in {"endpoint", "onset"} or sides != {side}:
        raise MetricInvariantError("duration reference target side mismatch")
    accepted = sorted(int(r["frame"]) for r in validated if r["t0_detection_state"] == "accepted")
    if not accepted:
        raise MetricInvariantError("duration reference requires at least one accepted T0 detection")
    return min(accepted) if side == "endpoint" else max(accepted)


def true_duration(truth_record: Mapping[str, Any], t_ref: int) -> float:
    validate_truth_record(truth_record)
    truth = float(truth_record["latent_transition_time"])
    side = str(truth_record["target_side"])
    return float(truth - t_ref) if side == "endpoint" else float(t_ref - truth)


def point_duration(outcome: BaselineOutcome, t_ref: int) -> float | None:
    if outcome.method not in POINT_DURATION_METHODS:
        raise MetricInvariantError(f"{outcome.method} is not a frozen point-duration method")
    if outcome.status != "finite_claim":
        return None
    if outcome.anchor_frame is None:
        raise MetricInvariantError("finite point-derived output is missing anchor_frame")
    k = int(outcome.anchor_frame)
    return float(k - t_ref) if outcome.target_side == "endpoint" else float(t_ref - k)


def duration_interval(outcome: BaselineOutcome, t_ref: int) -> dict[str, Any] | None:
    """Transform a finite target claim ``(L,R]`` into the frozen duration interval."""

    if outcome.status != "finite_claim":
        return None
    if outcome.left_frame is None or outcome.right_frame is None:
        raise MetricInvariantError("finite interval-duration output lacks endpoints")
    L, R = int(outcome.left_frame), int(outcome.right_frame)
    if outcome.target_side == "endpoint":
        lower, upper = float(L - t_ref), float(R - t_ref)
        lower_closed, upper_closed = False, True
    elif outcome.target_side == "onset":
        lower, upper = float(t_ref - R), float(t_ref - L)
        lower_closed, upper_closed = True, False
    else:
        raise MetricInvariantError("unknown target side")
    return {
        "lower": lower,
        "upper": upper,
        "lower_closed": lower_closed,
        "upper_closed": upper_closed,
        "width": float(R - L),
        "midpoint": float((lower + upper) / 2.0),
    }


def duration_interval_covers_truth(
    interval: Mapping[str, Any],
    *,
    true_duration_value: float,
    target_side: str,
) -> bool:
    lower = float(interval["lower"])
    upper = float(interval["upper"])
    value = float(true_duration_value)
    if target_side == "endpoint":
        return bool(lower < value <= upper)
    if target_side == "onset":
        return bool(lower <= value < upper)
    raise MetricInvariantError("unknown target side")


def build_duration_case(
    *,
    method_records: Sequence[Mapping[str, Any]],
    truth_record: Mapping[str, Any],
    outcomes: Mapping[str, BaselineOutcome],
    interval_methods: Sequence[str] = ("B6",),
) -> DurationCase:
    """Construct one duration case without executing/recomputing any baseline."""

    validate_truth_record(truth_record)
    case_id = str(truth_record["case_id"]).lower()
    t_ref = common_t0_reference(method_records, target_side=str(truth_record["target_side"]))
    tdur = true_duration(truth_record, t_ref)
    point: dict[str, float | None] = {}
    intervals: dict[str, Mapping[str, Any] | None] = {}
    for method in POINT_DURATION_METHODS:
        if method in outcomes:
            if str(outcomes[method].case_id).lower() != case_id:
                raise MetricInvariantError("duration outcome/truth identity mismatch")
            point[method] = point_duration(outcomes[method], t_ref)
    for method in interval_methods:
        if method in outcomes:
            if str(outcomes[method].case_id).lower() != case_id:
                raise MetricInvariantError("duration outcome/truth identity mismatch")
            intervals[method] = duration_interval(outcomes[method], t_ref)
    return DurationCase(
        case_id=case_id,
        target_side=str(truth_record["target_side"]),
        t_ref=t_ref,
        true_duration=tdur,
        point_durations=point,
        interval_durations=intervals,
    )


def _bias_mae(estimates: np.ndarray, truth: np.ndarray) -> tuple[float, float]:
    errors = np.asarray(estimates, dtype=np.float64) - np.asarray(truth, dtype=np.float64)
    return float(np.mean(errors, dtype=np.float64)), float(np.mean(np.abs(errors), dtype=np.float64))


def summarize_point_durations(
    cases: Sequence[DurationCase],
    *,
    methods: Sequence[str] = POINT_DURATION_METHODS,
) -> dict[str, Any]:
    """Common-subset bias/MAE plus per-method finite point-duration yield."""

    methods = tuple(methods)
    unknown = set(methods) - set(POINT_DURATION_METHODS)
    if unknown:
        raise MetricInvariantError(f"unknown point-duration methods: {sorted(unknown)}")
    n_total = len(cases)
    yields: dict[str, Any] = {}
    for method in methods:
        finite = sum(c.point_durations.get(method) is not None for c in cases)
        yields[method] = (
            _defined_ratio(finite, n_total) if n_total else _undefined_ratio(UNDEFINED_EMPTY)
        )

    common = [c for c in cases if all(c.point_durations.get(m) is not None for m in methods)]
    if not common:
        summaries = {
            m: {
                "status": UNDEFINED_EMPTY_COMMON_DURATION,
                "n": 0,
                "signed_bias": None,
                "mae": None,
            }
            for m in methods
        }
        return {
            "status": UNDEFINED_EMPTY_COMMON_DURATION,
            "n_common": 0,
            "methods": list(methods),
            "common_case_ids": [],
            "summaries": summaries,
            "finite_yield": yields,
        }

    truth = np.asarray([c.true_duration for c in common], dtype=np.float64)
    summaries: dict[str, Any] = {}
    for method in methods:
        estimates = np.asarray([float(c.point_durations[method]) for c in common], dtype=np.float64)
        bias, mae = _bias_mae(estimates, truth)
        summaries[method] = {"status": DEFINED, "n": len(common), "signed_bias": bias, "mae": mae}
    return {
        "status": DEFINED,
        "n_common": len(common),
        "methods": list(methods),
        "common_case_ids": [c.case_id for c in common],
        "summaries": summaries,
        "finite_yield": yields,
    }


def summarize_interval_durations(cases: Sequence[DurationCase], *, method: str = "B6") -> dict[str, Any]:
    """Primary interval coverage/width plus midpoint sensitivity and finite yield."""

    n_total = len(cases)
    finite = [c for c in cases if c.interval_durations.get(method) is not None]
    finite_yield = _defined_ratio(len(finite), n_total) if n_total else _undefined_ratio(UNDEFINED_EMPTY)
    if not finite:
        return {
            "status": UNDEFINED_ZERO_FINITE,
            "n": 0,
            "finite_yield": finite_yield,
            "coverage": _undefined_ratio(UNDEFINED_ZERO_FINITE),
            "width": _width_summary([], UNDEFINED_ZERO_FINITE),
            "midpoint_sensitivity": {
                "status": UNDEFINED_ZERO_FINITE,
                "n": 0,
                "signed_bias": None,
                "mae": None,
            },
        }
    covers: list[bool] = []
    widths: list[float] = []
    midpoints: list[float] = []
    truths: list[float] = []
    for case in finite:
        interval = case.interval_durations[method]
        assert interval is not None
        covers.append(
            duration_interval_covers_truth(
                interval,
                true_duration_value=case.true_duration,
                target_side=case.target_side,
            )
        )
        widths.append(float(interval["width"]))
        midpoints.append(float(interval["midpoint"]))
        truths.append(float(case.true_duration))
    bias, mae = _bias_mae(np.asarray(midpoints), np.asarray(truths))
    return {
        "status": DEFINED,
        "n": len(finite),
        "finite_yield": finite_yield,
        "coverage": _defined_ratio(sum(covers), len(covers)),
        "width": _width_summary(widths, UNDEFINED_ZERO_FINITE),
        "midpoint_sensitivity": {
            "status": DEFINED,
            "n": len(finite),
            "signed_bias": bias,
            "mae": mae,
        },
    }


# ---------------------------------------------------------------------------
# Case normalization for M8/M9/M10 and hypotheses
# ---------------------------------------------------------------------------


def b5_eligible(method_records: Sequence[Mapping[str, Any]]) -> bool:
    """Frozen common B5 eligibility: at least five accepted T0 detections.

    Signal validation and observed success/failure do not define eligibility.
    """

    seen_frames: set[int] = set()
    case_ids: set[str] = set()
    event_ids: set[str] = set()
    track_ids: set[str] = set()
    for row in method_records:
        validate_method_visible_record(row)
        frame = int(row["frame"])
        if frame in seen_frames:
            raise MetricInvariantError("B5 eligibility records contain duplicate raw-frame indices")
        seen_frames.add(frame)
        case_ids.add(str(row["case_id"]).lower())
        event_ids.add(str(row["t0_event_id"]))
        track_ids.add(str(row["t0_track_id"]))
    if len(case_ids) != 1 or len(event_ids) != 1 or len(track_ids) != 1:
        raise MetricInvariantError("B5 eligibility requires one common-T0 case/event/track")
    return sum(row["t0_detection_state"] == "accepted" for row in method_records) >= 5


def _acquisition_span(method_records: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    for row in method_records:
        validate_method_visible_record(row)
    acquisition = [int(r["frame"]) for r in method_records if not bool(r["movie_boundary"])]
    if not acquisition:
        raise MetricInvariantError("case has no acquisition-good frame")
    return min(acquisition), max(acquisition)


def _common_edge_px(method_records: Sequence[Mapping[str, Any]]) -> int:
    accepted = [r for r in method_records if r["t0_detection_state"] == "accepted"]
    if not accepted:
        raise MetricInvariantError("edge metadata requires an accepted T0 detection")
    values = {int(r["edge_px"]) for r in accepted}
    if len(values) != 1:
        raise MetricInvariantError("accepted T0 rows disagree on edge_px")
    return next(iter(values))


def make_scored_case(
    *,
    outcomes: Mapping[str, BaselineOutcome],
    truth_record: Mapping[str, Any],
    method_records: Sequence[Mapping[str, Any]] | None = None,
    base_case_id: str | None = None,
    variant_kind: str = "base",
    fn_rate: float | None = None,
    fp_rate: float | None = None,
    decoy: str | None = None,
    edge_type: str | None = None,
    b5_eligible_value: bool | None = None,
) -> ScoredCase:
    """Normalize one case after all supplied method outcomes have been fixed."""

    validate_truth_record(truth_record)
    case_id = str(truth_record["case_id"]).lower()
    _validate_case_id(case_id)
    base_id = case_id if base_case_id is None else str(base_case_id).lower()
    _validate_case_id(base_id)
    if variant_kind not in {"base", "support", "decoy"}:
        raise MetricInvariantError("variant_kind must be base/support/decoy")
    if decoy is not None and decoy not in M9_DECOYS:
        raise MetricInvariantError("decoy must be D1, D2 or D3")
    if variant_kind == "support":
        if fn_rate not in M9_RATES or fp_rate not in M9_RATES:
            raise MetricInvariantError("support variant requires frozen FN/FP rates")
    if variant_kind == "decoy" and decoy is None:
        raise MetricInvariantError("decoy variant requires decoy category")

    normalized_outcomes: dict[str, BaselineOutcome] = {}
    normalized_scores: dict[str, BoundaryScore] = {}
    for method, outcome in outcomes.items():
        if method != outcome.method:
            raise MetricInvariantError("outcome mapping key disagrees with outcome.method")
        if str(outcome.case_id).lower() != case_id:
            raise MetricInvariantError("fixed outcome case_id disagrees with truth record")
        normalized_outcomes[method] = outcome
        normalized_scores[method] = score_target_boundary(outcome, truth_record)

    full_left = full_right = edge_px = None
    if method_records is not None:
        record_ids = {str(r["case_id"]).lower() for r in method_records}
        if record_ids != {case_id}:
            raise MetricInvariantError("method records disagree with truth case_id")
        full_left, full_right = _acquisition_span(method_records)
        edge_px = _common_edge_px(method_records)
        elig = b5_eligible(method_records)
    else:
        if b5_eligible_value is None:
            raise MetricInvariantError("b5_eligible_value is required when method_records are absent")
        elig = bool(b5_eligible_value)

    return ScoredCase(
        base_case_id=base_id,
        case_id=case_id,
        family=str(truth_record["family"]),
        stratum=str(truth_record["stratum"]),
        target_side=str(truth_record["target_side"]),
        truth_time=float(truth_record["latent_transition_time"]),
        outcomes=normalized_outcomes,
        scores=normalized_scores,
        b5_eligible=elig,
        variant_kind=variant_kind,
        fn_rate=fn_rate,
        fp_rate=fp_rate,
        decoy=decoy,
        full_left=full_left,
        full_right=full_right,
        edge_type=edge_type,
        edge_px=edge_px,
    )


def _require_methods(case: ScoredCase, methods: Sequence[str]) -> None:
    missing = [m for m in methods if m not in case.scores or m not in case.outcomes]
    if missing:
        raise MetricInvariantError(f"case {case.case_id} lacks required fixed methods {missing}")


def _indicator(case: ScoredCase, method: str, category: str) -> float:
    _require_methods(case, (method,))
    if category not in THREE_WAY_CATEGORIES:
        raise MetricInvariantError("unknown three-way category")
    return float(case.scores[method].category == category)


# ---------------------------------------------------------------------------
# M8 and M9
# ---------------------------------------------------------------------------


def m8_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    """Frozen standalone M8 on unperturbed B5-eligible F0+F0b cases."""

    subset = [
        c
        for c in cases
        if c.family in {"F0", "F0b"} and c.variant_kind == "base" and c.b5_eligible
    ]
    for case in subset:
        _require_methods(case, ("B5", "B6"))
    if not subset:
        return {
            "status": UNDEFINED_EMPTY,
            "n": 0,
            "numerator": 0,
            "denominator": 0,
            "value": None,
        }
    indicators = [
        int(c.scores["B5"].category == CLAIM_HIT and c.scores["B6"].category == NO_CLAIM)
        for c in subset
    ]
    numerator = int(sum(indicators))
    out = _defined_ratio(numerator, len(subset))
    out["case_indicators"] = {c.base_case_id: i for c, i in zip(subset, indicators)}
    return out


def _m9_same_semantics(a: ScoredCase, b: ScoredCase) -> bool:
    if a.family != b.family or a.base_case_id != b.base_case_id:
        return False
    for method in M9_METHODS:
        _require_methods(a, (method,))
        _require_methods(b, (method,))
        if a.scores[method].category != b.scores[method].category:
            return False
    return a.b5_eligible == b.b5_eligible


def _m9_cell_payload(cases: Sequence[ScoredCase], *, include_m8: bool) -> dict[str, Any]:
    if not cases:
        undefined = {
            outcome: _undefined_ratio(UNDEFINED_EMPTY) for outcome in THREE_WAY_CATEGORIES
        }
        contrasts = {
            pair: {outcome: _scalar(status=UNDEFINED_EMPTY, n=0, value=None) for outcome in THREE_WAY_CATEGORIES}
            for pair in ("B6-B5", "B5M-B5", "B6-B5M")
        }
        out: dict[str, Any] = {
            "n": 0,
            "rates": {method: dict(undefined) for method in M9_METHODS},
            "contrasts": contrasts,
        }
        if include_m8:
            out["m8_joint_rate"] = _undefined_ratio(UNDEFINED_EMPTY)
        return out

    ids = [c.base_case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise MetricInvariantError("M9 cell contains duplicate base latent case_id")
    for case in cases:
        _require_methods(case, M9_METHODS)

    rates: dict[str, Any] = {}
    for method in M9_METHODS:
        method_rates = {}
        for outcome in THREE_WAY_CATEGORIES:
            numerator = sum(int(c.scores[method].category == outcome) for c in cases)
            method_rates[outcome] = _defined_ratio(numerator, len(cases))
        total = sum(method_rates[y]["value"] for y in THREE_WAY_CATEGORIES)
        if not math.isclose(float(total), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise MetricInvariantError("M9 three-way probabilities do not sum to one")
        rates[method] = method_rates

    pair_defs = {
        "B6-B5": ("B6", "B5"),
        "B5M-B5": ("B5M", "B5"),
        "B6-B5M": ("B6", "B5M"),
    }
    contrasts: dict[str, Any] = {}
    for label, (a, b) in pair_defs.items():
        contrasts[label] = {}
        for outcome in THREE_WAY_CATEGORIES:
            d = np.asarray(
                [_indicator(c, a, outcome) - _indicator(c, b, outcome) for c in cases],
                dtype=np.float64,
            )
            contrasts[label][outcome] = _scalar(
                status=DEFINED, n=len(cases), value=float(np.mean(d, dtype=np.float64))
            )

    out = {"n": len(cases), "rates": rates, "contrasts": contrasts}
    if include_m8:
        eligible = [c for c in cases if c.b5_eligible]
        if not eligible:
            out["m8_joint_rate"] = _undefined_ratio(UNDEFINED_EMPTY)
        else:
            num = sum(
                int(c.scores["B5"].category == CLAIM_HIT and c.scores["B6"].category == NO_CLAIM)
                for c in eligible
            )
            out["m8_joint_rate"] = _defined_ratio(num, len(eligible))
    return out


def _dedupe_m9(cases: Sequence[ScoredCase]) -> list[ScoredCase]:
    """Deduplicate only the permitted base/(0,0) alias by base latent identity."""

    by_id: dict[str, ScoredCase] = {}
    for case in sorted(cases, key=lambda c: (c.base_case_id, c.case_id)):
        existing = by_id.get(case.base_case_id)
        if existing is None:
            by_id[case.base_case_id] = case
            continue
        if not _m9_same_semantics(existing, case):
            raise MetricInvariantError("duplicate M9 base identity disagrees semantically")
        # Exact semantic aliases are counted once. Prefer explicit support (0,0)
        # representation if present, but this choice cannot change metrics.
        if case.variant_kind == "support" and case.fn_rate == 0.0 and case.fp_rate == 0.0:
            by_id[case.base_case_id] = case
    return list(by_id.values())


def m9_report(cases: Sequence[ScoredCase], *, include_pooled: bool = False) -> dict[str, Any]:
    """Canonical F1-F4 3x3 support-error grid plus separate D1/D2/D3 strata."""

    illegal_families = {c.family for c in cases if c.family not in M9_FAMILIES}
    if illegal_families:
        raise MetricInvariantError(f"canonical M9 accepts F1-F4 only, got {sorted(illegal_families)}")

    families: dict[str, Any] = {}
    for family in M9_FAMILIES:
        fam_cases = [c for c in cases if c.family == family]
        grid: dict[str, Any] = {}
        for fn in M9_RATES:
            for fp in M9_RATES:
                raw = [
                    c
                    for c in fam_cases
                    if (
                        (c.variant_kind == "support" and c.fn_rate == fn and c.fp_rate == fp)
                        or (fn == 0.0 and fp == 0.0 and c.variant_kind == "base")
                    )
                ]
                cell = _dedupe_m9(raw)
                grid[f"FN={fn:.2f}|FP={fp:.2f}"] = _m9_cell_payload(cell, include_m8=True)
        decoys: dict[str, Any] = {}
        for decoy in M9_DECOYS:
            raw = [c for c in fam_cases if c.variant_kind == "decoy" and c.decoy == decoy]
            decoys[decoy] = _m9_cell_payload(_dedupe_m9(raw), include_m8=False)
        families[family] = {"grid": grid, "decoys": decoys}

    out: dict[str, Any] = {"families": families}
    if include_pooled:
        pooled_grid: dict[str, Any] = {}
        for fn in M9_RATES:
            for fp in M9_RATES:
                raw = [
                    c
                    for c in cases
                    if (
                        (c.variant_kind == "support" and c.fn_rate == fn and c.fp_rate == fp)
                        or (fn == 0.0 and fp == 0.0 and c.variant_kind == "base")
                    )
                ]
                pooled_grid[f"FN={fn:.2f}|FP={fp:.2f}"] = _m9_cell_payload(_dedupe_m9(raw), include_m8=True)
        pooled_decoys = {
            d: _m9_cell_payload(_dedupe_m9([c for c in cases if c.variant_kind == "decoy" and c.decoy == d]), include_m8=False)
            for d in M9_DECOYS
        }
        out["pooled_descriptive"] = {"grid": pooled_grid, "decoys": pooled_decoys}
    return out


# ---------------------------------------------------------------------------
# M10/H7 acquisition-edge population (v1.6)
# ---------------------------------------------------------------------------


def h7_membership(case: ScoredCase) -> tuple[bool, str | None]:
    """Return canonical H7-set membership and primary truth class."""

    if case.family != "F6":
        return False, None
    if case.full_left is None or case.full_right is None:
        raise MetricInvariantError("F6 H7 classification requires frozen acquisition span")
    temporal_outside = case.truth_time < case.full_left or case.truth_time > case.full_right
    if temporal_outside:
        return True, "temporal_acquisition_edge"
    if case.edge_type in PURE_SPATIAL_EDGE_TYPES:
        if case.edge_px is None:
            raise MetricInvariantError("pure-spatial F6 case requires edge_px")
        if case.edge_px < SPATIAL_MARGIN_PX:
            return True, "spatial_acquisition_edge"
    return False, None


def _m10_class(outcome: BaselineOutcome) -> str:
    if outcome.status == "censored":
        return "correct_censoring"
    if outcome.status == "finite_claim":
        return "incorrect_internal_finite_claim"
    if outcome.status == "no_claim":
        return "other_no_claim"
    raise MetricInvariantError("output status outside accepted A4 vocabulary")


def m10_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    """Frozen M10 report and canonical paired H7 case inventory."""

    h7: list[tuple[ScoredCase, str]] = []
    spatial_controls: list[ScoredCase] = []
    for case in cases:
        if case.family != "F6":
            continue
        member, truth_class = h7_membership(case)
        if member:
            assert truth_class is not None
            h7.append((case, truth_class))
        elif case.edge_type in PURE_SPATIAL_EDGE_TYPES and case.edge_px in {2, 3}:
            spatial_controls.append(case)

    if not h7:
        h7_report: dict[str, Any] = {
            "status": UNDEFINED_INFERENTIAL,
            "n": 0,
            "methods": {
                m: {
                    "correct_censoring": _undefined_ratio(UNDEFINED_EMPTY),
                    "incorrect_internal_finite_claim": _undefined_ratio(UNDEFINED_EMPTY),
                    "other_no_claim": _undefined_ratio(UNDEFINED_EMPTY),
                }
                for m in ("B5", "B6")
            },
            "case_ids": [],
        }
    else:
        ids = [c.base_case_id for c, _ in h7]
        if len(ids) != len(set(ids)):
            raise MetricInvariantError("mixed/duplicate F6 case entered H7 more than once")
        method_report: dict[str, Any] = {}
        for method in ("B5", "B6"):
            classes = []
            for case, _ in h7:
                _require_methods(case, (method,))
                classes.append(_m10_class(case.outcomes[method]))
            method_report[method] = {
                label: _defined_ratio(sum(v == label for v in classes), len(classes))
                for label in ("correct_censoring", "incorrect_internal_finite_claim", "other_no_claim")
            }
        h7_report = {
            "status": DEFINED,
            "n": len(h7),
            "methods": method_report,
            "case_ids": sorted(ids),
            "truth_class_by_case": {c.base_case_id: cls for c, cls in h7},
        }

    spatial_truth_strata: dict[str, Any] = {}
    pure_spatial = [c for c in cases if c.family == "F6" and c.edge_type in PURE_SPATIAL_EDGE_TYPES]
    for edge_type in sorted(PURE_SPATIAL_EDGE_TYPES):
        stratum = [c for c in pure_spatial if c.edge_type == edge_type]
        if not stratum:
            continue
        b6_values = []
        b5_classes = []
        for case in stratum:
            _require_methods(case, ("B5", "B6"))
            b6 = case.outcomes["B6"]
            b6_values.append(
                int(
                    b6.status == "censored"
                    and b6.b6_decision is not None
                    and b6.b6_decision.boundary == "spatial"
                )
            )
            b5_classes.append(_m10_class(case.outcomes["B5"]))
        spatial_truth_strata[edge_type] = {
            "n": len(stratum),
            "spatial_type_correct_B6": _defined_ratio(sum(b6_values), len(stratum)),
            "B5": {
                "p_censored": _defined_ratio(sum(v == "correct_censoring" for v in b5_classes), len(stratum)),
                "p_finite_claim": _defined_ratio(sum(v == "incorrect_internal_finite_claim" for v in b5_classes), len(stratum)),
                "p_no_claim": _defined_ratio(sum(v == "other_no_claim" for v in b5_classes), len(stratum)),
                "predicted_spatial_type": {"status": NOT_OBSERVABLE, "n": len(stratum), "value": None},
                "predicted_spatial_side": {"status": NOT_OBSERVABLE, "n": len(stratum), "value": None},
            },
            "B6": {
                "predicted_spatial_side": {"status": NOT_OBSERVABLE, "n": len(stratum), "value": None}
            },
        }

    controls_by_stratum: dict[str, Any] = {}
    for case in spatial_controls:
        _require_methods(case, ("B5", "B6"))
        key = f"{case.edge_type}|edge_px={case.edge_px}"
        controls_by_stratum.setdefault(key, []).append(case)
    control_report: dict[str, Any] = {}
    for key, subset in controls_by_stratum.items():
        method_report = {}
        for method in ("B5", "B6"):
            classes = [_m10_class(c.outcomes[method]) for c in subset]
            method_report[method] = {
                "p_censored": _defined_ratio(sum(v == "correct_censoring" for v in classes), len(subset)),
                "p_finite_claim": _defined_ratio(sum(v == "incorrect_internal_finite_claim" for v in classes), len(subset)),
                "p_no_claim": _defined_ratio(sum(v == "other_no_claim" for v in classes), len(subset)),
            }
        control_report[key] = {"n": len(subset), "methods": method_report}

    return {
        "h7_set": h7_report,
        "spatial_truth_strata": spatial_truth_strata,
        "pure_spatial_internal_controls": control_report,
    }


# ---------------------------------------------------------------------------
# Deterministic paired statistical engine (v1.1)
# ---------------------------------------------------------------------------


def metric_seed64(kind: str, hypothesis_id: str, family_id: str) -> int:
    """Exact v1.1 SHA-256 -> first-8-byte unsigned big-endian seed."""

    if kind not in {"bootstrap", "permutation"}:
        raise MetricInvariantError("seed kind must be bootstrap or permutation")
    if hypothesis_id not in HYPOTHESIS_FAMILY_TOKENS:
        raise MetricInvariantError("unknown frozen hypothesis_id")
    if family_id not in HYPOTHESIS_FAMILY_TOKENS[hypothesis_id]:
        raise MetricInvariantError("family_id is not frozen for this hypothesis")
    payload = (
        FROZEN_CONTRACT_HASH.encode("ascii")
        + (b"metric-bootstrap" if kind == "bootstrap" else b"metric-permutation")
        + hypothesis_id.encode("ascii")
        + family_id.encode("ascii")
    )
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def bootstrap_indices(n: int, hypothesis_id: str, family_id: str) -> np.ndarray:
    if n <= 0:
        raise MetricInvariantError("bootstrap requires a positive latent-case count")
    rng = np.random.Generator(np.random.PCG64(metric_seed64("bootstrap", hypothesis_id, family_id)))
    return rng.integers(
        low=0,
        high=n,
        size=(BOOTSTRAP_RESAMPLES, n),
        dtype=np.int64,
        endpoint=False,
    )


def permutation_signs(n: int, hypothesis_id: str, family_id: str) -> np.ndarray:
    if n <= 0:
        raise MetricInvariantError("permutation requires a positive latent-case count")
    rng = np.random.Generator(np.random.PCG64(metric_seed64("permutation", hypothesis_id, family_id)))
    bits = rng.integers(
        low=0,
        high=2,
        size=(PERMUTATIONS, n),
        dtype=np.int8,
        endpoint=False,
    )
    return 2 * bits.astype(np.int8) - 1


def _canonical_differences(differences_by_case: Mapping[str, float]) -> tuple[tuple[str, ...], np.ndarray]:
    if not differences_by_case:
        return tuple(), np.asarray([], dtype=np.float64)
    normalized: dict[str, float] = {}
    for raw_id, raw_value in differences_by_case.items():
        case_id = str(raw_id).lower()
        _validate_case_id(case_id)
        if case_id in normalized:
            raise MetricInvariantError("duplicate canonical latent-case identity")
        value = float(raw_value)
        if not math.isfinite(value):
            raise MetricInvariantError("paired case-level contribution must be finite")
        normalized[case_id] = value
    ids = tuple(sorted(normalized))
    return ids, np.asarray([normalized[i] for i in ids], dtype=np.float64)


def paired_bootstrap_mean(
    differences_by_case: Mapping[str, float],
    *,
    hypothesis_id: str,
    family_id: str,
) -> dict[str, Any]:
    """Paired percentile bootstrap for the mean case-level statistic."""

    ids, d = _canonical_differences(differences_by_case)
    if d.size == 0:
        return _undefined_inferential("empty frozen conditioning set")
    index = bootstrap_indices(int(d.size), hypothesis_id, family_id)
    replicates = np.mean(d[index], axis=1, dtype=np.float64)
    estimate = float(np.mean(d, dtype=np.float64))
    q05 = float(np.quantile(replicates, 0.05, method="linear"))
    q95 = float(np.quantile(replicates, 0.95, method="linear"))
    return {
        "status": DEFINED,
        "n": int(d.size),
        "case_ids": list(ids),
        "estimate": estimate,
        "ci90": [q05, q95],
        "lower95": q05,
        "upper95": q95,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    }


def paired_random_sign_pvalue(
    differences_by_case: Mapping[str, float],
    *,
    hypothesis_id: str,
    family_id: str,
) -> dict[str, Any]:
    """Frozen one-sided positive-direction paired random-sign Monte-Carlo test."""

    ids, d = _canonical_differences(differences_by_case)
    if d.size == 0:
        return {"status": UNDEFINED_INFERENTIAL, "n": 0, "case_ids": [], "p_raw": None}
    signs = permutation_signs(int(d.size), hypothesis_id, family_id)
    observed = float(np.mean(d, dtype=np.float64))
    perm = np.mean(signs * d[None, :], axis=1, dtype=np.float64)
    b = int(np.count_nonzero(perm >= observed))
    p_raw = float((b + 1) / (PERMUTATIONS + 1))
    return {
        "status": DEFINED,
        "n": int(d.size),
        "case_ids": list(ids),
        "observed": observed,
        "tail_count_b": b,
        "permutations": PERMUTATIONS,
        "p_raw": p_raw,
    }


def holm_adjust(raw_p_by_family: Mapping[str, float | None]) -> dict[str, float | None]:
    """Exact frozen four-family Holm rule with deterministic F1<F2<F3<F4 ties."""

    if set(raw_p_by_family) != set(HOLM_FAMILIES):
        raise MetricInvariantError("Holm block must contain exactly F1,F2,F3,F4")
    if any(raw_p_by_family[f] is None for f in HOLM_FAMILIES):
        return {f: None for f in HOLM_FAMILIES}
    values: dict[str, float] = {}
    for family in HOLM_FAMILIES:
        p = float(raw_p_by_family[family])  # type: ignore[arg-type]
        if not 0.0 <= p <= 1.0 or not math.isfinite(p):
            raise MetricInvariantError("raw p-values must be finite in [0,1]")
        values[family] = p
    order_index = {f: i for i, f in enumerate(HOLM_FAMILIES)}
    ordered = sorted(HOLM_FAMILIES, key=lambda f: (values[f], order_index[f]))
    running = 0.0
    adjusted_sorted: dict[str, float] = {}
    m = 4
    for rank, family in enumerate(ordered, start=1):
        a = (m - rank + 1) * values[family]
        running = min(1.0, max(running, a))
        adjusted_sorted[family] = float(running)
    return {f: adjusted_sorted[f] for f in HOLM_FAMILIES}


# ---------------------------------------------------------------------------
# Mechanical verdict primitives
# ---------------------------------------------------------------------------


def h1_verdict(*, miss_ci90: Sequence[float] | None, hit_ci90: Sequence[float] | None) -> str:
    if miss_ci90 is None or hit_ci90 is None:
        return INCONCLUSIVE
    miss_lo, miss_hi = map(float, miss_ci90)
    hit_lo, hit_hi = map(float, hit_ci90)
    miss_inside = miss_lo >= -0.03 and miss_hi <= 0.03
    hit_inside = hit_lo >= -0.05 and hit_hi <= 0.05
    if miss_inside and hit_inside:
        return SUPPORTED
    miss_outside = miss_hi < -0.03 or miss_lo > 0.03
    hit_outside = hit_hi < -0.05 or hit_lo > 0.05
    if miss_outside or hit_outside:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h2_verdict(*, estimate: float | None, lower95: float | None, upper95: float | None, p_holm: float | None) -> str:
    if None in (estimate, lower95, upper95, p_holm):
        return INCONCLUSIVE
    if float(estimate) >= 0.05 and float(lower95) > 0.0 and float(p_holm) < 0.05:
        return SUPPORTED
    if float(upper95) < 0.05:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h3_verdict(
    *,
    hit_estimate: float | None,
    hit_lower95: float | None,
    hit_upper95: float | None,
    hit_p_holm: float | None,
    miss_lower95: float | None,
    miss_upper95: float | None,
) -> str:
    values = (hit_estimate, hit_lower95, hit_upper95, hit_p_holm, miss_lower95, miss_upper95)
    if any(v is None for v in values):
        return INCONCLUSIVE
    if (
        float(hit_estimate) >= 0.05
        and float(hit_lower95) > 0.0
        and float(hit_p_holm) < 0.05
        and float(miss_upper95) <= 0.02
    ):
        return SUPPORTED
    if float(hit_upper95) < 0.05 or float(miss_lower95) > 0.02:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h4_verdict(
    *,
    miss_estimate: float | None,
    miss_lower95: float | None,
    miss_upper95: float | None,
    miss_p_holm: float | None,
    hit_lower95: float | None,
    hit_upper95: float | None,
) -> str:
    values = (miss_estimate, miss_lower95, miss_upper95, miss_p_holm, hit_lower95, hit_upper95)
    if any(v is None for v in values):
        return INCONCLUSIVE
    if (
        float(miss_estimate) >= 0.05
        and float(miss_lower95) > 0.0
        and float(miss_p_holm) < 0.05
        and float(hit_lower95) >= -0.05
    ):
        return SUPPORTED
    if float(miss_upper95) < 0.05 or float(hit_upper95) < -0.05:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h5_verdict(*, lower95: float | None, upper95: float | None) -> str:
    if lower95 is None or upper95 is None:
        return INCONCLUSIVE
    if float(upper95) <= 0.03:
        return SUPPORTED
    if float(lower95) > 0.03:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h6_verdict(*, estimate: float | None, lower95: float | None, upper95: float | None, p_holm: float | None) -> str:
    if None in (estimate, lower95, upper95, p_holm):
        return INCONCLUSIVE
    if float(estimate) > 0.0 and float(lower95) > 0.0 and float(p_holm) < 0.05:
        return SUPPORTED
    if float(upper95) <= 0.0:
        return NOT_SUPPORTED
    return INCONCLUSIVE


def h7_verdict(*, lower95: float | None, upper95: float | None) -> str:
    if lower95 is None or upper95 is None:
        return INCONCLUSIVE
    if float(upper95) <= 0.02:
        return SUPPORTED
    if float(lower95) > 0.02:
        return NOT_SUPPORTED
    return INCONCLUSIVE


# ---------------------------------------------------------------------------
# H1-H7 frozen reports from ScoredCase collections
# ---------------------------------------------------------------------------


def _base_family_cases(cases: Sequence[ScoredCase], family: str) -> list[ScoredCase]:
    return [c for c in cases if c.family == family and c.variant_kind == "base"]


def _diff_map(cases: Sequence[ScoredCase], a: str, b: str, category: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for case in cases:
        _require_methods(case, (a, b))
        if case.base_case_id in out:
            raise MetricInvariantError("duplicate base latent identity in paired hypothesis set")
        out[case.base_case_id] = _indicator(case, a, category) - _indicator(case, b, category)
    return out


def h1_report(cases: Sequence[ScoredCase], *, hypothesis_id: str) -> dict[str, Any]:
    if hypothesis_id not in {"H1A", "H1B"}:
        raise MetricInvariantError("H1 report requires H1A or H1B")
    family = "F0" if hypothesis_id == "H1A" else "F0b"
    subset = [c for c in _base_family_cases(cases, family) if c.b5_eligible]
    miss = paired_bootstrap_mean(
        _diff_map(subset, "B6", "B5", CLAIM_MISS),
        hypothesis_id=hypothesis_id,
        family_id=family,
    )
    hit = paired_bootstrap_mean(
        _diff_map(subset, "B6", "B5", CLAIM_HIT),
        hypothesis_id=hypothesis_id,
        family_id=family,
    )
    verdict = h1_verdict(miss_ci90=miss.get("ci90"), hit_ci90=hit.get("ci90"))
    status = DEFINED if miss.get("status") == DEFINED and hit.get("status") == DEFINED else UNDEFINED_INFERENTIAL
    result = {
        "hypothesis": hypothesis_id,
        "family": family,
        "method_pair": ["B6", "B5"],
        "status": status,
        "n": len(subset),
        "D_miss": miss,
        "D_hit": hit,
        "verdict": verdict,
    }
    if hypothesis_id == "H1B":
        result["descriptive_F0b_N_S"] = h1b_descriptive_strata_report(cases)
    return result


def _holm_hypothesis_block(
    cases_by_family: Mapping[str, Sequence[ScoredCase]],
    *,
    hypothesis_id: str,
    permutation_diff_builder: Any,
) -> tuple[dict[str, Any], dict[str, float | None], list[str]]:
    family_stats: dict[str, Any] = {}
    raw: dict[str, float | None] = {}
    undefined: list[str] = []
    for family in HOLM_FAMILIES:
        diffs = permutation_diff_builder(cases_by_family[family])
        perm = paired_random_sign_pvalue(diffs, hypothesis_id=hypothesis_id, family_id=family)
        family_stats[family] = perm
        raw[family] = perm.get("p_raw")
        if perm.get("status") != DEFINED:
            undefined.append(family)
    holm = holm_adjust(raw)
    return family_stats, holm, undefined


def h1b_descriptive_strata_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    """Descriptive F0b-N/F0b-S subreports; no replacement H1 verdicts."""

    f0b = [c for c in _base_family_cases(cases, "F0b") if c.b5_eligible]
    out: dict[str, Any] = {}
    for mechanism in ("N", "S"):
        token = f"mechanism={mechanism}"
        subset = [c for c in f0b if token in c.stratum.split(";")]
        for case in subset:
            _require_methods(case, ("B5", "B6"))
        marginal: dict[str, Any] = {}
        for method in ("B5", "B6"):
            scores = [c.scores[method] for c in subset]
            marginal[method] = three_way_summary(scores)
        miss = paired_bootstrap_mean(
            _diff_map(subset, "B6", "B5", CLAIM_MISS),
            hypothesis_id="H1B",
            family_id="F0b",
        )
        hit = paired_bootstrap_mean(
            _diff_map(subset, "B6", "B5", CLAIM_HIT),
            hypothesis_id="H1B",
            family_id="F0b",
        )
        out[mechanism] = {
            "status": DEFINED if subset else UNDEFINED_EMPTY,
            "n": len(subset),
            "marginal_three_way": marginal,
            "D_miss_B6_minus_B5": miss,
            "D_hit_B6_minus_B5": hit,
            "replacement_hypothesis": False,
            "verdict": None,
        }
    return out


def h2_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    by_family = {f: _base_family_cases(cases, f) for f in HOLM_FAMILIES}
    permutations, holm, undefined = _holm_hypothesis_block(
        by_family,
        hypothesis_id="H2",
        permutation_diff_builder=lambda xs: _diff_map(xs, "B5", "B5M", CLAIM_MISS),
    )
    results: dict[str, Any] = {}
    for family in HOLM_FAMILIES:
        boot = paired_bootstrap_mean(
            _diff_map(by_family[family], "B5", "B5M", CLAIM_MISS),
            hypothesis_id="H2",
            family_id=family,
        )
        p_holm = holm[family]
        verdict = INCONCLUSIVE if undefined else h2_verdict(
            estimate=boot.get("estimate"), lower95=boot.get("lower95"), upper95=boot.get("upper95"), p_holm=p_holm
        )
        results[family] = {
            "D_miss": boot,
            "p_raw": permutations[family].get("p_raw"),
            "p_holm": p_holm,
            "verdict": verdict,
        }
    return {
        "hypothesis": "H2",
        "status": UNDEFINED_INFERENTIAL if undefined else DEFINED,
        "undefined_families": undefined,
        "families": results,
    }


def h3_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    by_family = {f: _base_family_cases(cases, f) for f in HOLM_FAMILIES}
    permutations, holm, undefined = _holm_hypothesis_block(
        by_family,
        hypothesis_id="H3",
        permutation_diff_builder=lambda xs: _diff_map(xs, "B6", "B5M", CLAIM_HIT),
    )
    results: dict[str, Any] = {}
    for family in HOLM_FAMILIES:
        hit = paired_bootstrap_mean(
            _diff_map(by_family[family], "B6", "B5M", CLAIM_HIT), hypothesis_id="H3", family_id=family
        )
        miss = paired_bootstrap_mean(
            _diff_map(by_family[family], "B6", "B5M", CLAIM_MISS), hypothesis_id="H3", family_id=family
        )
        p_holm = holm[family]
        verdict = INCONCLUSIVE if undefined else h3_verdict(
            hit_estimate=hit.get("estimate"),
            hit_lower95=hit.get("lower95"),
            hit_upper95=hit.get("upper95"),
            hit_p_holm=p_holm,
            miss_lower95=miss.get("lower95"),
            miss_upper95=miss.get("upper95"),
        )
        results[family] = {
            "D_hit": hit,
            "D_miss": miss,
            "p_raw_hit": permutations[family].get("p_raw"),
            "p_holm_hit": p_holm,
            "verdict": verdict,
        }
    return {
        "hypothesis": "H3",
        "status": UNDEFINED_INFERENTIAL if undefined else DEFINED,
        "undefined_families": undefined,
        "families": results,
    }


def h4_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    by_family = {f: _base_family_cases(cases, f) for f in HOLM_FAMILIES}
    permutations, holm, undefined = _holm_hypothesis_block(
        by_family,
        hypothesis_id="H4",
        permutation_diff_builder=lambda xs: _diff_map(xs, "B5", "B6", CLAIM_MISS),
    )
    results: dict[str, Any] = {}
    for family in HOLM_FAMILIES:
        miss = paired_bootstrap_mean(
            _diff_map(by_family[family], "B5", "B6", CLAIM_MISS), hypothesis_id="H4", family_id=family
        )
        hit = paired_bootstrap_mean(
            _diff_map(by_family[family], "B6", "B5", CLAIM_HIT), hypothesis_id="H4", family_id=family
        )
        p_holm = holm[family]
        verdict = INCONCLUSIVE if undefined else h4_verdict(
            miss_estimate=miss.get("estimate"),
            miss_lower95=miss.get("lower95"),
            miss_upper95=miss.get("upper95"),
            miss_p_holm=p_holm,
            hit_lower95=hit.get("lower95"),
            hit_upper95=hit.get("upper95"),
        )
        results[family] = {
            "D_miss": miss,
            "D_hit": hit,
            "p_raw_miss": permutations[family].get("p_raw"),
            "p_holm_miss": p_holm,
            "verdict": verdict,
        }
    return {
        "hypothesis": "H4",
        "status": UNDEFINED_INFERENTIAL if undefined else DEFINED,
        "undefined_families": undefined,
        "families": results,
    }


def h5_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    m8 = m8_report(cases)
    indicators = m8.get("case_indicators", {})
    boot = paired_bootstrap_mean(indicators, hypothesis_id="H5", family_id="F0+F0b")
    verdict = h5_verdict(lower95=boot.get("lower95"), upper95=boot.get("upper95"))
    return {"hypothesis": "H5", "M8": m8, "bootstrap": boot, "verdict": verdict}


def h6_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    by_family: dict[str, list[ScoredCase]] = {}
    for family in HOLM_FAMILIES:
        raw = [
            c
            for c in cases
            if c.family == family and c.variant_kind == "support" and c.fn_rate == 0.10 and c.fp_rate == 0.10
        ]
        by_family[family] = _dedupe_m9(raw)
    permutations, holm, undefined = _holm_hypothesis_block(
        by_family,
        hypothesis_id="H6",
        permutation_diff_builder=lambda xs: _diff_map(xs, "B5", "B6", CLAIM_MISS),
    )
    results: dict[str, Any] = {}
    for family in HOLM_FAMILIES:
        boot = paired_bootstrap_mean(
            _diff_map(by_family[family], "B5", "B6", CLAIM_MISS), hypothesis_id="H6", family_id=family
        )
        p_holm = holm[family]
        verdict = INCONCLUSIVE if undefined else h6_verdict(
            estimate=boot.get("estimate"), lower95=boot.get("lower95"), upper95=boot.get("upper95"), p_holm=p_holm
        )
        results[family] = {
            "D_miss": boot,
            "p_raw": permutations[family].get("p_raw"),
            "p_holm": p_holm,
            "verdict": verdict,
        }
    return {
        "hypothesis": "H6",
        "status": UNDEFINED_INFERENTIAL if undefined else DEFINED,
        "undefined_families": undefined,
        "families": results,
    }


def h7_report(cases: Sequence[ScoredCase]) -> dict[str, Any]:
    selected: list[ScoredCase] = []
    for case in cases:
        member, _ = h7_membership(case)
        if member:
            selected.append(case)
    ids = [c.base_case_id for c in selected]
    if len(ids) != len(set(ids)):
        raise MetricInvariantError("H7 set contains duplicate base latent identity")
    if not selected:
        return {
            "hypothesis": "H7",
            "status": UNDEFINED_INFERENTIAL,
            "D_internal": _undefined_inferential("empty canonical H7 conditioning set"),
            "correct_censoring": {
                "status": UNDEFINED_INFERENTIAL,
                "P_correct_B5": None,
                "P_correct_B6": None,
                "D_correct": None,
                "D_correct_90CI": None,
            },
            "verdict": INCONCLUSIVE,
            "reason": "empty canonical H7 conditioning set",
        }
    for case in selected:
        _require_methods(case, ("B5", "B6"))
    internal = {
        c.base_case_id: float(c.outcomes["B6"].status == "finite_claim")
        - float(c.outcomes["B5"].status == "finite_claim")
        for c in selected
    }
    d_internal = paired_bootstrap_mean(internal, hypothesis_id="H7", family_id="F6")
    verdict = h7_verdict(lower95=d_internal.get("lower95"), upper95=d_internal.get("upper95"))

    c_b5 = np.asarray([float(c.outcomes["B5"].status == "censored") for c in selected], dtype=np.float64)
    c_b6 = np.asarray([float(c.outcomes["B6"].status == "censored") for c in selected], dtype=np.float64)
    d_correct_map = {
        c.base_case_id: float(b6 - b5) for c, b5, b6 in zip(selected, c_b5, c_b6)
    }
    correct_boot = paired_bootstrap_mean(d_correct_map, hypothesis_id="H7", family_id="F6")
    return {
        "hypothesis": "H7",
        "status": DEFINED,
        "n": len(selected),
        "D_internal": d_internal,
        "correct_censoring": {
            "status": DEFINED,
            "P_correct_B5": float(np.mean(c_b5, dtype=np.float64)),
            "P_correct_B6": float(np.mean(c_b6, dtype=np.float64)),
            "D_correct": correct_boot.get("estimate"),
            "D_correct_90CI": correct_boot.get("ci90"),
            "bootstrap_resamples": correct_boot.get("bootstrap_resamples"),
            "permutation": None,
            "holm": None,
        },
        "verdict": verdict,
    }
