from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List

import correction_state_tracker_r141 as r141
import correction_dependency_guard_r142 as r142
import progress_hierarchy_r143 as r143

_CHECKPOINT_SCHEMA = "bres-live-critical-pair-collection-checkpoint-r144-v1"
_ALLOWED_STATUS = {"A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _payload_without_self_hash(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    payload = copy.deepcopy(checkpoint)
    payload.pop("checkpoint_payload_sha256", None)
    return payload


def _policy_guard(checkpoint: Dict[str, Any]) -> None:
    expected = {
        "active_test_runtime": "V2.28 TEST R116",
        "stable_version": "V2.27",
        "critical_pair_count": 17,
        "work_item_ids_preserved_from_r140": True,
        "checkpoint_is_documentary_only": True,
        "resume_requires_same_r140_queue": True,
        "resume_requires_same_r139_correction_sheet": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_checkpoint": False,
        "recognition_score_used_for_checkpoint": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
    for key, expected_value in expected.items():
        if checkpoint.get(key) != expected_value:
            raise ValueError(f"r144_checkpoint_policy_escalation:{key}")


def export_checkpoint(state: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Export a compact, integrity-protected checkpoint of documentary collection state.

    Immutable R140 item content is not duplicated. Only mutable R141/R142 state,
    history, provenance hashes, and read-only R143 resume pointers are persisted.
    The export grants no physical evidence and cannot mutate the runtime/catalogue.
    """
    # R141 guards the immutable queue and R139 correction sheet; R142 additionally
    # normalizes any dependency-driven reopen before the snapshot is taken.
    reconciled = r142.reconcile_dependency_state(state, work_queue, current_correction_sheet)
    dependency = r142.build_dependency_report(reconciled, work_queue, current_correction_sheet)
    hierarchy = r143.build_progress_hierarchy(reconciled, work_queue, current_correction_sheet)

    queue_ids = [item["work_item_id"] for item in work_queue["items"]]
    by_id = {item["work_item_id"]: item for item in reconciled["items"]}
    if set(queue_ids) != set(by_id):
        raise ValueError("r144_work_item_id_set_mismatch")

    mutable_items: List[Dict[str, Any]] = []
    for item_id in queue_ids:
        item = by_id[item_id]
        mutable_items.append({
            "work_item_id": item_id,
            "status": item.get("status"),
            "block_reason": item.get("block_reason"),
            "status_change_count": int(item.get("status_change_count") or 0),
        })

    next_action = hierarchy.get("global_progress", {}).get("next_executable_action")
    checkpoint: Dict[str, Any] = {
        "schema": _CHECKPOINT_SCHEMA,
        "milestone": "BRES Cles catalogue audit R144",
        "source_state_schema": reconciled.get("schema"),
        "source_queue_schema": work_queue.get("schema"),
        "source_correction_sheet_schema": current_correction_sheet.get("schema"),
        "source_dependency_schema": dependency.get("schema"),
        "source_hierarchy_schema": hierarchy.get("schema"),
        "source_queue_sha256": _canonical_sha256(work_queue),
        "source_correction_sheet_sha256": _canonical_sha256(current_correction_sheet),
        "reconstructed_state_sha256": _canonical_sha256(reconciled),
        "dependency_snapshot_sha256": _canonical_sha256(dependency),
        "hierarchy_snapshot_sha256": _canonical_sha256(hierarchy),
        "active_test_runtime": "V2.28 TEST R116",
        "stable_version": "V2.27",
        "critical_pair_count": 17,
        "work_item_count": len(mutable_items),
        "mutable_items": mutable_items,
        "history": copy.deepcopy(reconciled.get("history", [])),
        "next_event_sequence": int(reconciled.get("next_event_sequence") or 1),
        "status_counts": copy.deepcopy(reconciled.get("status_counts", {})),
        "completed_item_count": int(reconciled.get("completed_item_count") or 0),
        "redo_item_count": int(reconciled.get("redo_item_count") or 0),
        "blocked_item_count": int(reconciled.get("blocked_item_count") or 0),
        "active_issue_count": int(reconciled.get("active_issue_count") or 0),
        "resolved_issue_count": int(reconciled.get("resolved_issue_count") or 0),
        "global_progress_state": hierarchy.get("global_progress", {}).get("progress_state"),
        "global_next_executable_work_item_id": None if next_action is None else next_action.get("work_item_id"),
        "finalisation_or_verification_item_count": dependency.get("finalisation_or_verification_item_count"),
        "dependency_ready_count": dependency.get("dependency_ready_count"),
        "dependency_blocked_count": dependency.get("dependency_blocked_count"),
        "work_item_ids_preserved_from_r140": True,
        "checkpoint_is_documentary_only": True,
        "resume_requires_same_r140_queue": True,
        "resume_requires_same_r139_correction_sheet": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_checkpoint": False,
        "recognition_score_used_for_checkpoint": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
    checkpoint["checkpoint_payload_sha256"] = _canonical_sha256(_payload_without_self_hash(checkpoint))
    return checkpoint


def import_checkpoint(checkpoint: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild the exact reconciled R141/R142 state and R143 projections.

    Exact resume is intentionally refused if the immutable queue or current R139
    correction sheet differs from the one used for export. A caller can import an
    exact checkpoint first, then explicitly reconcile against newer data later.
    """
    if not isinstance(checkpoint, dict) or checkpoint.get("schema") != _CHECKPOINT_SCHEMA:
        raise ValueError("r144_checkpoint_schema_invalid")
    _policy_guard(checkpoint)

    stored_payload_hash = _text(checkpoint.get("checkpoint_payload_sha256")).lower()
    if len(stored_payload_hash) != 64 or stored_payload_hash != _canonical_sha256(_payload_without_self_hash(checkpoint)):
        raise ValueError("r144_checkpoint_payload_hash_mismatch")

    expected_queue_sha = _canonical_sha256(work_queue)
    if checkpoint.get("source_queue_sha256") != expected_queue_sha:
        raise ValueError("r144_source_queue_drift")
    expected_sheet_sha = _canonical_sha256(current_correction_sheet)
    if checkpoint.get("source_correction_sheet_sha256") != expected_sheet_sha:
        raise ValueError("r144_source_correction_sheet_drift")

    mutable_items = checkpoint.get("mutable_items")
    if not isinstance(mutable_items, list) or checkpoint.get("work_item_count") != len(mutable_items):
        raise ValueError("r144_mutable_item_count_invalid")
    queue_ids = [item["work_item_id"] for item in work_queue.get("items", [])]
    checkpoint_ids = [_text(item.get("work_item_id")) for item in mutable_items if isinstance(item, dict)]
    if len(checkpoint_ids) != len(mutable_items) or any(not value for value in checkpoint_ids):
        raise ValueError("r144_work_item_id_missing")
    if len(set(checkpoint_ids)) != len(checkpoint_ids):
        raise ValueError("r144_duplicate_work_item_id")
    if checkpoint_ids != queue_ids:
        raise ValueError("r144_work_item_order_or_set_mismatch")

    base = r141.create_tracking_state(work_queue, current_correction_sheet)
    base_by_id = {item["work_item_id"]: item for item in base["items"]}
    for compact in mutable_items:
        item_id = compact["work_item_id"]
        status = _text(compact.get("status")).upper()
        if status not in _ALLOWED_STATUS:
            raise ValueError(f"r144_invalid_status:{item_id}")
        block_reason = _text(compact.get("block_reason"))
        if status == "BLOQUEE" and not block_reason:
            raise ValueError(f"r144_block_reason_missing:{item_id}")
        if status != "BLOQUEE" and block_reason:
            raise ValueError(f"r144_stale_block_reason:{item_id}")
        try:
            status_change_count = int(compact.get("status_change_count"))
        except (TypeError, ValueError):
            raise ValueError(f"r144_status_change_count_invalid:{item_id}")
        if status_change_count < 0:
            raise ValueError(f"r144_status_change_count_invalid:{item_id}")
        target = base_by_id[item_id]
        target["status"] = status
        target["block_reason"] = block_reason if status == "BLOQUEE" else None
        target["status_change_count"] = status_change_count
        target["completion_verified_against_current_sheet"] = status == "REALISEE" and not target["issue_active"]

    history = checkpoint.get("history")
    if not isinstance(history, list):
        raise ValueError("r144_history_invalid")
    known_ids = set(queue_ids)
    for event in history:
        if not isinstance(event, dict) or _text(event.get("work_item_id")) not in known_ids:
            raise ValueError("r144_history_unknown_work_item_id")
        if event.get("evidence_credit_granted") is not False:
            raise ValueError("r144_history_evidence_escalation")
    base["history"] = copy.deepcopy(history)
    base["next_event_sequence"] = int(checkpoint.get("next_event_sequence") or 0)
    base = r141._refresh_summary(base)
    r141._state_guard(base, work_queue)

    reconciled = r142.reconcile_dependency_state(base, work_queue, current_correction_sheet)
    state_sha = _canonical_sha256(reconciled)
    if state_sha != checkpoint.get("reconstructed_state_sha256"):
        raise ValueError("r144_reconstructed_state_mismatch")

    dependency = r142.build_dependency_report(reconciled, work_queue, current_correction_sheet)
    hierarchy = r143.build_progress_hierarchy(reconciled, work_queue, current_correction_sheet)
    if _canonical_sha256(dependency) != checkpoint.get("dependency_snapshot_sha256"):
        raise ValueError("r144_dependency_snapshot_mismatch")
    if _canonical_sha256(hierarchy) != checkpoint.get("hierarchy_snapshot_sha256"):
        raise ValueError("r144_hierarchy_snapshot_mismatch")

    next_action = hierarchy.get("global_progress", {}).get("next_executable_action")
    next_id = None if next_action is None else next_action.get("work_item_id")
    if next_id != checkpoint.get("global_next_executable_work_item_id"):
        raise ValueError("r144_next_action_mismatch")

    return {
        "schema": "bres-live-critical-pair-collection-checkpoint-import-r144-v1",
        "state": reconciled,
        "dependency_report": dependency,
        "progress_hierarchy": hierarchy,
        "checkpoint_payload_sha256": stored_payload_hash,
        "exact_state_reconstructed": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "decision_authority": "NONE",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
