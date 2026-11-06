"""Segment and track a selected HS-AFM feature within a specified movie window."""
from __future__ import annotations
import numpy as np
from scipy.ndimage import label, gaussian_filter, center_of_mass, binary_closing, binary_opening
from .load_asd import load_stack

_ST = np.ones((3, 3), bool)


def _poly_terms(ny, nx, deg=3):
    Y, X = np.mgrid[0:ny, 0:nx]
    Xn, Yn = (X - nx / 2) / nx, (Y - ny / 2) / ny
    return np.stack([((Xn ** i) * (Yn ** j)).ravel()
                     for i in range(deg + 1) for j in range(deg + 1 - i)], 1)


def robust_flatten(z, A):
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


def _binary(zf, sig, k, interior):
    zs = gaussian_filter(zf, 1.0)
    return binary_opening(binary_closing((zs < -k * sig) & interior, _ST), _ST)


def measure(zf, sig, k, center, interior, px2nm):
    if center is None:
        return np.nan, np.nan, np.nan
    lab, n = label(_binary(zf, sig, k, interior))
    L = lab[int(round(center[0])), int(round(center[1]))]
    if L == 0:
        best, bd = None, 6
        for LL in range(1, n + 1):
            cy, cx = center_of_mass(lab == LL)
            d = np.hypot(cy - center[0], cx - center[1])
            if d < bd:
                bd, best = d, (lab == LL)
        if best is None:
            return 0.0, np.nan, np.nan
        m = best
    else:
        m = lab == L
    return m.sum() * px2nm ** 2, -np.median(zf[m]), -zf[m].min()


def run(path, anchor, anchor_frame, window, border=12, k_primary=3, maxjump=18):
    d = load_stack(path)
    arr, px2nm, dt = d["frames_nm"], d["px2nm"], d["dt_s"]
    ny, nx = arr.shape[1:]
    A = _poly_terms(ny, nx, 3)
    interior = np.zeros((ny, nx), bool)
    interior[border:-border, border:-border] = True

    zfs, sigs = {}, {}
    for f in window:
        zfs[f], sigs[f] = robust_flatten(arr[f], A)

    centre = {f: None for f in window}
    fwd = range(anchor_frame, window.stop)
    bwd = range(anchor_frame, window.start - 1, -1)
    for seq in (fwd, bwd):
        prev = anchor
        for f in seq:
            if f not in zfs:
                continue
            lab, n = label(_binary(zfs[f], sigs[f], k_primary, interior))
            best, ba, bc = None, 0, None
            for L in range(1, n + 1):
                m = lab == L
                ap = m.sum()
                if ap < 4 or ap > 3000:
                    continue
                cy, cx = center_of_mass(m)
                if np.hypot(cy - prev[0], cx - prev[1]) < maxjump and ap > ba:
                    ba, best, bc = ap, m, (cy, cx)
            if bc is not None:
                centre[f] = bc
                prev = bc

    rows = []
    for f in window:
        c = centre[f]
        a2 = measure(zfs[f], sigs[f], 2, c, interior, px2nm)[0]
        a3, dmed, dmax = measure(zfs[f], sigs[f], 3, c, interior, px2nm)
        a4 = measure(zfs[f], sigs[f], 4, c, interior, px2nm)[0]
        rows.append(dict(frame=f, t=round(f * dt, 2),
                         detected=bool(c is not None and a3 > 0 and not np.isnan(a3)),
                         area2=a2, area3=a3, area4=a4, depth_med=dmed, depth_max=dmax,
                         cx=(c[1] if c else np.nan), cy=(c[0] if c else np.nan)))
    return rows
