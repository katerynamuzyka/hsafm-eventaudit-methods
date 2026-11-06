"""EventAudit: per-event endpoint / onset evidence classes on top of an `Observation`.

Nothing here changes an event, a flag, a duration or a track. The audit produces three
separate, additive tables:

  events      one row per frozen event: onset and endpoint evidence class, the per-frame code
              string that justifies it, and interval bounds for the unobserved transition.
  candidates  candidate continuation edges (event i end -> event j start) across an
              unobservable gap. Edges are *hypotheses*; they are never applied.
  frames      per-frame observability (production status, secondary QC, shift, support).

Per-frame codes (look-ahead after an endpoint, look-behind before an onset):
  X  excluded by production frame QC (never observed)
  Q  production-usable but flagged by the secondary frame QC supplied by the caller
  U  footprint has insufficient source-valid (measured) support
  R  local registration consistency check failed around the footprint
  A  an accepted component overlaps the footprint and belongs to a DIFFERENT retained event
  C  an accepted component overlaps the footprint but belongs to no retained event
  S  no accepted overlap, but >= min_above_frac of measured footprint pixels exceed k*sigma
  N  source-valid, registration-consistent, no accepted overlap, below the S fraction
  E  movie boundary reached
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter, shift as nd_shift

AUDIT_VERSION = "eventaudit-0.1-proto"

CLASSES = ("source_valid_negative", "observability_limited", "registration_limited",
           "assignment_ambiguous", "candidate_reappearance", "unresolved", "boundary_censored")


@dataclass(frozen=True)
class AuditParams:
    min_measured_frac: float = 0.5     # below -> U
    min_above_frac: float = 0.05       # S threshold (fraction of measured footprint > k*sigma)
    n_confirm: int = 2                 # consecutive N frames that confirm absence (frozen gap+1)
    lookahead_frames: int = 12         # raw frames examined beyond an endpoint / before an onset
    reg_check: bool = True
    max_plausible_shift_px: float = 20.0   # |production shift| above this -> R (lattice alias guard)
    reg_roi_half_px: int = 24
    reg_search_px: int = 4             # keep < half the lattice period to avoid aliasing
    reg_tol_px: float = 1.5
    reg_min_gain: float = 0.10
    reg_exclude_dilation_px: int = 6   # exclude the feature and its tails from the check
    spatial_margin_px: int = 2         # footprint this close to the excluded border -> boundary

    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]


def _footprint(obs, f, comp):
    return obs.frames[f].labels == comp + 1


def _reg_check(obs, f_ref, g, fp, p):
    """Bounded local consistency between the registered frames f_ref and g around a footprint.

    Integer-offset search within +-reg_search_px on the x-gradient of the flattened frames,
    excluding the (dilated) footprint itself, restricted to pixels source-valid in both frames.
    Returns (ok, best_offset_px, gain). Generalised from audit_014_shared_z_neighbor_qc."""
    a, b = obs.frames[f_ref], obs.frames[g]
    if a.zf is None or b.zf is None:
        return False, np.nan, np.nan
    ny, nx = obs.shape
    cy, cx = np.argwhere(fp).mean(0)
    h = p.reg_roi_half_px
    y0, y1 = max(0, int(cy) - h), min(ny, int(cy) + h + 1)
    x0, x1 = max(0, int(cx) - h), min(nx, int(cx) + h + 1)
    ga = np.gradient(gaussian_filter(a.zf.astype(float), 1.0), axis=1)[y0:y1, x0:x1]
    gb_full = np.gradient(gaussian_filter(b.zf.astype(float), 1.0), axis=1)
    bg = (~binary_dilation(fp, iterations=p.reg_exclude_dilation_px) & a.valid & b.valid)[y0:y1, x0:x1]
    if bg.sum() < 50:
        return False, np.nan, np.nan
    r = p.reg_search_px
    scores = {}
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            gb = nd_shift(gb_full, (dy, dx), order=0, mode="nearest")[y0:y1, x0:x1]
            scores[(dy, dx)] = float(np.median(np.abs(ga - gb)[bg]))
    (dy, dx), best = min(scores.items(), key=lambda kv: (kv[1], abs(kv[0][0]) + abs(kv[0][1])))
    zero = scores[(0, 0)]
    gain = (zero - best) / max(zero, 1e-12)
    off = float(np.hypot(dy, dx))
    # Fail only if a non-zero offset clearly improves agreement (misregistration evidence).
    # Texture-free neighbourhoods give no gain anywhere: registration is then 'not assessable',
    # which is reported (gain ~ 0) but not treated as a failure.
    ok = not (off > p.reg_tol_px and gain >= p.reg_min_gain)
    return ok, off, gain


def _code(obs, f_ref, g, fp, self_event, frame_qc, p):
    """Evidence code for frame g, for footprint fp defined at frame f_ref."""
    n = len(obs.frames)
    if g < 0 or g >= n:
        return "E", {}
    st = obs.frames[g]
    if not st.good:
        return "X", {}
    if g in frame_qc:
        return "Q", {}
    meas = fp & st.valid
    mfrac = meas.sum() / max(fp.sum(), 1)
    info = dict(measured=float(mfrac))
    if mfrac < p.min_measured_frac:
        return "U", info
    if obs.cfg.get("coordinate_frame") == "unknown":
        return "R", info                      # external transform unknown: never 'direct'
    jump = float(np.hypot(st.shift[0] - obs.frames[f_ref].shift[0],
                          st.shift[1] - obs.frames[f_ref].shift[1]))
    info["shift_jump_px"] = jump
    if max(float(np.hypot(*st.shift)), jump) > p.max_plausible_shift_px:
        return "R", info                      # implausible global shift: bounded local check can alias
    if p.reg_check:
        ok, off, gain = _reg_check(obs, f_ref, g, fp, p)
        info.update(reg_offset_px=off, reg_gain=gain)
        if not ok:
            return "R", info
    lab = st.labels[meas]
    comps = np.unique(lab[lab > 0]) - 1
    info["overlap"] = float((lab > 0).mean())
    info["above_k"] = float(st.above_k[meas].mean())
    if comps.size:
        owners = [obs.comp_owner.get((g, int(c))) for c in comps]
        evs = [obs.event_of_track(t) if t is not None else None for t in owners]
        other = [e for e in evs if e is not None and e != self_event]
        if other:
            info["other_event"] = int(other[0])
            info["other_track"] = int(owners[evs.index(other[0])])
            return "A", info
        info["other_track"] = int(owners[0]) if owners[0] is not None else None
        return "C", info
    if info["above_k"] >= p.min_above_frac:
        return "S", info
    return "N", info


def _classify(codes, n_confirm):
    """Map a code string to (class, index_of_decisive_code)."""
    gap = False
    run = 0
    for i, c in enumerate(codes):
        if c == "E":
            return "boundary_censored", i
        if c in "XQU":
            gap, run = True, 0
            continue
        if c == "R":
            return "registration_limited", i
        if c in "AC":
            return ("candidate_reappearance" if gap else "assignment_ambiguous"), i
        if c == "S":
            return "unresolved", i
        if c == "N":
            run += 1
            if run >= n_confirm:
                return ("observability_limited" if gap else "source_valid_negative"), i
    return "unresolved", None


def _audit_side(obs, ev_idx, track, side, frame_qc, p):
    pts = sorted(track["points"])
    f_ref, comp = (pts[-1] if side == "end" else pts[0])
    fp = _footprint(obs, f_ref, comp)
    step = 1 if side == "end" else -1
    boundary_frame = obs.good[-1] if side == "end" else obs.good[0]
    ny, nx = obs.shape
    b0 = obs.cfg.get("border_px", 12)          # frozen detector's excluded border
    ys, xs = np.nonzero(fp)
    edge = int(min(ys.min() - b0, ny - 1 - b0 - ys.max(), xs.min() - b0, nx - 1 - b0 - xs.max()))
    row = {f"{side}_frame": f_ref}
    if f_ref == boundary_frame:
        row.update({f"{side}_class": "boundary_censored", f"{side}_codes": "",
                    f"{side}_boundary": "temporal"})
        return row, None
    if edge < p.spatial_margin_px:
        row[f"{side}_boundary"] = "spatial"
    codes, infos = [], []
    g = f_ref
    for _ in range(p.lookahead_frames):
        g += step
        c, info = _code(obs, f_ref, g, fp, ev_idx, frame_qc, p)
        codes.append(c); infos.append((g, info))
        cls, k = _classify("".join(codes), p.n_confirm)
        if k is not None or c == "E":
            break
    cls, k = _classify("".join(codes), p.n_confirm)
    if row.get(f"{side}_boundary") == "spatial" and cls in ("source_valid_negative", "observability_limited", "unresolved"):
        cls = "boundary_censored"
    row[f"{side}_edge_px"] = edge
    row.update({f"{side}_class": cls, f"{side}_codes": "".join(codes),
                f"{side}_n_unobserved": sum(c in "XQUR" for c in codes[: (k + 1) if k is not None else None])})
    first_obs = next((inf for (gg, inf), c in zip(infos, codes) if c in "NSAC"), None)
    if first_obs:
        row[f"{side}_first_obs_measured_frac"] = round(first_obs.get("measured", np.nan), 3)
        row[f"{side}_first_obs_above_k_frac"] = round(first_obs.get("above_k", np.nan), 3)
        row[f"{side}_first_obs_overlap_frac"] = round(first_obs.get("overlap", np.nan), 3)
    # interval bounds for the unobserved transition (end side: last seen .. first confirmed absent)
    if cls in ("source_valid_negative", "observability_limited") and k is not None:
        first_absent = infos[k - p.n_confirm + 1][0]
        lo, hi = sorted((f_ref, first_absent))
        row[f"{side}_interval_frames"] = f"[{lo},{hi}]"
        row[f"{side}_interval_s"] = f"[{lo * obs.dt_s:.3f},{hi * obs.dt_s:.3f}]"
    cand = None
    if cls in ("assignment_ambiguous", "candidate_reappearance") and k is not None:
        inf = infos[k][1]
        row[f"{side}_other_event"] = inf.get("other_event")
        row[f"{side}_other_track"] = inf.get("other_track")
        if cls == "candidate_reappearance":
            cand = dict(frame=infos[k][0], other_event=inf.get("other_event"),
                        other_track=inf.get("other_track"), gap_codes="".join(codes[:k]),
                        overlap_frac=inf.get("overlap"))
    return row, cand


def row_artifact_frame_qc(frames_raw, n_mad=5.0):
    """Secondary frame QC ported from asd011_qc_badframes_reference_v1 (row step, row banding,
    robust range; each flagged above median + n_mad * MAD). Returns a set of frame indices."""
    z = np.asarray(frames_raw, float)
    rel = z - np.median(z, axis=(1, 2), keepdims=True)
    rm = np.median(rel, axis=2)
    step = np.abs(np.diff(rm, axis=1)).max(1)
    band = rm.std(1)
    rng = np.percentile(rel, 99, axis=(1, 2)) - np.percentile(rel, 1, axis=(1, 2))

    def flag(x):
        med = np.median(x); mad = 1.4826 * np.median(np.abs(x - med))
        return x > med + n_mad * mad
    return set(np.nonzero(flag(step) | flag(band) | flag(rng))[0].tolist())


def audit_events(obs, *, frame_qc=None, params: AuditParams = AuditParams()):
    """Audit every frozen event. Returns dict(events=[...], candidates=[...], frames=[...])."""
    frame_qc = set(frame_qc or ())
    rows, cands = [], []
    for tr in obs.tracks:
        ei = tr["event_index"]
        if ei is None:
            continue
        e = obs.events[ei]
        frames_det = sorted({f for f, _ in tr["points"]})
        row = dict(event_index=ei, track_id=tr["track_id"], f0=frames_det[0], f1=frames_det[-1],
                   n_det_frames=len(frames_det), fully_observed_frozen=bool(e["fully_observed"]))
        for side in ("start", "end"):
            r, c = _audit_side(obs, ei, tr, side, frame_qc, params)
            row.update(r)
            if c:
                c.update(side=side, event=ei)
                cands.append(c)
        # internal gaps: frames between first and last detection without a detection of this event
        gaps = []
        pts = dict(sorted(tr["points"]))
        prev = frames_det[0]
        for g in range(frames_det[0] + 1, frames_det[-1]):
            if g in pts:
                prev = g
                continue
            c, _ = _code(obs, prev, g, _footprint(obs, prev, pts[prev]), ei, frame_qc, params)
            gaps.append(f"{g}:{c}")
        row["internal_gap_codes"] = " ".join(gaps)
        row["audit_version"] = AUDIT_VERSION
        row["params_digest"] = params.digest()
        rows.append(row)
    rows.sort(key=lambda r: r["event_index"])
    # mutual candidate edges: end of i -> onset of j and onset of j -> end of i
    ends = {(c["event"], c["other_event"]) for c in cands if c["side"] == "end"}
    starts = {(c["other_event"], c["event"]) for c in cands if c["side"] == "start"}
    edges = []
    for (i, j) in sorted(ends | starts, key=lambda t: (t[0] if t[0] is not None else -1, t[1] if t[1] is not None else -1)):
        if i is None or j is None:
            continue
        edges.append(dict(from_event=i, to_event=j, mutual=(i, j) in ends and (i, j) in starts,
                          applied=False))
    fr = [dict(frame=i, production="good" if s.good else "excluded", secondary_qc=int(i in frame_qc),
               shift_dy=round(s.shift[0], 3), shift_dx=round(s.shift[1], 3),
               source_valid_frac=round(float(s.valid.mean()), 4))
          for i, s in sorted(obs.frames.items())]
    return dict(events=rows, candidates=edges, candidate_details=cands, frames=fr)
