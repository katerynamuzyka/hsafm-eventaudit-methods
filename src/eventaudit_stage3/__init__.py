"""EventAudit Stage 3 implementation package.

Stage 3A.1 contains development-only boundary-record schemas and the frozen-rule
B6 record-level decision core. Full F0-F8 generation, held-out execution, and
Stage-3B scoring remain unauthorized here.
"""

STAGE3_IMPLEMENTATION_PHASE = "Stage 3A.1"
HELD_OUT_EXECUTION_AUTHORIZED = False

__all__ = ["STAGE3_IMPLEMENTATION_PHASE", "HELD_OUT_EXECUTION_AUTHORIZED"]
