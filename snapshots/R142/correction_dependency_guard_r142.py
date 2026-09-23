from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List

import correction_state_tracker_r141 as r141

_DEPENDENCY_SCHEMA = "bres-live-critical-pair-collection-correction-dependency-r142-v1"
_FINAL_ACTIONS = {
    "FINALISER_SEANCE",
    "VERIFIER_SEANCE",
    "FINALISER_DOSSIER_CLE",
    "VERIFIER_DOSSIER_CLE",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _same_key(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (
        _text(a.get("pair_key")) == _text(b.get("pair_key"))
        and _text(a.get("workspace_key_slot_id")) == _text(b.get("workspace_key_slot_id"))
    )


def _dependency_ids_for_item(item: Dict[str, Any], queue_items: Iterable[Dict[str, Any]]) -> List[str]:
    action = _text(item.get("action")).upper()
    if action not in _FINAL_ACTIONS:
        return []
    phase_rank = int(item.get("phase_rank") or 999)
    session_slot = _text(item.get("session_slot"))
    deps: List[Dict[str, Any]] = []
    for candidate in queue_items:
        if candidate.get("work_item_id") == item.get("work_item_id") or not _same_key(item, candidate):
            continue
        candidate_rank = int(candidate.get("phase_rank") or 999)
        if candidate_rank >= phase_rank:
            continue
        if action in {"FINALISER_SEANCE", "VERIFIER_SEANCE"}:
            candidate_scope = _text(candidate.get("scope")).upper()
            candidate_session = _text(candidate.get("session_slot"))
            # Key identity is a prerequisite of each session. Session/face work
            # must belong to the session being finalized or verified.
            if candidate_scope == "KEY":
                deps.append(candidate)
            elif candidate_session == session_slot:
                deps.append(candidate)
        else:
            # A key folder depends on all lower-phase work for that key,
            # including the three sessions and their faces.
            deps.append(candidate)
    deps.sort(key=lambda x: (int(x.get("phase_rank") or 999), int(x.get("sequence") or 0), _text(x.get("work_item_id"))))
    return [_text(dep.get("work_item_id")) for dep in deps]


def build_dependency_report(state: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Build a documentary dependency report after R141 issue reconciliation.

    This report only determines whether finalisation/verification work may be
    *documentarily* completed. It cannot grant evidence, score a key, choose a
    catalogue candidate, or mutate the runtime/catalogue.
    """
    reconciled = r141.reconcile_tracking_state(state, work_queue, current_correction_sheet)
    queue_items = work_queue["items"]
    state_by_id = {item["work_item_id"]: item for item in reconciled["items"]}
    final_rows: List[Dict[str, Any]] = []
    for source_item in queue_items:
        action = _text(source_item.get("action")).upper()
        if action not in _FINAL_ACTIONS:
            continue
        dep_ids = _dependency_ids_for_item(source_item, queue_items)
        blockers = []
        for dep_id in dep_ids:
            dep_state = state_by_id[dep_id]
            if dep_state.get("status") != "REALISEE":
                blockers.append({
                    "work_item_id": dep_id,
                    "status": dep_state.get("status"),
                    "action": dep_state.get("action"),
                    "scope": dep_state.get("scope"),
                    "session_slot": dep_state.get("session_slot"),
                    "face": dep_state.get("face"),
                    "issue_active": dep_state.get("issue_active"),
                })
        row_state = state_by_id[source_item["work_item_id"]]
        final_rows.append({
            "work_item_id": source_item["work_item_id"],
            "action": action,
            "pair_key": source_item.get("pair_key"),
            "workspace_key_slot_id": source_item.get("workspace_key_slot_id"),
            "session_slot": source_item.get("session_slot"),
            "status": row_state.get("status"),
            "issue_active": row_state.get("issue_active"),
            "dependency_count": len(dep_ids),
            "active_dependency_count": len(blockers),
            "dependency_ready": len(blockers) == 0,
            "blocking_dependencies": blockers,
        })
    return {
        "schema": _DEPENDENCY_SCHEMA,
        "source_state_schema": reconciled.get("schema"),
        "source_queue_schema": work_queue.get("schema"),
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "finalisation_or_verification_item_count": len(final_rows),
        "dependency_ready_count": sum(1 for row in final_rows if row["dependency_ready"]),
        "dependency_blocked_count": sum(1 for row in final_rows if not row["dependency_ready"]),
        "items": final_rows,
        "dependency_order_is_documentary_only": True,
        "finalisation_requires_all_dependencies_realisee": True,
        "dependency_regression_reopens_completed_parent": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_dependency": False,
        "recognition_score_used_for_dependency": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }


def _append_dependency_reopen_event(result: Dict[str, Any], item: Dict[str, Any], blocker_ids: List[str]) -> None:
    sequence = int(result["next_event_sequence"])
    result["history"].append({
        "event_id": f"R141-EVENT-{sequence:06d}",
        "event_sequence": sequence,
        "work_item_id": item["work_item_id"],
        "previous_status": "REALISEE",
        "new_status": "A_REFAIRE",
        "event_type": "REOUVERTURE_AUTOMATIQUE_DEPENDANCE_ACTIVE_R142",
        "note": "DEPENDANCES_ACTIVES:" + ",".join(blocker_ids),
        "issue_active_after_event": item.get("issue_active"),
        "evidence_credit_granted": False,
    })
    result["next_event_sequence"] = sequence + 1


def reconcile_dependency_state(state: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Reconcile R141 issues, then reopen completed parents whose dependency regressed."""
    result = r141.reconcile_tracking_state(state, work_queue, current_correction_sheet)
    queue_by_id = {item["work_item_id"]: item for item in work_queue["items"]}
    state_by_id = {item["work_item_id"]: item for item in result["items"]}
    finals = [item for item in work_queue["items"] if _text(item.get("action")).upper() in _FINAL_ACTIONS]
    finals.sort(key=lambda x: (int(x.get("phase_rank") or 999), int(x.get("sequence") or 0)))
    for source_item in finals:
        tracked = state_by_id[source_item["work_item_id"]]
        if tracked.get("status") != "REALISEE":
            continue
        blocker_ids = [
            dep_id for dep_id in _dependency_ids_for_item(source_item, work_queue["items"])
            if state_by_id[dep_id].get("status") != "REALISEE"
        ]
        if blocker_ids:
            tracked["status"] = "A_REFAIRE"
            tracked["completion_verified_against_current_sheet"] = False
            tracked["status_change_count"] = int(tracked.get("status_change_count") or 0) + 1
            _append_dependency_reopen_event(result, tracked, blocker_ids)
    # Reuse R141's summary logic. It is intentionally private but belongs to the
    # same immutable audit layer and avoids divergent status accounting.
    return r141._refresh_summary(result)


def apply_dependency_guarded_status_updates(
    state: Dict[str, Any],
    work_queue: Dict[str, Any],
    current_correction_sheet: Dict[str, Any],
    updates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply an externally atomic update batch with R142 dependency guards.

    Updates are processed in R140 phase/sequence order on a copy. A parent may
    become REALISEE in the same batch as its dependencies, but never before all
    its prerequisite work is itself REALISEE and issue-resolved.
    """
    if not isinstance(updates, list):
        raise ValueError("r142_updates_must_be_list")
    ids = [_text(update.get("work_item_id")) for update in updates if isinstance(update, dict)]
    if len(ids) != len(updates) or any(not value for value in ids):
        raise ValueError("r142_update_work_item_id_missing")
    if len(set(ids)) != len(ids):
        raise ValueError("r142_duplicate_update_in_batch")
    queue_by_id = {item["work_item_id"]: item for item in work_queue.get("items", [])}
    if any(item_id not in queue_by_id for item_id in ids):
        missing = next(item_id for item_id in ids if item_id not in queue_by_id)
        raise ValueError(f"r142_unknown_work_item_id:{missing}")

    ordered = sorted(
        [copy.deepcopy(update) for update in updates],
        key=lambda update: (
            int(queue_by_id[update["work_item_id"]].get("phase_rank") or 999),
            int(queue_by_id[update["work_item_id"]].get("sequence") or 0),
        ),
    )
    working = reconcile_dependency_state(state, work_queue, current_correction_sheet)
    for update in ordered:
        item_id = update["work_item_id"]
        target = _text(update.get("status")).upper()
        source_item = queue_by_id[item_id]
        if target == "REALISEE" and _text(source_item.get("action")).upper() in _FINAL_ACTIONS:
            tracked_by_id = {item["work_item_id"]: item for item in working["items"]}
            blocker_ids = [
                dep_id for dep_id in _dependency_ids_for_item(source_item, work_queue["items"])
                if tracked_by_id[dep_id].get("status") != "REALISEE"
            ]
            if blocker_ids:
                raise ValueError(f"r142_dependencies_not_completed:{item_id}:{','.join(blocker_ids)}")
        working = r141.apply_status_updates(working, work_queue, current_correction_sheet, [update])
    return reconcile_dependency_state(working, work_queue, current_correction_sheet)
