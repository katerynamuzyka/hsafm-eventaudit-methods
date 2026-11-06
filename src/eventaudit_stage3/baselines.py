"""Development-only Stage-3 baseline code authorized through Stage 3A.1.

Only the record-level B6 decision core is implemented.  B1-B5/B5M orchestration,
full benchmark execution, held-out execution, and scoring remain intentionally
unimplemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Mapping, Sequence
import math

from .boundary_record import validate_method_visible_record

MIN_MEASURED_FRAC = 0.50
MIN_ABOVE_FRAC = 0.05
N_CONFIRM = 2
LOOKAHEAD_FRAMES = 12
SPATIAL_MARGIN_PX = 2
THETA = 1.0

DECISION_PRECEDENCE = ("E", "X", "Q", "U", "R", "A", "C", "S", "N")
B6_CLASSES = frozenset(
    {
        "source_valid_negative",
        "observability_limited",
        "registration_limited",
        "assignment_ambiguous",
        "candidate_reappearance",
        "unresolved",
        "boundary_censored",
    }
)

# Explicit declaration for static whitelist tests.  B6 uses no truth-only field.
B6_METHOD_KEYS_USED = frozenset(
    {
        "case_id",
        "target_side",
        "frame",
        "t0_event_id",
        "t0_track_id",
        "production_good",
        "secondary_qc_bad",
        "measured_frac",
        "registration_supported",
        "b5_peak",
        "above_frac",
        "component_state",
        "other_event_ids",
        "edge_px",
        "movie_boundary",
    }
)


class B6InputError(ValueError):
    """Raised for malformed/incomplete development records supplied to B6."""


@dataclass(frozen=True)
class B6FrameEvidence:
    """One coded frame plus independently retained assignment/content evidence."""

    frame: int
    code: str
    component_state: str
    other_event_ids: tuple[Any, ...]


@dataclass(frozen=True)
class B6Decision:
    """Frozen-rule B6 result for one endpoint/onset side."""

    target_side: str
    anchor_frame: int
    provisional_class: str
    final_class: str
    codes: str
    decisive_index: int | None
    decisive_frame: int | None
    decisive_code: str | None
    boundary: str | None
    edge_px: int
    interval_frames: str | None
    n_unobserved: int
    decisive_component_state: str | None
    decisive_other_event_ids: tuple[Any, ...]


def b6_frame_code(record: Mapping[str, Any]) -> str:
    """Return the exact frozen B6 per-frame code under Stage-3 record semantics."""
    validate_method_visible_record(record)

    if record["movie_boundary"]:
        return "E"
    if not record["production_good"]:
        return "X"
    if record["secondary_qc_bad"]:
        return "Q"
    if float(record["measured_frac"]) < MIN_MEASURED_FRAC:
        return "U"
    if not record["registration_supported"]:
        return "R"

    component_state = record["component_state"]
    if component_state == "other":
        return "A"
    if component_state in {"self", "unowned"}:
        # Frozen evidence.py returns C whenever an accepted overlap exists but no
        # *other* retained event is identified.  A self-owned accepted overlap
        # therefore also falls on the frozen C branch.
        return "C"

    above_frac = float(record["above_frac"])
    if (
        float(record["b5_peak"]) >= THETA
        and not math.isnan(above_frac)
        and above_frac >= MIN_ABOVE_FRAC
    ):
        return "S"
    return "N"


def b6_frame_evidence(record: Mapping[str, Any]) -> B6FrameEvidence:
    """Code one frame without erasing independently retained assignment evidence."""
    code = b6_frame_code(record)
    return B6FrameEvidence(
        frame=int(record["frame"]),
        code=code,
        component_state=str(record["component_state"]),
        other_event_ids=tuple(record["other_event_ids"]),
    )


def classify_b6_codes(codes: Sequence[str]) -> tuple[str, int | None]:
    """Map a code sequence to the frozen provisional class and decisive index."""
    gap = False
    run = 0
    for index, code in enumerate(codes):
        if code not in DECISION_PRECEDENCE:
            raise B6InputError(f"unknown B6 code: {code!r}")
        if code == "E":
            return "boundary_censored", index
        if code in {"X", "Q", "U"}:
            gap = True
            run = 0
            continue
        if code == "R":
            return "registration_limited", index
        if code in {"A", "C"}:
            return ("candidate_reappearance" if gap else "assignment_ambiguous"), index
        if code == "S":
            return "unresolved", index
        if code == "N":
            run += 1
            if run >= N_CONFIRM:
                return ("observability_limited" if gap else "source_valid_negative"), index
    return "unresolved", None


def _assert_same_case(anchor: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    for key in ("case_id", "target_side", "t0_event_id", "t0_track_id"):
        if record[key] != anchor[key]:
            raise B6InputError(f"outward record changes {key!r} within one B6 side")


def evaluate_b6_boundary(
    *,
    anchor_record: Mapping[str, Any],
    outward_records: Sequence[Mapping[str, Any]],
    first_good_frame: int,
    last_good_frame: int,
) -> B6Decision:
    """Evaluate one record-level B6 endpoint/onset side under frozen v1 rules.

    ``first_good_frame`` and ``last_good_frame`` are method-side quantities derived
    from production-good movie frames; they are not truth fields.  ``outward_records``
    must provide each raw frame index needed by the walk, including any explicit
    movie-boundary (E) row.  Missing raw-frame records fail closed rather than being
    silently treated as good frames or as E.
    """
    validate_method_visible_record(anchor_record)
    if not isinstance(first_good_frame, int) or isinstance(first_good_frame, bool):
        raise B6InputError("first_good_frame must be an integer")
    if not isinstance(last_good_frame, int) or isinstance(last_good_frame, bool):
        raise B6InputError("last_good_frame must be an integer")
    if first_good_frame > last_good_frame:
        raise B6InputError("first_good_frame cannot exceed last_good_frame")

    side = str(anchor_record["target_side"])
    anchor_frame = int(anchor_record["frame"])
    edge_px = int(anchor_record["edge_px"])
    step = 1 if side == "endpoint" else -1
    temporal_boundary_frame = last_good_frame if side == "endpoint" else first_good_frame

    if anchor_frame == temporal_boundary_frame:
        return B6Decision(
            target_side=side,
            anchor_frame=anchor_frame,
            provisional_class="boundary_censored",
            final_class="boundary_censored",
            codes="",
            decisive_index=None,
            decisive_frame=None,
            decisive_code=None,
            boundary="temporal",
            edge_px=edge_px,
            interval_frames=None,
            n_unobserved=0,
            decisive_component_state=None,
            decisive_other_event_ids=(),
        )

    by_frame: dict[int, Mapping[str, Any]] = {}
    for record in outward_records:
        validate_method_visible_record(record)
        _assert_same_case(anchor_record, record)
        frame = int(record["frame"])
        if frame in by_frame:
            raise B6InputError(f"duplicate outward record for raw frame {frame}")
        by_frame[frame] = record

    evidences: list[B6FrameEvidence] = []
    provisional_class = "unresolved"
    decisive_index: int | None = None

    for offset in range(1, LOOKAHEAD_FRAMES + 1):
        expected_frame = anchor_frame + step * offset
        if expected_frame not in by_frame:
            raise B6InputError(
                f"missing raw-frame record {expected_frame} before B6 lookahead completed"
            )
        evidence = b6_frame_evidence(by_frame[expected_frame])
        evidences.append(evidence)
        provisional_class, decisive_index = classify_b6_codes([item.code for item in evidences])
        if decisive_index is not None:
            break

    codes = "".join(item.code for item in evidences)
    if decisive_index is None:
        provisional_class, decisive_index = classify_b6_codes(codes)

    boundary = "spatial" if edge_px < SPATIAL_MARGIN_PX else None
    final_class = provisional_class
    if boundary == "spatial" and provisional_class in {
        "source_valid_negative",
        "observability_limited",
        "unresolved",
    }:
        final_class = "boundary_censored"

    interval_frames: str | None = None
    if (
        final_class in {"source_valid_negative", "observability_limited"}
        and decisive_index is not None
    ):
        first_absent_index = decisive_index - N_CONFIRM + 1
        first_absent_frame = evidences[first_absent_index].frame
        lo, hi = sorted((anchor_frame, first_absent_frame))
        interval_frames = f"[{lo},{hi}]"

    decisive = evidences[decisive_index] if decisive_index is not None else None
    count_limit = decisive_index + 1 if decisive_index is not None else len(evidences)
    n_unobserved = sum(item.code in {"X", "Q", "U", "R"} for item in evidences[:count_limit])

    return B6Decision(
        target_side=side,
        anchor_frame=anchor_frame,
        provisional_class=provisional_class,
        final_class=final_class,
        codes=codes,
        decisive_index=decisive_index,
        decisive_frame=None if decisive is None else decisive.frame,
        decisive_code=None if decisive is None else decisive.code,
        boundary=boundary,
        edge_px=edge_px,
        interval_frames=interval_frames,
        n_unobserved=n_unobserved,
        decisive_component_state=None if decisive is None else decisive.component_state,
        decisive_other_event_ids=() if decisive is None else decisive.other_event_ids,
    )


def run_baseline(name: str, *args: Any, **kwargs: Any) -> Any:
    """Route only the Stage-3A.1-authorized B6 record core.

    B1-B5/B5M remain outside this development step.
    """
    if name == "B6":
        return evaluate_b6_boundary(*args, **kwargs)
    raise NotImplementedError(
        f"Stage 3A.1 implements only the B6 record-level decision core; {name!r} is not implemented."
    )
