from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r130-v1"
_SOURCE_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"
_REPORT_SCHEMA = "bres-live-diagnostic-traceable-sufficiency-report-r131-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_SESSION_COUNT = 3
_REQUIRED_CAPTURE_COUNT = 6
_REQUIRED_KEY_COUNT_FOR_PAIR_REVIEW = 2
_REQUIRED_SIDES = {"RECTO", "VERSO"}


def _canonical_pair(a: str, b: str) -> Tuple[str, str]:
    return tuple(sorted((str(a).strip(), str(b).strip())))


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


def _entry_policy_ok(entry: Dict[str, Any]) -> bool:
    return (
        entry.get("source_schema") == _SOURCE_SCHEMA
        and entry.get("evidence_status") == "MEASURED_UNVALIDATED"
        and entry.get("decision_authority") == "NONE"
        and entry.get("policy_status") == "A_CONFIRMER"
        and entry.get("validated_reference") is None
    )


def _sha_ok(value: Any) -> bool:
    return bool(_SHA256_RE.fullmatch(str(value or "").strip().lower()))


def _entry_traceability(entry: Dict[str, Any]) -> Dict[str, Any]:
    result_id = str(entry.get("result_id", "")).strip().lower()
    physical_key_id = str(entry.get("physical_key_id", "")).strip()
    rows = entry.get("source_capture_provenance", [])
    rows = rows if isinstance(rows, list) else []

    capture_ids: List[str] = []
    source_hashes: List[str] = []
    by_session: Dict[str, List[str]] = defaultdict(list)
    record_shape_ok = True

    for row in rows:
        if not isinstance(row, dict):
            record_shape_ok = False
            continue
        sid = str(row.get("capture_session_id", "")).strip()
        side = str(row.get("side", "")).strip()
        capture_id = str(row.get("capture_id", "")).strip()
        source_hash = str(row.get("source_file_sha256", "")).strip().lower()
        if not sid or side not in _REQUIRED_SIDES or not capture_id or not _sha_ok(source_hash):
            record_shape_ok = False
        if sid:
            by_session[sid].append(side)
        if capture_id:
            capture_ids.append(capture_id)
        if source_hash:
            source_hashes.append(source_hash)

    distinct_sessions = sorted(by_session)
    exact_dual_face_sessions = bool(distinct_sessions) and all(
        len(by_session[sid]) == 2 and set(by_session[sid]) == _REQUIRED_SIDES
        for sid in distinct_sessions
    )
    session_coverage_ok = (
        len(distinct_sessions) == _REQUIRED_SESSION_COUNT
        and exact_dual_face_sessions
    )
    capture_record_count_ok = len(rows) == _REQUIRED_CAPTURE_COUNT
    capture_ids_unique = (
        len(capture_ids) == _REQUIRED_CAPTURE_COUNT
        and len(set(capture_ids)) == _REQUIRED_CAPTURE_COUNT
    )
    source_hashes_unique = (
        len(source_hashes) == _REQUIRED_CAPTURE_COUNT
        and len(set(source_hashes)) == _REQUIRED_CAPTURE_COUNT
    )
    packet_digest_ok = _sha_ok(entry.get("source_packet_sha256"))
    provenance_digest_ok = _sha_ok(entry.get("provenance_digest_sha256"))
    result_id_ok = _sha_ok(result_id)

    traceability_complete = all([
        bool(physical_key_id),
        result_id_ok,
        record_shape_ok,
        capture_record_count_ok,
        session_coverage_ok,
        capture_ids_unique,
        source_hashes_unique,
        packet_digest_ok,
        provenance_digest_ok,
    ])

    return {
        "result_id": result_id or None,
        "result_id_sha256_shape_ok": result_id_ok,
        "physical_key_id_present": bool(physical_key_id),
        "source_capture_record_count": len(rows),
        "source_capture_record_count_ok": capture_record_count_ok,
        "source_capture_record_shape_ok": record_shape_ok,
        "distinct_capture_session_ids": distinct_sessions,
        "distinct_capture_session_count": len(distinct_sessions),
        "three_session_recto_verso_coverage_complete": session_coverage_ok,
        "capture_ids_unique_within_entry": capture_ids_unique,
        "source_capture_sha256_unique_within_entry": source_hashes_unique,
        "source_packet_sha256_valid": packet_digest_ok,
        "provenance_digest_sha256_valid": provenance_digest_ok,
        "source_capture_sha256_provenance_available": traceability_complete,
        "traceability_complete": traceability_complete,
        "measurement_values_used_for_status": False,
        "capture_ids": capture_ids,
        "source_capture_sha256": source_hashes,
    }


