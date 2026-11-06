"""Read-only observation of the FROZEN population detector.

`observe_frozen_detector` calls the unmodified `feature_events.detect_events_array` and records,
without altering any computation, the per-frame state that the released function discards:
registration shifts, source-valid pixel support, flattened frames, noise scale, supra-threshold
maps, accepted-component masks and track membership.

Mechanism (read-only instrumentation of the detector):
  * `feature_events.nd_shift` is wrapped for the duration of the call to capture the shift
    vectors computed by `drift_correct` (the wrapper returns the original result unchanged);
  * a `sys.settrace` line observer, attached only to the code object of
    `detect_events_array`, reads local variables at three marker lines. Marker lines are located
    from the function source; if any marker is missing the observer refuses to run
    (no guessed instrumentation).

The returned `events` list is the object returned by the frozen function itself.
"""
from __future__ import annotations

import hashlib
import inspect
import sys
from dataclasses import dataclass, field

import numpy as np

from .. import feature_events as fe

MARKERS = {
    "blobs_done": "det[f] = blobs",
    "end_tracking": "first_g, last_g = good[0], good[-1]",
}


def source_valid_mask(shape, shift):
    """Pixels of a frame registered with ``scipy.ndimage.shift(z, shift, order=1)`` whose
    interpolation source coordinates (i - shift) lie inside the measured raw frame.
    Everything else was filled by ``mode='nearest'`` edge extrapolation."""
    ny, nx = shape
    sy = np.arange(ny, dtype=float) - float(shift[0])
    sx = np.arange(nx, dtype=float) - float(shift[1])
    return ((sy >= 0) & (sy <= ny - 1))[:, None] & ((sx >= 0) & (sx <= nx - 1))[None, :]


@dataclass
class FrameState:
    index: int
    good: bool
    shift: tuple = (0.0, 0.0)
    valid: np.ndarray | None = None        # source-valid support (bool)
    zf: np.ndarray | None = None           # flattened registered frame (float32), good frames only
    sigma: float | None = None
    above_k: np.ndarray | None = None      # sign*smooth(zf) > k*sigma, interior only, pre-morphology
    labels: np.ndarray | None = None       # accepted components relabelled 1..m in frozen blob order


@dataclass
class Observation:
    shape: tuple
    px2nm: float
    dt_s: float
    cfg: dict
    good: list
    bad: list
    frames: dict                            # index -> FrameState
    events: list                            # exactly what the frozen function returned
    info: dict
    tracks: list = field(default_factory=list)   # dicts: track_id, points[(f, comp)], event_index
    comp_owner: dict = field(default_factory=dict)  # (f, comp) -> track_id
    input_sha256: str = ""
    source: str = "frozen_rc2_observer"

    def event_of_track(self, tid):
        return self.tracks[tid]["event_index"]


class _Observer:
    def __init__(self):
        self.code = fe.detect_events_array.__code__
        src, start = inspect.getsourcelines(fe.detect_events_array)
        self.lines = {}
        for off, line in enumerate(src):
            for key, marker in MARKERS.items():
                if line.strip().startswith(marker):
                    self.lines[key] = start + off
        if set(self.lines) != set(MARKERS):
            raise RuntimeError("Frozen detector marker lines not found; refusing to instrument.")
        self.per_frame = {}
        self.blob_id = {}
        self.end = None

    def global_trace(self, frame, event, arg):
        if event == "call" and frame.f_code is self.code:
            return self.local_trace
        return None

    def local_trace(self, frame, event, arg):
        if event != "line":
            return self.local_trace
        ln, d = frame.f_lineno, frame.f_locals
        if ln == self.lines["blobs_done"]:
            f = int(d["f"])
            lab, n, blobs = d["lab"], int(d["n"]), d["blobs"]
            sizes = np.bincount(lab.ravel(), minlength=n + 1)
            keep = [L for L in range(1, n + 1) if d["min_px"] <= sizes[L] <= d["max_px"]]
            if len(keep) != len(blobs):
                raise RuntimeError(f"accepted-label/blob mismatch at frame {f}")
            relab = np.zeros(n + 1, np.int32)
            relab[keep] = np.arange(1, len(keep) + 1)
            for i, b in enumerate(blobs):
                self.blob_id[id(b)] = (f, i)
            k, sig = float(d["k"]), float(d["sig"])
            self.per_frame[f] = dict(
                zf=np.asarray(d["zf"], np.float32), sigma=sig,
                above_k=(d["sigfield"] > k * sig) & d["interior"],
                labels=relab[lab])
        elif ln == self.lines["end_tracking"]:
            self.end = dict(tracks=d["tracks"], good=list(d["good"]), bad=sorted(d["bad"]),
                            min_frames=int(d["min_frames"]))
        return self.local_trace


def observe_frozen_detector(frames, px2nm, dt_s, *, bad_frames=None, meta=None, **cfg):
    """Run the frozen detector once, unmodified, and return an `Observation`."""
    frames = np.asarray(frames, float)
    sha = hashlib.sha256(np.ascontiguousarray(frames).tobytes()).hexdigest()
    shifts = {0: (0.0, 0.0)}
    orig_shift = fe.nd_shift
    calls = [0]

    def observed_shift(inp, shift, *a, **kw):
        calls[0] += 1
        shifts[calls[0]] = (float(shift[0]), float(shift[1]))
        return orig_shift(inp, shift, *a, **kw)

    obs = _Observer()
    prev_trace = sys.gettrace()
    fe.nd_shift = observed_shift
    sys.settrace(obs.global_trace)
    try:
        events, info = fe.detect_events_array(frames, px2nm, dt_s, bad_frames=bad_frames,
                                              meta=meta, **cfg)
    finally:
        sys.settrace(prev_trace)
        fe.nd_shift = orig_shift
    if obs.end is None:
        return Observation(frames.shape[1:], px2nm, dt_s, dict(cfg), [], [], {}, events, info,
                           input_sha256=sha)
    if hashlib.sha256(np.ascontiguousarray(frames).tobytes()).hexdigest() != sha:
        raise RuntimeError("input array was modified during observation")
    do_drift = cfg.get("do_drift", True)
    n = frames.shape[0]
    if do_drift and calls[0] != n - 1:
        raise RuntimeError(f"expected {n - 1} registration shifts, captured {calls[0]}")
    good, bad = obs.end["good"], obs.end["bad"]
    states = {}
    for i in range(n):
        sh = shifts.get(i, (0.0, 0.0)) if do_drift else (0.0, 0.0)
        st = FrameState(index=i, good=i in obs.per_frame, shift=sh,
                        valid=source_valid_mask(frames.shape[1:], sh))
        if i in obs.per_frame:
            p = obs.per_frame[i]
            st.zf, st.sigma, st.above_k, st.labels = p["zf"], p["sigma"], p["above_k"], p["labels"]
        states[i] = st
    tracks, owner, ev_i = [], {}, 0
    for tid, tr in enumerate(obs.end["tracks"]):
        pts = [obs.blob_id[id(b)] for _, b in tr["pts"]]
        retained = len({f for f, _ in pts}) >= obs.end["min_frames"]
        tracks.append(dict(track_id=tid, points=pts, event_index=ev_i if retained else None))
        ev_i += int(retained)
        for p in pts:
            owner[p] = tid
    if ev_i != len(events):
        raise RuntimeError("track->event reconstruction disagrees with frozen output")
    return Observation(frames.shape[1:], float(px2nm), float(dt_s), dict(cfg), good, bad, states,
                       events, info, tracks, owner, sha)
