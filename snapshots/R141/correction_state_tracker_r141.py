from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, Iterable, List, Tuple

_QUEUE_SCHEMA = "bres-live-critical-pair-collection-correction-work-queue-r140-v1"
_CORRECTION_SCHEMA = "bres-live-critical-pair-collection-correction-sheet-r139-v1"
_STATE_SCHEMA = "bres-live-critical-pair-collection-correction-state-r141-v1"
_ALLOWED_STATUS = {"A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE"}
_ALLOWED_TRANSITIONS = {
    "A_FAIRE": {"REALISEE", "BLOQUEE"},
    "BLOQUEE": {"A_FAIRE", "REALISEE"},
    "REALISEE": {"A_REFAIRE"},
    "A_REFAIRE": {"A_FAIRE", "REALISEE", "BLOQUEE"},
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _issue_tuple_from_item(item: Dict[str, Any]) -> Tuple[str, str, str, str, str, str, str]:
    return (
        _text(item.get("pair_key")),
        _text(item.get("workspace_key_slot_id")),
        _text(item.get("session_slot")),
        _text(item.get("face")).upper(),
        _text(item.get("scope")).upper(),
        _text(item.get("action")).upper(),
        _text(item.get("reason")),
    )


def _issue_key(issue: Tuple[str, str, str, str, str, str, str]) -> str:
    return "|".join(issue)


def _queue_policy_guard(queue: Dict[str, Any]) -> None:
    if queue.get("schema") != _QUEUE_SCHEMA:
        raise ValueError("r140_queue_schema_invalid")
    expected = {
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "ordering_is_documentary_only": True,
        "queue_is_resumable_by_work_item_id": True,
        "completion_requires_real_correction": True,
        "queue_completion_counts_as_real_physical_evidence": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_priority": False,
        "recognition_score_used_for_priority": False,
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
        if queue.get(key) != expected_value:
            raise ValueError(f"r140_queue_policy_escalation:{key}")

    items = queue.get("items")
    if not isinstance(items, list) or queue.get("work_item_count") != len(items):
        raise ValueError("r140_queue_item_count_invalid")
    ids = [_text(item.get("work_item_id")) for item in items]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("r140_queue_work_item_id_duplicate_or_missing")
    issues = [_issue_key(_issue_tuple_from_item(item)) for item in items]
    if len(set(issues)) != len(issues):
        raise ValueError("r140_queue_duplicate_semantic_action")
    if any(item.get("completion_requires_real_correction") is not True for item in items):
        raise ValueError("r140_queue_completion_guard_missing")
    if any(item.get("completion_grants_evidence_credit") is not False for item in items):
        raise ValueError("r140_queue_evidence_escalation")


def _correction_policy_guard(sheet: Dict[str, Any]) -> None:
    if sheet.get("schema") != _CORRECTION_SCHEMA:
        raise ValueError("r139_correction_schema_invalid")
    expected = {
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurements_used_for_correction": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
    }
    for key, expected_value in expected.items():
        if sheet.get(key) != expected_value:
            raise ValueError(f"r139_correction_policy_escalation:{key}")
    pair_sheets = sheet.get("pair_sheets")
    if not isinstance(pair_sheets, list) or len(pair_sheets) != 17:
        raise ValueError("critical_pair_count_invalid")


def _iter_correction_issues(sheet: Dict[str, Any]) -> Iterable[Tuple[str, str, str, str, str, str, str]]:
    for pair in sheet.get("pair_sheets", []):
        pair_key = _text(pair.get("pair_key"))
        for key in pair.get("keys", []):
            key_slot = _text(key.get("workspace_key_slot_id"))
            for action in key.get("actions", []):
                yield (
                    pair_key, key_slot, "", "", "KEY",
                    _text(action.get("action")).upper(), _text(action.get("reason")),
                )
            for session in key.get("sessions", []):
                session_slot = _text(session.get("session_slot"))
                for action in session.get("actions", []):
                    yield (
                        pair_key, key_slot, session_slot, "", "SESSION",
                        _text(action.get("action")).upper(), _text(action.get("reason")),
                    )
                for face in session.get("faces", []):
                    face_label = _text(face.get("face")).upper()
                    for action in face.get("actions", []):
                        yield (
                            pair_key, key_slot, session_slot, face_label, "FACE",
                            _text(action.get("action")).upper(), _text(action.get("reason")),
                        )


def _active_issue_keys(sheet: Dict[str, Any]) -> set[str]:
    _correction_policy_guard(sheet)
    issues = [_issue_key(issue) for issue in _iter_correction_issues(sheet)]
    if len(set(issues)) != len(issues):
        raise ValueError("r139_duplicate_semantic_action")
    return set(issues)


def _source_projection(item: Dict[str, Any]) -> Dict[str, Any]:
    fields = [
        "work_item_id", "sequence", "pair_key", "workspace_key_slot_id", "physical_key_id",
        "session_slot", "face", "capture_id", "scope", "reason", "action", "instruction",
        "phase_rank", "phase", "completion_requires_real_correction",
        "completion_grants_evidence_credit",
    ]
    return {field: copy.deepcopy(item.get(field)) for field in fields}


def _status_counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {status: 0 for status in sorted(_ALLOWED_STATUS)}
    for item in items:
        counts[item["status"]] += 1
    return counts


def _refresh_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    items = state["items"]
    state["status_counts"] = _status_counts(items)
    state["active_issue_count"] = sum(1 for item in items if item["issue_active"])
    state["resolved_issue_count"] = sum(1 for item in items if not item["issue_active"])
    state["resolved_pending_completion_count"] = sum(
        1 for item in items if not item["issue_active"] and item["status"] != "REALISEE"
    )
    state["completed_item_count"] = sum(1 for item in items if item["status"] == "REALISEE")
    state["redo_item_count"] = sum(1 for item in items if item["status"] == "A_REFAIRE")
    state["blocked_item_count"] = sum(1 for item in items if item["status"] == "BLOQUEE")
    state["all_completed_items_are_resolved"] = all(
        (item["status"] != "REALISEE") or (not item["issue_active"]) for item in items
    )
    state["completion_counts_as_real_physical_evidence"] = False
    state["counts_as_real_physical_evidence"] = False
    state["evidence_credit"] = 0
    return state


def create_tracking_state(work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Create an R141 tracking state from the immutable R140 work queue.

    R140 work_item_id values are preserved verbatim. Completion is never inferred
    from a status request alone: the corresponding R139 issue must be absent from
    the current correction sheet before an item may become REALISEE.
    """
    _queue_policy_guard(work_queue)
    active = _active_issue_keys(current_correction_sheet)
    source_queue_sha = _canonical_sha256(work_queue)
    items: List[Dict[str, Any]] = []
    for source_item in work_queue["items"]:
        issue = _issue_key(_issue_tuple_from_item(source_item))
        projection = _source_projection(source_item)
        items.append({
            **projection,
            "issue_key": issue,
            "source_item_sha256": _canonical_sha256(projection),
            "status": "A_FAIRE",
            "block_reason": None,
            "issue_active": issue in active,
            "issue_resolved": issue not in active,
            "completion_verified_against_current_sheet": False,
            "status_change_count": 0,
        })

    state = {
        "schema": _STATE_SCHEMA,
        "source_queue_schema": _QUEUE_SCHEMA,
        "source_queue_sha256": source_queue_sha,
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "work_item_count": len(items),
        "items": items,
        "history": [],
        "next_event_sequence": 1,
        "work_item_ids_preserved_from_r140": True,
        "completion_requires_issue_absent_from_current_r139": True,
        "automatic_reopen_to_redo_when_issue_reappears": True,
        "duplicate_updates_rejected": True,
        "invalid_state_transitions_rejected": True,
        "source_queue_drift_rejected": True,
        "source_item_provenance_hashes_verified": True,
        "measurements_used_for_state": False,
        "recognition_score_used_for_state": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
    return _refresh_summary(state)


def _state_guard(state: Dict[str, Any], work_queue: Dict[str, Any]) -> None:
    _queue_policy_guard(work_queue)
    if state.get("schema") != _STATE_SCHEMA:
        raise ValueError("r141_state_schema_invalid")
    if state.get("source_queue_schema") != _QUEUE_SCHEMA:
        raise ValueError("r141_source_queue_schema_invalid")
    if state.get("source_queue_sha256") != _canonical_sha256(work_queue):
        raise ValueError("r141_source_queue_drift")
    expected = {
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "work_item_ids_preserved_from_r140": True,
        "completion_requires_issue_absent_from_current_r139": True,
        "automatic_reopen_to_redo_when_issue_reappears": True,
        "duplicate_updates_rejected": True,
        "invalid_state_transitions_rejected": True,
        "source_queue_drift_rejected": True,
        "source_item_provenance_hashes_verified": True,
        "measurements_used_for_state": False,
        "recognition_score_used_for_state": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "completion_counts_as_real_physical_evidence": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
    }
    for key, expected_value in expected.items():
        if state.get(key) != expected_value:
            raise ValueError(f"r141_state_policy_or_guard_invalid:{key}")

    state_items = state.get("items")
    if not isinstance(state_items, list) or state.get("work_item_count") != len(state_items):
        raise ValueError("r141_state_item_count_invalid")
    queue_items = work_queue["items"]
    if len(state_items) != len(queue_items):
        raise ValueError("r141_state_queue_length_mismatch")
    state_ids = [_text(item.get("work_item_id")) for item in state_items]
    if len(set(state_ids)) != len(state_ids) or any(not item_id for item_id in state_ids):
        raise ValueError("r141_duplicate_or_missing_work_item_id")
    queue_by_id = {_text(item.get("work_item_id")): item for item in queue_items}
    if set(state_ids) != set(queue_by_id):
        raise ValueError("r141_work_item_id_set_mismatch")

    seen_issue_keys: set[str] = set()
    for state_item in state_items:
        item_id = _text(state_item.get("work_item_id"))
        source_projection = _source_projection(queue_by_id[item_id])
        if state_item.get("source_item_sha256") != _canonical_sha256(source_projection):
            raise ValueError(f"r141_source_item_provenance_mismatch:{item_id}")
        issue = _issue_key(_issue_tuple_from_item(queue_by_id[item_id]))
        if state_item.get("issue_key") != issue:
            raise ValueError(f"r141_issue_key_mismatch:{item_id}")
        if issue in seen_issue_keys:
            raise ValueError("r141_duplicate_semantic_action")
        seen_issue_keys.add(issue)
        if state_item.get("status") not in _ALLOWED_STATUS:
            raise ValueError(f"r141_invalid_persisted_status:{item_id}")
        if state_item.get("status") == "BLOQUEE" and not _text(state_item.get("block_reason")):
            raise ValueError(f"r141_block_reason_missing:{item_id}")
        if state_item.get("status") != "BLOQUEE" and state_item.get("block_reason") not in {None, ""}:
            raise ValueError(f"r141_stale_block_reason:{item_id}")

    history = state.get("history")
    if not isinstance(history, list):
        raise ValueError("r141_history_invalid")
    event_ids = [_text(event.get("event_id")) for event in history]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("r141_duplicate_history_event_id")
    if state.get("next_event_sequence") != len(history) + 1:
        raise ValueError("r141_next_event_sequence_invalid")


def _append_event(state: Dict[str, Any], item: Dict[str, Any], previous_status: str, new_status: str, event_type: str, note: str | None = None) -> None:
    sequence = int(state["next_event_sequence"])
    state["history"].append({
        "event_id": f"R141-EVENT-{sequence:06d}",
        "event_sequence": sequence,
        "work_item_id": item["work_item_id"],
        "previous_status": previous_status,
        "new_status": new_status,
        "event_type": event_type,
        "note": note or None,
        "issue_active_after_event": item["issue_active"],
        "evidence_credit_granted": False,
    })
    state["next_event_sequence"] = sequence + 1


def reconcile_tracking_state(state: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh issue presence and reopen REALISEE items when the issue reappears."""
    _state_guard(state, work_queue)
    active = _active_issue_keys(current_correction_sheet)
    result = copy.deepcopy(state)
    for item in result["items"]:
        issue_active = item["issue_key"] in active
        item["issue_active"] = issue_active
        item["issue_resolved"] = not issue_active
        if item["status"] == "REALISEE" and issue_active:
            previous = item["status"]
            item["status"] = "A_REFAIRE"
            item["completion_verified_against_current_sheet"] = False
            item["status_change_count"] += 1
            _append_event(result, item, previous, "A_REFAIRE", "REOUVERTURE_AUTOMATIQUE_ANOMALIE_REAPPARUE")
        elif item["status"] == "REALISEE":
            item["completion_verified_against_current_sheet"] = True
        else:
            item["completion_verified_against_current_sheet"] = False
    return _refresh_summary(result)


def apply_status_updates(
    state: Dict[str, Any],
    work_queue: Dict[str, Any],
    current_correction_sheet: Dict[str, Any],
    updates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply an atomic batch of explicit status changes and then reconcile.

    A work item can become REALISEE only after its semantic R139 issue is absent
    from the supplied current correction sheet. Duplicate updates, unknown IDs,
    invalid transitions and unsupported statuses are rejected atomically.
    """
    reconciled = reconcile_tracking_state(state, work_queue, current_correction_sheet)
    if not isinstance(updates, list):
        raise ValueError("r141_updates_must_be_list")
    update_ids = [_text(update.get("work_item_id")) for update in updates if isinstance(update, dict)]
    if len(update_ids) != len(updates) or any(not value for value in update_ids):
        raise ValueError("r141_update_work_item_id_missing")
    if len(set(update_ids)) != len(update_ids):
        raise ValueError("r141_duplicate_update_in_batch")

    result = copy.deepcopy(reconciled)
    by_id = {item["work_item_id"]: item for item in result["items"]}
    for update in updates:
        item_id = _text(update.get("work_item_id"))
        if item_id not in by_id:
            raise ValueError(f"r141_unknown_work_item_id:{item_id}")
        target = _text(update.get("status")).upper()
        if target not in _ALLOWED_STATUS:
            raise ValueError(f"r141_invalid_target_status:{target or 'EMPTY'}")
        item = by_id[item_id]
        current = item["status"]
        if target == current:
            raise ValueError(f"r141_redundant_status_transition:{item_id}:{current}")
        if target not in _ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"r141_invalid_status_transition:{item_id}:{current}->{target}")
        if target == "REALISEE" and item["issue_active"]:
            raise ValueError(f"r141_real_completion_requires_issue_resolved:{item_id}")
        if target == "A_REFAIRE" and not item["issue_active"]:
            raise ValueError(f"r141_redo_requires_issue_active:{item_id}")
        if target in {"A_FAIRE", "BLOQUEE"} and not item["issue_active"]:
            raise ValueError(f"r141_open_status_requires_issue_active:{item_id}:{target}")

        block_reason = _text(update.get("block_reason"))
        if target == "BLOQUEE" and not block_reason:
            raise ValueError(f"r141_block_reason_required:{item_id}")

        item["status"] = target
        item["block_reason"] = block_reason if target == "BLOQUEE" else None
        item["completion_verified_against_current_sheet"] = target == "REALISEE" and not item["issue_active"]
        item["status_change_count"] += 1
        _append_event(result, item, current, target, "MISE_A_JOUR_EXPLICITE", _text(update.get("note")) or None)

    return _refresh_summary(result)