def _global_uniqueness(entry_docs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    docs = list(entry_docs)
    capture_ids = [cid for d in docs for cid in d.get("capture_ids", [])]
    hashes = [sha for d in docs for sha in d.get("source_capture_sha256", [])]
    return {
        "capture_ids_unique_across_pair_registry": len(capture_ids) == len(set(capture_ids)),
        "source_capture_sha256_unique_across_pair_registry": len(hashes) == len(set(hashes)),
        "source_capture_records": len(hashes),
        "distinct_source_capture_ids": len(set(capture_ids)),
        "distinct_source_capture_sha256": len(set(hashes)),
    }


def assess_traceable_sufficiency(registry: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    """Assess documentary readiness using R130 source provenance only.

    Numeric physical measurements are deliberately ignored. The report can only say
    whether provenance is complete enough for descriptive review; it cannot choose a
    reference, validate a candidate, define a tolerance or mutate runtime/catalogue.
    """
    _validate_registry(registry)
    pair = _canonical_pair(a, b)
    pair_key = f"{pair[0]}::{pair[1]}"
    bucket = copy.deepcopy(registry.get("pairs", {}).get(pair_key))

    report: Dict[str, Any] = {
        "schema": _REPORT_SCHEMA,
        "source_registry_schema": _REGISTRY_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "candidate_pair": {"a": pair[0], "b": pair[1]},
        "analysis_status": "DOCUMENTATION_AND_PROVENANCE_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "physical_measurement_assessment_allowed": False,
        "measurement_values_used_for_status": False,
        "source_capture_sha256_provenance_preserved_by_r130": True,
        "documentation_status": "NO_DATA",
        "per_physical_key": {},
        "pair_summary": {
            "diagnostic_entries": 0,
            "distinct_physical_keys": 0,
            "physical_key_ids": [],
            "keys_ready_for_within_key_traceable_descriptive_review": 0,
            "all_keys_ready_for_within_key_traceable_descriptive_review": False,
            "pair_traceable_descriptive_review_ready": False,
            "capture_ids_unique_across_pair_registry": True,
            "source_capture_sha256_unique_across_pair_registry": True,
            "documentation_status": "NO_DATA",
            "candidate_selection": None,
            "validated_reference": None,
            "physical_measurement_assessment": None,
            "acceptance_threshold_mm": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER"
        },
        "candidate_selection": None,
        "validated_reference": None,
        "physical_measurement_assessment": None,
        "acceptance_threshold_mm": None,
    }
    if not bucket:
        report["analysis_note"] = "NO_DIAGNOSTIC_DATA_FOR_PAIR"
        return report

    if bucket.get("decision_authority") != "NONE" or bucket.get("policy_status") != "A_CONFIRMER":
        raise ValueError("pair_bucket_policy_escalation")

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    all_docs: List[Dict[str, Any]] = []
    for entry in bucket.get("entries", []):
        if not _entry_policy_ok(entry):
            raise ValueError("entry_policy_escalation_or_invalid_source")
        key_id = str(entry.get("physical_key_id", "")).strip()
        if not key_id:
            raise ValueError("physical_key_id_missing")
        doc = _entry_traceability(entry)
        grouped[key_id].append(doc)
        all_docs.append(doc)

    global_unique = _global_uniqueness(all_docs)
    global_provenance_ok = (
        global_unique["capture_ids_unique_across_pair_registry"]
        and global_unique["source_capture_sha256_unique_across_pair_registry"]
    )

    ready_key_count = 0
    total_entries = 0
    for key_id in sorted(grouped):
        docs = grouped[key_id]
        total_entries += len(docs)
        result_ids = [d["result_id"] for d in docs if d["result_id"]]
        result_ids_unique = len(result_ids) == len(set(result_ids))
        key_ready = (
            bool(docs)
            and all(d["traceability_complete"] for d in docs)
            and result_ids_unique
            and global_provenance_ok
        )
        if key_ready:
            ready_key_count += 1
        report["per_physical_key"][key_id] = {
            "diagnostic_entries": len(docs),
            "distinct_result_ids": len(set(result_ids)),
            "result_ids_unique_within_key": result_ids_unique,
            "entry_traceability": [
                {k: v for k, v in d.items() if k not in {"capture_ids", "source_capture_sha256"}}
                for d in docs
            ],
            "source_traceability_coverage_complete": all(d["traceability_complete"] for d in docs) if docs else False,
            "global_source_capture_non_reuse_confirmed": global_provenance_ok,
            "documentation_status": (
                "READY_FOR_WITHIN_KEY_TRACEABLE_DESCRIPTIVE_REVIEW"
                if key_ready
                else "SOURCE_TRACEABILITY_INCOMPLETE"
            ),
            "candidate_selection": None,
            "validated_reference": None,
            "physical_measurement_assessment": None,
            "acceptance_threshold_mm": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        }

    ids = sorted(grouped)
    all_keys_ready = bool(ids) and ready_key_count == len(ids)
    pair_ready = (
        len(ids) >= _REQUIRED_KEY_COUNT_FOR_PAIR_REVIEW
        and all_keys_ready
        and global_provenance_ok
    )
    if pair_ready:
        status = "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW"
    elif all_keys_ready:
        status = "READY_FOR_WITHIN_KEY_TRACEABLE_DESCRIPTIVE_REVIEW"
    else:
        status = "SOURCE_TRACEABILITY_INCOMPLETE"

    report["documentation_status"] = status
    report["pair_summary"] = {
        "diagnostic_entries": total_entries,
        "distinct_physical_keys": len(ids),
        "physical_key_ids": ids,
        "keys_ready_for_within_key_traceable_descriptive_review": ready_key_count,
        "all_keys_ready_for_within_key_traceable_descriptive_review": all_keys_ready,
        "pair_traceable_descriptive_review_ready": pair_ready,
        "capture_ids_unique_across_pair_registry": global_unique["capture_ids_unique_across_pair_registry"],
        "source_capture_sha256_unique_across_pair_registry": global_unique["source_capture_sha256_unique_across_pair_registry"],
        "source_capture_records": global_unique["source_capture_records"],
        "distinct_source_capture_ids": global_unique["distinct_source_capture_ids"],
        "distinct_source_capture_sha256": global_unique["distinct_source_capture_sha256"],
        "source_capture_sha256_provenance_available": all(d["traceability_complete"] for d in all_docs) if all_docs else False,
        "measurement_values_used_for_status": False,
        "documentation_status": status,
        "candidate_selection": None,
        "validated_reference": None,
        "physical_measurement_assessment": None,
        "acceptance_threshold_mm": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }
    return report
