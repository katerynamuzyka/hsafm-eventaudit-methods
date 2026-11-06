"""Physically separate truth-record schema for EventAudit Stage 3A.1.

No method module imports this file.  Its purpose is to validate the separate
truth-side serialization described by the frozen generator specification.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

TRUTH_RECORD_FIELDS = frozenset(
    {
        "case_id",
        "family",
        "stratum",
        "target_side",
        "latent_transition_time",
        "true_event_presence_trajectory",
        "true_corruption_window",
        "true_support_state",
        "true_assignment_identity",
        "duration_bin",
        "clean_twin_mapping",
        "seed_metadata",
    }
)

REQUIRED_TRUTH_RECORD_FIELDS = TRUTH_RECORD_FIELDS
TARGET_SIDES = frozenset({"endpoint", "onset"})
DURATION_BINS = frozenset({"short", "medium", "long"})
FAMILIES = frozenset({"F0", "F0b", "F1", "F2", "F3", "F4", "F5", "F6", "F7a", "F7b", "F8"})
N_FRAMES = 64
_CASE_ID_RE = re.compile(r"^[0-9a-fA-F]{16}$")


class TruthRecordSchemaError(ValueError):
    """Raised when a separate truth record violates the frozen Stage-3 schema."""


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _is_case_id(value: Any) -> bool:
    return isinstance(value, str) and _CASE_ID_RE.fullmatch(value) is not None


def validate_truth_record(record: Mapping[str, Any]) -> None:
    """Validate one physically separate truth record.

    The frozen specification names the truth concepts but does not freeze a
    categorical vocabulary/shape for ``true_support_state`` or
    ``true_assignment_identity``.  Those two fields are therefore required but
    intentionally not reinterpreted here.
    """
    if not isinstance(record, Mapping):
        raise TruthRecordSchemaError("truth record must be a mapping")

    keys = set(record)
    missing = REQUIRED_TRUTH_RECORD_FIELDS - keys
    extra = keys - TRUTH_RECORD_FIELDS
    if missing:
        raise TruthRecordSchemaError(f"missing required truth fields: {sorted(missing)}")
    if extra:
        raise TruthRecordSchemaError(f"unknown truth fields: {sorted(extra)}")

    if not _is_case_id(record["case_id"]):
        raise TruthRecordSchemaError("case_id must be an opaque 16-hex identifier")
    if record["family"] not in FAMILIES:
        raise TruthRecordSchemaError(f"family must be one of {sorted(FAMILIES)}")
    if not isinstance(record["stratum"], str) or not record["stratum"].strip():
        raise TruthRecordSchemaError("stratum must be a non-empty string")
    if record["target_side"] not in TARGET_SIDES:
        raise TruthRecordSchemaError(f"target_side must be one of {sorted(TARGET_SIDES)}")
    if not _is_finite_number(record["latent_transition_time"]):
        raise TruthRecordSchemaError("latent_transition_time must be finite")

    trajectory = record["true_event_presence_trajectory"]
    if isinstance(trajectory, (str, bytes)) or not isinstance(trajectory, Sequence):
        raise TruthRecordSchemaError("true_event_presence_trajectory must be a sequence")
    if len(trajectory) != N_FRAMES or any(not isinstance(v, bool) for v in trajectory):
        raise TruthRecordSchemaError(f"true_event_presence_trajectory must contain {N_FRAMES} booleans")

    window = record["true_corruption_window"]
    if isinstance(window, (str, bytes)) or not isinstance(window, Sequence):
        raise TruthRecordSchemaError("true_corruption_window must be a sequence of raw-frame indices")
    for frame in window:
        if not isinstance(frame, int) or isinstance(frame, bool) or not 0 <= frame < N_FRAMES:
            raise TruthRecordSchemaError("true_corruption_window contains an invalid raw-frame index")

    # The frozen spec requires these truth concepts to be physically separate,
    # but does not freeze their internal serialization vocabulary in v1.  Their
    # presence is enforced by the exact-key check above; no extra scientific
    # categories are invented here.

    if record["duration_bin"] not in DURATION_BINS:
        raise TruthRecordSchemaError(f"duration_bin must be one of {sorted(DURATION_BINS)}")

    twin = record["clean_twin_mapping"]
    if twin is not None and not (_is_case_id(twin) or isinstance(twin, Mapping)):
        raise TruthRecordSchemaError("clean_twin_mapping must be null, an opaque case_id, or a mapping")

    if not isinstance(record["seed_metadata"], Mapping):
        raise TruthRecordSchemaError("seed_metadata must be a mapping")
