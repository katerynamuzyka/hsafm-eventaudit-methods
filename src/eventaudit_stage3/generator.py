"""Stage 3A.3 deterministic development-only F0-F8 observation-record generator.

The module implements the cumulative frozen generator authority through the
v1.4 A3 clarification addendum.  It generates record-level synthetic data only;
there is no image synthesis, benchmark scoring, metric machinery, or held-out
namespace entry point here.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np

from .boundary_record import METHOD_VISIBLE_FIELDS, validate_method_visible_record
from .generator_seed import (
    DevelopmentSeedManifest,
    base_case_id,
    build_development_seed_manifest,
    clean_variant_descriptor,
    development_case_seed,
    purpose_rng,
    variant_case_id,
)
from .truth_record import validate_truth_record

N_FRAMES = 64
THETA = 1.0
MIN_MEASURED_FRAC = 0.50
MIN_ABOVE_FRAC = 0.05
DEFAULT_EDGE_PX = 3

FAMILY_ORDER = ("F0", "F0b", "F1", "F2", "F3", "F4", "F5", "F6", "F7b", "F7a", "F8")
PRIMARY_FAMILIES = ("F0", "F0b", "F1", "F2", "F3", "F4", "F5", "F6", "F7b")
DURATION_BOUNDS = {
    "short": (4, 6),
    "medium": (7, 12),
    "long": (13, 20),
}
DURATION_ORDER = ("short", "medium", "long")
TARGET_ORDER = ("endpoint", "onset")


class GeneratorInvariantError(RuntimeError):
    """Raised when generation cannot satisfy the frozen A3 construction."""


@dataclass(frozen=True)
class CaseDesign:
    global_case_index: int
    family: str
    target_side: str
    replicate_index: int
    sigma: float
    duration_bin: str
    factors: tuple[tuple[str, Any], ...] = field(default_factory=tuple)

    def factor(self, name: str, default: Any = None) -> Any:
        return dict(self.factors).get(name, default)

    @property
    def factor_map(self) -> dict[str, Any]:
        return dict(self.factors)

    @property
    def stratum(self) -> str:
        if not self.factors:
            return "base"
        return ";".join(f"{key}={value}" for key, value in self.factors)


@dataclass(frozen=True)
class GeneratedCase:
    """One materialized case with physically separate method and truth objects."""

    method_records: tuple[dict[str, Any], ...]
    truth_record: dict[str, Any]
    construction: dict[str, Any]

    @property
    def case_id(self) -> str:
        return str(self.truth_record["case_id"])


@dataclass(frozen=True)
class CaseGeometry:
    l0_clean: int
    latent_transition_time: float
    first_good: int
    last_good: int
    corruption_window: tuple[int, ...]


# ---------------------------------------------------------------------------
# Canonical enumeration
# ---------------------------------------------------------------------------


def _f1_f4_noise_duration(target_side: str, r: int) -> tuple[float, str]:
    if target_side == "endpoint":
        if 0 <= r <= 5:
            sigma = 0.0
            j = r
        elif 6 <= r <= 11:
            sigma = 0.15
            j = r - 6
        else:
            raise GeneratorInvariantError("endpoint F1-F4 replicate must be 0..11")
        return sigma, DURATION_ORDER[j % 3]
    if target_side == "onset":
        if 0 <= r <= 2:
            return 0.0, DURATION_ORDER[r]
        if 3 <= r <= 5:
            return 0.15, ("long", "short", "medium")[r - 3]
        raise GeneratorInvariantError("onset F1-F4 replicate must be 0..5")
    raise GeneratorInvariantError(f"unknown target side: {target_side}")


def _nested_noise(target_side: str, r: int, endpoint_half: int, onset_half: int) -> float:
    if target_side == "endpoint":
        return 0.0 if r < endpoint_half else 0.15
    return 0.0 if r < onset_half else 0.15


def enumerate_base_designs() -> tuple[CaseDesign, ...]:
    """Return the canonical 3294 base latent units in frozen top-level order."""
    designs: list[CaseDesign] = []
    idx = 0

    def add(
        family: str,
        target: str,
        r: int,
        sigma: float,
        duration: str,
        factors: Sequence[tuple[str, Any]],
    ) -> None:
        nonlocal idx
        designs.append(
            CaseDesign(
                global_case_index=idx,
                family=family,
                target_side=target,
                replicate_index=r,
                sigma=float(sigma),
                duration_bin=duration,
                factors=tuple(factors),
            )
        )
        idx += 1

    # F0: noise x duration; target side then replicate.
    for sigma in (0.0, 0.15):
        for duration in DURATION_ORDER:
            for target in TARGET_ORDER:
                n_rep = 36 if target == "endpoint" else 18
                for r in range(n_rep):
                    add("F0", target, r, sigma, duration, (("noise", sigma), ("duration", duration)))

    # F0b: mechanism x noise x duration.
    for mechanism in ("N", "S"):
        for sigma in (0.0, 0.15):
            for duration in DURATION_ORDER:
                for target in TARGET_ORDER:
                    n_rep = 18 if target == "endpoint" else 9
                    for r in range(n_rep):
                        add(
                            "F0b",
                            target,
                            r,
                            sigma,
                            duration,
                            (("mechanism", mechanism), ("noise", sigma), ("duration", duration)),
                        )

    # F1-F4: transition x numerical mode x severity.  Duration is nested by v1.4.
    for family in ("F1", "F2", "F3", "F4"):
        for transition in ("before", "inside", "after"):
            for numerical_mode in ("absence-like", "presence-like"):
                for severity in ("mild", "intermediate", "severe"):
                    for target in TARGET_ORDER:
                        n_rep = 12 if target == "endpoint" else 6
                        for r in range(n_rep):
                            sigma, duration = _f1_f4_noise_duration(target, r)
                            add(
                                family,
                                target,
                                r,
                                sigma,
                                duration,
                                (
                                    ("transition", transition),
                                    ("numerical_mode", numerical_mode),
                                    ("severity", severity),
                                ),
                            )

    # F5: overlap x ownership x duration.
    for overlap in (0.25, 0.50, 0.75):
        for ownership in ("A", "C"):
            for duration in DURATION_ORDER:
                for target in TARGET_ORDER:
                    n_rep = 12 if target == "endpoint" else 6
                    for r in range(n_rep):
                        sigma = _nested_noise(target, r, endpoint_half=6, onset_half=3)
                        add(
                            "F5",
                            target,
                            r,
                            sigma,
                            duration,
                            (("overlap_fraction", overlap), ("ownership", ownership), ("duration", duration)),
                        )

    # F6: edge type x duration.
    edge_types = (
        "temporal-left",
        "temporal-right",
        "temporal-both",
        "spatial-top",
        "spatial-bottom",
        "spatial-left",
        "spatial-right",
        "spatial-corner",
        "mixed temporal+spatial",
    )
    for edge_type in edge_types:
        for duration in DURATION_ORDER:
            for target in TARGET_ORDER:
                n_rep = 8 if target == "endpoint" else 4
                for r in range(n_rep):
                    sigma = _nested_noise(target, r, endpoint_half=4, onset_half=2)
                    add(
                        "F6",
                        target,
                        r,
                        sigma,
                        duration,
                        (("edge_type", edge_type), ("duration", duration)),
                    )

    # F7b: true absence length x duration.
    for absence_length in (1, 2, 3):
        for duration in DURATION_ORDER:
            for target in TARGET_ORDER:
                n_rep = 24 if target == "endpoint" else 12
                for r in range(n_rep):
                    sigma = _nested_noise(target, r, endpoint_half=12, onset_half=6)
                    add(
                        "F7b",
                        target,
                        r,
                        sigma,
                        duration,
                        (("absence_length", absence_length), ("duration", duration)),
                    )

    # F7a: offset x duration.
    for offset in (0.25, 0.50, 0.75):
        for duration in DURATION_ORDER:
            for target in TARGET_ORDER:
                n_rep = 12 if target == "endpoint" else 6
                for r in range(n_rep):
                    sigma = _nested_noise(target, r, endpoint_half=6, onset_half=3)
                    add(
                        "F7a",
                        target,
                        r,
                        sigma,
                        duration,
                        (("offset", offset), ("duration", duration)),
                    )

    # F8: combination x duration.
    for combination in ("X+U", "Q+R", "U+A", "U+C"):
        for duration in DURATION_ORDER:
            for target in TARGET_ORDER:
                n_rep = 12 if target == "endpoint" else 6
                for r in range(n_rep):
                    sigma = _nested_noise(target, r, endpoint_half=6, onset_half=3)
                    add(
                        "F8",
                        target,
                        r,
                        sigma,
                        duration,
                        (("combination", combination), ("duration", duration)),
                    )

    if idx != 3294:
        raise GeneratorInvariantError(f"canonical base inventory must contain 3294 cases, got {idx}")
    return tuple(designs)


# ---------------------------------------------------------------------------
# Deterministic numerical construction
# ---------------------------------------------------------------------------


def _draw_duration(case_seed: int, duration_bin: str) -> int:
    low, high = DURATION_BOUNDS[duration_bin]
    rng = np.random.Generator(np.random.PCG64(case_seed))
    return int(rng.integers(low, high + 1))


def _potential_frame_draws(case_seed: int, frame: int) -> tuple[np.float64, np.float64, np.float64]:
    present = np.float64(purpose_rng(case_seed, b"signal-present", frame).uniform(1.4, 2.0))
    absent = np.float64(purpose_rng(case_seed, b"signal-absent", frame).uniform(0.0, 0.4))
    z = np.float64(purpose_rng(case_seed, b"noise-z", frame).standard_normal())
    return present, absent, z


def _observed_signal(case_seed: int, frame: int, sigma: float, state: str) -> np.float64:
    present, absent, z = _potential_frame_draws(case_seed, frame)
    if state == "present":
        base = present
    elif state == "absent":
        base = absent
    else:
        raise GeneratorInvariantError(f"unknown signal state {state!r}")
    return np.float64(base + np.float64(sigma) * z)


def _f0b_signal(case_seed: int, frame: int, sigma: float, mechanism: str) -> np.float64:
    tag = b"f0b-N" if mechanism == "N" else b"f0b-S"
    rng = purpose_rng(case_seed, tag, frame)
    for _ in range(1_000_000):
        if mechanism == "N":
            base = np.float64(rng.uniform(0.0, 0.4))
        elif mechanism == "S":
            base = np.float64(rng.uniform(1.4, 2.0))
        else:
            raise GeneratorInvariantError(f"unknown F0b mechanism {mechanism!r}")
        z = np.float64(rng.standard_normal())
        candidate = np.float64(base + np.float64(sigma) * z)
        if mechanism == "N" and candidate < 1.0:
            return candidate
        if mechanism == "S" and candidate >= 1.0:
            return candidate
    raise GeneratorInvariantError("F0b rejection sampling exceeded deterministic safety bound")


def synthesize_above_frac(measured_frac: float, b5_peak: float) -> float:
    if float(measured_frac) <= 0.0:
        return float("nan")
    if float(b5_peak) < THETA:
        return 0.0
    return MIN_ABOVE_FRAC


def _opaque_related_id(base_id: str, tag: bytes) -> str:
    return hashlib.sha256(bytes.fromhex(base_id) + b"\x00related\x00" + tag).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Geometry / truth placement
# ---------------------------------------------------------------------------


def _severity_length(severity: str) -> int:
    return {"mild": 1, "intermediate": 2, "severe": 3}[severity]


def _f1_f4_geometry(design: CaseDesign) -> CaseGeometry:
    L = 31 if design.target_side == "endpoint" else 32
    s = _severity_length(str(design.factor("severity")))
    transition = str(design.factor("transition"))
    if design.target_side == "endpoint":
        if transition == "before":
            w0, w1 = L + 1, L + s
            truth = w0 - 0.25
        elif transition == "inside":
            w0 = L - math.floor((s - 1) / 2)
            w1 = w0 + s - 1
            truth = (w0 + w1 + 1) / 2
        elif transition == "after":
            w1 = L - 1
            w0 = L - s
            truth = w1 + 1.25
        else:
            raise GeneratorInvariantError("invalid transition factor")
    else:
        if transition == "before":
            w0, w1 = L - s, L - 1
            truth = w1 + 0.25
        elif transition == "inside":
            w1 = L + math.floor((s - 1) / 2)
            w0 = w1 - s + 1
            truth = (w0 + w1 - 1) / 2
        elif transition == "after":
            w0, w1 = L + 1, L + s
            truth = w0 - 1.25
        else:
            raise GeneratorInvariantError("invalid transition factor")
    return CaseGeometry(L, float(truth), 0, 63, tuple(range(w0, w1 + 1)))


def _f6_geometry(design: CaseDesign) -> CaseGeometry:
    edge = str(design.factor("edge_type"))
    target = design.target_side
    if edge == "temporal-left":
        first, last = 8, 63
        if target == "onset":
            return CaseGeometry(8, 7.75, first, last, tuple(range(0, 8)))
        return CaseGeometry(31, 31.5, first, last, tuple(range(0, 8)))
    if edge == "temporal-right":
        first, last = 0, 55
        if target == "endpoint":
            return CaseGeometry(55, 55.25, first, last, tuple(range(56, 64)))
        return CaseGeometry(32, 31.5, first, last, tuple(range(56, 64)))
    if edge == "temporal-both":
        first, last = 8, 55
        corruption = tuple(range(0, 8)) + tuple(range(56, 64))
        if target == "onset":
            return CaseGeometry(8, 7.75, first, last, corruption)
        return CaseGeometry(55, 55.25, first, last, corruption)
    if edge == "mixed temporal+spatial":
        if target == "onset":
            return CaseGeometry(8, 7.75, 8, 63, tuple(range(0, 8)))
        return CaseGeometry(55, 55.25, 0, 55, tuple(range(56, 64)))
    # Pure spatial rows use full acquisition and internal anchors.
    L = 31 if target == "endpoint" else 32
    return CaseGeometry(L, 31.5, 0, 63, tuple())


def _case_geometry(design: CaseDesign) -> CaseGeometry:
    if design.family in {"F1", "F2", "F3", "F4"}:
        return _f1_f4_geometry(design)
    if design.family == "F6":
        return _f6_geometry(design)
    L = 31 if design.target_side == "endpoint" else 32
    truth = 31.5
    if design.family == "F7a":
        delta = float(design.factor("offset"))
        truth = L + delta if design.target_side == "endpoint" else L - delta
    # Other family-specific corruption windows are filled after the clean template exists.
    return CaseGeometry(L, float(truth), 0, 63, tuple())


def _clean_accepted_frames(target_side: str, l0_clean: int, D: int) -> set[int]:
    if target_side == "endpoint":
        frames = set(range(l0_clean - D + 1, l0_clean + 1))
    else:
        frames = set(range(l0_clean, l0_clean + D))
    if not frames or min(frames) < 0 or max(frames) >= N_FRAMES:
        raise GeneratorInvariantError("clean accepted span falls outside raw movie")
    return frames


def _edge_px(design: CaseDesign) -> int:
    if design.family == "F6" and str(design.factor("edge_type")) in {
        "spatial-top",
        "spatial-bottom",
        "spatial-left",
        "spatial-right",
        "spatial-corner",
        "mixed temporal+spatial",
    }:
        return 1 + (design.replicate_index % 3)
    return DEFAULT_EDGE_PX


def _presence_like_self(design: CaseDesign) -> bool:
    if design.family not in {"F2", "F3", "F4"} or design.factor("numerical_mode") != "presence-like":
        return False
    r = design.replicate_index
    if design.target_side == "endpoint":
        j = r if r < 6 else r - 6
        return j in {0, 1, 2}
    return r in {0, 1, 3}


# ---------------------------------------------------------------------------
# Record materialization
# ---------------------------------------------------------------------------


def _base_row(
    *,
    case_id: str,
    target_side: str,
    frame: int,
    edge_px: int,
    accepted: bool,
    case_seed: int,
    sigma: float,
) -> dict[str, Any]:
    signal_state = "present" if accepted else "absent"
    peak = _observed_signal(case_seed, frame, sigma, signal_state)
    row: dict[str, Any] = {
        "case_id": case_id,
        "target_side": target_side,
        "frame": frame,
        "time_frame_units": float(frame),
        "t0_event_id": "t0",
        "t0_track_id": "k0",
        "t0_detection_state": "accepted" if accepted else "not_accepted",
        "production_good": True,
        "secondary_qc_bad": False,
        "measured_frac": 1.0,
        "registration_supported": True,
        "b5_peak": peak,
        "above_frac": synthesize_above_frac(1.0, peak),
        "component_state": "self" if accepted else "none",
        "other_event_ids": [],
        "edge_px": int(edge_px),
        "movie_boundary": False,
        "candidate_applied": False,
    }
    return row


def _set_signal(row: dict[str, Any], *, case_seed: int, sigma: float, signal_state: str) -> None:
    peak = _observed_signal(case_seed, int(row["frame"]), sigma, signal_state)
    row["b5_peak"] = peak
    row["above_frac"] = synthesize_above_frac(float(row["measured_frac"]), float(peak))


def _neutral_boundary_row(row: dict[str, Any]) -> None:
    row.update(
        {
            "movie_boundary": True,
            "production_good": True,
            "secondary_qc_bad": False,
            "measured_frac": 1.0,
            "registration_supported": True,
            "component_state": "none",
            "other_event_ids": [],
            "t0_detection_state": "not_accepted",
            "b5_peak": np.float64(0.0),
            "above_frac": 0.0,
            "candidate_applied": False,
        }
    )


def _first_outward(l0_clean: int, target_side: str) -> int:
    return l0_clean + 1 if target_side == "endpoint" else l0_clean - 1


def _apply_family_corruption(
    records: list[dict[str, Any]],
    *,
    design: CaseDesign,
    case_seed: int,
    base_id: str,
    geometry: CaseGeometry,
    clean_variant: bool,
) -> tuple[tuple[int, ...], dict[str, list[int]], dict[str, Any]]:
    """Apply only authorized family mechanics and return truth-side summaries."""
    support = {"X": [], "Q": [], "U": [], "R": [], "E": []}
    assignment: dict[str, Any] = {"other_frames": [], "unowned_frames": [], "other_event_id": None}

    # Acquisition boundary is intrinsic to F6 and remains in its clean/base construction.
    if design.family == "F6":
        for f in range(N_FRAMES):
            if not geometry.first_good <= f <= geometry.last_good:
                _neutral_boundary_row(records[f])
                support["E"].append(f)
        if clean_variant:
            # F6 has no clean-twin materialization in the frozen design.
            raise GeneratorInvariantError("clean_variant is only authorized for F1-F4")
        return tuple(geometry.corruption_window), support, assignment

    if clean_variant:
        if design.family not in {"F1", "F2", "F3", "F4"}:
            raise GeneratorInvariantError("clean twin is only authorized for F1-F4")
        return tuple(), support, assignment

    if design.family == "F0":
        return tuple(), support, assignment

    if design.family == "F0b":
        f = _first_outward(geometry.l0_clean, design.target_side)
        mechanism = str(design.factor("mechanism"))
        row = records[f]
        row["t0_detection_state"] = "not_accepted"
        row["component_state"] = "none"
        row["other_event_ids"] = []
        row["production_good"] = True
        row["secondary_qc_bad"] = False
        row["measured_frac"] = 1.0
        row["registration_supported"] = True
        peak = _f0b_signal(case_seed, f, design.sigma, mechanism)
        row["b5_peak"] = peak
        row["above_frac"] = 0.0 if mechanism == "N" else MIN_ABOVE_FRAC
        return (f,), support, assignment

    if design.family in {"F1", "F2", "F3", "F4"}:
        mode = str(design.factor("numerical_mode"))
        signal_state = "present" if mode == "presence-like" else "absent"
        accepted_self_stratum = _presence_like_self(design)
        for f in geometry.corruption_window:
            row = records[f]
            # Numerical mode always applies on every corruption frame.
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state=signal_state)
            if design.family == "F1":
                row["production_good"] = False
                row["t0_detection_state"] = "not_accepted"
                row["component_state"] = "none"
                row["other_event_ids"] = []
                support["X"].append(f)
            elif design.family == "F2":
                severity = str(design.factor("severity"))
                low, high = {
                    "mild": (0.40, 0.49),
                    "intermediate": (0.20, 0.39),
                    "severe": (0.00, 0.19),
                }[severity]
                mf = np.float64(purpose_rng(case_seed, b"f2-measured", f).uniform(low, high))
                row["measured_frac"] = mf
                row["above_frac"] = synthesize_above_frac(float(mf), float(row["b5_peak"]))
                support["U"].append(f)
            elif design.family == "F3":
                row["secondary_qc_bad"] = True
                support["Q"].append(f)
            elif design.family == "F4":
                row["registration_supported"] = False
                support["R"].append(f)

            # Q/U/R alone never delete an already accepted T0 positive.  The
            # accepted-self stratum additionally places accepted self identity
            # on every corrupted presence-like frame.
            if accepted_self_stratum:
                row["t0_detection_state"] = "accepted"
                row["component_state"] = "self"
                row["other_event_ids"] = []
        return tuple(geometry.corruption_window), support, assignment

    if design.family == "F5":
        f = _first_outward(geometry.l0_clean, design.target_side)
        row = records[f]
        row["t0_detection_state"] = "not_accepted"
        row["production_good"] = True
        row["secondary_qc_bad"] = False
        row["measured_frac"] = 1.0
        row["registration_supported"] = True
        _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="present")
        ownership = str(design.factor("ownership"))
        if ownership == "A":
            other_id = _opaque_related_id(base_id, b"f5-other")
            row["component_state"] = "other"
            row["other_event_ids"] = [other_id]
            assignment["other_frames"].append(f)
            assignment["other_event_id"] = other_id
        else:
            row["component_state"] = "unowned"
            row["other_event_ids"] = []
            assignment["unowned_frames"].append(f)
        return (f,), support, assignment

    if design.family == "F7b":
        A = int(design.factor("absence_length"))
        other_id = _opaque_related_id(base_id, b"f7b-recurrent")
        assignment["other_event_id"] = other_id
        absence: list[int] = []
        if design.target_side == "endpoint":
            absence = list(range(geometry.l0_clean + 1, geometry.l0_clean + A + 1))
            recurrent = list(range(geometry.l0_clean + A + 1, geometry.last_good + 1))
        else:
            absence = list(range(geometry.l0_clean - A, geometry.l0_clean))
            recurrent = list(range(geometry.first_good, geometry.l0_clean - A))
        for f in absence:
            row = records[f]
            row["t0_detection_state"] = "not_accepted"
            row["component_state"] = "none"
            row["other_event_ids"] = []
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="absent")
        for f in recurrent:
            row = records[f]
            row["t0_detection_state"] = "not_accepted"
            row["component_state"] = "other"
            row["other_event_ids"] = [other_id]
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="present")
            assignment["other_frames"].append(f)
        return tuple(absence), support, assignment

    if design.family == "F7a":
        return tuple(), support, assignment

    if design.family == "F8":
        f = _first_outward(geometry.l0_clean, design.target_side)
        row = records[f]
        row["t0_detection_state"] = "not_accepted"
        row["component_state"] = "none"
        row["other_event_ids"] = []
        combo = str(design.factor("combination"))
        if combo == "X+U":
            row["production_good"] = False
            row["measured_frac"] = 0.25
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="absent")
            support["X"].append(f)
            support["U"].append(f)
        elif combo == "Q+R":
            row["secondary_qc_bad"] = True
            row["registration_supported"] = False
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="absent")
            support["Q"].append(f)
            support["R"].append(f)
        elif combo == "U+A":
            row["measured_frac"] = 0.25
            other_id = _opaque_related_id(base_id, b"f8-other")
            row["component_state"] = "other"
            row["other_event_ids"] = [other_id]
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="present")
            row["above_frac"] = synthesize_above_frac(float(row["measured_frac"]), float(row["b5_peak"]))
            support["U"].append(f)
            assignment["other_frames"].append(f)
            assignment["other_event_id"] = other_id
        elif combo == "U+C":
            row["measured_frac"] = 0.25
            row["component_state"] = "unowned"
            _set_signal(row, case_seed=case_seed, sigma=design.sigma, signal_state="present")
            row["above_frac"] = synthesize_above_frac(float(row["measured_frac"]), float(row["b5_peak"]))
            support["U"].append(f)
            assignment["unowned_frames"].append(f)
        else:
            raise GeneratorInvariantError("unknown F8 combination")
        return (f,), support, assignment

    raise GeneratorInvariantError(f"unimplemented family {design.family}")


def _post_corruption_anchor(records: Sequence[Mapping[str, Any]], target_side: str) -> int:
    accepted = [int(row["frame"]) for row in records if row["t0_detection_state"] == "accepted"]
    if not accepted:
        raise GeneratorInvariantError("case has no post-corruption accepted target T0 detection")
    return max(accepted) if target_side == "endpoint" else min(accepted)


def _truth_trajectory(target_side: str, truth_time: float) -> list[bool]:
    if target_side == "endpoint":
        return [bool(f < truth_time) for f in range(N_FRAMES)]
    return [bool(f > truth_time) for f in range(N_FRAMES)]


def _materialize_case(
    design: CaseDesign,
    *,
    manifest: DevelopmentSeedManifest,
    clean_variant: bool,
) -> GeneratedCase:
    case_seed = development_case_seed(design.global_case_index)
    D = _draw_duration(case_seed, design.duration_bin)
    base_id = base_case_id(manifest.sha256, design.global_case_index)
    emitted_id = variant_case_id(base_id, clean_variant_descriptor()) if clean_variant else base_id
    geometry = _case_geometry(design)
    accepted = _clean_accepted_frames(design.target_side, geometry.l0_clean, D)
    edge_px = _edge_px(design)
    records = [
        _base_row(
            case_id=emitted_id,
            target_side=design.target_side,
            frame=f,
            edge_px=edge_px,
            accepted=f in accepted,
            case_seed=case_seed,
            sigma=design.sigma,
        )
        for f in range(N_FRAMES)
    ]

    corruption_window, support_state, assignment_state = _apply_family_corruption(
        records,
        design=design,
        case_seed=case_seed,
        base_id=base_id,
        geometry=geometry,
        clean_variant=clean_variant,
    )

    # Keep derived above_frac consistent after any support change not already refreshed.
    for row in records:
        if not row["movie_boundary"]:
            row["above_frac"] = synthesize_above_frac(float(row["measured_frac"]), float(row["b5_peak"]))
        validate_method_visible_record(row)
        if set(row) != set(METHOD_VISIBLE_FIELDS):
            raise GeneratorInvariantError("method-visible record key drift")

    l0_method = _post_corruption_anchor(records, design.target_side)
    clean_id = variant_case_id(base_id, clean_variant_descriptor()) if design.family in {"F1", "F2", "F3", "F4"} else None
    twin_mapping: Any
    if clean_variant:
        twin_mapping = base_id
    else:
        twin_mapping = clean_id

    truth = {
        "case_id": emitted_id,
        "family": design.family,
        "stratum": design.stratum,
        "target_side": design.target_side,
        "latent_transition_time": float(geometry.latent_transition_time),
        "true_event_presence_trajectory": _truth_trajectory(design.target_side, geometry.latent_transition_time),
        "true_corruption_window": list(corruption_window),
        "true_support_state": support_state,
        "true_assignment_identity": assignment_state,
        "duration_bin": design.duration_bin,
        "clean_twin_mapping": twin_mapping,
        "seed_metadata": {
            "namespace": "dev",
            "case_seed_uint64": int(case_seed),
            "global_case_index": int(design.global_case_index),
            "seed_manifest_hash": manifest.sha256,
            "D": int(D),
            "sigma": float(design.sigma),
            "l0_clean": int(geometry.l0_clean),
            "l0_method": int(l0_method),
            "first_good_frame": int(geometry.first_good),
            "last_good_frame": int(geometry.last_good),
            "matched_corruption_window": list(geometry.corruption_window),
            "variant": "clean" if clean_variant else "base",
        },
    }
    validate_truth_record(truth)

    construction = {
        "design": design,
        "base_case_id": base_id,
        "case_seed": case_seed,
        "D": D,
        "l0_clean": geometry.l0_clean,
        "l0_method": l0_method,
        "first_good_frame": geometry.first_good,
        "last_good_frame": geometry.last_good,
        "corruption_window": tuple(corruption_window),
        "support_truth": support_state,
        "is_clean_twin": clean_variant,
    }
    return GeneratedCase(tuple(records), truth, construction)


def generate_base_case(
    design: CaseDesign,
    manifest: DevelopmentSeedManifest | None = None,
) -> GeneratedCase:
    return _materialize_case(
        design,
        manifest=manifest or build_development_seed_manifest(),
        clean_variant=False,
    )


def generate_clean_twin(
    design: CaseDesign,
    manifest: DevelopmentSeedManifest | None = None,
) -> GeneratedCase:
    if design.family not in {"F1", "F2", "F3", "F4"}:
        raise GeneratorInvariantError("clean twins are frozen only for F1-F4")
    return _materialize_case(
        design,
        manifest=manifest or build_development_seed_manifest(),
        clean_variant=True,
    )


def generate_all_base_cases(
    manifest: DevelopmentSeedManifest | None = None,
) -> tuple[GeneratedCase, ...]:
    manifest = manifest or build_development_seed_manifest()
    return tuple(generate_base_case(design, manifest) for design in enumerate_base_designs())


# ---------------------------------------------------------------------------
# Inventory / invariant helpers
# ---------------------------------------------------------------------------


def generator_inventory(designs: Sequence[CaseDesign] | None = None) -> dict[str, Any]:
    designs = tuple(designs or enumerate_base_designs())
    family_counts = Counter(d.family for d in designs)
    target_counts: dict[str, Counter[str]] = defaultdict(Counter)
    duration_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for d in designs:
        target_counts[d.family][d.target_side] += 1
        duration_counts[d.family][d.duration_bin] += 1

    core = [d for d in designs if d.family in PRIMARY_FAMILIES]
    return {
        "schema": "STAGE3A3_GENERATOR_INVENTORY_V1",
        "base_latent_units": len(designs),
        "core_primary_families": len(PRIMARY_FAMILIES),
        "core_latent_cases_total": len(core),
        "core_endpoint_targeted": sum(d.target_side == "endpoint" for d in core),
        "core_onset_targeted": sum(d.target_side == "onset" for d in core),
        "family_counts": dict(family_counts),
        "target_counts": {k: dict(v) for k, v in target_counts.items()},
        "duration_counts": {k: dict(v) for k, v in duration_counts.items()},
        "f7a_reference_cases": family_counts["F7a"],
        "f8_secondary_cases": family_counts["F8"],
    }


def assert_base_inventory_invariants(designs: Sequence[CaseDesign] | None = None) -> None:
    designs = tuple(designs or enumerate_base_designs())
    inv = generator_inventory(designs)
    expected_families = {family: 324 for family in PRIMARY_FAMILIES}
    expected_families.update({"F7a": 162, "F8": 216})
    if inv["family_counts"] != expected_families:
        raise GeneratorInvariantError(f"family count mismatch: {inv['family_counts']}")
    if inv["core_latent_cases_total"] != 2916:
        raise GeneratorInvariantError("core total must be 2916")
    if inv["core_endpoint_targeted"] != 1944 or inv["core_onset_targeted"] != 972:
        raise GeneratorInvariantError("core target-side totals mismatch")
    if inv["base_latent_units"] != 3294:
        raise GeneratorInvariantError("base latent inventory must be 3294")

    # v1.4 exact F1-F4 duration/noise allocations within every 18-cell stratum.
    for family in ("F1", "F2", "F3", "F4"):
        cells: dict[tuple[Any, ...], list[CaseDesign]] = defaultdict(list)
        for d in designs:
            if d.family != family:
                continue
            key = (d.factor("transition"), d.factor("numerical_mode"), d.factor("severity"), d.target_side)
            cells[key].append(d)
        if len(cells) != 36:  # 18 scientific cells x 2 target sides
            raise GeneratorInvariantError(f"{family} target-side cell count mismatch")
        for key, members in cells.items():
            target = key[-1]
            expected_n = 12 if target == "endpoint" else 6
            if len(members) != expected_n:
                raise GeneratorInvariantError(f"{family} {key} replicate count mismatch")
            duration = Counter(d.duration_bin for d in members)
            expected_duration = {"short": 4, "medium": 4, "long": 4} if target == "endpoint" else {"short": 2, "medium": 2, "long": 2}
            if duration != expected_duration:
                raise GeneratorInvariantError(f"{family} {key} duration mapping mismatch")


def find_designs(*, family: str, target_side: str | None = None, **factor_equals: Any) -> tuple[CaseDesign, ...]:
    out = []
    for design in enumerate_base_designs():
        if design.family != family:
            continue
        if target_side is not None and design.target_side != target_side:
            continue
        if any(design.factor(k) != v for k, v in factor_equals.items()):
            continue
        out.append(design)
    return tuple(out)
