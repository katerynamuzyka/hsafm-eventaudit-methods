"""Method-visible boundary-record schema for EventAudit Stage 3A.1.

The whitelist is copied exactly from ``GENERATOR_SPEC_v1_FROZEN_2026-10-02``.
This module deliberately contains no truth-schema import.  Method code can import
this module with the truth file/module physically absent.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

METHOD_VISIBLE_FIELDS = frozenset(
    {
        "case_id",
        "target_side",
        "frame",
        "time_frame_units",
        "t0_event_id",
        "t0_track_id",
        "t0_detection_state",
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
        "candidate_applied",
    }
)

REQUIRED_METHOD_VISIBLE_FIELDS = METHOD_VISIBLE_FIELDS
TARGET_SIDES = frozenset({"endpoint", "onset"})
COMPONENT_STATES = frozenset({"none", "self", "other", "unowned"})

# These names are not an alternative schema.  They are representative truth/
# construction metadata whose appearance in a method-visible row must fail closed.
TRUTH_LEAKAGE_KEYS = frozenset(
    {
        "family",
        "stratum",
        "severity",
        "duration_bin",
        "corruption_truth",
        "latent_transition_time",
        "latent_time",
        "true_event_presence_trajectory",
        "true_corruption_window",
        "true_support_state",
        "true_assignment_identity",
        "clean_twin_mapping",
        "clean_twin_id",
        "perturbation_condition",
        "perturbation_label",
        "seed",
        "seed_metadata",
        "semantic_case_index",
        "global_case_index",
    }
)

_CASE_ID_RE = re.compile(r"^[0-9a-fA-F]{16}$")


class MethodVisibleSchemaError(ValueError):
    """Raised when a method-visible record violates the frozen Stage-3 schema."""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return _is_number(value) and math.isfinite(float(value))


def _is_id_scalar(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    return isinstance(value, str) and bool(value.strip())


def _validate_other_event_ids(value: Any) -> None:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise MethodVisibleSchemaError("other_event_ids must be a sequence of ID scalars")
    if any(not _is_id_scalar(item) for item in value):
        raise MethodVisibleSchemaError("other_event_ids contains an invalid ID")


def validate_method_visible_record(record: Mapping[str, Any]) -> None:
    """Validate one Stage-3 method-visible frame record, failing closed.

    Frozen v1 explicitly freezes the whitelist and several value domains, but it
    does *not* enumerate a vocabulary for ``t0_detection_state`` or the concrete
    scalar representation of T0 IDs.  The validator therefore constrains those
    fields structurally rather than inventing new scientific categories.
    """
    if not isinstance(record, Mapping):
        raise MethodVisibleSchemaError("record must be a mapping")

    keys = set(record)
    missing = REQUIRED_METHOD_VISIBLE_FIELDS - keys
    extra = keys - METHOD_VISIBLE_FIELDS
    if missing:
        raise MethodVisibleSchemaError(f"missing required method-visible fields: {sorted(missing)}")
    if extra:
        leaked = sorted(extra & TRUTH_LEAKAGE_KEYS)
        if leaked:
            raise MethodVisibleSchemaError(f"truth/construction metadata leaked into method record: {leaked}")
        raise MethodVisibleSchemaError(f"unknown method-visible fields: {sorted(extra)}")

    case_id = record["case_id"]
    if not isinstance(case_id, str) or not _CASE_ID_RE.fullmatch(case_id):
        raise MethodVisibleSchemaError("case_id must be an opaque 16-hex identifier")

    if record["target_side"] not in TARGET_SIDES:
        raise MethodVisibleSchemaError(f"target_side must be one of {sorted(TARGET_SIDES)}")

    frame = record["frame"]
    if not isinstance(frame, int) or isinstance(frame, bool):
        raise MethodVisibleSchemaError("frame must be an integer raw-frame index")

    time_value = record["time_frame_units"]
    if not _is_finite_number(time_value) or float(time_value) != float(frame):
        raise MethodVisibleSchemaError("time_frame_units must equal the raw frame index")

    if not _is_id_scalar(record["t0_event_id"]):
        raise MethodVisibleSchemaError("t0_event_id must be a non-negative integer or non-empty string")
    if not _is_id_scalar(record["t0_track_id"]):
        raise MethodVisibleSchemaError("t0_track_id must be a non-negative integer or non-empty string")

    detection_state = record["t0_detection_state"]
    if not isinstance(detection_state, str) or not detection_state.strip():
        raise MethodVisibleSchemaError("t0_detection_state must be a non-empty string")

    for key in ("production_good", "secondary_qc_bad", "registration_supported", "movie_boundary"):
        if not isinstance(record[key], bool):
            raise MethodVisibleSchemaError(f"{key} must be boolean")

    measured_frac = record["measured_frac"]
    if not _is_finite_number(measured_frac) or not 0.0 <= float(measured_frac) <= 1.0:
        raise MethodVisibleSchemaError("measured_frac must be finite and in [0,1]")

    if not _is_finite_number(record["b5_peak"]):
        raise MethodVisibleSchemaError("b5_peak must be finite")

    above_frac = record["above_frac"]
    above_is_nan = _is_number(above_frac) and math.isnan(float(above_frac))
    if not above_is_nan:
        if not _is_finite_number(above_frac) or not 0.0 <= float(above_frac) <= 1.0:
            raise MethodVisibleSchemaError("above_frac must be NaN or finite in [0,1]")

    # Frozen record-consistency rules.  With no measured pixels the fraction is
    # undefined; with measured pixels it must be defined.  Below theta (=1), the
    # measured-pixel above-threshold fraction is zero.
    if float(measured_frac) == 0.0:
        if not above_is_nan:
            raise MethodVisibleSchemaError("above_frac must be NaN when measured_frac is zero")
    else:
        if above_is_nan:
            raise MethodVisibleSchemaError("above_frac cannot be NaN when measured pixels exist")
        if float(record["b5_peak"]) < 1.0 and float(above_frac) != 0.0:
            raise MethodVisibleSchemaError("b5_peak < theta requires above_frac == 0")

    component_state = record["component_state"]
    if component_state not in COMPONENT_STATES:
        raise MethodVisibleSchemaError(f"component_state must be one of {sorted(COMPONENT_STATES)}")

    _validate_other_event_ids(record["other_event_ids"])
    has_other_ids = len(record["other_event_ids"]) > 0
    if component_state == "other" and not has_other_ids:
        raise MethodVisibleSchemaError("component_state='other' requires retained other_event_ids")
    if component_state != "other" and has_other_ids:
        raise MethodVisibleSchemaError("other_event_ids are only valid with component_state='other'")

    edge_px = record["edge_px"]
    if not isinstance(edge_px, int) or isinstance(edge_px, bool):
        raise MethodVisibleSchemaError("edge_px must be an integer pixel distance")

    if record["candidate_applied"] is not False:
        raise MethodVisibleSchemaError("candidate_applied must be false in Stage 3B")
