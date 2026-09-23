from __future__ import annotations

import copy
from typing import Any, Dict, List

_PLAN_SCHEMA = "bres-live-critical-pair-collection-plan-r135-v1"
_WORKSPACE_SCHEMA = "bres-live-critical-pair-collection-workspace-r137-v1"
_REQUIRED_SESSIONS_PER_KEY = 3
_FACES = ("RECTO", "VERSO")


def _validate_plan(plan: Dict[str, Any]) -> None:
    if plan.get("schema") != _PLAN_SCHEMA:
        raise ValueError("r135_plan_schema_invalid")
    if plan.get("active_test_runtime") != "V2.28 TEST R116":
        raise ValueError("runtime_not_r116")
    if plan.get("evidence_origin") != "REAL_PHYSICAL":
        raise ValueError("workspace_requires_real_physical_plan")
    required = {
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurements_used_for_plan": False,
        "synthetic_data_counts_as_real_physical_evidence": False,
    }
    for key, expected in required.items():
        if plan.get(key) != expected:
            raise ValueError(f"r135_plan_policy_escalation:{key}")
    rows = plan.get("collection_queue")
    if not isinstance(rows, list) or len(rows) != 17:
        raise ValueError("r135_critical_pair_count_invalid")


def build_collection_workspace(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Create empty, non-evidentiary capture workspaces from the R135 queue.

    This function allocates only *missing* physical-key slots. It never creates a
    physical key id, capture id, file path, source hash, measurement value, evidence
    credit, candidate decision, threshold, or validation. A prepared slot becomes
    usable evidence only after a separate real capture/ingestion workflow fills and
    verifies it.
    """
    _validate_plan(plan)
    source = copy.deepcopy(plan)
    workspaces: List[Dict[str, Any]] = []
    seen_pair_keys: set[str] = set()
    seen_slot_ids: set[str] = set()
    total_key_slots = total_sessions = total_face_slots = 0

    for row in source["collection_queue"]:
        if not isinstance(row, dict):
            raise ValueError("collection_queue_row_invalid")
        if row.get("decision_authority") != "NONE" or row.get("policy_status") != "A_CONFIRMER":
            raise ValueError("r135_pair_policy_escalation")
        if row.get("validated_reference") is not None or row.get("candidate_selection") is not None:
            raise ValueError("r135_pair_decision_escalation")
        if row.get("acceptance_threshold_mm") is not None or row.get("physical_measurement_assessment") is not None:
            raise ValueError("r135_pair_measurement_escalation")
        if row.get("measurements_used_for_plan") is not False:
            raise ValueError("r135_pair_measurements_used")

        pair_key = str(row.get("pair_key", "")).strip()
        if not pair_key or pair_key in seen_pair_keys:
            raise ValueError("pair_key_invalid_or_duplicate")
        seen_pair_keys.add(pair_key)
        pair = row.get("candidate_pair") or {}
        a = str(pair.get("a", "")).strip()
        b = str(pair.get("b", "")).strip()
        if not a or not b or a == b:
            raise ValueError("candidate_pair_invalid")

        missing_keys = int(row.get("missing_independent_physical_keys", 0) or 0)
        missing_sessions = int(row.get("missing_documented_sessions", 0) or 0)
        if missing_keys < 0 or missing_sessions < 0:
            raise ValueError("negative_missing_collection_count")
        if missing_sessions != missing_keys * _REQUIRED_SESSIONS_PER_KEY:
            raise ValueError("missing_session_count_inconsistent")

        key_slots: List[Dict[str, Any]] = []
        safe_pair = pair_key.replace("::", "__")
        for key_index in range(1, missing_keys + 1):
            slot_id = f"{safe_pair}__KEY_SLOT_{key_index:02d}"
            if slot_id in seen_slot_ids:
                raise ValueError("workspace_slot_id_duplicate")
            seen_slot_ids.add(slot_id)
            sessions = []
            for session_index in range(1, _REQUIRED_SESSIONS_PER_KEY + 1):
                session_id = f"S{session_index}"
                faces = []
                for face in _FACES:
                    faces.append({
                        "face": face,
                        "capture_id": None,
                        "source_path": None,
                        "source_file_sha256": None,
                        "captured": False,
                        "verified": False,
                        "evidence_credit": 0,
                    })
                sessions.append({
                    "session_slot": session_id,
                    "real_session_id": None,
                    "calibration_50mm_status": None,
                    "calibration_100mm_status": None,
                    "faces": faces,
                    "session_complete": False,
                    "session_verified": False,
                    "evidence_credit": 0,
                })
            key_slots.append({
                "workspace_key_slot_id": slot_id,
                "physical_key_id": None,
                "physical_key_identity_confirmed": False,
                "sessions": sessions,
                "key_workspace_complete": False,
                "key_workspace_verified": False,
                "evidence_credit": 0,
                "counts_as_real_physical_evidence": False,
            })
            total_key_slots += 1
            total_sessions += _REQUIRED_SESSIONS_PER_KEY
            total_face_slots += _REQUIRED_SESSIONS_PER_KEY * len(_FACES)

        workspaces.append({
            "pair_key": pair_key,
            "candidate_pair": {"a": a, "b": b},
            "maker_a": row.get("maker_a"),
            "maker_b": row.get("maker_b"),
            "family_a": row.get("family_a"),
            "family_b": row.get("family_b"),
            "collection_action": row.get("collection_action"),
            "missing_independent_physical_keys_at_generation": missing_keys,
            "missing_documented_sessions_at_generation": missing_sessions,
            "prepared_key_slots": key_slots,
            "prepared_workspace_only": True,
            "workspace_counts_as_real_physical_evidence": False,
            "measurements_used_for_workspace": False,
            "candidate_selection": None,
            "validated_reference": None,
            "acceptance_threshold_mm": None,
            "physical_measurement_assessment": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        })

    if len(seen_pair_keys) != 17:
        raise ValueError("critical_pair_set_incomplete")

    return {
        "schema": _WORKSPACE_SCHEMA,
        "source_plan_schema": _PLAN_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "workspace_status": "EMPTY_CAPTURE_WORKSPACES_ONLY",
        "critical_pair_count": 17,
        "prepared_missing_key_slots": total_key_slots,
        "prepared_session_slots": total_sessions,
        "prepared_face_capture_slots": total_face_slots,
        "capture_faces": list(_FACES),
        "sessions_per_key_slot": _REQUIRED_SESSIONS_PER_KEY,
        "workspaces": workspaces,
        "workspace_counts_as_real_physical_evidence": False,
        "prepared_slots_must_not_be_counted_as_evidence": True,
        "measurements_used_for_workspace": False,
        "evidence_status": "EMPTY_PLACEHOLDER",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
