"""Deterministic development-only seed/ID utilities for Stage 3A.3.

This module intentionally exposes no held-out namespace API.  All public seed
functions are hard-wired to the approved ``dev`` construction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

import numpy as np

CONTRACT_SHA256: Final = "86ee65277b917ca513ffc1a5754748384240456172d883bff40c83d2804493d4"
GENERATOR_SPEC_SHA256: Final = "ae7c769c0668481433608914eb58f780de2ef1e163294093e789b618e43d9bb9"
CLARIFICATION_V1_1_SHA256: Final = "a51e48789c738fcefa24f8a476a99db085c823e107c066a023d81992549c1590"
CLARIFICATION_V1_2_SHA256: Final = "38700c1c5e9e39e5d40539e10793d72ca8765e117f78d615fe395e66f5d04a00"
CLARIFICATION_V1_3_SHA256: Final = "d3a952672d2ce1ec221b83fe777437fa3954270a25b316063f31a2b7ad1efbe6"
CLARIFICATION_V1_4_SHA256: Final = "4bf415bcbb08036144b56738a63a314b9560e08ab779c7751d1d51bbbf4024c3"

_RATE_TOKENS: Final = {
    0.0: b"0",
    0.10: b"0.10",
    0.25: b"0.25",
}


class GeneratorSeedError(ValueError):
    """Raised when a development seed/ID request violates the frozen A3 rules."""


@dataclass(frozen=True)
class DevelopmentSeedManifest:
    """Canonical development-only seed manifest and its content hash."""

    content: dict[str, str]
    canonical_bytes: bytes
    sha256: str


def _canonical_manifest_bytes(content: dict[str, str]) -> bytes:
    """Serialize manifest as canonical sorted compact UTF-8 JSON plus LF."""
    return (
        json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        + b"\n"
    )


def build_development_seed_manifest() -> DevelopmentSeedManifest:
    content = {
        "case_enumeration_schema": "STAGE3A3_CASE_ENUM_V1",
        "contract_sha256": CONTRACT_SHA256,
        "generator_clarification_sha256": CLARIFICATION_V1_1_SHA256,
        "generator_clarification_v1_2_sha256": CLARIFICATION_V1_2_SHA256,
        "generator_clarification_v1_3_sha256": CLARIFICATION_V1_3_SHA256,
        "generator_clarification_v1_4_sha256": CLARIFICATION_V1_4_SHA256,
        "generator_spec_sha256": GENERATOR_SPEC_SHA256,
        "namespace": "dev",
        "rng": "numpy.random.Generator(PCG64)",
        "schema": "STAGE3A3_DEV_SEED_MANIFEST_V1",
    }
    payload = _canonical_manifest_bytes(content)
    return DevelopmentSeedManifest(
        content=content,
        canonical_bytes=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def render_case_index(case_index: int) -> bytes:
    if not isinstance(case_index, int) or isinstance(case_index, bool) or case_index < 0:
        raise GeneratorSeedError("case_index must be a non-negative integer")
    return str(case_index).encode("ascii")


def development_case_seed(case_index: int) -> int:
    """Frozen development seed; no generic namespace parameter exists."""
    payload = CONTRACT_SHA256.encode("ascii") + b"dev" + render_case_index(case_index)
    return int(hashlib.sha256(payload).hexdigest()[:16], 16)


def base_case_id(seed_manifest_hash: str, global_case_index: int) -> str:
    if not isinstance(seed_manifest_hash, str) or len(seed_manifest_hash) != 64:
        raise GeneratorSeedError("seed_manifest_hash must be a 64-hex string")
    try:
        bytes.fromhex(seed_manifest_hash)
    except ValueError as exc:
        raise GeneratorSeedError("seed_manifest_hash must be hexadecimal") from exc
    payload = seed_manifest_hash.lower().encode("ascii") + b"case" + render_case_index(global_case_index)
    return hashlib.sha256(payload).hexdigest()[:16]


def case_seed_bytes(case_seed: int) -> bytes:
    if not isinstance(case_seed, int) or isinstance(case_seed, bool) or not 0 <= case_seed < 2**64:
        raise GeneratorSeedError("case_seed must be uint64")
    return int(case_seed).to_bytes(8, byteorder="big", signed=False)


def rate_token(rate: float) -> bytes:
    for key, token in _RATE_TOKENS.items():
        if float(rate) == key:
            return token
    raise GeneratorSeedError("rate must be exactly one of 0, 0.10, 0.25")


def purpose_rng(case_seed: int, purpose_tag: bytes, frame: int) -> np.random.Generator:
    if purpose_tag not in {
        b"signal-present",
        b"signal-absent",
        b"noise-z",
        b"f2-measured",
        b"f0b-N",
        b"f0b-S",
    }:
        raise GeneratorSeedError(f"unauthorized purpose tag: {purpose_tag!r}")
    if not isinstance(frame, int) or isinstance(frame, bool) or not 0 <= frame <= 63:
        raise GeneratorSeedError("frame must be an integer in 0..63")
    payload = (
        case_seed_bytes(case_seed)
        + b"\x00a3-purpose\x00"
        + purpose_tag
        + b"\x00"
        + f"{frame:02d}".encode("ascii")
    )
    seed64 = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)
    return np.random.Generator(np.random.PCG64(seed64))


def support_perturbation_rng(
    case_seed: int, fn_rate: float, fp_rate: float
) -> np.random.Generator:
    payload = (
        case_seed_bytes(case_seed)
        + b"support-perturb"
        + rate_token(fn_rate)
        + rate_token(fp_rate)
    )
    digest = hashlib.sha256(payload).digest()
    seed64 = int.from_bytes(digest[:8], "big", signed=False)
    return np.random.Generator(np.random.PCG64(seed64))


def variant_case_id(base_id: str, variant_descriptor: bytes) -> str:
    if not isinstance(base_id, str) or len(base_id) != 16:
        raise GeneratorSeedError("base_id must be 16 hex characters")
    try:
        base_bytes = bytes.fromhex(base_id)
    except ValueError as exc:
        raise GeneratorSeedError("base_id must be hexadecimal") from exc
    if not isinstance(variant_descriptor, bytes) or not variant_descriptor:
        raise GeneratorSeedError("variant_descriptor must be non-empty bytes")
    payload = base_bytes + b"\x00variant\x00" + variant_descriptor
    return hashlib.sha256(payload).hexdigest()[:16]


def clean_variant_descriptor() -> bytes:
    return b"clean"


def support_variant_descriptor(fn_rate: float, fp_rate: float, *, clean: bool = False) -> bytes:
    prefix = b"clean-support\x00fn=" if clean else b"support\x00fn="
    return prefix + rate_token(fn_rate) + b"\x00fp=" + rate_token(fp_rate)
