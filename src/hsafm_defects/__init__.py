"""hsafm_defects — reproducible HS-AFM defect/feature-dynamics analysis.

Public API:
    load_stack, detect_bad_frames, flatten_plane          (load_asd)
    robust_flatten, detect_events, detect_events_array, survival_tau, drift_correct  (feature_events)
    run (case-study single-defect tracking)               (segment_track)
"""
from .load_asd import load_stack, detect_bad_frames, flatten_plane
from .feature_events import (robust_flatten, detect_events, detect_events_array,
                             survival_tau, drift_correct, _poly_terms)
from .segment_track import run

__version__ = "0.1.0"
__all__ = ["load_stack", "detect_bad_frames", "flatten_plane", "robust_flatten",
           "detect_events", "detect_events_array", "survival_tau", "drift_correct",
           "_poly_terms", "run", "__version__"]
