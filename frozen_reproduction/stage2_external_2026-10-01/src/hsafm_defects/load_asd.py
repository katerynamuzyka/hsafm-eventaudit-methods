"""Load calibrated Kodec/RIBM .asd HS-AFM stacks using AFMReader.

Return height frames and acquisition metadata for downstream analysis.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter
from AFMReader.asd import load_asd

# HS-AFM stacks trigger many small np.linalg.lstsq calls (robust flattening); under the
# container's BLAS these oversubscribe threads and intermittently deadlock. Pin to a single
# BLAS thread process-wide (numerically identical, just deadlock-free and fast).
try:
    from threadpoolctl import threadpool_limits
    _TPL = threadpool_limits(limits=1)   # kept alive at module scope to hold the limit
except Exception:  # threadpoolctl not installed -> fall back silently
    _TPL = None


def load_stack(path: str, channel: str = "TP") -> dict:
    frames, px2nm, meta = load_asd(file_path=path, channel=channel)
    frames_nm = np.asarray(frames, dtype=float)
    dt_s = float(meta["frame_time"]) / 1000.0
    n = frames_nm.shape[0]
    return {
        "frames_nm": frames_nm,
        "px2nm": float(px2nm),
        "dt_s": dt_s,
        "t_s": np.arange(n) * dt_s,
        "meta": meta,
    }


def flatten_plane(z: np.ndarray) -> np.ndarray:
    ny, nx = z.shape
    Y, X = np.mgrid[0:ny, 0:nx]
    A = np.c_[X.ravel(), Y.ravel(), np.ones(z.size)]
    coef, *_ = np.linalg.lstsq(A, z.ravel(), rcond=None)
    return z - (coef[0] * X + coef[1] * Y + coef[2])


def detect_bad_frames(frames_nm: np.ndarray,
                      dead_row_frac: float = 0.15,
                      zrange_lo: float = 0.30,
                      zrange_hi: float = 4.0) -> list[int]:
    n = frames_nm.shape[0]
    flat = np.stack([flatten_plane(f) for f in frames_nm])
    dead = np.array([(frames_nm[i].std(axis=1) < 1e-6).mean() for i in range(n)])
    zr = np.array([np.percentile(flat[i], 99) - np.percentile(flat[i], 1) for i in range(n)])
    med = np.median(zr)
    bad = {i for i in range(n) if dead[i] > dead_row_frac}
    bad |= {i for i in range(n) if zr[i] > zrange_hi * med or zr[i] < zrange_lo * med}
    return sorted(bad)
