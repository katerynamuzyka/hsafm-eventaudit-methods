"""Development-only Stage 3A.3 variants and decoy-position mechanics."""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .boundary_record import validate_method_visible_record
from .generator import GeneratedCase, GeneratorInvariantError, synthesize_above_frac
from .generator_seed import (
    rate_token,
    support_perturbation_rng,
    support_variant_descriptor,
    variant_case_id,
)
from .truth_record import validate_truth_record

ALLOWED_RATES = (0.0, 0.10, 0.25)


def _selection_count(rate: float, n_eligible: int) -> int:
    if float(rate) not in ALLOWED_RATES:
        raise GeneratorInvariantError("perturbation rate must be 0, 0.10 or 0.25")
    if n_eligible < 0:
        raise GeneratorInvariantError("eligible-frame count cannot be negative")
    return max(0, min(n_eligible, math.floor(float(rate) * n_eligible + 0.5)))


def _fp_eligible(row: Mapping[str, Any]) -> bool:
    return (
        row["movie_boundary"] is False
        and row["production_good"] is True
        and row["secondary_qc_bad"] is False
        and float(row["measured_frac"]) >= 0.50
        and row["registration_supported"] is True
    )


def support_truth_pools(case: GeneratedCase) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return canonical truth-defined FN and FP pools from the unperturbed case."""
    support_truth = case.construction["support_truth"]
    fn_set = set()
    for axis in ("Q", "U", "R"):
        fn_set.update(int(f) for f in support_truth.get(axis, []))
    fn_pool = tuple(sorted(fn_set))
    fp_pool = tuple(sorted(int(row["frame"]) for row in case.method_records if _fp_eligible(row)))
    # True X/Q/U/R frames are excluded by the predicate or removed explicitly.
    true_failed = set(int(f) for axis in ("X", "Q", "U", "R") for f in support_truth.get(axis, []))
    fp_pool = tuple(f for f in fp_pool if f not in true_failed)
    if set(fn_pool) & set(fp_pool):
        raise GeneratorInvariantError("truth-defined FN and FP pools must be disjoint")
    return fn_pool, fp_pool


def apply_support_perturbation(
    case: GeneratedCase,
    *,
    fn_rate: float,
    fp_rate: float,
) -> GeneratedCase:
    """Materialize one deterministic support-perturbation variant."""
    fn_rate = float(fn_rate)
    fp_rate = float(fp_rate)
    # Canonical token validation also rejects alternate numeric values.
    rate_token(fn_rate)
    rate_token(fp_rate)

    case_seed = int(case.construction["case_seed"])
    fn_pool, fp_pool = support_truth_pools(case)
    n_fn = _selection_count(fn_rate, len(fn_pool))
    n_fp = _selection_count(fp_rate, len(fp_pool))

    rng = support_perturbation_rng(case_seed, fn_rate, fp_rate)
    fn_order = rng.permutation(np.asarray(fn_pool, dtype=np.int64))
    fp_order = rng.permutation(np.asarray(fp_pool, dtype=np.int64))
    fn_selected = sorted(int(x) for x in fn_order[:n_fn])
    fp_selected = sorted(int(x) for x in fp_order[:n_fp])

    is_clean = bool(case.construction.get("is_clean_twin", False))
    base_id = str(case.construction["base_case_id"])
    descriptor = support_variant_descriptor(fn_rate, fp_rate, clean=is_clean)
    new_id = variant_case_id(base_id, descriptor)

    records = [copy.deepcopy(row) for row in case.method_records]
    by_frame = {int(row["frame"]): row for row in records}
    support_truth = case.construction["support_truth"]

    for f in fn_selected:
        row = by_frame[f]
        if f in support_truth.get("Q", []):
            row["secondary_qc_bad"] = False
        if f in support_truth.get("U", []):
            row["measured_frac"] = 0.75
        if f in support_truth.get("R", []):
            row["registration_supported"] = True

    for i, f in enumerate(fp_selected):
        row = by_frame[f]
        axis = ("Q", "U", "R")[i % 3]
        if axis == "Q":
            row["secondary_qc_bad"] = True
        elif axis == "U":
            row["measured_frac"] = 0.25
        else:
            row["registration_supported"] = False

    for row in records:
        row["case_id"] = new_id
        if not row["movie_boundary"]:
            row["above_frac"] = synthesize_above_frac(float(row["measured_frac"]), float(row["b5_peak"]))
        validate_method_visible_record(row)

    truth = copy.deepcopy(case.truth_record)
    truth["case_id"] = new_id
    truth["clean_twin_mapping"] = {
        "base_latent_case_id": base_id,
        "source_variant_case_id": case.case_id,
    }
    truth["seed_metadata"] = copy.deepcopy(truth["seed_metadata"])
    truth["seed_metadata"].update(
        {
            "variant": "clean-support" if is_clean else "support",
            "fn_rate": fn_rate,
            "fp_rate": fp_rate,
            "fn_selected_frames": fn_selected,
            "fp_selected_frames": fp_selected,
        }
    )
    validate_truth_record(truth)

    construction = copy.deepcopy(case.construction)
    construction.update(
        {
            "source_case_id": case.case_id,
            "is_support_variant": True,
            "fn_rate": fn_rate,
            "fp_rate": fp_rate,
            "fn_pool": fn_pool,
            "fp_pool": fp_pool,
            "fn_selected": tuple(fn_selected),
            "fp_selected": tuple(fp_selected),
        }
    )
    return GeneratedCase(tuple(records), truth, construction)


def materialize_support_grid(case: GeneratedCase) -> tuple[GeneratedCase, ...]:
    return tuple(
        apply_support_perturbation(case, fn_rate=fn_rate, fp_rate=fp_rate)
        for fn_rate in ALLOWED_RATES
        for fp_rate in ALLOWED_RATES
    )


def resolve_decoy_position(case: GeneratedCase, category: str) -> int:
    """Resolve D1/D2/D3 exactly, failing closed if category cannot be preserved."""
    records = {int(row["frame"]): row for row in case.method_records}
    side = str(case.truth_record["target_side"])
    l0 = int(case.construction["l0_method"])

    if category == "D1":
        accepted = sorted(
            f for f, row in records.items() if row["t0_detection_state"] == "accepted"
        )
        if not accepted:
            raise GeneratorInvariantError("D1 requires at least one accepted target T0 frame")
        midpoint = (accepted[0] + accepted[-1]) / 2.0
        distances = [(abs(f - midpoint), f) for f in accepted]
        min_dist = min(d for d, _ in distances)
        tied = [f for d, f in distances if d == min_dist]
        return max(tied) if side == "endpoint" else min(tied)

    if category == "D2":
        for offset in (3, 2, 4, 1, 5):
            f = l0 + offset if side == "endpoint" else l0 - offset
            if 0 <= f < 64 and _fp_eligible(records[f]):
                return f
        raise GeneratorInvariantError("no category-preserving D2 frame exists")

    if category == "D3":
        for d in range(8, 64):
            candidates = (l0 + d, l0 - d) if side == "endpoint" else (l0 - d, l0 + d)
            for f in candidates:
                if 0 <= f < 64 and abs(f - l0) >= 8 and _fp_eligible(records[f]):
                    return f
        raise GeneratorInvariantError("no category-preserving D3 frame exists")

    raise GeneratorInvariantError("decoy category must be D1, D2 or D3")


def assert_unique_case_ids(cases: Sequence[GeneratedCase]) -> None:
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise GeneratorInvariantError("materialized case_id collision")
