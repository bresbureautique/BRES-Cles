from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_checkpoint_delta_contract_r145.json").read_text(encoding="utf-8"))
source = (ROOT / "collection_checkpoint_delta_r145.py").read_text(encoding="utf-8")
req = contract["requirements"]
policy = contract["policy"]
checks = {
    "contract_schema_is_r145": contract.get("schema") == "bres-live-critical-pair-collection-checkpoint-delta-contract-r145-v1",
    "valid_r144_inputs_required": req.get("inputs_are_integrity_valid_r144_checkpoints") is True and "_validate_checkpoint" in source,
    "same_queue_required": req.get("same_r140_queue_required") is True and "r145_source_queue_drift" in source,
    "same_order_required": req.get("same_work_item_order_required") is True and "r145_work_item_order_or_set_drift" in source,
    "sheet_drift_reported": req.get("correction_sheet_drift_is_reported_not_silently_ignored") is True and '"correction_sheet_changed"' in source,
    "history_append_only": req.get("history_must_be_append_only") is True and "r145_history_not_append_only" in source,
    "event_sequence_monotonic": req.get("event_sequence_must_not_regress") is True and "r145_event_sequence_regression" in source,
    "change_counter_monotonic": req.get("status_change_count_must_not_regress") is True and "r145_status_change_count_regression" in source,
    "deterministic_changes_reported": req.get("changed_work_items_are_reported_deterministically") is True and '"changed_work_items"' in source,
    "transitions_reported": req.get("transition_counts_are_reported") is True and '"transition_counts"' in source,
    "history_additions_reported": req.get("added_history_events_are_reported") is True and '"history_events_added"' in source,
    "delta_sha_present": req.get("report_has_sha256_integrity_fingerprint") is True and '"delta_report_sha256"' in source,
    "read_only_required": req.get("comparison_is_read_only") is True,
    "runtime_pinned_to_r116": policy.get("active_test_runtime") == "V2.28 TEST R116" and '"active_test_runtime": "V2.28 TEST R116"' in source,
    "stable_pinned_to_v227": policy.get("stable_version") == "V2.27" and '"stable_version": "V2.27"' in source,
    "documentary_only": policy.get("checkpoint_delta_is_documentary_only") is True and '"checkpoint_delta_is_documentary_only": True' in source,
    "evidence_credit_forbidden": policy.get("evidence_credit") == 0 and policy.get("counts_as_real_physical_evidence") is False and '"evidence_credit": 0' in source,
    "measurements_not_used": policy.get("measurements_used_for_delta") is False and '"measurements_used_for_delta": False' in source,
    "recognition_score_not_used": policy.get("recognition_score_used_for_delta") is False and '"recognition_score_used_for_delta": False' in source,
    "no_decision_authority": policy.get("decision_authority") == "NONE" and '"decision_authority": "NONE"' in source,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False and '"canonical_catalogue_write_allowed": False' in source,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False and '"runtime_mutation_allowed": False' in source,
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False and '"automatic_validation_allowed": False' in source,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False and '"candidate_selection_allowed": False' in source,
    "validated_reference_none": policy.get("validated_reference") is None and '"validated_reference": None' in source,
    "module_has_no_file_write_side_effect": ".write_text(" not in source and ".write_bytes(" not in source and "open(" not in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-checkpoint-delta-boundary-guard-r145-v1",
    "milestone": "BRES Cles catalogue audit R145",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_DELTA_BOUNDARY_GUARD_R145.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_DELTA_BOUNDARY_GUARD_R145.txt").write_text("\n".join([
    "BRES CLES — GARDE FRONTIERE DELTA CHECKPOINT R145", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
