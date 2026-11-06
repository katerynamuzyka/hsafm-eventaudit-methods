"""
Generalized dynamic-feature event detector for HS-AFM stacks.

Same population-mode analysis used across the study (robust flatten -> k-sigma detection ->
morphological clean -> frame-to-frame linking into space-time events -> per-event
area/amplitude/volume/lifetime -> single-exponential survival fit), refactored so the feature
polarity is a parameter:

    sign = -1  ->  depressions / voids
    sign = +1  ->  protrusions / transient molecular features (GltPh membrane, SbcCD/DNA)

I/O is split from computation: ``detect_events`` reads an .asd and calls ``detect_events_array``,
which operates on a plain (N, Ny, Nx) array so it is unit-testable on synthetic stacks.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import (label, gaussian_filter, center_of_mass,
                           binary_closing, binary_opening, shift as nd_shift)
from skimage.registration import phase_cross_correlation
from .load_asd import load_stack, detect_bad_frames

_ST = np.ones((3, 3), bool)


def _poly_terms(ny, nx, deg=3):
    Y, X = np.mgrid[0:ny, 0:nx]
    Xn, Yn = (X - nx / 2) / nx, (Y - ny / 2) / ny
    return np.stack([((Xn ** i) * (Yn ** j)).ravel()
                     for i in range(deg + 1) for j in range(deg + 1 - i)], 1)


def robust_flatten(z, A):
    """Degree-3 polynomial background subtraction with iterative feature masking.
    Returns (flattened_height_centred_on_membrane, robust_membrane_sigma)."""
    mask = np.ones(z.shape, bool)
    for _ in range(4):
        c, *_ = np.linalg.lstsq(A[mask.ravel()], z.ravel()[mask.ravel()], rcond=None)
        r = z - (A @ c).reshape(z.shape)
        mad = np.median(np.abs(r[mask] - np.median(r[mask]))) * 1.4826
        md = np.median(r[mask])
        mask = (r > md - 2.5 * mad) & (r < md + 3 * mad)
    c, *_ = np.linalg.lstsq(A[mask.ravel()], z.ravel()[mask.ravel()], rcond=None)
    zf = z - (A @ c).reshape(z.shape)
    m = np.median(zf[mask])
    sig = np.median(np.abs(zf[mask] - m)) * 1.4826
    return zf - m, sig


def drift_correct(frames, ref_win=5):
    """Register each frame to a rolling-mean reference by subpixel phase cross-correlation."""
    out = np.empty_like(frames)
    out[0] = frames[0]
    for i in range(1, len(frames)):
        ref = frames[max(0, i - ref_win):i].mean(0)
        sh, _, _ = phase_cross_correlation(ref, frames[i], upsample_factor=10, normalization=None)
        out[i] = nd_shift(frames[i], sh, order=1, mode="nearest")
    return out


def detect_events_array(frames, px2nm, dt_s, sign=-1, k=3.0, min_area_nm2=3.7,
                        maxjump_nm=11.0, border_px=12, min_frames=2, gap=1,
                        do_drift=True, smooth_px=1.0, max_area_nm2=None,
                        bad_frames=None, meta=None):
    """Detect and link dynamic features of a given polarity into space-time events.

    Parameters operate on a plain float array ``frames`` of shape (N, Ny, Nx) in nm.
    Returns (events_list, info_dict). Each event dict has t0, t1, lifetime_s, n_frames,
    peak_area_nm2, mean_area_nm2, peak_amp_nm, volume_nm3, fully_observed.
    """
    frames = np.asarray(frames, float)
    ny, nx = frames.shape[1:]
    bad = set(bad_frames) if bad_frames is not None else set(detect_bad_frames(frames))
    good = [i for i in range(frames.shape[0]) if i not in bad]
    if len(good) < min_frames:
        return [], dict(px2nm=px2nm, dt_s=dt_s, n_frames=frames.shape[0], n_good=len(good))
    A = _poly_terms(ny, nx, 3)
    if do_drift:
        frames = drift_correct(frames)

    interior = np.zeros((ny, nx), bool)
    interior[border_px:-border_px, border_px:-border_px] = True
    min_px = max(4, int(round(min_area_nm2 / px2nm ** 2)))
    max_px = int(round(max_area_nm2 / px2nm ** 2)) if max_area_nm2 else int(0.25 * ny * nx)
    maxjump = maxjump_nm / px2nm

    det = {}
    for f in good:
        zf, sig = robust_flatten(frames[f], A)
        sigfield = sign * gaussian_filter(zf, smooth_px)
        binm = binary_opening(binary_closing((sigfield > k * sig) & interior, _ST), _ST)
        lab, n = label(binm)
        blobs = []
        for L in range(1, n + 1):
            m = lab == L
            ap = int(m.sum())
            if ap < min_px or ap > max_px:
                continue
            cy, cx = center_of_mass(m)
            amp = float((sign * zf)[m].max())
            vol = float(np.clip(sign * zf, 0, None)[m].sum() * px2nm ** 2)
            blobs.append(dict(cy=cy, cx=cx, area_px=ap, amp=amp, vol=vol))
        det[f] = blobs

    tracks, active = [], []
    for f in good:
        for tr in active:
            tr["matched"] = False
        for b in det[f]:
            best, bd = None, maxjump
            for tr in active:
                dd = np.hypot(b["cy"] - tr["last_c"][0], b["cx"] - tr["last_c"][1])
                if dd < bd and not tr.get("matched", False):
                    bd, best = dd, tr
            if best is None:
                tr = dict(pts=[(f, b)], last_c=(b["cy"], b["cx"]), missed=0, matched=True)
                tracks.append(tr); active.append(tr)
            else:
                best["pts"].append((f, b)); best["last_c"] = (b["cy"], b["cx"])
                best["missed"] = 0; best["matched"] = True
        still = []
        for tr in active:
            if not tr["matched"]:
                tr["missed"] += 1
            if tr["missed"] <= gap:
                still.append(tr)
        active = still

    first_g, last_g = good[0], good[-1]
    events = []
    for tr in tracks:
        fs = [p[0] for p in tr["pts"]]
        if len(set(fs)) < min_frames:
            continue
        f0, f1 = min(fs), max(fs)
        blobs = [p[1] for p in tr["pts"]]
        areas = np.array([b["area_px"] for b in blobs]) * px2nm ** 2
        amps = np.array([b["amp"] for b in blobs])
        vols = np.array([b["vol"] for b in blobs])
        events.append(dict(
            t0=round(f0 * dt_s, 3), t1=round(f1 * dt_s, 3),
            lifetime_s=round((f1 - f0) * dt_s, 3), n_frames=len(set(fs)),
            peak_area_nm2=float(areas.max()), mean_area_nm2=float(areas.mean()),
            peak_amp_nm=float(amps.max()), volume_nm3=float(vols.max()),
            fully_observed=bool((f0 > first_g) and (f1 < last_g))))
    info = dict(px2nm=px2nm, dt_s=dt_s, n_frames=frames.shape[0], n_good=len(good),
                field_nm=float(nx * px2nm), min_px=min_px, sign=sign, k=k)
    if meta is not None:
        info["comment"] = str(meta.get("comment_without_null", "")).replace("\r", " ")
        info["field_nm"] = float(meta.get("x_nm", nx * px2nm))
    return events, info


def detect_events(path, channel="TP", verbose=True, **kwargs):
    """Load an .asd stack and run the population detector (thin I/O wrapper)."""
    d = load_stack(path, channel=channel)
    events, info = detect_events_array(d["frames_nm"], d["px2nm"], d["dt_s"],
                                       meta=d["meta"], **kwargs)
    if verbose:
        print(f"[{path}] {len(events)} events "
              f"({sum(e['fully_observed'] for e in events)} fully observed) | "
              f"{info['n_good']}/{info['n_frames']} good frames | "
              f"{info['px2nm']:.3f} nm/px | {info['dt_s']:.3f} s/frame")
    return events, info


def survival_tau(events, dt_s=None):
    """Single-exponential fit to the lifetime survival function of fully-observed cycles.
    Returns dict(k, tau, r2, n)."""
    life = np.array([e["lifetime_s"] for e in events if e["fully_observed"]])
    life = life[life > 0]
    n = len(life)
    if n < 5:
        return dict(k=np.nan, tau=np.nan, r2=np.nan, n=n)
    ts = np.sort(life)
    surv = 1.0 - (np.arange(1, n + 1) - 0.5) / n
    m = surv > 0.02
    x, y = ts[m], np.log(surv[m])
    coef = np.polyfit(x, y, 1)
    k = -coef[0]
    yhat = np.polyval(coef, x)
    ss_res = np.sum((y - yhat) ** 2); ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return dict(k=float(k), tau=float(1.0 / k) if k > 0 else np.nan, r2=float(r2), n=n)
