from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

ROOT = Path(__file__).resolve().parent
_CRITICAL = json.loads((ROOT / "catalogue/evidence/catalogue_ocr_critical_pair_registry_r121.json").read_text(encoding="utf-8"))
_ALLOWED_PAIRS = {
    tuple(sorted((str(p["a"]).strip(), str(p["b"]).strip())))
    for p in _CRITICAL.get("critical_pairs", [])
}

_SOURCE_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"
_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r130-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_pair(pair: Dict[str, Any]) -> Tuple[str, str]:
    return tuple(sorted((str(pair.get("a", "")).strip(), str(pair.get("b", "")).strip())))


def new_registry() -> Dict[str, Any]:
    return {
        "schema": _REGISTRY_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "source_ingestion_schema": _SOURCE_SCHEMA,
        "registry_status": "DIAGNOSTIC_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "pairs": {},
    }


def _validate_registry(registry: Dict[str, Any]) -> None:
    if registry.get("schema") != _REGISTRY_SCHEMA:
        raise ValueError("registry_schema_invalid")
    fixed = {
        "registry_status": "DIAGNOSTIC_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
    }
    for key, expected in fixed.items():
        if registry.get(key) != expected:
            raise ValueError(f"registry_policy_escalation:{key}")


def _validate_source(source: Dict[str, Any]) -> Tuple[str, str]:
    if source.get("schema") != _SOURCE_SCHEMA:
        raise ValueError("source_schema_invalid")
    if source.get("accepted_for_diagnostics") is not True or source.get("ingestion_status") != "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS":
        raise ValueError("source_not_accepted")
    fixed = {
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "source_capture_sha256_provenance_complete": True,
        "source_capture_ids_unique": True,
        "source_capture_sha256_unique": True,
    }
    for key, expected in fixed.items():
        if source.get(key) != expected:
            raise ValueError(f"source_policy_or_provenance_invalid:{key}")
    pair = _canonical_pair(source.get("candidate_pair", {}))
    if not pair[0] or not pair[1] or pair[0] == pair[1]:
        raise ValueError("candidate_pair_invalid")
    if pair not in _ALLOWED_PAIRS:
        raise ValueError("candidate_pair_not_in_r121_critical_registry")
    physical_key_id = str(source.get("physical_key_id", "")).strip()
    if not physical_key_id:
        raise ValueError("physical_key_id_missing")
    rows = source.get("source_capture_provenance", [])
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("source_capture_provenance_incomplete")
    ids, hashes = [], []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("source_capture_provenance_record_invalid")
        cid = str(row.get("capture_id", "")).strip()
        sha = str(row.get("source_file_sha256", "")).strip().lower()
        sid = str(row.get("capture_session_id", "")).strip()
        side = str(row.get("side", "")).strip()
        if not cid or not sid or side not in {"RECTO", "VERSO"} or not _SHA256_RE.fullmatch(sha):
            raise ValueError("source_capture_provenance_record_invalid")
        ids.append(cid); hashes.append(sha)
    if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
        raise ValueError("source_capture_provenance_not_unique")
    if not _SHA256_RE.fullmatch(str(source.get("provenance_digest_sha256", "")).lower()):
        raise ValueError("provenance_digest_invalid")
    if not _SHA256_RE.fullmatch(str(source.get("source_packet_sha256", "")).lower()):
        raise ValueError("source_packet_digest_invalid")
    return pair


def _stable_result_id(source: Dict[str, Any], pair: Tuple[str, str]) -> str:
    payload = {
        "physical_key_id": source.get("physical_key_id"),
        "pair": list(pair),
        "provenance_digest_sha256": source.get("provenance_digest_sha256"),
        "source_packet_sha256": source.get("source_packet_sha256"),
        "diagnostics": source.get("diagnostics", {}),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _summary(entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(entries)
    ids = [p["capture_id"] for e in rows for p in e.get("source_capture_provenance", [])]
    hashes = [p["source_file_sha256"] for e in rows for p in e.get("source_capture_provenance", [])]
    return {
        "diagnostic_entries": len(rows),
        "distinct_physical_keys": len({e.get("physical_key_id") for e in rows}),
        "source_capture_records": len(hashes),
        "distinct_source_capture_ids": len(set(ids)),
        "distinct_source_capture_sha256": len(set(hashes)),
        "source_capture_sha256_provenance_complete": bool(rows) and len(hashes) == 6 * len(rows),
        "source_capture_reuse_detected": len(hashes) != len(set(hashes)) or len(ids) != len(set(ids)),
        "candidate_selection": None,
        "validated_reference": None,
        "physical_tolerance_decision": None,
        "acceptance_threshold_mm": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }


def add_diagnostic_result(registry: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Add one R130 result while preserving capture IDs and SHA-256 values.

    Capture ids and source-file hashes may not be reused anywhere in this registry.
    The registry remains descriptive-only and cannot select or validate a reference.
    """
    _validate_registry(registry)
    pair = _validate_source(source)
    out = copy.deepcopy(registry)
    pair_key = f"{pair[0]}::{pair[1]}"
    bucket = out["pairs"].setdefault(pair_key, {
        "candidate_pair": {"a": pair[0], "b": pair[1]},
        "policy_status": "A_CONFIRMER",
        "decision_authority": "NONE",
        "entries": [],
        "summary": _summary([]),
    })
    if bucket.get("policy_status") != "A_CONFIRMER" or bucket.get("decision_authority") != "NONE":
        raise ValueError("pair_bucket_policy_escalation")

    new_ids = {p["capture_id"] for p in source["source_capture_provenance"]}
    new_hashes = {p["source_file_sha256"] for p in source["source_capture_provenance"]}
    existing_ids = {p["capture_id"] for e in bucket["entries"] for p in e.get("source_capture_provenance", [])}
    existing_hashes = {p["source_file_sha256"] for e in bucket["entries"] for p in e.get("source_capture_provenance", [])}
    if new_ids & existing_ids:
        raise ValueError("capture_id_reused_across_registry")
    if new_hashes & existing_hashes:
        raise ValueError("source_file_sha256_reused_across_registry")

    result_id = _stable_result_id(source, pair)
    if any(e.get("result_id") == result_id for e in bucket["entries"]):
        return out
    bucket["entries"].append({
        "result_id": result_id,
        "physical_key_id": str(source.get("physical_key_id")).strip(),
        "source_schema": source.get("schema"),
        "source_packet_sha256": source.get("source_packet_sha256"),
        "provenance_digest_sha256": source.get("provenance_digest_sha256"),
        "source_capture_provenance": copy.deepcopy(source.get("source_capture_provenance", [])),
        "diagnostics": copy.deepcopy(source.get("diagnostics", {})),
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "validated_reference": None,
    })
    bucket["summary"] = _summary(bucket["entries"])
    return out


def summarize_pair(registry: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    _validate_registry(registry)
    pair = tuple(sorted((str(a).strip(), str(b).strip())))
    bucket = registry.get("pairs", {}).get(f"{pair[0]}::{pair[1]}")
    return copy.deepcopy(bucket.get("summary", _summary([]))) if bucket else _summary([])
