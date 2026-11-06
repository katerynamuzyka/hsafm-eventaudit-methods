"""Development-only Stage-3A.2 bridge to frozen ``evidence.py``.

This module does not generate benchmark families or held-out cases.  It builds
small deterministic pixel/observer fixtures, invokes the exact frozen reference
source read-only, derives Stage-3 method-visible records from the same observer
quantities by one explicit adapter, and compares frozen B6 outputs with the
Stage-3 record-level B6 implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

import numpy as np

from .baselines import (
    LOOKAHEAD_FRAMES,
    b6_frame_code,
    evaluate_b6_boundary,
)

FROZEN_EVIDENCE_SHA256 = "5484fdfb9faceec14ca7ef3b9e0b5017f96e8d0c46f1b4581c17b25405a4cce1"
HELD_OUT_EXECUTION_AUTHORIZED = False
SCIENTIFIC_HELDOUT_EXECUTION = 0

N_FRAMES = 64
SHAPE = (40, 40)
BORDER_PX = 12
FOOTPRINT_SHAPE = (4, 5)  # 20 pixels: exact 0.50 and 0.05 fractions are representable.
SELF_EVENT_ID = 0
SELF_TRACK_ID = 10
OTHER_EVENT_ID = 1
OTHER_TRACK_ID = 99
DT_S = 1.0


@dataclass
class ToyFrame:
    """Minimal image-level frame state consumed by frozen ``evidence.py``."""

    good: bool
    valid: np.ndarray
    labels: np.ndarray
    above_k: np.ndarray
    zf: np.ndarray
    shift: tuple[float, float]


@dataclass
class ToyObservation:
    """Minimal frozen-observer surface required by ``audit_events``."""

    frames: dict[int, ToyFrame]
    tracks: list[dict[str, Any]]
    events: list[dict[str, Any]]
    comp_owner: dict[tuple[int, int], int]
    cfg: dict[str, Any]
    shape: tuple[int, int]
    good: list[int]
    dt_s: float
    track_to_event: dict[int, int]

    def event_of_track(self, track_id: int) -> int | None:
        return self.track_to_event.get(track_id)


@dataclass(frozen=True)
class FrameDirective:
    """Toy image/observer condition, never an expected B6 label."""

    production_good: bool = True
    secondary_qc_bad: bool = False
    measured_frac: float = 1.0
    above_frac: float = 0.0
    component_state: str = "none"
    shift_dx: float = 0.0


@dataclass
class ConformanceFixture:
    """One deterministic development-only toy scenario."""

    name: str
    groups: tuple[str, ...]
    side: str
    anchor_frame: int
    edge_px_requested: int
    directives: tuple[FrameDirective, ...]
    obs: ToyObservation
    frame_qc: frozenset[int]
    anchor_component: int = 0
    case_id: str = ""


@dataclass(frozen=True)
class ConformanceResult:
    name: str
    groups: tuple[str, ...]
    side: str
    frozen_codes: str
    stage3_codes: str
    frozen_class: str
    stage3_class: str
    frozen_interval_frames: str | None
    stage3_interval_frames: str | None
    frozen_interval_s: str | None
    stage3_interval_s_bridge: str | None
    frozen_boundary: str | None
    stage3_boundary: str | None
    frozen_edge_px: int | None
    stage3_edge_px: int
    per_frame_code_equal: bool
    additive_component_state: str | None
    additive_other_event_ids: tuple[Any, ...]
    mismatch_fields: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatch_fields


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_frozen_evidence(path: Path) -> ModuleType:
    """Load the exact frozen source read-only after enforcing its SHA-256."""
    path = Path(path)
    actual = _sha256_file(path)
    if actual != FROZEN_EVIDENCE_SHA256:
        raise RuntimeError(
            "frozen evidence.py identity mismatch: "
            f"expected {FROZEN_EVIDENCE_SHA256}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location("eventaudit_stage3_frozen_evidence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen evidence source: {path}")
    module = importlib.util.module_from_spec(spec)
    # Python 3.13 dataclasses resolve annotations through sys.modules while the
    # module body executes.  Register only the temporary import object; the
    # frozen source bytes remain untouched.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def _footprint_slice(edge_px: int) -> tuple[slice, slice]:
    """Place a 20-pixel anchor footprint at an exact frozen edge distance."""
    h, w = FOOTPRINT_SHAPE
    if edge_px < 0:
        raise ValueError("edge_px must be non-negative")
    # Fix x comfortably inside the detector border; move only y to control edge.
    y0 = BORDER_PX + edge_px
    x0 = 18
    if y0 + h > SHAPE[0] - BORDER_PX or x0 + w > SHAPE[1] - BORDER_PX:
        raise ValueError("requested footprint does not fit inside toy image")
    return slice(y0, y0 + h), slice(x0, x0 + w)


def _empty_frame(fp: np.ndarray) -> ToyFrame:
    valid = np.ones(SHAPE, dtype=bool)
    labels = np.zeros(SHAPE, dtype=np.int16)
    above_k = np.zeros(SHAPE, dtype=bool)
    zf = np.zeros(SHAPE, dtype=float)
    zf[fp] = 0.2
    return ToyFrame(
        good=True,
        valid=valid,
        labels=labels,
        above_k=above_k,
        zf=zf,
        shift=(0.0, 0.0),
    )


def _measured_indices(fp: np.ndarray, measured_frac: float) -> np.ndarray:
    coords = np.argwhere(fp)
    n = len(coords)
    count_float = measured_frac * n
    count = int(round(count_float))
    if not math.isclose(count_float, count, abs_tol=1e-12):
        raise ValueError(
            f"toy footprint of {n} pixels cannot represent measured_frac={measured_frac} exactly"
        )
    if not 0 <= count <= n:
        raise ValueError("measured_frac outside [0,1]")
    return coords[:count]


def _apply_directive(
    frame: ToyFrame,
    directive: FrameDirective,
    fp: np.ndarray,
    *,
    frame_index: int,
    comp_owner: dict[tuple[int, int], int],
    frame_qc: set[int],
) -> None:
    frame.good = directive.production_good
    if directive.secondary_qc_bad:
        frame_qc.add(frame_index)

    # Measured support is controlled only within the anchor footprint.  Pixels
    # outside it remain source-valid so frozen registration has a stable background.
    frame.valid[fp] = False
    measured = _measured_indices(fp, directive.measured_frac)
    if len(measured):
        yy, xx = measured[:, 0], measured[:, 1]
        frame.valid[yy, xx] = True

    frame.above_k[fp] = False
    frame.zf[fp] = 0.2
    above_count_float = directive.above_frac * len(measured)
    above_count = int(round(above_count_float))
    if not math.isclose(above_count_float, above_count, abs_tol=1e-12):
        raise ValueError(
            f"measured-pixel count {len(measured)} cannot represent above_frac={directive.above_frac} exactly"
        )
    if above_count:
        chosen = measured[:above_count]
        yy, xx = chosen[:, 0], chosen[:, 1]
        frame.above_k[yy, xx] = True
        frame.zf[yy, xx] = 1.2

    frame.labels[fp] = 0
    if directive.component_state != "none" and len(measured):
        yy, xx = measured[:, 0], measured[:, 1]
        frame.labels[yy, xx] = 1
        if directive.component_state == "self":
            comp_owner[(frame_index, 0)] = SELF_TRACK_ID
        elif directive.component_state == "other":
            comp_owner[(frame_index, 0)] = OTHER_TRACK_ID
        elif directive.component_state == "unowned":
            comp_owner.pop((frame_index, 0), None)
        else:
            raise ValueError(f"unknown component_state {directive.component_state!r}")

    frame.shift = (0.0, float(directive.shift_dx))


def _default_anchor(side: str) -> int:
    return 20 if side == "endpoint" else 43


def _e_anchor(side: str) -> int:
    return 61 if side == "endpoint" else 2


def _temporal_anchor(side: str) -> int:
    return 60 if side == "endpoint" else 3


def _step(side: str) -> int:
    if side == "endpoint":
        return 1
    if side == "onset":
        return -1
    raise ValueError(f"unknown side {side!r}")


def _case_id(name: str, side: str) -> str:
    # Development fixture identity only; not a seed and not a held-out namespace.
    return hashlib.sha256(f"stage3a2-development-fixture|{name}|{side}".encode()).hexdigest()[:16]


def build_fixture(
    *,
    name: str,
    groups: Iterable[str],
    side: str,
    directives: Iterable[FrameDirective],
    edge_px: int = 3,
    anchor_frame: int | None = None,
) -> ConformanceFixture:
    """Build one toy image/observer fixture from physical observer conditions."""
    anchor = _default_anchor(side) if anchor_frame is None else anchor_frame
    step = _step(side)
    directives = tuple(directives)

    fp = np.zeros(SHAPE, dtype=bool)
    ys, xs = _footprint_slice(edge_px)
    fp[ys, xs] = True

    frames = {i: _empty_frame(fp) for i in range(N_FRAMES)}
    comp_owner: dict[tuple[int, int], int] = {}
    frame_qc: set[int] = set()

    # Anchor component defines the frozen footprint and is owned by the audited event.
    frames[anchor].labels[fp] = 1
    comp_owner[(anchor, 0)] = SELF_TRACK_ID

    for offset, directive in enumerate(directives, start=1):
        g = anchor + step * offset
        if 0 <= g < N_FRAMES:
            _apply_directive(
                frames[g], directive, fp,
                frame_index=g,
                comp_owner=comp_owner,
                frame_qc=frame_qc,
            )
        else:
            # Out-of-movie E is represented by geometry, not by a synthetic frame.
            break

    good = sorted(i for i, st in frames.items() if st.good)
    if not good:
        raise ValueError("toy observation must contain at least one production-good frame")

    obs = ToyObservation(
        frames=frames,
        tracks=[{
            "event_index": SELF_EVENT_ID,
            "points": [(anchor, 0)],
            "track_id": SELF_TRACK_ID,
        }],
        events=[{"fully_observed": False}, {"fully_observed": False}],
        comp_owner=comp_owner,
        cfg={"border_px": BORDER_PX, "coordinate_frame": "registered"},
        shape=SHAPE,
        good=good,
        dt_s=DT_S,
        track_to_event={SELF_TRACK_ID: SELF_EVENT_ID, OTHER_TRACK_ID: OTHER_EVENT_ID},
    )
    return ConformanceFixture(
        name=name,
        groups=tuple(groups),
        side=side,
        anchor_frame=anchor,
        edge_px_requested=edge_px,
        directives=directives,
        obs=obs,
        frame_qc=frozenset(frame_qc),
        case_id=_case_id(name, side),
    )


def _D(**kwargs: Any) -> FrameDirective:
    return FrameDirective(**kwargs)


def build_fixture_inventory() -> list[ConformanceFixture]:
    """Return all predeclared deterministic Stage-3A.2 development fixtures."""
    fixtures: list[ConformanceFixture] = []

    def add_pair(
        name: str,
        groups: tuple[str, ...],
        directives: tuple[FrameDirective, ...],
        *,
        edge_px: int = 3,
        anchor_mode: str = "default",
    ) -> None:
        for side in ("endpoint", "onset"):
            if anchor_mode == "default":
                anchor = _default_anchor(side)
            elif anchor_mode == "e":
                anchor = _e_anchor(side)
            elif anchor_mode == "temporal":
                anchor = _temporal_anchor(side)
            else:
                raise ValueError(anchor_mode)
            fixtures.append(build_fixture(
                name=name,
                groups=groups + (("onset_time_reverse",) if side == "onset" else ()),
                side=side,
                directives=directives,
                edge_px=edge_px,
                anchor_frame=anchor,
            ))

    # 1. Immediate temporal censoring: the anchor is first/last good because all
    # remaining raw frames toward the movie edge are production-excluded X.
    add_pair(
        "temporal_anchor_trailing_leading_x",
        ("temporal_anchor",),
        (_D(production_good=False), _D(production_good=False), _D(production_good=False)),
        anchor_mode="temporal",
    )

    # 2. E reached after zero N, after one N, and after an X gap.  A final Q frame
    # keeps the physical edge frame production-good so the anchor itself is not the
    # immediate first/last-good temporal boundary.
    add_pair("e_after_zero_n", ("e_reached",), (_D(secondary_qc_bad=True), _D(secondary_qc_bad=True)), anchor_mode="e")
    add_pair("e_after_one_n", ("e_reached",), (_D(), _D(secondary_qc_bad=True)), anchor_mode="e")
    add_pair("e_after_x_gap", ("e_reached",), (_D(production_good=False), _D(secondary_qc_bad=True)), anchor_mode="e")

    # 3. Twelve raw-frame exhaustion families.
    mixed_gaps = tuple(
        _D(production_good=False) if i % 3 == 0 else
        _D(secondary_qc_bad=True) if i % 3 == 1 else
        _D(measured_frac=0.4)
        for i in range(12)
    )
    add_pair("lookahead_12_xqu", ("lookahead_exhaustion",), mixed_gaps)
    alternating = tuple(_D(production_good=False) if i % 2 == 0 else _D() for i in range(12))
    add_pair("lookahead_alternating_x_n", ("lookahead_exhaustion",), alternating)

    # 4. Consecutive-N reset.
    add_pair(
        "n_x_n_n_reset",
        ("n_run_reset",),
        (_D(), _D(production_good=False), _D(), _D()),
    )

    # 5. Frozen threshold boundaries.
    add_pair("measured_frac_exact_0_50", ("thresholds",), (_D(measured_frac=0.5), _D()))
    add_pair("above_frac_exact_0_05", ("thresholds",), (_D(above_frac=0.05),))
    for edge in (1, 2, 3):
        add_pair(f"edge_px_exact_{edge}", ("thresholds",), (_D(), _D()), edge_px=edge)

    # 6. Spatial override crossed with every provisional frozen B6 class.
    spatial_cases: tuple[tuple[str, tuple[FrameDirective, ...], str], ...] = (
        ("svn", (_D(), _D()), "default"),
        ("obs", (_D(production_good=False), _D(), _D()), "default"),
        ("unresolved", (_D(above_frac=0.05),), "default"),
        ("registration_limited", (_D(shift_dx=25.0),), "default"),
        ("assignment_ambiguous", (_D(component_state="other"),), "default"),
        ("candidate_reappearance", (_D(production_good=False), _D(component_state="other")), "default"),
        ("boundary_censored", (_D(secondary_qc_bad=True), _D(secondary_qc_bad=True)), "e"),
    )
    for label, directives, mode in spatial_cases:
        add_pair(
            f"spatial_cross_{label}",
            ("spatial_override", "interval_after_spatial_override") if label in {"svn", "obs"} else ("spatial_override",),
            directives,
            edge_px=1,
            anchor_mode=mode,
        )

    # 7. Precedence co-occurrences and additive invariant #6.
    add_pair("cooccur_u_and_c", ("cooccurrence",), (_D(measured_frac=0.4, component_state="unowned"), _D(), _D()))
    add_pair("cooccur_q_and_a", ("cooccurrence",), (_D(secondary_qc_bad=True, component_state="other"), _D(), _D()))
    add_pair("cooccur_x_and_assignment", ("cooccurrence",), (_D(production_good=False, component_state="other"), _D(), _D()))
    add_pair("cooccur_r_and_a", ("cooccurrence", "invariant6"), (_D(shift_dx=25.0, component_state="other"),))

    # Direct C-code coverage (all other codes/classes occur in the groups above).
    add_pair("direct_c_unowned", ("direct_code_coverage",), (_D(component_state="unowned"),))

    return fixtures


def _anchor_footprint(frozen: ModuleType, fixture: ConformanceFixture) -> np.ndarray:
    return frozen._footprint(fixture.obs, fixture.anchor_frame, fixture.anchor_component)


def _edge_px_from_anchor(frozen: ModuleType, fixture: ConformanceFixture) -> int:
    fp = _anchor_footprint(frozen, fixture)
    ny, nx = fixture.obs.shape
    b0 = fixture.obs.cfg.get("border_px", 12)
    ys, xs = np.nonzero(fp)
    return int(min(ys.min() - b0, ny - 1 - b0 - ys.max(), xs.min() - b0, nx - 1 - b0 - xs.max()))


def _registration_supported(
    frozen: ModuleType,
    fixture: ConformanceFixture,
    frame: int,
    params: Any,
) -> bool:
    if not 0 <= frame < len(fixture.obs.frames):
        return False
    obs = fixture.obs
    st = obs.frames[frame]
    f_ref = fixture.anchor_frame
    fp = _anchor_footprint(frozen, fixture)
    if obs.cfg.get("coordinate_frame") == "unknown":
        return False
    jump = float(np.hypot(
        st.shift[0] - obs.frames[f_ref].shift[0],
        st.shift[1] - obs.frames[f_ref].shift[1],
    ))
    if max(float(np.hypot(*st.shift)), jump) > params.max_plausible_shift_px:
        return False
    if params.reg_check:
        ok, _off, _gain = frozen._reg_check(obs, f_ref, frame, fp, params)
        return bool(ok)
    return True


def _component_state_and_ids(
    fixture: ConformanceFixture,
    frame: int,
    fp: np.ndarray,
) -> tuple[str, list[int]]:
    if not 0 <= frame < len(fixture.obs.frames):
        return "none", []
    st = fixture.obs.frames[frame]
    meas = fp & st.valid
    lab = st.labels[meas]
    comps = np.unique(lab[lab > 0]) - 1
    if comps.size == 0:
        return "none", []

    owners = [fixture.obs.comp_owner.get((frame, int(c))) for c in comps]
    event_ids = [fixture.obs.event_of_track(t) if t is not None else None for t in owners]
    others = sorted({int(e) for e in event_ids if e is not None and e != SELF_EVENT_ID})
    if others:
        return "other", others
    if any(e == SELF_EVENT_ID for e in event_ids):
        return "self", []
    return "unowned", []


def extract_method_visible_record(
    frozen: ModuleType,
    fixture: ConformanceFixture,
    frame: int,
    *,
    params: Any | None = None,
) -> dict[str, Any]:
    """Derive one Stage-3 record from the same toy observer quantities.

    This is the single extraction rule used for all conformance cases.  It never
    receives an expected code/class.  Frozen registration helper logic is reused
    read-only solely to expose the same observer registration state as a boolean.
    """
    params = frozen.AuditParams() if params is None else params
    fp = _anchor_footprint(frozen, fixture)
    edge_px = _edge_px_from_anchor(frozen, fixture)
    movie_boundary = not (0 <= frame < len(fixture.obs.frames))

    if movie_boundary:
        return {
            "case_id": fixture.case_id,
            "target_side": fixture.side,
            "frame": frame,
            "time_frame_units": frame,
            "t0_event_id": SELF_EVENT_ID,
            "t0_track_id": SELF_TRACK_ID,
            "t0_detection_state": "accepted_anchor" if frame == fixture.anchor_frame else "observer_frame",
            "production_good": False,
            "secondary_qc_bad": False,
            "measured_frac": 0.0,
            "registration_supported": False,
            "b5_peak": 0.0,
            "above_frac": math.nan,
            "component_state": "none",
            "other_event_ids": [],
            "edge_px": edge_px,
            "movie_boundary": True,
            "candidate_applied": False,
        }

    st = fixture.obs.frames[frame]
    meas = fp & st.valid
    measured_frac = float(meas.sum() / max(fp.sum(), 1))
    if meas.any():
        above_frac = float(st.above_k[meas].mean())
        b5_peak = float(np.max(st.zf[meas]))
    else:
        above_frac = math.nan
        b5_peak = 0.0
    component_state, other_ids = _component_state_and_ids(fixture, frame, fp)

    return {
        "case_id": fixture.case_id,
        "target_side": fixture.side,
        "frame": frame,
        "time_frame_units": frame,
        "t0_event_id": SELF_EVENT_ID,
        "t0_track_id": SELF_TRACK_ID,
        "t0_detection_state": "accepted_anchor" if frame == fixture.anchor_frame else "observer_frame",
        "production_good": bool(st.good),
        "secondary_qc_bad": frame in fixture.frame_qc,
        "measured_frac": measured_frac,
        "registration_supported": _registration_supported(frozen, fixture, frame, params),
        "b5_peak": b5_peak,
        "above_frac": above_frac,
        "component_state": component_state,
        "other_event_ids": other_ids,
        "edge_px": edge_px,
        "movie_boundary": False,
        "candidate_applied": False,
    }


def _stage3_interval_s(interval_frames: str | None, dt_s: float) -> str | None:
    """Bridge-only rendering of frozen seconds field from Stage-3 frame interval."""
    if interval_frames is None:
        return None
    lo_s, hi_s = interval_frames.strip("[]").split(",")
    lo, hi = int(lo_s), int(hi_s)
    return f"[{lo * dt_s:.3f},{hi * dt_s:.3f}]"


def compare_fixture(frozen: ModuleType, fixture: ConformanceFixture) -> ConformanceResult:
    """Run one fixture through frozen image-level and Stage-3 record-level paths."""
    params = frozen.AuditParams()
    frozen_all = frozen.audit_events(fixture.obs, frame_qc=set(fixture.frame_qc), params=params)
    frozen_event = next(row for row in frozen_all["events"] if row["event_index"] == SELF_EVENT_ID)
    frozen_side = "end" if fixture.side == "endpoint" else "start"

    anchor_record = extract_method_visible_record(frozen, fixture, fixture.anchor_frame, params=params)
    step = _step(fixture.side)
    outward_records = [
        extract_method_visible_record(
            frozen,
            fixture,
            fixture.anchor_frame + step * offset,
            params=params,
        )
        for offset in range(1, LOOKAHEAD_FRAMES + 1)
    ]
    stage3 = evaluate_b6_boundary(
        anchor_record=anchor_record,
        outward_records=outward_records,
        first_good_frame=fixture.obs.good[0],
        last_good_frame=fixture.obs.good[-1],
    )

    frozen_codes = frozen_event[f"{frozen_side}_codes"]
    frozen_class = frozen_event[f"{frozen_side}_class"]
    frozen_interval_frames = frozen_event.get(f"{frozen_side}_interval_frames")
    frozen_interval_s = frozen_event.get(f"{frozen_side}_interval_s")
    frozen_boundary = frozen_event.get(f"{frozen_side}_boundary")
    frozen_edge = frozen_event.get(f"{frozen_side}_edge_px")

    per_frame_equal = True
    fp = _anchor_footprint(frozen, fixture)
    for offset, frozen_code_from_walk in enumerate(frozen_codes, start=1):
        g = fixture.anchor_frame + step * offset
        direct_frozen_code, _ = frozen._code(
            fixture.obs,
            fixture.anchor_frame,
            g,
            fp,
            SELF_EVENT_ID,
            set(fixture.frame_qc),
            params,
        )
        stage3_code = b6_frame_code(extract_method_visible_record(frozen, fixture, g, params=params))
        if direct_frozen_code != frozen_code_from_walk or stage3_code != direct_frozen_code:
            per_frame_equal = False
            break

    stage3_interval_s = _stage3_interval_s(stage3.interval_frames, fixture.obs.dt_s)
    mismatches: list[str] = []
    if frozen_codes != stage3.codes:
        mismatches.append("codes")
    if frozen_class != stage3.final_class:
        mismatches.append("class")
    if frozen_interval_frames != stage3.interval_frames:
        mismatches.append("interval_frames")
    if frozen_interval_s != stage3_interval_s:
        mismatches.append("interval_s")
    if frozen_boundary != stage3.boundary:
        mismatches.append("boundary")
    if frozen_edge is not None and int(frozen_edge) != stage3.edge_px:
        mismatches.append("edge_px")
    if not per_frame_equal:
        mismatches.append("per_frame_code")

    return ConformanceResult(
        name=fixture.name,
        groups=fixture.groups,
        side=fixture.side,
        frozen_codes=frozen_codes,
        stage3_codes=stage3.codes,
        frozen_class=frozen_class,
        stage3_class=stage3.final_class,
        frozen_interval_frames=frozen_interval_frames,
        stage3_interval_frames=stage3.interval_frames,
        frozen_interval_s=frozen_interval_s,
        stage3_interval_s_bridge=stage3_interval_s,
        frozen_boundary=frozen_boundary,
        stage3_boundary=stage3.boundary,
        frozen_edge_px=None if frozen_edge is None else int(frozen_edge),
        stage3_edge_px=stage3.edge_px,
        per_frame_code_equal=per_frame_equal,
        additive_component_state=stage3.decisive_component_state,
        additive_other_event_ids=stage3.decisive_other_event_ids,
        mismatch_fields=tuple(mismatches),
    )


def run_conformance_suite(frozen_path: Path) -> dict[str, Any]:
    frozen = load_frozen_evidence(Path(frozen_path))
    fixtures = build_fixture_inventory()
    results = [compare_fixture(frozen, fixture) for fixture in fixtures]
    mismatch_count = sum(not result.passed for result in results)
    return {
        "stage": "Stage 3A.2",
        "development_only": True,
        "frozen_evidence_py_sha256": FROZEN_EVIDENCE_SHA256,
        "held_out_execution_authorized": False,
        "scientific_heldout_execution": 0,
        "fixture_count": len(fixtures),
        "fixture_inventory": [
            {
                "name": f.name,
                "side": f.side,
                "groups": list(f.groups),
                "anchor_frame": f.anchor_frame,
                "edge_px_requested": f.edge_px_requested,
            }
            for f in fixtures
        ],
        "mismatch_count": mismatch_count,
        "status": "PASS" if mismatch_count == 0 else "FAIL",
        "results": [
            {
                "name": r.name,
                "side": r.side,
                "groups": list(r.groups),
                "frozen_codes": r.frozen_codes,
                "stage3_codes": r.stage3_codes,
                "frozen_class": r.frozen_class,
                "stage3_class": r.stage3_class,
                "frozen_interval_frames": r.frozen_interval_frames,
                "stage3_interval_frames": r.stage3_interval_frames,
                "frozen_interval_s": r.frozen_interval_s,
                "stage3_interval_s_bridge": r.stage3_interval_s_bridge,
                "frozen_boundary": r.frozen_boundary,
                "stage3_boundary": r.stage3_boundary,
                "frozen_edge_px": r.frozen_edge_px,
                "stage3_edge_px": r.stage3_edge_px,
                "per_frame_code_equal": r.per_frame_code_equal,
                "additive_component_state": r.additive_component_state,
                "additive_other_event_ids": list(r.additive_other_event_ids),
                "mismatch_fields": list(r.mismatch_fields),
                "pass": r.passed,
            }
            for r in results
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-evidence", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_conformance_suite(args.frozen_evidence)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"STAGE3A2_DEVELOPMENT_CONFORMANCE={summary['status']}")
    print(f"FROZEN_EVIDENCE_PY_SHA256={summary['frozen_evidence_py_sha256']}")
    print(f"FIXTURE_COUNT={summary['fixture_count']}")
    print(f"CONFORMANCE_MISMATCHES={summary['mismatch_count']}")
    print("HELD_OUT_EXECUTION_AUTHORIZED=NO")
    print("SCIENTIFIC_HELDOUT_EXECUTION=0")
    print(f"RESULT_JSON={args.json.resolve()}")
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
