from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("r130_provenance", ROOT / "provenance_ingestor_r130.py")
_r130 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r130)

_SCHEMA = "bres-live-physical-collection-folder-import-r132-v1"
_PACKET_SCHEMA = "bres-live-discriminant-collection-packet-r125-v1"
_PROVENANCE_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"
_REQUIRED_FACES = (("recto", "RECTO"), ("verso", "VERSO"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _safe_relpath(root: Path, raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    rel = Path(text)
    if rel.is_absolute():
        return None
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return rel


def _empty_result(errors: List[str], warnings: List[str] | None = None) -> Dict[str, Any]:
    return {
        "schema": _SCHEMA,
        "source_packet_schema": None,
        "source_provenance_schema": _PROVENANCE_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "import_status": "REJECTED",
        "accepted_for_diagnostics": False,
        "errors": list(errors),
        "warnings": list(warnings or []),
        "physical_key_id": None,
        "candidate_pair": {},
        "source_folder_manifest": [],
        "source_folder_digest_sha256": None,
        "diagnostic_envelope": None,
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }


def import_collection_folder(folder: str | Path) -> Dict[str, Any]:
    """Import one physical-key collection folder into the R130 diagnostic layer.

    Expected layout: a packet.json plus six source images referenced by relative
    ``source_file_relpath`` fields under the three recto/verso capture slots.
    Source bytes are verified against the declared SHA-256 values before any R130
    diagnostic ingestion. This adapter never validates a reference and never writes
    to the runtime or canonical catalogue.
    """
    root = Path(folder).resolve()
    errors: List[str] = []
    warnings: List[str] = []
    if not root.is_dir():
        return _empty_result(["collection_folder_missing"])

    packet_path = root / "packet.json"
    if not packet_path.is_file():
        return _empty_result(["packet_json_missing"])
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except Exception:
        return _empty_result(["packet_json_invalid"])
    if not isinstance(packet, dict):
        return _empty_result(["packet_json_not_object"])

    source = copy.deepcopy(packet)
    if source.get("schema") != _PACKET_SCHEMA:
        errors.append("packet_schema_invalid")

    sessions = source.get("collection_sessions", [])
    if not isinstance(sessions, list) or len(sessions) != 3:
        errors.append("requires_exactly_three_collection_sessions")
        sessions = sessions if isinstance(sessions, list) else []

    manifest: List[Dict[str, Any]] = []
    seen_relpaths: set[str] = set()
    seen_capture_ids: set[str] = set()
    seen_hashes: set[str] = set()

    for sidx, session in enumerate(sessions, 1):
        sid = str(session.get("capture_session_id", "")).strip()
        captures = session.get("captures", {}) if isinstance(session, dict) else {}
        for face_key, expected_side in _REQUIRED_FACES:
            prefix = f"session_{sidx}_{face_key}"
            capture = captures.get(face_key, {}) if isinstance(captures, dict) else {}
            if not isinstance(capture, dict):
                errors.append(prefix + "_capture_missing")
                continue
            if capture.get("side") != expected_side:
                errors.append(prefix + "_side_mismatch")
            capture_id = str(capture.get("capture_id", "")).strip()
            if not capture_id:
                errors.append(prefix + "_capture_id_missing")
            elif capture_id in seen_capture_ids:
                errors.append("capture_id_reused_across_folder")
            else:
                seen_capture_ids.add(capture_id)

            rel = _safe_relpath(root, capture.get("source_file_relpath"))
            if rel is None:
                errors.append(prefix + "_source_file_relpath_invalid")
                continue
            rel_text = rel.as_posix()
            if rel_text in seen_relpaths:
                errors.append("source_file_relpath_reused_across_folder")
            else:
                seen_relpaths.add(rel_text)
            source_path = (root / rel).resolve()
            if not source_path.is_file():
                errors.append(prefix + "_source_file_missing")
                continue
            size = source_path.stat().st_size
            if size <= 0:
                errors.append(prefix + "_source_file_empty")
                continue
            actual_sha = _sha256_file(source_path)
            declared_sha = str(capture.get("source_file_sha256", "")).strip().lower()
            if declared_sha != actual_sha:
                errors.append(prefix + "_source_file_sha256_mismatch")
            if actual_sha in seen_hashes:
                errors.append("source_file_sha256_reused_across_folder")
            else:
                seen_hashes.add(actual_sha)
            manifest.append({
                "capture_session_id": sid,
                "side": expected_side,
                "capture_id": capture_id,
                "source_file_relpath": rel_text,
                "source_file_sha256": actual_sha,
                "size_bytes": size,
            })

    if len(manifest) != 6:
        errors.append("requires_exactly_six_verified_source_files")

    diagnostic = None
    if not errors:
        diagnostic = _r130.ingest_packet_with_provenance(source)
        if diagnostic.get("schema") != _PROVENANCE_SCHEMA:
            errors.append("r130_provenance_schema_invalid")
        if not diagnostic.get("accepted_for_diagnostics"):
            errors.extend("r130:" + str(e) for e in diagnostic.get("errors", []))

    accepted = not errors and bool(diagnostic and diagnostic.get("accepted_for_diagnostics"))
    return {
        "schema": _SCHEMA,
        "source_packet_schema": source.get("schema"),
        "source_provenance_schema": _PROVENANCE_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "import_status": "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS" if accepted else "REJECTED",
        "accepted_for_diagnostics": accepted,
        "errors": errors,
        "warnings": warnings + (copy.deepcopy(diagnostic.get("warnings", [])) if diagnostic else []),
        "physical_key_id": source.get("physical_key_id"),
        "candidate_pair": copy.deepcopy(source.get("candidate_pair", {})),
        "source_folder_manifest": manifest,
        "source_folder_digest_sha256": _sha256_json(manifest) if len(manifest) == 6 else None,
        "diagnostic_envelope": copy.deepcopy(diagnostic) if accepted else None,
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
