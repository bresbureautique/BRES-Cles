from __future__ import annotations

from typing import Any, Dict, List

import collection_checkpoint_r144 as r144
import collection_checkpoint_delta_r145 as r145

_CHAIN_SCHEMA = "bres-live-critical-pair-collection-checkpoint-chain-r147-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _policy() -> Dict[str, Any]:
    return {
        "active_test_runtime": "V2.28 TEST R116",
        "stable_version": "V2.27",
        "critical_pair_count": 17,
        "checkpoint_chain_is_documentary_only": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_chain": False,
        "recognition_score_used_for_chain": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }


def audit_checkpoint_chain(checkpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit a chronological chain of R144 checkpoints using R145 deltas.

    The chain is read-only and documentary. It verifies continuity of the immutable
    R140 queue and append-only R141 history, then summarizes progress over time.
    """
    if not isinstance(checkpoints, list) or not checkpoints:
        raise ValueError("r147_checkpoint_chain_empty")

    for index, checkpoint in enumerate(checkpoints):
        r145._validate_checkpoint(checkpoint, f"chain_{index:03d}")

    queue_hash = checkpoints[0].get("source_queue_sha256")
    work_item_count = checkpoints[0].get("work_item_count")
    item_order = [row.get("work_item_id") for row in checkpoints[0].get("mutable_items", [])]
    if work_item_count != 1462 or len(item_order) != 1462:
        raise ValueError("r147_work_item_count_invalid")

    checkpoint_rows: List[Dict[str, Any]] = []
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint.get("source_queue_sha256") != queue_hash:
            raise ValueError(f"r147_source_queue_drift:{index}")
        if checkpoint.get("work_item_count") != work_item_count:
            raise ValueError(f"r147_work_item_count_drift:{index}")
        ids = [row.get("work_item_id") for row in checkpoint.get("mutable_items", [])]
        if ids != item_order:
            raise ValueError(f"r147_work_item_order_or_set_drift:{index}")
        checkpoint_rows.append({
            "index": index,
            "checkpoint_payload_sha256": checkpoint.get("checkpoint_payload_sha256"),
            "source_correction_sheet_sha256": checkpoint.get("source_correction_sheet_sha256"),
            "history_event_count": len(checkpoint.get("history", [])),
            "next_event_sequence": checkpoint.get("next_event_sequence"),
            "status_counts": checkpoint.get("status_counts"),
            "global_progress_state": checkpoint.get("global_progress_state"),
            "global_next_executable_work_item_id": checkpoint.get("global_next_executable_work_item_id"),
        })

    deltas: List[Dict[str, Any]] = []
    all_changed_ids: set[str] = set()
    total_added_events = 0
    total_changed_transitions = 0
    correction_sheet_change_count = 0
    for index in range(1, len(checkpoints)):
        delta = r145.compare_checkpoints(checkpoints[index - 1], checkpoints[index])
        changed_ids = [row["work_item_id"] for row in delta.get("changed_work_items", [])]
        all_changed_ids.update(changed_ids)
        total_added_events += int(delta.get("history_events_added_count") or 0)
        total_changed_transitions += int(delta.get("changed_work_item_count") or 0)
        correction_sheet_change_count += int(bool(delta.get("correction_sheet_changed")))
        deltas.append({
            "from_index": index - 1,
            "to_index": index,
            "before_checkpoint_payload_sha256": delta.get("before_checkpoint_payload_sha256"),
            "after_checkpoint_payload_sha256": delta.get("after_checkpoint_payload_sha256"),
            "changed_work_item_count": delta.get("changed_work_item_count"),
            "changed_work_item_ids": changed_ids,
            "history_events_added_count": delta.get("history_events_added_count"),
            "correction_sheet_changed": delta.get("correction_sheet_changed"),
            "global_next_executable_work_item_id_before": delta.get("global_next_executable_work_item_id_before"),
            "global_next_executable_work_item_id_after": delta.get("global_next_executable_work_item_id_after"),
            "delta_report_sha256": delta.get("delta_report_sha256"),
        })

    first = checkpoints[0]
    last = checkpoints[-1]
    report: Dict[str, Any] = {
        "schema": _CHAIN_SCHEMA,
        "milestone": "BRES Cles catalogue audit R147",
        "source_checkpoint_schema": first.get("schema"),
        "source_delta_schema": "bres-live-critical-pair-collection-checkpoint-delta-r145-v1",
        "source_queue_sha256": queue_hash,
        "tracked_work_item_count": work_item_count,
        "checkpoint_count": len(checkpoints),
        "transition_count": max(0, len(checkpoints) - 1),
        "checkpoints": checkpoint_rows,
        "deltas": deltas,
        "unique_changed_work_item_count": len(all_changed_ids),
        "total_changed_work_item_transitions": total_changed_transitions,
        "total_history_events_added": total_added_events,
        "correction_sheet_change_count": correction_sheet_change_count,
        "first_checkpoint_payload_sha256": first.get("checkpoint_payload_sha256"),
        "last_checkpoint_payload_sha256": last.get("checkpoint_payload_sha256"),
        "history_event_count_first": len(first.get("history", [])),
        "history_event_count_last": len(last.get("history", [])),
        "status_counts_first": first.get("status_counts"),
        "status_counts_last": last.get("status_counts"),
        "global_progress_state_first": first.get("global_progress_state"),
        "global_progress_state_last": last.get("global_progress_state"),
        "global_next_executable_work_item_id_first": first.get("global_next_executable_work_item_id"),
        "global_next_executable_work_item_id_last": last.get("global_next_executable_work_item_id"),
        "history_is_append_only_across_chain": True,
        "r140_queue_is_constant_across_chain": True,
        "work_item_order_is_constant_across_chain": True,
        **_policy(),
    }
    report["chain_report_sha256"] = r144._canonical_sha256(report)
    return report
