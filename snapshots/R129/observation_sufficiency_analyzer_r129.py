from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r127-v1"
_REPORT_SCHEMA = "bres-live-diagnostic-observation-sufficiency-report-r129-v1"
_SOURCE_SCHEMA = "bres-live-discriminant-diagnostic-ingestion-r126-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_SESSION_COUNT = 3
_REQUIRED_KEY_COUNT_FOR_PAIR_REVIEW = 2


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
    }
    for key, expected in fixed.items():
        if registry.get(key) != expected:
            raise ValueError(f"registry_policy_escalation:{key}")


def _entry_policy_ok(entry: Dict[str, Any]) -> bool:
    return (
        entry.get("source_schema") == _SOURCE_SCHEMA
        and entry.get("ingestion_status") == "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS"
        and entry.get("evidence_status") == "MEASURED_UNVALIDATED"
        and entry.get("decision_authority") == "NONE"
        and entry.get("policy_status") == "A_CONFIRMER"
        and entry.get("validated_reference") is None
    )


def _entry_documentation(entry: Dict[str, Any]) -> Dict[str, Any]:
    result_id = str(entry.get("result_id", "")).strip().lower()
    physical_key_id = str(entry.get("physical_key_id", "")).strip()
    records = entry.get("diagnostics", {}).get("recto_verso_geometry_signatures", [])
    records = records if isinstance(records, list) else []

    session_ids: List[str] = []
    complete_dual_face_records = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        sid = str(record.get("capture_session_id", "")).strip()
        recto = str(record.get("recto", "")).strip()
        verso = str(record.get("verso", "")).strip()
        if sid:
            session_ids.append(sid)
        if sid and recto and verso:
            complete_dual_face_records += 1

    distinct_session_ids = sorted(set(session_ids))
    result_id_shape_ok = bool(_SHA256_RE.fullmatch(result_id))
    session_coverage_ok = (
        len(distinct_session_ids) >= _REQUIRED_SESSION_COUNT
        and complete_dual_face_records >= _REQUIRED_SESSION_COUNT
    )
    registry_provenance_ok = (
        bool(physical_key_id)
        and result_id_shape_ok
        and entry.get("source_schema") == _SOURCE_SCHEMA
        and entry.get("ingestion_status") == "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS"
    )

    return {
        "result_id": result_id or None,
        "result_id_sha256_shape_ok": result_id_shape_ok,
        "physical_key_id_present": bool(physical_key_id),
        "session_record_count": len(records),
        "distinct_capture_session_ids": distinct_session_ids,
        "distinct_capture_session_count": len(distinct_session_ids),
        "complete_recto_verso_session_records": complete_dual_face_records,
        "session_coverage_ok": session_coverage_ok,
        "registry_provenance_ok": registry_provenance_ok,
        "source_capture_sha256_provenance_available": False,
        "measurement_values_used_for_status": False,
    }


def assess_observation_sufficiency(registry: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    """Assess R129 documentation coverage for a critical-pair diagnostic bucket.

    Only registry provenance structure and observation counts are used. Numeric physical
    measurements are intentionally ignored. The result can say whether the stored
    documentation is ready for descriptive review, but it cannot judge measurement
    quality, define a tolerance, choose a candidate, or validate a reference.
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
        "analysis_status": "DOCUMENTATION_ONLY",
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
        "source_capture_sha256_provenance_preserved_by_r127": False,
        "documentation_status": "NO_DATA",
        "per_physical_key": {},
        "pair_summary": {
            "diagnostic_entries": 0,
            "distinct_physical_keys": 0,
            "physical_key_ids": [],
            "keys_ready_for_within_key_descriptive_review": 0,
            "all_keys_ready_for_within_key_descriptive_review": False,
            "pair_descriptive_review_ready": False,
            "documentation_status": "NO_DATA",
            "candidate_selection": None,
            "validated_reference": None,
            "physical_measurement_assessment": None,
            "acceptance_threshold_mm": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
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
    for entry in bucket.get("entries", []):
        if not _entry_policy_ok(entry):
            raise ValueError("entry_policy_escalation_or_invalid_source")
        key_id = str(entry.get("physical_key_id", "")).strip()
        if not key_id:
            raise ValueError("physical_key_id_missing")
        grouped[key_id].append(entry)

    ready_key_count = 0
    total_entries = 0
    for key_id in sorted(grouped):
        entry_docs = [_entry_documentation(entry) for entry in grouped[key_id]]
        total_entries += len(entry_docs)
        result_ids = [row["result_id"] for row in entry_docs if row["result_id"]]
        all_entries_structurally_ready = bool(entry_docs) and all(
            row["registry_provenance_ok"] and row["session_coverage_ok"]
            for row in entry_docs
        )
        result_ids_unique = len(result_ids) == len(set(result_ids))
        key_ready = all_entries_structurally_ready and result_ids_unique
        if key_ready:
            ready_key_count += 1
        report["per_physical_key"][key_id] = {
            "diagnostic_entries": len(entry_docs),
            "distinct_result_ids": len(set(result_ids)),
            "result_ids_unique_within_key": result_ids_unique,
            "entry_documentation": entry_docs,
            "registry_provenance_coverage_complete": all(
                row["registry_provenance_ok"] for row in entry_docs
            ) if entry_docs else False,
            "three_session_coverage_complete": all(
                row["session_coverage_ok"] for row in entry_docs
            ) if entry_docs else False,
            "source_capture_sha256_provenance_available": False,
            "documentation_status": (
                "READY_FOR_WITHIN_KEY_DESCRIPTIVE_REVIEW"
                if key_ready
                else "WITHIN_KEY_DOCUMENTATION_INCOMPLETE"
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
    )
    if pair_ready:
        status = "READY_FOR_PAIR_DESCRIPTIVE_REVIEW"
    elif all_keys_ready:
        status = "READY_FOR_WITHIN_KEY_DESCRIPTIVE_REVIEW"
    else:
        status = "WITHIN_KEY_DOCUMENTATION_INCOMPLETE"

    report["documentation_status"] = status
    report["pair_summary"] = {
        "diagnostic_entries": total_entries,
        "distinct_physical_keys": len(ids),
        "physical_key_ids": ids,
        "keys_ready_for_within_key_descriptive_review": ready_key_count,
        "all_keys_ready_for_within_key_descriptive_review": all_keys_ready,
        "pair_descriptive_review_ready": pair_ready,
        "documentation_status": status,
        "source_capture_sha256_provenance_available": False,
        "measurement_values_used_for_status": False,
        "candidate_selection": None,
        "validated_reference": None,
        "physical_measurement_assessment": None,
        "acceptance_threshold_mm": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }
    return report
