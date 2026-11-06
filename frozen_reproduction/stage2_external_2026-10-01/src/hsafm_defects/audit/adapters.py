"""Tracker-agnostic adapter: build an `Observation` from an external detection/track table
(e.g. exported from NanoLocz or BioAFMviewer A3) plus the original movie.

Minimal schema (one row per detection per frame; units stated explicitly):
    frame        int, 0-based index into the original movie
    y_px, x_px   float, centroid in the coordinate frame declared by `coordinate_frame`
    track_id     int or None (None = detection not assigned to any track)
Optional:
    area_px      float, footprint area -> disk footprint of equal area (else `default_radius_px`)
    mask         2-D bool array, exact footprint (overrides the disk)

Movie-level metadata: px2nm, dt_s, excluded_frames, and per-frame `shifts` (dy, dx) if the
external tool registered the movie with a pure translation. Unknown transforms -> declare
coordinate_frame="unknown": every look-ahead frame is then coded R (registration-limited).

IMPORTANT semantic difference: for external tracks the absence evidence (codes N/S) comes from
the audit's own evidence model (frozen robust_flatten + k*sigma threshold), NOT from the external
detector. Assignment codes (A/C) require ALL detections, not only tracked ones.
"""
from __future__ import annotations

import hashlib

import numpy as np
from scipy.ndimage import gaussian_filter, shift as nd_shift

from .. import feature_events as fe
from .observe import FrameState, Observation, source_valid_mask


def observation_from_tables(frames_raw, px2nm, dt_s, detections, *, excluded_frames=(),
                            shifts=None, coordinate_frame="raw", sign=-1, k=3.0, border_px=12,
                            default_radius_px=4.0, min_frames=2, source="external_table"):
    if coordinate_frame not in ("raw", "registered", "unknown"):
        raise ValueError("coordinate_frame must be 'raw', 'registered' or 'unknown'")
    if coordinate_frame == "registered" and shifts is None:
        raise ValueError("registered coordinates require the per-frame shifts used")
    z = np.asarray(frames_raw, float)
    n, ny, nx = z.shape
    excluded = set(int(f) for f in excluded_frames)
    good = [f for f in range(n) if f not in excluded]
    A = fe._poly_terms(ny, nx, 3)
    interior = np.zeros((ny, nx), bool)
    interior[border_px:-border_px, border_px:-border_px] = True
    Y, X = np.mgrid[0:ny, 0:nx]
    by_frame = {}
    for d in detections:
        by_frame.setdefault(int(d["frame"]), []).append(d)
    states, owner, track_pts = {}, {}, {}
    for f in range(n):
        sh = tuple(shifts[f]) if coordinate_frame == "registered" else (0.0, 0.0)
        st = FrameState(index=f, good=f in good, shift=sh, valid=source_valid_mask((ny, nx), sh))
        if st.good:
            reg = nd_shift(z[f], sh, order=1, mode="nearest") if any(sh) else z[f]
            zf, sig = fe.robust_flatten(reg, A)
            st.zf, st.sigma = zf.astype(np.float32), float(sig)
            st.above_k = (sign * gaussian_filter(zf, 1.0) > k * sig) & interior
            lab = np.zeros((ny, nx), np.int32)
            for i, d in enumerate(by_frame.get(f, [])):
                if d.get("mask") is not None:
                    m = np.asarray(d["mask"], bool)
                else:
                    r = np.sqrt(d["area_px"] / np.pi) if d.get("area_px") else default_radius_px
                    m = (Y - d["y_px"]) ** 2 + (X - d["x_px"]) ** 2 <= r * r
                lab[m] = i + 1
                if d.get("track_id") is not None:
                    owner[(f, i)] = int(d["track_id"])
                    track_pts.setdefault(int(d["track_id"]), []).append((f, i))
            st.labels = lab
        states[f] = st
    tracks, events, remap = [], [], {}
    for tid in sorted(track_pts):
        pts = sorted(track_pts[tid])
        fs = sorted({f for f, _ in pts})
        keep = len(fs) >= min_frames
        new_id = len(tracks)
        remap[tid] = new_id
        tracks.append(dict(track_id=new_id, external_track_id=tid, points=pts,
                           event_index=len(events) if keep else None))
        if keep:
            events.append(dict(t0=round(fs[0] * dt_s, 3), t1=round(fs[-1] * dt_s, 3),
                               lifetime_s=round((fs[-1] - fs[0]) * dt_s, 3), n_frames=len(fs),
                               fully_observed=bool(fs[0] > good[0] and fs[-1] < good[-1])))
    owner = {key: remap[t] for key, t in owner.items()}
    obs = Observation((ny, nx), float(px2nm), float(dt_s),
                      dict(sign=sign, k=k, border_px=border_px, coordinate_frame=coordinate_frame),
                      good, sorted(excluded), states, events, dict(source=source), tracks, owner,
                      hashlib.sha256(np.ascontiguousarray(z).tobytes()).hexdigest(), source)
    return obs
