#!/usr/bin/env python3
"""EventAudit external validation Stage-2 observer runner.

Public distribution copy: documentation-only source annotations have been standardized;
the source hashes below identify this distributed copy, not the archived original bytes.

Stage-2 is a separately versioned external-observer validation using current-upstream
GltPh and SbcCD raw ASD inputs. Historical byte identity is NOT established.

Preflight performs hashes/schema/static checks only. It does not open ASD data through
AFMReader, does not call the detector, does not call the EventAudit observer/evidence layer,
and does not call survival_tau.

Authorized execution topology (success path):
  * canonical load_stack: 2 calls (GltPh main, SbcCD main)
  * EventAudit observe_frozen_detector: 2 calls
  * canonical detect_events_array: 2 calls total, one internal to each observer call
  * frozen Stage-1B compatibility comparator: 2 calls
  * EventAudit audit_events: 2 calls
  * external-table adapter observation_from_tables: 0 calls
  * 11-nm controls: 0 detector calls (already frozen upstream in Stage-1B)
  * survival_tau: 0 calls

No threshold tuning or alternative detector configuration exists in this runner.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import threadpoolctl
from threadpoolctl import threadpool_limits

from stage1b_compatibility_contract import compare_event_lists_stage1b

STAGE2_VERSION = "EventAudit-external-observer-validation-stage2-v1-2026-10-01"
ACQUISITION_STATUS = "current upstream acquisition; historical byte identity NOT established"
ORIGINAL_STAGE1_VERDICT = "FAILED under the preregistered exact IEEE-754 event-list identity criterion"
UPSTREAM_STAGE1B_VERDICT = "PASS under the separately frozen post-failure diagnostic compatibility criterion"
APPROVAL_TOKEN = "I_APPROVE_EVENTAUDIT_EXTERNAL_STAGE2_OBSERVER_VALIDATION_RUN"

MAIN_CONFIG = {"sign": +1, "k": 3.0, "min_area_nm2": 12.0, "maxjump_nm": 14.0}
EXPECTED_COUNTS = {"gltph": 52, "sbccd": 674}
AUDIT_PARAMS = {
    "min_measured_frac": 0.5,
    "min_above_frac": 0.05,
    "n_confirm": 2,
    "lookahead_frames": 12,
    "reg_check": True,
    "max_plausible_shift_px": 20.0,
    "reg_roi_half_px": 24,
    "reg_search_px": 4,
    "reg_tol_px": 1.5,
    "reg_min_gain": 0.10,
    "reg_exclude_dilation_px": 6,
    "spatial_margin_px": 2,
}
AUDIT_PARAMS_DIGEST = "047a5cf360574c5e"
SECONDARY_FRAME_QC_POLICY = "empty_set_no_additional_external_secondary_qc"

INPUTS = {
    "gltph_asd": {"sha256": "7fd78cda50dc4c8cd091d4a9ac231af7564004aec6d4b18b19f94adee4ae2e88", "bytes": 13322797},
    "sbccd_asd": {"sha256": "46e192a8bc85b60578dca4eb2c26e6685e1158f9c112316660d389527a6dffa0", "bytes": 31532819},
    "canonical_results_json": {"sha256": "cdf7d9844b6132f1b17030be3900853d38b4810152bebb3b1b934aed96fdadd4", "bytes": 269341},
}

STAGE1B_RESULTS = {
    "CONTROL_11NM_REGENERATED.json": "ad8b6713a83ff614e1f297a3e44aa3cbe77d5dd0a18178d44cf03446674ec853",
    "GLTPH_STAGE1B_COMPATIBILITY.json": "287d228e214cecd2d1766e03966c76119c81a2686e7b8af94a875c8cdc34971d",
    "NUMERIC_PROVENANCE.json": "1aee4be6626e83e830fcd22ed2a2836bd20b4aa33d6f1d86494e8727dd59df7a",
    "PROVENANCE_FINAL.json": "7d1c336a8585e1d0a91b4bf1be3d47fc6aa8bcf58bf37062f920fe022172aa27",
    "PROVENANCE_START.json": "d0f7e981cbf398c2d07579625f10b6cd7616bd16cc22aa236b37cf8b697500b9",
    "SBCCD_MAIN_REGENERATED.json": "c04dd5681a3fe60d8d99fd2fd1f8daafc59ce359de9a1a2dd9b566af2a68c3a1",
    "SBCCD_STAGE1B_COMPATIBILITY.json": "6073945c1b014beb3302296a20b58e583b9ffe89ab936bdfc24c70b504881d38",
    "STAGE1B_SUMMARY.json": "51251249a84bcd6e54ebfd75ef89acf822b9570928b1d8dfe6c18a29705dffbc",
    "OUTPUT_SHA256.json": "c2f15d4da021b098818d2e5f68fc2553383c42465b03998de69363b54373c7c3",
}

SOURCE_HASHES = {
    "src/hsafm_defects/feature_events.py": "7a5a4e543eb94614eeeb2e10d4301c534453d6bb70e50ef22556512be344a1cf",
    "src/hsafm_defects/load_asd.py": "bdc90fb5bbb57c26a388fbe69733c21da89c7deb750add441ed463d917202f19",
    "src/hsafm_defects/audit/adapters.py": "1cd212de82008e85909cf46aeec0ffaee4c4c91a6664ddfb35689101981b578c",
    "src/hsafm_defects/audit/observe.py": "53be31f8d3e262f31fb7616be1cb13f63efa948dbc4eea34b48070edea337f1a",
    "src/hsafm_defects/audit/evidence.py": "5484fdfb9faceec14ca7ef3b9e0b5017f96e8d0c46f1b4581c17b25405a4cce1",
    "src/hsafm_defects/__init__.py": "7b14ed37426333e58c29deac562c9b1ffa8eb6df712a5fae7258c00bca9283d6",
    "src/hsafm_defects/audit/__init__.py": "7ecea6c98f34c8e6518573d1db473bc2895f36b64892d17949f1887dd837f004",
    "stage1b_compatibility_contract.py": "7bf09f4e1e773ed0190576a3020c5bf0721d4140d203216b1a8f45b5b0311d17",
}

ALLOWED_CLASSES = {
    "source_valid_negative", "observability_limited", "registration_limited",
    "assignment_ambiguous", "candidate_reappearance", "unresolved", "boundary_censored",
}
ALLOWED_CODES = set("XQURACSNE")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_file(path: Path, expected_sha: str, expected_bytes: int | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"required file missing: {path}")
    size = path.stat().st_size
    if expected_bytes is not None and size != expected_bytes:
        raise RuntimeError(f"byte-count mismatch for {path}: expected {expected_bytes}, got {size}")
    got = sha256_path(path)
    if got != expected_sha:
        raise RuntimeError(f"SHA-256 mismatch for {path}: expected {expected_sha}, got {got}")
    return {"path": str(path.resolve()), "bytes": size, "sha256": got}


def json_read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def jsonable(x: Any) -> Any:
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def write_json(path: Path, obj: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(jsonable(obj), f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def canonical_main_events(canonical: dict[str, Any], dataset: str) -> list[dict[str, Any]]:
    if dataset not in canonical or not isinstance(canonical[dataset], dict):
        raise RuntimeError(f"canonical results missing dataset {dataset}")
    block = canonical[dataset]
    if block.get("config") != MAIN_CONFIG:
        raise RuntimeError(f"canonical {dataset} config mismatch: {block.get('config')!r}")
    events = block.get("events")
    if not isinstance(events, list):
        raise RuntimeError(f"canonical {dataset} events is not a list")
    if len(events) != EXPECTED_COUNTS[dataset]:
        raise RuntimeError(f"canonical {dataset} count mismatch: expected {EXPECTED_COUNTS[dataset]}, got {len(events)}")
    return events


def static_source_checks(root: Path) -> dict[str, Any]:
    feature = (root / "src/hsafm_defects/feature_events.py").read_text(encoding="utf-8")
    observe = (root / "src/hsafm_defects/audit/observe.py").read_text(encoding="utf-8")
    evidence = (root / "src/hsafm_defects/audit/evidence.py").read_text(encoding="utf-8")
    runner_text = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(runner_text)

    direct_detect_calls = 0
    survival_tau_calls = 0
    adapter_calls = 0
    secondary_qc_calls = 0
    stage2_dataset_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"detect_events", "detect_events_array"}:
                direct_detect_calls += 1
            if name == "survival_tau":
                survival_tau_calls += 1
            if name == "observation_from_tables":
                adapter_calls += 1
            if name == "row_artifact_frame_qc":
                secondary_qc_calls += 1
            if name == "run_stage2_dataset" and node.args and isinstance(node.args[0], ast.Constant):
                stage2_dataset_calls.append(str(node.args[0].value))

    helper_counts = {"load_stack": 0, "observe_frozen_detector": 0, "compare_event_lists_stage1b": 0, "audit_events": 0}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run_stage2_dataset":
            for c in ast.walk(node):
                if not isinstance(c, ast.Call):
                    continue
                if isinstance(c.func, ast.Name):
                    nm = c.func.id
                elif isinstance(c.func, ast.Attribute):
                    nm = c.func.attr
                else:
                    nm = None
                if nm in helper_counts:
                    helper_counts[nm] += 1

    wrapped_dataset_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        is_limit1 = False
        for item in node.items:
            ce = item.context_expr
            if isinstance(ce, ast.Call) and ((isinstance(ce.func, ast.Name) and ce.func.id == "threadpool_limits") or (isinstance(ce.func, ast.Attribute) and ce.func.attr == "threadpool_limits")):
                for kw in ce.keywords:
                    if kw.arg == "limits" and isinstance(kw.value, ast.Constant) and kw.value.value == 1:
                        is_limit1 = True
                if ce.args and isinstance(ce.args[0], ast.Constant) and ce.args[0].value == 1:
                    is_limit1 = True
        if is_limit1:
            for c in ast.walk(node):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "run_stage2_dataset" and c.args and isinstance(c.args[0], ast.Constant):
                    wrapped_dataset_calls.append(str(c.args[0].value))

    checks = {
        "feature_marker_blobs_done_count": feature.count("det[f] = blobs"),
        "feature_marker_end_tracking_count": feature.count("first_g, last_g = good[0], good[-1]"),
        "observe_declares_blobs_marker": '"blobs_done": "det[f] = blobs"' in observe,
        "observe_declares_end_tracking_marker": '"end_tracking": "first_g, last_g = good[0], good[-1]"' in observe,
        "observe_calls_detect_events_array_once": observe.count("fe.detect_events_array(") == 1,
        "evidence_has_audit_events": "def audit_events(" in evidence,
        "evidence_has_frozen_class_vocabulary": "CLASSES =" in evidence,
        "runner_direct_detector_calls": direct_detect_calls,
        "runner_survival_tau_calls": survival_tau_calls,
        "runner_external_adapter_calls": adapter_calls,
        "runner_row_artifact_frame_qc_calls": secondary_qc_calls,
        "runner_explicit_stage2_dataset_call_sites": stage2_dataset_calls,
        "runner_stage2_dataset_calls_under_threadpool_limits_1": wrapped_dataset_calls,
        "run_stage2_dataset_helper_call_counts": helper_counts,
        "runner_has_threadpool_limit": "with threadpool_limits(limits=1):" in runner_text,
        "runner_has_no_row_artifact_frame_qc_call": secondary_qc_calls == 0,
    }
    if checks["feature_marker_blobs_done_count"] != 1 or checks["feature_marker_end_tracking_count"] != 1:
        raise RuntimeError("canonical detector observer marker compatibility failed")
    if not checks["observe_declares_blobs_marker"] or not checks["observe_declares_end_tracking_marker"]:
        raise RuntimeError("frozen observer marker declarations mismatch")
    if not checks["observe_calls_detect_events_array_once"]:
        raise RuntimeError("frozen observer detector-call topology mismatch")
    if direct_detect_calls != 0 or survival_tau_calls != 0 or adapter_calls != 0:
        raise RuntimeError("Stage-2 runner contains prohibited direct detector/survival/adapter call sites")
    if stage2_dataset_calls != ["gltph", "sbccd"]:
        raise RuntimeError(f"Stage-2 dataset call topology mismatch: {stage2_dataset_calls!r}")
    if wrapped_dataset_calls != ["gltph", "sbccd"]:
        raise RuntimeError(f"Stage-2 dataset calls are not both under threadpool_limits(limits=1): {wrapped_dataset_calls!r}")
    if helper_counts != {"load_stack": 1, "observe_frozen_detector": 1, "compare_event_lists_stage1b": 1, "audit_events": 1}:
        raise RuntimeError(f"Stage-2 per-dataset call topology mismatch: {helper_counts!r}")
    if not checks["runner_has_threadpool_limit"] or not checks["runner_has_no_row_artifact_frame_qc_call"]:
        raise RuntimeError("Stage-2 threading/QC policy static check failed")
    return checks


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(__file__).resolve().parent
    verified_sources = {}
    for rel, expected in SOURCE_HASHES.items():
        verified_sources[rel] = check_file(root / rel, expected)

    verified_inputs = {
        "gltph_asd": check_file(args.gltph, INPUTS["gltph_asd"]["sha256"], INPUTS["gltph_asd"]["bytes"]),
        "sbccd_asd": check_file(args.sbccd, INPUTS["sbccd_asd"]["sha256"], INPUTS["sbccd_asd"]["bytes"]),
        "canonical_results_json": check_file(args.canonical_results, INPUTS["canonical_results_json"]["sha256"], INPUTS["canonical_results_json"]["bytes"]),
    }
    canonical = json_read(args.canonical_results)
    canonical_counts = {d: len(canonical_main_events(canonical, d)) for d in ("gltph", "sbccd")}

    if not args.stage1b_dir.is_dir():
        raise RuntimeError(f"Stage-1B result directory missing: {args.stage1b_dir}")
    verified_stage1b = {}
    for name, expected in STAGE1B_RESULTS.items():
        verified_stage1b[name] = check_file(args.stage1b_dir / name, expected)

    static = static_source_checks(root)
    return {
        "stage2_version": STAGE2_VERSION,
        "status": "PREFLIGHT_PASS_NO_SCIENTIFIC_EXECUTION",
        "acquisition_status": ACQUISITION_STATUS,
        "original_stage1_verdict": ORIGINAL_STAGE1_VERDICT,
        "upstream_stage1b_verdict": UPSTREAM_STAGE1B_VERDICT,
        "verified_sources": verified_sources,
        "verified_inputs": verified_inputs,
        "verified_stage1b_results": verified_stage1b,
        "canonical_counts": canonical_counts,
        "main_config": MAIN_CONFIG,
        "audit_params": AUDIT_PARAMS,
        "audit_params_digest": AUDIT_PARAMS_DIGEST,
        "secondary_frame_qc_policy": SECONDARY_FRAME_QC_POLICY,
        "static_source_checks": static,
        "planned_call_topology": {
            "canonical_load_stack_calls": 2,
            "eventaudit_observe_frozen_detector_calls": 2,
            "canonical_detect_events_array_calls_internal_to_observer": 2,
            "stage1b_compatibility_comparisons": 2,
            "eventaudit_audit_events_calls": 2,
            "external_adapter_observation_from_tables_calls": 0,
            "control_11nm_detector_calls": 0,
            "survival_tau_calls": 0,
        },
        "scientific_execution_performed": False,
        "detector_calls": 0,
        "eventaudit_calls": 0,
        "survival_tau_calls": 0,
    }


def environment_snapshot() -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "scipy", "scikit-image", "AFMReader", "threadpoolctl"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        np.show_config()
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "package_versions": packages,
        "threadpoolctl_version": getattr(threadpoolctl, "__version__", None),
        "threadpool_info_before_scientific_imports": threadpoolctl.threadpool_info(),
        "numpy_show_config": buf.getvalue().splitlines(),
        "thread_environment": {k: os.environ.get(k) for k in (
            "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "BLIS_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
    }


def import_local_scientific_modules(root: Path):
    src = str((root / "src").resolve())
    if src not in sys.path:
        sys.path.insert(0, src)
    for name in list(sys.modules):
        if name == "hsafm_defects" or name.startswith("hsafm_defects."):
            del sys.modules[name]
    load_mod = importlib.import_module("hsafm_defects.load_asd")
    observe_mod = importlib.import_module("hsafm_defects.audit.observe")
    evidence_mod = importlib.import_module("hsafm_defects.audit.evidence")
    expected = {
        "load": (root / "src/hsafm_defects/load_asd.py").resolve(),
        "observe": (root / "src/hsafm_defects/audit/observe.py").resolve(),
        "evidence": (root / "src/hsafm_defects/audit/evidence.py").resolve(),
        "feature": (root / "src/hsafm_defects/feature_events.py").resolve(),
    }
    actual = {
        "load": Path(load_mod.__file__).resolve(),
        "observe": Path(observe_mod.__file__).resolve(),
        "evidence": Path(evidence_mod.__file__).resolve(),
        "feature": Path(importlib.import_module("hsafm_defects.feature_events").__file__).resolve(),
    }
    if actual != expected:
        raise RuntimeError(f"package-local import resolution failed: actual={actual}, expected={expected}")
    return load_mod, observe_mod, evidence_mod, {k: str(v) for k, v in actual.items()}


def check_observation_invariants(obs: Any, dataset: str, expected_count: int) -> dict[str, Any]:
    if len(obs.events) != expected_count:
        raise RuntimeError(f"{dataset}: observer event count expected {expected_count}, got {len(obs.events)}")
    retained = [tr for tr in obs.tracks if tr["event_index"] is not None]
    if len(retained) != expected_count:
        raise RuntimeError(f"{dataset}: retained-track count expected {expected_count}, got {len(retained)}")
    event_indices = [int(tr["event_index"]) for tr in retained]
    if event_indices != list(range(expected_count)):
        raise RuntimeError(f"{dataset}: retained track->event mapping is not exact 0..{expected_count-1}")
    good = list(obs.good)
    if not good:
        raise RuntimeError(f"{dataset}: observer has no good frames")
    for tr in retained:
        ei = int(tr["event_index"])
        pts = [(int(f), int(c)) for f, c in tr["points"]]
        fs = [f for f, _ in pts]
        if len(fs) != len(set(fs)):
            raise RuntimeError(f"{dataset}: event {ei} has duplicate detection frames")
        e = obs.events[ei]
        f0, f1 = min(fs), max(fs)
        if int(e["n_frames"]) != len(set(fs)):
            raise RuntimeError(f"{dataset}: event {ei} n_frames disagrees with track membership")
        if float(e["t0"]).hex() != float(round(f0 * obs.dt_s, 3)).hex():
            raise RuntimeError(f"{dataset}: event {ei} t0 disagrees with track membership")
        if float(e["t1"]).hex() != float(round(f1 * obs.dt_s, 3)).hex():
            raise RuntimeError(f"{dataset}: event {ei} t1 disagrees with track membership")
        if float(e["lifetime_s"]).hex() != float(round((f1 - f0) * obs.dt_s, 3)).hex():
            raise RuntimeError(f"{dataset}: event {ei} lifetime disagrees with track membership")
        expected_fo = bool(f0 > good[0] and f1 < good[-1])
        if bool(e["fully_observed"]) != expected_fo:
            raise RuntimeError(f"{dataset}: event {ei} fully_observed disagrees with track membership")
    return {
        "event_count": len(obs.events),
        "retained_track_count": len(retained),
        "total_track_count": len(obs.tracks),
        "good_frame_count": len(obs.good),
        "excluded_frame_count": len(obs.bad),
        "track_event_mapping_exact": True,
        "track_temporal_summary_invariants_pass": True,
    }


def check_audit_invariants(obs: Any, audit: dict[str, Any], dataset: str, expected_count: int, params_digest: str) -> dict[str, Any]:
    rows = audit.get("events")
    frames = audit.get("frames")
    candidates = audit.get("candidates")
    details = audit.get("candidate_details")
    if not all(isinstance(x, list) for x in (rows, frames, candidates, details)):
        raise RuntimeError(f"{dataset}: malformed raw audit output")
    if len(rows) != expected_count:
        raise RuntimeError(f"{dataset}: audit event rows expected {expected_count}, got {len(rows)}")
    if [int(r["event_index"]) for r in rows] != list(range(expected_count)):
        raise RuntimeError(f"{dataset}: audit event_index ordering mismatch")
    retained_by_event = {int(tr["event_index"]): tr for tr in obs.tracks if tr["event_index"] is not None}
    for row in rows:
        ei = int(row["event_index"])
        tr = retained_by_event[ei]
        fs = sorted({int(f) for f, _ in tr["points"]})
        if int(row["track_id"]) != int(tr["track_id"]):
            raise RuntimeError(f"{dataset}: audit row {ei} track_id mismatch")
        if int(row["f0"]) != fs[0] or int(row["f1"]) != fs[-1] or int(row["n_det_frames"]) != len(fs):
            raise RuntimeError(f"{dataset}: audit row {ei} temporal fields mismatch track membership")
        if bool(row["fully_observed_frozen"]) != bool(obs.events[ei]["fully_observed"]):
            raise RuntimeError(f"{dataset}: audit row {ei} fully_observed mismatch")
        if row.get("audit_version") != "eventaudit-0.1-proto" or row.get("params_digest") != params_digest:
            raise RuntimeError(f"{dataset}: audit row {ei} version/params digest mismatch")
        for side in ("start", "end"):
            cls = row.get(f"{side}_class")
            if cls not in ALLOWED_CLASSES:
                raise RuntimeError(f"{dataset}: audit row {ei} invalid {side}_class {cls!r}")
            codes = row.get(f"{side}_codes", "")
            if not isinstance(codes, str) or any(c not in ALLOWED_CODES for c in codes):
                raise RuntimeError(f"{dataset}: audit row {ei} invalid {side}_codes {codes!r}")
        gap_text = row.get("internal_gap_codes", "")
        if gap_text:
            for tok in gap_text.split():
                try:
                    _, code = tok.rsplit(":", 1)
                except ValueError as exc:
                    raise RuntimeError(f"{dataset}: malformed internal gap code token {tok!r}") from exc
                if code not in ALLOWED_CODES:
                    raise RuntimeError(f"{dataset}: invalid internal gap code {code!r}")
    if len(frames) != len(obs.frames):
        raise RuntimeError(f"{dataset}: audit frame-row count mismatch")
    good_set = set(obs.good)
    for fr in frames:
        i = int(fr["frame"])
        expected_prod = "good" if i in good_set else "excluded"
        if fr.get("production") != expected_prod:
            raise RuntimeError(f"{dataset}: frame {i} production status mismatch")
        if int(fr.get("secondary_qc", -1)) != 0:
            raise RuntimeError(f"{dataset}: secondary_qc must remain zero under frozen external policy")
    for edge in candidates:
        if edge.get("applied") is not False:
            raise RuntimeError(f"{dataset}: candidate edge was applied; hypotheses must remain unapplied")
        if not (0 <= int(edge["from_event"]) < expected_count and 0 <= int(edge["to_event"]) < expected_count):
            raise RuntimeError(f"{dataset}: candidate edge event index out of range")
    return {
        "audit_event_rows": len(rows),
        "audit_frame_rows": len(frames),
        "candidate_edges": len(candidates),
        "candidate_detail_rows": len(details),
        "class_vocabulary_valid": True,
        "code_vocabulary_valid": True,
        "params_digest_exact": True,
        "secondary_qc_empty_policy_preserved": True,
        "candidate_edges_unapplied": True,
    }


def export_tracks(obs: Any) -> dict[str, Any]:
    return {
        "source": obs.source,
        "input_sha256_array": obs.input_sha256,
        "shape": list(obs.shape),
        "px2nm": float(obs.px2nm),
        "dt_s": float(obs.dt_s),
        "cfg": obs.cfg,
        "good_frames": list(obs.good),
        "excluded_frames": list(obs.bad),
        "events": obs.events,
        "info": obs.info,
        "tracks": [
            {
                "track_id": int(tr["track_id"]),
                "event_index": None if tr["event_index"] is None else int(tr["event_index"]),
                "points": [[int(f), int(c)] for f, c in tr["points"]],
            }
            for tr in obs.tracks
        ],
        "component_ownership": [
            {"frame": int(f), "component": int(c), "track_id": int(tid)}
            for (f, c), tid in sorted(obs.comp_owner.items())
        ],
    }


def descriptive_summary(dataset: str, audit: dict[str, Any], obs: Any) -> dict[str, Any]:
    rows = audit["events"]
    return {
        "dataset": dataset,
        "interpretation": "descriptive EventAudit evidence representation only; not accuracy, physical closure, or biological truth",
        "n_events": len(rows),
        "start_class_counts": dict(sorted(Counter(r["start_class"] for r in rows).items())),
        "end_class_counts": dict(sorted(Counter(r["end_class"] for r in rows).items())),
        "candidate_edge_count": len(audit["candidates"]),
        "mutual_candidate_edge_count": sum(bool(e.get("mutual")) for e in audit["candidates"]),
        "good_frame_count": len(obs.good),
        "excluded_frame_count": len(obs.bad),
        "secondary_qc_frame_count": 0,
    }


def run_stage2_dataset(dataset: str, path: Path, canonical_events: list[dict[str, Any]], expected_count: int,
                       load_mod: Any, observe_mod: Any, evidence_mod: Any, params: Any) -> dict[str, Any]:
    d = load_mod.load_stack(str(path))
    obs = observe_mod.observe_frozen_detector(
        d["frames_nm"], d["px2nm"], d["dt_s"], meta=d["meta"], **MAIN_CONFIG
    )
    compatibility = compare_event_lists_stage1b(canonical_events, obs.events, dataset)
    if len(obs.events) != expected_count:
        raise RuntimeError(f"{dataset}: Stage-2 observer count expected {expected_count}, got {len(obs.events)}")
    if not compatibility.get("compatibility_pass"):
        raise RuntimeError(f"{dataset}: Stage-2 observer events fail frozen Stage-1B compatibility gate")
    observer_invariants = check_observation_invariants(obs, dataset, expected_count)
    audit = evidence_mod.audit_events(obs, frame_qc=set(), params=params)
    audit_invariants = check_audit_invariants(obs, audit, dataset, expected_count, params.digest())
    return {
        "observation": obs,
        "compatibility": compatibility,
        "observer_invariants": observer_invariants,
        "audit": audit,
        "audit_invariants": audit_invariants,
        "summary": descriptive_summary(dataset, audit, obs),
    }


def output_hashes(output_dir: Path) -> dict[str, Any]:
    out = {}
    for p in sorted(output_dir.iterdir(), key=lambda x: x.name):
        if p.is_file() and p.name != "OUTPUT_SHA256.json":
            out[p.name] = {"bytes": p.stat().st_size, "sha256": sha256_path(p)}
    return out


def execute(args: argparse.Namespace, pf: dict[str, Any]) -> None:
    if args.approval_token != APPROVAL_TOKEN:
        raise RuntimeError("Stage-2 execution approval token missing or incorrect")
    if args.output_dir is None:
        raise RuntimeError("--output-dir is required with --execute-stage2")
    if args.output_dir.exists():
        raise RuntimeError(f"output directory already exists; refusing overwrite: {args.output_dir}")
    canonical_repo = args.canonical_results.resolve().parent.parent
    prospective = args.output_dir.resolve(strict=False)
    if prospective == canonical_repo or prospective.is_relative_to(canonical_repo):
        raise RuntimeError("Stage-2 output directory must be outside the canonical repository")

    canonical = json_read(args.canonical_results)
    environment = environment_snapshot()
    root = Path(__file__).resolve().parent
    load_mod, observe_mod, evidence_mod, import_paths = import_local_scientific_modules(root)
    params = evidence_mod.AuditParams(**AUDIT_PARAMS)
    if params.digest() != AUDIT_PARAMS_DIGEST:
        raise RuntimeError(f"AuditParams digest mismatch: expected {AUDIT_PARAMS_DIGEST}, got {params.digest()}")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / "ENVIRONMENT.json", environment)
    write_json(args.output_dir / "PROVENANCE_START.json", {
        "stage2_version": STAGE2_VERSION,
        "status": "STAGE2_EXECUTION_STARTED",
        "acquisition_status": ACQUISITION_STATUS,
        "original_stage1_verdict": ORIGINAL_STAGE1_VERDICT,
        "upstream_stage1b_verdict": UPSTREAM_STAGE1B_VERDICT,
        "verified_preflight": pf,
        "package_local_import_paths": import_paths,
        "main_config": MAIN_CONFIG,
        "audit_params": AUDIT_PARAMS,
        "audit_params_digest": AUDIT_PARAMS_DIGEST,
        "secondary_frame_qc_policy": SECONDARY_FRAME_QC_POLICY,
        "manuscript_facing_biological_claim_authorized": False,
    })

    completed = []
    try:
        with threadpool_limits(limits=1):
            numeric = {
                "threadpool_info_inside_explicit_limit": threadpoolctl.threadpool_info(),
                "threadpoolctl_version": getattr(threadpoolctl, "__version__", None),
            }
            write_json(args.output_dir / "NUMERIC_PROVENANCE.json", numeric)

            gltph = run_stage2_dataset("gltph", args.gltph, canonical_main_events(canonical, "gltph"), EXPECTED_COUNTS["gltph"], load_mod, observe_mod, evidence_mod, params)
            write_json(args.output_dir / "GLTPH_OBSERVER_EVENT_COMPATIBILITY.json", gltph["compatibility"])
            write_json(args.output_dir / "GLTPH_REGENERATED_TRACKS.json", export_tracks(gltph["observation"]))
            write_json(args.output_dir / "GLTPH_EVENTAUDIT_RAW.json", gltph["audit"])
            write_json(args.output_dir / "GLTPH_EVENTAUDIT_INVARIANTS.json", {"observer": gltph["observer_invariants"], "audit": gltph["audit_invariants"]})
            completed.append("gltph")

            sbccd = run_stage2_dataset("sbccd", args.sbccd, canonical_main_events(canonical, "sbccd"), EXPECTED_COUNTS["sbccd"], load_mod, observe_mod, evidence_mod, params)
            write_json(args.output_dir / "SBCCD_OBSERVER_EVENT_COMPATIBILITY.json", sbccd["compatibility"])
            write_json(args.output_dir / "SBCCD_REGENERATED_TRACKS.json", export_tracks(sbccd["observation"]))
            write_json(args.output_dir / "SBCCD_EVENTAUDIT_RAW.json", sbccd["audit"])
            write_json(args.output_dir / "SBCCD_EVENTAUDIT_INVARIANTS.json", {"observer": sbccd["observer_invariants"], "audit": sbccd["audit_invariants"]})
            completed.append("sbccd")

        write_json(args.output_dir / "STAGE2_DESCRIPTIVE_SUMMARY.json", {
            "stage2_version": STAGE2_VERSION,
            "acquisition_status": ACQUISITION_STATUS,
            "interpretation_boundary": "descriptive observer/evidence outputs only; no accuracy score, physical closure label, biological truth validation, or manuscript-facing biological claim",
            "gltph": gltph["summary"],
            "sbccd": sbccd["summary"],
        })
        write_json(args.output_dir / "STAGE2_COMPLETENESS.json", {
            "complete": True,
            "datasets_completed": completed,
            "expected_event_counts": EXPECTED_COUNTS,
            "observer_event_rows_complete": True,
            "audit_event_rows_complete": True,
            "audit_frame_rows_complete": True,
            "stage1b_compatibility_gate_passed": True,
            "secondary_qc_policy": SECONDARY_FRAME_QC_POLICY,
            "overall_accuracy_score_computed": False,
            "physical_closure_label_computed": False,
            "survival_tau_called": False,
            "threshold_tuning": False,
        })
        write_json(args.output_dir / "PROVENANCE_FINAL.json", {
            "stage2_version": STAGE2_VERSION,
            "status": "STAGE2_EXECUTION_COMPLETE",
            "acquisition_status": ACQUISITION_STATUS,
            "original_stage1_verdict": ORIGINAL_STAGE1_VERDICT,
            "upstream_stage1b_verdict": UPSTREAM_STAGE1B_VERDICT,
            "completed_datasets": completed,
            "planned_call_topology_realized_on_success_path": {
                "canonical_load_stack_calls": 2,
                "eventaudit_observe_frozen_detector_calls": 2,
                "canonical_detect_events_array_calls_internal_to_observer": 2,
                "stage1b_compatibility_comparisons": 2,
                "eventaudit_audit_events_calls": 2,
                "external_adapter_calls": 0,
                "control_11nm_detector_calls": 0,
                "survival_tau_calls": 0,
            },
            "manuscript_facing_biological_claim_authorized": False,
        })
    except Exception as exc:
        if not (args.output_dir / "PROVENANCE_FINAL.json").exists():
            write_json(args.output_dir / "PROVENANCE_FINAL.json", {
                "stage2_version": STAGE2_VERSION,
                "status": "STAGE2_EXECUTION_FAILED_CLOSED",
                "completed_datasets_before_failure": completed,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "manuscript_facing_biological_claim_authorized": False,
            })
        write_json(args.output_dir / "OUTPUT_SHA256.json", output_hashes(args.output_dir))
        raise
    write_json(args.output_dir / "OUTPUT_SHA256.json", output_hashes(args.output_dir))


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-stage2", action="store_true")
    ap.add_argument("--gltph", type=Path, required=True)
    ap.add_argument("--sbccd", type=Path, required=True)
    ap.add_argument("--canonical-results", type=Path, required=True)
    ap.add_argument("--stage1b-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--approval-token")
    args = ap.parse_args()
    try:
        pf = preflight(args)
        if args.preflight_only:
            print(json.dumps(pf, indent=2, sort_keys=True))
            return 0
        execute(args, pf)
        print("STAGE2_EXECUTION_COMPLETE")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
