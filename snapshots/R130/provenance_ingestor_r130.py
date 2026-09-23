from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("r126_ingestor", ROOT / "collection_packet_ingestor_r126.py")
_r126 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r126)

_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"
_R126_SCHEMA = "bres-live-discriminant-diagnostic-ingestion-r126-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _extract_capture_provenance(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for session in packet.get("collection_sessions", []):
        session_id = str(session.get("capture_session_id", "")).strip()
        captures = session.get("captures", {})
        for face, expected in (("recto", "RECTO"), ("verso", "VERSO")):
            capture = captures.get(face, {})
            capture_id = str(capture.get("capture_id", "")).strip()
            source_sha = str(capture.get("source_file_sha256", "")).strip().lower()
            side = str(capture.get("side", "")).strip()
            if not session_id:
                raise ValueError("capture_session_id_missing")
            if side != expected:
                raise ValueError("capture_side_invalid")
            if not capture_id:
                raise ValueError("capture_id_missing")
            if not _SHA256_RE.fullmatch(source_sha):
                raise ValueError("source_file_sha256_invalid")
            rows.append({
                "capture_session_id": session_id,
                "side": expected,
                "capture_id": capture_id,
                "source_file_sha256": source_sha,
            })
    if len(rows) != 6:
        raise ValueError("requires_exactly_six_source_captures")
    ids = [r["capture_id"] for r in rows]
    hashes = [r["source_file_sha256"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("capture_id_reused_within_packet")
    if len(hashes) != len(set(hashes)):
        raise ValueError("source_file_sha256_reused_within_packet")
    return rows


def ingest_packet_with_provenance(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Promote an R125 packet into a non-authoritative R130 diagnostic envelope.

    R130 preserves source capture identifiers and source file SHA-256 values end-to-end.
    It does not validate a reference, define a physical threshold, mutate R116, or write
    the canonical catalogue.
    """
    source = copy.deepcopy(packet)
    base = _r126.ingest_packet(source)
    if base.get("schema") != _R126_SCHEMA:
        raise ValueError("r126_schema_invalid")

    provenance: List[Dict[str, Any]] = []
    provenance_errors: List[str] = []
    try:
        provenance = _extract_capture_provenance(source)
    except ValueError as exc:
        provenance_errors.append(str(exc))

    accepted = bool(base.get("accepted_for_diagnostics")) and not provenance_errors
    provenance_digest = _sha256_json(provenance) if provenance else None
    source_packet_sha = _sha256_json(source)

    return {
        "schema": _SCHEMA,
        "source_ingestion_schema": _R126_SCHEMA,
        "source_packet_schema": source.get("schema"),
        "active_test_runtime": "V2.28 TEST R116",
        "ingestion_status": "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS" if accepted else "REJECTED",
        "accepted_for_diagnostics": accepted,
        "source_r126_accepted": bool(base.get("accepted_for_diagnostics")),
        "errors": list(base.get("errors", [])) + provenance_errors,
        "warnings": copy.deepcopy(base.get("warnings", [])),
        "physical_key_id": source.get("physical_key_id"),
        "candidate_pair": copy.deepcopy(base.get("candidate_pair", {})),
        "diagnostics": copy.deepcopy(base.get("diagnostics", {})),
        "source_capture_provenance": provenance,
        "source_capture_count": len(provenance),
        "source_capture_ids_unique": len({r["capture_id"] for r in provenance}) == len(provenance) if provenance else False,
        "source_capture_sha256_unique": len({r["source_file_sha256"] for r in provenance}) == len(provenance) if provenance else False,
        "source_capture_sha256_provenance_complete": accepted and len(provenance) == 6,
        "provenance_digest_sha256": provenance_digest,
        "source_packet_sha256": source_packet_sha,
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
