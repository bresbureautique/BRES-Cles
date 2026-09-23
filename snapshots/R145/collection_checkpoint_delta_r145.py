from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Dict, List

import collection_checkpoint_r144 as r144

_DELTA_SCHEMA = "bres-live-critical-pair-collection-checkpoint-delta-r145-v1"
_ALLOWED_STATUS = {"A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _validate_checkpoint(checkpoint: Dict[str, Any], label: str) -> None:
    if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "bres-live-critical-pair-collection-checkpoint-r144-v1":
        raise ValueError(f"r145_{label}_checkpoint_schema_invalid")
    r144._policy_guard(checkpoint)
    stored = _text(checkpoint.get("checkpoint_payload_sha256")).lower()
    computed = r144._canonical_sha256(r144._payload_without_self_hash(checkpoint))
    if len(stored) != 64 or stored != computed:
        raise ValueError(f"r145_{label}_checkpoint_payload_hash_mismatch")

    items = checkpoint.get("mutable_items")
    if not isinstance(items, list) or checkpoint.get("work_item_count") != len(items):
        raise ValueError(f"r145_{label}_mutable_item_count_invalid")
    ids: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"r145_{label}_mutable_item_invalid")
        item_id = _text(item.get("work_item_id"))
        status = _text(item.get("status")).upper()
        if not item_id:
            raise ValueError(f"r145_{label}_work_item_id_missing")
        if status not in _ALLOWED_STATUS:
            raise ValueError(f"r145_{label}_invalid_status:{item_id}")
        try:
            count = int(item.get("status_change_count"))
        except (TypeError, ValueError):
            raise ValueError(f"r145_{label}_status_change_count_invalid:{item_id}")
        if count < 0:
            raise ValueError(f"r145_{label}_status_change_count_invalid:{item_id}")
        ids.append(item_id)
    if len(set(ids)) != len(ids):
        raise ValueError(f"r145_{label}_duplicate_work_item_id")

    history = checkpoint.get("history")
    if not isinstance(history, list):
        raise ValueError(f"r145_{label}_history_invalid")
    try:
        next_sequence = int(checkpoint.get("next_event_sequence"))
    except (TypeError, ValueError):
        raise ValueError(f"r145_{label}_next_event_sequence_invalid")
    if next_sequence < 1:
        raise ValueError(f"r145_{label}_next_event_sequence_invalid")


def compare_checkpoints(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two valid R144 checkpoints without mutating either one.

    The comparison is intentionally documentary. It accepts correction-sheet drift
    between sessions, but requires the exact same immutable R140 queue and exact
    work-item ordering. State counters/history must evolve monotonically.
    """
    _validate_checkpoint(before, "before")
    _validate_checkpoint(after, "after")

    if before.get("source_queue_sha256") != after.get("source_queue_sha256"):
        raise ValueError("r145_source_queue_drift")
    if before.get("work_item_count") != after.get("work_item_count"):
        raise ValueError("r145_work_item_count_drift")

    before_items = before["mutable_items"]
    after_items = after["mutable_items"]
    before_ids = [item["work_item_id"] for item in before_items]
    after_ids = [item["work_item_id"] for item in after_items]
    if before_ids != after_ids:
        raise ValueError("r145_work_item_order_or_set_drift")

    before_history = before["history"]
    after_history = after["history"]
    if len(after_history) < len(before_history) or after_history[:len(before_history)] != before_history:
        raise ValueError("r145_history_not_append_only")
    if int(after["next_event_sequence"]) < int(before["next_event_sequence"]):
        raise ValueError("r145_event_sequence_regression")

    changed: List[Dict[str, Any]] = []
    transition_counter: Counter[str] = Counter()
    status_count_delta = {
        status: int(after.get("status_counts", {}).get(status, 0)) - int(before.get("status_counts", {}).get(status, 0))
        for status in ("A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE")
    }

    for old, new in zip(before_items, after_items):
        old_count = int(old.get("status_change_count") or 0)
        new_count = int(new.get("status_change_count") or 0)
        item_id = old["work_item_id"]
        if new_count < old_count:
            raise ValueError(f"r145_status_change_count_regression:{item_id}")
        old_status = _text(old.get("status")).upper()
        new_status = _text(new.get("status")).upper()
        old_reason = _text(old.get("block_reason")) or None
        new_reason = _text(new.get("block_reason")) or None
        if old_status != new_status or old_reason != new_reason or old_count != new_count:
            transition = f"{old_status}->{new_status}"
            transition_counter[transition] += 1
            changed.append({
                "work_item_id": item_id,
                "before_status": old_status,
                "after_status": new_status,
                "before_block_reason": old_reason,
                "after_block_reason": new_reason,
                "status_change_count_before": old_count,
                "status_change_count_after": new_count,
                "status_change_count_delta": new_count - old_count,
                "transition": transition,
            })

    added_history = copy.deepcopy(after_history[len(before_history):])
    report: Dict[str, Any] = {
        "schema": _DELTA_SCHEMA,
        "milestone": "BRES Cles catalogue audit R145",
        "source_checkpoint_schema": before.get("schema"),
        "active_test_runtime": "V2.28 TEST R116",
        "stable_version": "V2.27",
        "critical_pair_count": 17,
        "tracked_work_item_count": len(before_items),
        "before_checkpoint_payload_sha256": before.get("checkpoint_payload_sha256"),
        "after_checkpoint_payload_sha256": after.get("checkpoint_payload_sha256"),
        "same_r140_queue": True,
        "correction_sheet_changed": before.get("source_correction_sheet_sha256") != after.get("source_correction_sheet_sha256"),
        "changed_work_item_count": len(changed),
        "unchanged_work_item_count": len(before_items) - len(changed),
        "changed_work_items": changed,
        "transition_counts": dict(sorted(transition_counter.items())),
        "status_count_delta": status_count_delta,
        "history_event_count_before": len(before_history),
        "history_event_count_after": len(after_history),
        "history_events_added_count": len(added_history),
        "history_events_added": added_history,
        "next_event_sequence_before": int(before["next_event_sequence"]),
        "next_event_sequence_after": int(after["next_event_sequence"]),
        "global_progress_state_before": before.get("global_progress_state"),
        "global_progress_state_after": after.get("global_progress_state"),
        "global_next_executable_work_item_id_before": before.get("global_next_executable_work_item_id"),
        "global_next_executable_work_item_id_after": after.get("global_next_executable_work_item_id"),
        "checkpoint_delta_is_documentary_only": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_delta": False,
        "recognition_score_used_for_delta": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
    report["delta_report_sha256"] = r144._canonical_sha256(report)
    return report
