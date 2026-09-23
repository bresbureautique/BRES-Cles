from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

import correction_dependency_guard_r142 as r142

_HIERARCHY_SCHEMA = "bres-live-critical-pair-collection-progress-hierarchy-r143-v1"
_ALLOWED_STATUS = {"A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE"}
_FINAL_ACTIONS = {
    "FINALISER_SEANCE",
    "VERIFIER_SEANCE",
    "FINALISER_DOSSIER_CLE",
    "VERIFIER_DOSSIER_CLE",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sort_key(item: Dict[str, Any]) -> Tuple[int, int, str]:
    return (
        int(item.get("phase_rank") or 999),
        int(item.get("sequence") or 0),
        _text(item.get("work_item_id")),
    )


def _policy_guard(work_queue: Dict[str, Any]) -> None:
    expected = {
        "schema": "bres-live-critical-pair-collection-correction-work-queue-r140-v1",
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "ordering_is_documentary_only": True,
        "queue_is_resumable_by_work_item_id": True,
        "completion_requires_real_correction": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_priority": False,
        "recognition_score_used_for_priority": False,
        "decision_authority": "NONE",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
    for key, expected_value in expected.items():
        if work_queue.get(key) != expected_value:
            raise ValueError(f"r143_queue_policy_escalation:{key}")


def _state_counts(items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(_text(item.get("status")).upper() for item in items)
    return {status: int(counts.get(status, 0)) for status in ("A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE")}


def _progress_state(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "VIDE"
    statuses = [_text(item.get("status")).upper() for item in items]
    if all(status == "REALISEE" for status in statuses):
        return "PRET"
    if "BLOQUEE" in statuses:
        return "BLOQUE"
    if "A_REFAIRE" in statuses:
        return "A_REFAIRE"
    if "REALISEE" in statuses:
        return "EN_COURS"
    return "A_FAIRE"


def _node_summary(items: List[Dict[str, Any]], executable_ids: set[str]) -> Dict[str, Any]:
    ordered = sorted(items, key=_sort_key)
    next_item = next((item for item in ordered if item.get("work_item_id") in executable_ids), None)
    counts = _state_counts(ordered)
    return {
        "work_item_count": len(ordered),
        "status_counts": counts,
        "progress_state": _progress_state(ordered),
        "ready": bool(ordered) and counts["REALISEE"] == len(ordered),
        "blocked": counts["BLOQUEE"] > 0,
        "next_executable_action": None if next_item is None else {
            "work_item_id": next_item.get("work_item_id"),
            "action": next_item.get("action"),
            "instruction": next_item.get("instruction"),
            "phase": next_item.get("phase"),
            "phase_rank": next_item.get("phase_rank"),
            "scope": next_item.get("scope"),
            "session_slot": next_item.get("session_slot"),
            "face": next_item.get("face"),
            "status": next_item.get("status"),
        },
    }


def _scope_items(items: Iterable[Dict[str, Any]], *, pair_key: str, key_slot: Optional[str] = None,
                 session_slot: Optional[str] = None, face: Optional[str] = None) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in items:
        if _text(item.get("pair_key")) != pair_key:
            continue
        if key_slot is not None and _text(item.get("workspace_key_slot_id")) != key_slot:
            continue
        if session_slot is not None and _text(item.get("session_slot")) != session_slot:
            continue
        if face is not None and _text(item.get("face")).upper() != face.upper():
            continue
        result.append(item)
    return result


def _executable_ids(reconciled_items: List[Dict[str, Any]], dependency_report: Dict[str, Any]) -> set[str]:
    dependency_ready = {
        row["work_item_id"]: bool(row.get("dependency_ready"))
        for row in dependency_report.get("items", [])
    }
    executable: set[str] = set()
    for item in reconciled_items:
        status = _text(item.get("status")).upper()
        if status not in {"A_FAIRE", "A_REFAIRE"}:
            continue
        action = _text(item.get("action")).upper()
        if action in _FINAL_ACTIONS and not dependency_ready.get(item.get("work_item_id"), False):
            continue
        # An issue must still be active before documentary work is presented as actionable.
        # Final actions may become actionable because their dependency chain is ready even
        # when their own issue flag is represented indirectly by R139/R141.
        if item.get("issue_active") is False and action not in _FINAL_ACTIONS:
            continue
        executable.add(item["work_item_id"])
    return executable


def build_progress_hierarchy(state: Dict[str, Any], work_queue: Dict[str, Any], current_correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Build a read-only pair -> key -> session -> face progress view.

    R143 does not create or complete work. It reconciles R141/R142 state, projects
    it into a deterministic hierarchy, and points to the next documentary action
    that is actually executable under the existing R142 dependency guard.
    """
    _policy_guard(work_queue)
    reconciled = r142.reconcile_dependency_state(state, work_queue, current_correction_sheet)
    items = reconciled.get("items", [])
    if len(items) != int(work_queue.get("work_item_count") or -1):
        raise ValueError("r143_state_queue_count_mismatch")
    if any(_text(item.get("status")).upper() not in _ALLOWED_STATUS for item in items):
        raise ValueError("r143_invalid_status")

    queue_by_id = {item["work_item_id"]: item for item in work_queue["items"]}
    if set(queue_by_id) != {item.get("work_item_id") for item in items}:
        raise ValueError("r143_work_item_id_set_mismatch")

    # Merge immutable R140 ordering/instruction fields with current R141/R142 status.
    merged_items: List[Dict[str, Any]] = []
    state_by_id = {item["work_item_id"]: item for item in items}
    for source in work_queue["items"]:
        tracked = state_by_id[source["work_item_id"]]
        merged = dict(source)
        merged.update({
            "status": tracked.get("status"),
            "issue_active": tracked.get("issue_active"),
            "completion_verified_against_current_sheet": tracked.get("completion_verified_against_current_sheet"),
        })
        merged_items.append(merged)

    dependency_report = r142.build_dependency_report(reconciled, work_queue, current_correction_sheet)
    executable_ids = _executable_ids(merged_items, dependency_report)

    pair_order = [entry["pair_key"] for entry in work_queue.get("pair_summary", [])]
    if len(pair_order) != 17 or len(set(pair_order)) != 17:
        raise ValueError("r143_critical_pair_order_invalid")

    pairs: List[Dict[str, Any]] = []
    key_count = session_count = face_count = 0
    for pair_key in pair_order:
        pair_items = _scope_items(merged_items, pair_key=pair_key)
        key_slots = sorted({_text(i.get("workspace_key_slot_id")) for i in pair_items if _text(i.get("workspace_key_slot_id"))})
        keys: List[Dict[str, Any]] = []
        for key_slot in key_slots:
            key_items = _scope_items(merged_items, pair_key=pair_key, key_slot=key_slot)
            sessions: List[Dict[str, Any]] = []
            session_slots = [slot for slot in ("S1", "S2", "S3") if any(_text(i.get("session_slot")) == slot for i in key_items)]
            for session_slot in session_slots:
                session_items = _scope_items(merged_items, pair_key=pair_key, key_slot=key_slot, session_slot=session_slot)
                faces: List[Dict[str, Any]] = []
                for face in ("RECTO", "VERSO"):
                    face_items = _scope_items(merged_items, pair_key=pair_key, key_slot=key_slot, session_slot=session_slot, face=face)
                    if face_items:
                        face_summary = _node_summary(face_items, executable_ids)
                        face_summary.update({"face": face})
                        faces.append(face_summary)
                        face_count += 1
                session_summary = _node_summary(session_items, executable_ids)
                session_summary.update({"session_slot": session_slot, "faces": faces})
                sessions.append(session_summary)
                session_count += 1
            key_summary = _node_summary(key_items, executable_ids)
            key_summary.update({"workspace_key_slot_id": key_slot, "sessions": sessions})
            keys.append(key_summary)
            key_count += 1
        pair_summary = _node_summary(pair_items, executable_ids)
        pair_summary.update({"pair_key": pair_key, "keys": keys})
        pairs.append(pair_summary)

    global_summary = _node_summary(merged_items, executable_ids)
    return {
        "schema": _HIERARCHY_SCHEMA,
        "source_state_schema": reconciled.get("schema"),
        "source_queue_schema": work_queue.get("schema"),
        "source_dependency_schema": dependency_report.get("schema"),
        "active_test_runtime": "V2.28 TEST R116",
        "stable_version": "V2.27",
        "critical_pair_count": len(pairs),
        "key_slot_count": key_count,
        "session_slot_count": session_count,
        "face_slot_count": face_count,
        "tracked_work_item_count": len(merged_items),
        "global_progress": global_summary,
        "pairs": pairs,
        "hierarchy_is_read_only": True,
        "next_action_uses_r140_order_and_r142_dependencies": True,
        "progress_is_documentary_only": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_progress": False,
        "recognition_score_used_for_progress": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
