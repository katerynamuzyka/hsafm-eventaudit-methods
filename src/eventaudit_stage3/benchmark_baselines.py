"""Development-only Stage-3A.4 benchmark baselines and common dispatch.

This module implements B1-B5/B5M plus the representation-only B1-B6 interface.
The accepted B6 scientific core is imported from :mod:`eventaudit_stage3.baselines`
and is not reimplemented here.  A5 scoring, held-out execution, and Stage 3B/3C
remain intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Mapping, Sequence

from .boundary_record import validate_method_visible_record
from .baselines import (
    B6Decision,
    MIN_MEASURED_FRAC,
    SPATIAL_MARGIN_PX,
    THETA,
    evaluate_b6_boundary,
)

class BaselineInputError(ValueError):
    """Raised when a frozen baseline cannot be evaluated from supplied method records."""


@dataclass(frozen=True)
class BaselineOutcome:
    """Representation-only common boundary outcome for B1-B6.

    ``status`` is one of the frozen target-boundary categories: ``finite_claim``,
    ``censored`` or ``no_claim``.  Finite claims always represent ``(L,R]`` in raw
    frame units.  ``reason`` is populated only where frozen authority specifies a
    no-claim reason.  ``b6_decision`` retains the accepted inherited B6 result when
    B6 is dispatched; no B6 scientific rule is duplicated here.
    """

    method: str
    case_id: str
    target_side: str
    status: str
    left_frame: int | None = None
    right_frame: int | None = None
    anchor_frame: int | None = None
    reason: str | None = None
    b6_decision: B6Decision | None = None

    def __post_init__(self) -> None:
        if self.status not in {"finite_claim", "censored", "no_claim"}:
            raise ValueError(f"unknown baseline status {self.status!r}")
        finite = self.status == "finite_claim"
        if finite != (self.left_frame is not None and self.right_frame is not None):
            raise ValueError("finite_claim requires both L/R and non-finite outcomes require neither")
        if finite and not self.left_frame < self.right_frame:
            raise ValueError("finite claim must satisfy L < R")


@dataclass(frozen=True)
class B4bReference:
    """Frozen B4b finite-window population-reference calculation."""

    n: int
    t: int
    b_start: int
    b_end: int
    effective_n: int
    p_complete: float


@dataclass(frozen=True)
class _PreparedRecords:
    rows: tuple[Mapping[str, Any], ...]
    by_frame: Mapping[int, Mapping[str, Any]]
    case_id: str
    target_side: str
    min_frame: int
    max_frame: int


# Explicit A4 declaration for static truth-isolation/whitelist tests.  The
# implementation uses no truth/construction field.
A4_METHOD_KEYS_USED = frozenset(
    {
        "case_id",
        "target_side",
        "frame",
        "t0_event_id",
        "t0_track_id",
        "t0_detection_state",
        "production_good",
        "secondary_qc_bad",
        "measured_frac",
        "registration_supported",
        "b5_peak",
        "edge_px",
        "movie_boundary",
    }
)


def _prepare_records(
    records: Sequence[Mapping[str, Any]],
    target_side: str | None,
) -> _PreparedRecords:
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence) or not records:
        raise BaselineInputError("records must be a non-empty sequence of method-visible rows")

    validated = []
    for row in records:
        validate_method_visible_record(row)
        validated.append(row)

    first = validated[0]
    side = str(first["target_side"] if target_side is None else target_side)
    if side not in {"endpoint", "onset"}:
        raise BaselineInputError("target_side must be 'endpoint' or 'onset'")

    case_id = str(first["case_id"])
    event_id = first["t0_event_id"]
    track_id = first["t0_track_id"]
    by_frame: dict[int, Mapping[str, Any]] = {}
    for row in validated:
        if row["target_side"] != side:
            raise BaselineInputError("records mix target sides or disagree with requested target_side")
        if row["case_id"] != case_id:
            raise BaselineInputError("records mix opaque case_id values")
        if row["t0_event_id"] != event_id or row["t0_track_id"] != track_id:
            raise BaselineInputError("records mix common-T0 event/track identities")
        frame = int(row["frame"])
        if frame in by_frame:
            raise BaselineInputError(f"duplicate raw-frame record {frame}")
        by_frame[frame] = row

    rows = tuple(by_frame[f] for f in sorted(by_frame))
    frames = tuple(by_frame)
    return _PreparedRecords(
        rows=rows,
        by_frame=by_frame,
        case_id=case_id,
        target_side=side,
        min_frame=min(frames),
        max_frame=max(frames),
    )


def _is_accepted(row: Mapping[str, Any]) -> bool:
    return row["t0_detection_state"] == "accepted"


def _accepted_rows(prepared: _PreparedRecords) -> tuple[Mapping[str, Any], ...]:
    accepted = tuple(row for row in prepared.rows if _is_accepted(row))
    if not accepted:
        raise BaselineInputError("baseline requires at least one accepted target-event T0 detection")
    return accepted


def _common_anchor(prepared: _PreparedRecords) -> int:
    frames = [int(row["frame"]) for row in _accepted_rows(prepared)]
    return max(frames) if prepared.target_side == "endpoint" else min(frames)


def _step(target_side: str) -> int:
    return 1 if target_side == "endpoint" else -1


def _finite_outcome(method: str, prepared: _PreparedRecords, anchor: int) -> BaselineOutcome:
    step = _step(prepared.target_side)
    adjacent = anchor + step
    lo, hi = sorted((anchor, adjacent))
    return BaselineOutcome(
        method=method,
        case_id=prepared.case_id,
        target_side=prepared.target_side,
        status="finite_claim",
        left_frame=lo,
        right_frame=hi,
        anchor_frame=anchor,
    )


def _censored_outcome(method: str, prepared: _PreparedRecords, anchor: int) -> BaselineOutcome:
    return BaselineOutcome(
        method=method,
        case_id=prepared.case_id,
        target_side=prepared.target_side,
        status="censored",
        anchor_frame=anchor,
    )


def _no_claim_outcome(
    method: str,
    prepared: _PreparedRecords,
    anchor: int,
    reason: str | None = None,
) -> BaselineOutcome:
    return BaselineOutcome(
        method=method,
        case_id=prepared.case_id,
        target_side=prepared.target_side,
        status="no_claim",
        anchor_frame=anchor,
        reason=reason,
    )


def _adjacent_raw_exists(prepared: _PreparedRecords, anchor: int) -> bool:
    return anchor + _step(prepared.target_side) in prepared.by_frame


def evaluate_b1(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    """Frozen B1: common-T0 detector-adjacent mapping, otherwise raw-edge censoring."""
    prepared = _prepare_records(records, target_side)
    anchor = _common_anchor(prepared)
    if not _adjacent_raw_exists(prepared, anchor):
        return _censored_outcome("B1", prepared, anchor)
    return _finite_outcome("B1", prepared, anchor)


def _b2_bridged_anchor(prepared: _PreparedRecords, miss_budget: int) -> int:
    """Return the target-side accepted frame reachable under frozen B2 gap handling."""
    ordered = prepared.rows if prepared.target_side == "endpoint" else tuple(reversed(prepared.rows))
    started = False
    misses = 0
    anchor: int | None = None

    for row in ordered:
        if not started:
            if _is_accepted(row):
                started = True
                anchor = int(row["frame"])
            continue

        if _is_accepted(row):
            # A later accepted T0 detection remains accepted irrespective of Q/U/R.
            anchor = int(row["frame"])
            misses = 0
            continue

        # Frozen A4-01 predicate: production-good non-accepted rows count; X skips.
        if bool(row["production_good"]):
            misses += 1
            if misses > miss_budget:
                break

    if anchor is None:
        raise BaselineInputError("B2 requires at least one accepted target-event T0 detection")
    return anchor


def evaluate_b2(
    records: Sequence[Mapping[str, Any]],
    *,
    target_side: str | None = None,
    miss_budget: int,
    method: str,
) -> BaselineOutcome:
    if miss_budget not in {1, 2}:
        raise BaselineInputError("B2 miss_budget must be 1 or 2")
    prepared = _prepare_records(records, target_side)
    anchor = _b2_bridged_anchor(prepared, miss_budget)
    if not _adjacent_raw_exists(prepared, anchor):
        return _censored_outcome(method, prepared, anchor)
    return _finite_outcome(method, prepared, anchor)


def evaluate_b2a(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    return evaluate_b2(records, target_side=target_side, miss_budget=1, method="B2a")


def evaluate_b2b(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    return evaluate_b2(records, target_side=target_side, miss_budget=2, method="B2b")


def _temporal_acquisition_boundary(prepared: _PreparedRecords, anchor: int) -> bool:
    adjacent = prepared.by_frame.get(anchor + _step(prepared.target_side))
    return adjacent is None or bool(adjacent["movie_boundary"])


def _spatial_acquisition_boundary(prepared: _PreparedRecords, anchor: int) -> bool:
    return int(prepared.by_frame[anchor]["edge_px"]) < SPATIAL_MARGIN_PX


def _evaluate_acquisition_complete_mapping(
    method: str,
    records: Sequence[Mapping[str, Any]],
    target_side: str | None,
) -> BaselineOutcome:
    prepared = _prepare_records(records, target_side)
    anchor = _common_anchor(prepared)
    if _temporal_acquisition_boundary(prepared, anchor):
        return _censored_outcome(method, prepared, anchor)
    if _spatial_acquisition_boundary(prepared, anchor):
        return _censored_outcome(method, prepared, anchor)
    return _finite_outcome(method, prepared, anchor)


def evaluate_b3(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    """Frozen B3: B1 internally, censor at temporal or spatial acquisition boundary."""
    return _evaluate_acquisition_complete_mapping("B3", records, target_side)


def evaluate_b4a(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    """Frozen B4a complete-boundary mapping."""
    return _evaluate_acquisition_complete_mapping("B4a", records, target_side)


def evaluate_b4b(
    *,
    n: int,
    t: int,
    b_start: int = 0,
    b_end: int = 0,
) -> B4bReference:
    """Frozen B4b finite-window reference p_complete(t)=(N-t+1)/N."""
    for name, value in (("n", n), ("t", t), ("b_start", b_start), ("b_end", b_end)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise BaselineInputError(f"{name} must be an integer")
    if n < 1 or t < 1 or b_start < 0 or b_end < 0:
        raise BaselineInputError("B4b requires n,t >= 1 and non-negative buffers")
    effective_n = n - b_start - b_end
    if effective_n < 1:
        raise BaselineInputError("B4b effective N must be positive")
    if t > effective_n:
        raise BaselineInputError("B4b inclusive duration t cannot exceed effective N")
    p_complete = (effective_n - t + 1) / effective_n
    return B4bReference(
        n=n,
        t=t,
        b_start=b_start,
        b_end=b_end,
        effective_n=effective_n,
        p_complete=float(p_complete),
    )


def _target_buffer(
    prepared: _PreparedRecords,
    anchor: int,
) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    """Return (availability, rows) for the exact five-frame target-side buffer.

    availability is ``ok``, ``acquisition_edge`` or ``partial``.  An explicit
    movie-boundary row is acquisition-edge evidence; a missing row inside the
    observed raw-frame span is an otherwise non-calculable partial buffer.
    """
    step = _step(prepared.target_side)
    rows = []
    for offset in range(1, 6):
        frame = anchor + step * offset
        row = prepared.by_frame.get(frame)
        if row is None:
            outside_raw_span = frame < prepared.min_frame or frame > prepared.max_frame
            return ("acquisition_edge" if outside_raw_span else "partial"), tuple()
        if bool(row["movie_boundary"]):
            return "acquisition_edge", tuple()
        rows.append(row)
    return "ok", tuple(rows)


def _support_valid(row: Mapping[str, Any]) -> bool:
    return (
        bool(row["production_good"])
        and not bool(row["secondary_qc_bad"])
        and float(row["measured_frac"]) >= MIN_MEASURED_FRAC
        and bool(row["registration_supported"])
    )


def _has_two_consecutive_below_threshold(buffer_rows: Sequence[Mapping[str, Any]]) -> bool:
    below = [float(row["b5_peak"]) < THETA for row in buffer_rows]
    return any(a and b for a, b in zip(below, below[1:]))


def _b5_signal_passes(
    buffer_rows: Sequence[Mapping[str, Any]],
    accepted_track_rows: Sequence[Mapping[str, Any]],
) -> bool:
    if len(buffer_rows) != 5:
        raise BaselineInputError("B5 signal rule requires the complete five-frame target buffer")
    if not accepted_track_rows:
        raise BaselineInputError("B5 signal rule requires at least one accepted T0 detection")
    if not _has_two_consecutive_below_threshold(buffer_rows):
        return False
    buffer_max = max(float(row["b5_peak"]) for row in buffer_rows)
    track_max = max(float(row["b5_peak"]) for row in accepted_track_rows)
    return buffer_max < track_max


def _evaluate_b5_common(
    method: str,
    records: Sequence[Mapping[str, Any]],
    target_side: str | None,
    *,
    support_masked: bool,
) -> BaselineOutcome:
    prepared = _prepare_records(records, target_side)
    accepted = _accepted_rows(prepared)
    anchor = _common_anchor(prepared)

    if len(accepted) < 5:
        return _no_claim_outcome(method, prepared, anchor, reason="min_length")

    availability, buffer_rows = _target_buffer(prepared, anchor)
    if availability == "acquisition_edge":
        return _censored_outcome(method, prepared, anchor)
    if availability == "partial":
        return _no_claim_outcome(method, prepared, anchor, reason="partial")

    track_rows: Sequence[Mapping[str, Any]] = accepted
    if support_masked:
        if not all(_support_valid(row) for row in buffer_rows):
            return _no_claim_outcome(method, prepared, anchor, reason="partial_support")
        supported_accepted = tuple(row for row in accepted if _support_valid(row))
        if not supported_accepted:
            return _no_claim_outcome(method, prepared, anchor, reason="partial_support")
        track_rows = supported_accepted

    if not _b5_signal_passes(buffer_rows, track_rows):
        # Frozen authority specifies no special reason for ordinary signal-validation
        # failure; it is simply no finite claim.
        return _no_claim_outcome(method, prepared, anchor)

    return _finite_outcome(method, prepared, anchor)


def evaluate_b5(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    return _evaluate_b5_common("B5", records, target_side, support_masked=False)


def evaluate_b5m(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    return _evaluate_b5_common("B5M", records, target_side, support_masked=True)


def _parse_b6_interval(interval_frames: str) -> tuple[int, int]:
    if not (interval_frames.startswith("[") and interval_frames.endswith("]")):
        raise BaselineInputError(f"unexpected inherited B6 interval representation {interval_frames!r}")
    parts = interval_frames[1:-1].split(",")
    if len(parts) != 2:
        raise BaselineInputError(f"unexpected inherited B6 interval representation {interval_frames!r}")
    try:
        lo, hi = (int(part) for part in parts)
    except ValueError as exc:
        raise BaselineInputError(
            f"unexpected inherited B6 interval representation {interval_frames!r}"
        ) from exc
    if lo >= hi:
        raise BaselineInputError("inherited B6 finite interval must satisfy L < R")
    return lo, hi


def evaluate_b6_via_interface(
    records: Sequence[Mapping[str, Any]], *, target_side: str | None = None
) -> BaselineOutcome:
    """Representation/dispatch adapter around the accepted B6 implementation."""
    prepared = _prepare_records(records, target_side)
    anchor = _common_anchor(prepared)
    anchor_record = prepared.by_frame[anchor]

    acquisition_rows = tuple(row for row in prepared.rows if not bool(row["movie_boundary"]))
    if not acquisition_rows:
        raise BaselineInputError("B6 requires at least one acquisition-good raw-frame record")
    first_good = min(int(row["frame"]) for row in acquisition_rows)
    last_good = max(int(row["frame"]) for row in acquisition_rows)
    step = _step(prepared.target_side)
    outward = tuple(
        row
        for row in prepared.rows
        if (int(row["frame"]) - anchor) * step > 0
    )

    decision = evaluate_b6_boundary(
        anchor_record=anchor_record,
        outward_records=outward,
        first_good_frame=first_good,
        last_good_frame=last_good,
    )

    if decision.final_class in {"source_valid_negative", "observability_limited"}:
        if decision.interval_frames is None:
            raise BaselineInputError("inherited B6 finite class is missing its frozen interval")
        lo, hi = _parse_b6_interval(decision.interval_frames)
        return BaselineOutcome(
            method="B6",
            case_id=prepared.case_id,
            target_side=prepared.target_side,
            status="finite_claim",
            left_frame=lo,
            right_frame=hi,
            anchor_frame=anchor,
            b6_decision=decision,
        )
    if decision.final_class == "boundary_censored":
        return BaselineOutcome(
            method="B6",
            case_id=prepared.case_id,
            target_side=prepared.target_side,
            status="censored",
            anchor_frame=anchor,
            b6_decision=decision,
        )
    return BaselineOutcome(
        method="B6",
        case_id=prepared.case_id,
        target_side=prepared.target_side,
        status="no_claim",
        anchor_frame=anchor,
        reason=decision.final_class,
        b6_decision=decision,
    )


def run_baseline(
    name: str,
    records: Sequence[Mapping[str, Any]] | None = None,
    *,
    target_side: str | None = None,
    **kwargs: Any,
) -> BaselineOutcome | B4bReference:
    """Execute one named frozen Stage-3 A4 baseline deterministically.

    Boundary methods consume method-visible observation records only.  B4b is the
    separately frozen population-reference algebra and therefore consumes only
    ``n``, ``t``, ``b_start`` and ``b_end`` numeric arguments.
    """
    dispatch = {
        "B1": evaluate_b1,
        "B2a": evaluate_b2a,
        "B2b": evaluate_b2b,
        "B3": evaluate_b3,
        "B4a": evaluate_b4a,
        "B5": evaluate_b5,
        "B5M": evaluate_b5m,
        "B6": evaluate_b6_via_interface,
    }
    if name == "B4b":
        if records is not None:
            raise BaselineInputError("B4b does not consume observation records")
        allowed = {"n", "t", "b_start", "b_end"}
        extra = set(kwargs) - allowed
        if extra:
            raise BaselineInputError(f"unexpected B4b arguments: {sorted(extra)}")
        if "n" not in kwargs or "t" not in kwargs:
            raise BaselineInputError("B4b requires n and t")
        return evaluate_b4b(
            n=kwargs["n"],
            t=kwargs["t"],
            b_start=kwargs.get("b_start", 0),
            b_end=kwargs.get("b_end", 0),
        )

    if name not in dispatch:
        raise BaselineInputError(f"unknown frozen baseline {name!r}")
    if records is None:
        raise BaselineInputError(f"{name} requires method-visible observation records")
    if kwargs:
        raise BaselineInputError(f"unexpected {name} arguments: {sorted(kwargs)}")
    return dispatch[name](records, target_side=target_side)

