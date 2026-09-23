from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_checkpoint_contract_r144.json").read_text(encoding="utf-8"))
source = (ROOT / "collection_checkpoint_r144.py").read_text(encoding="utf-8")
req = contract["requirements"]
policy = contract["policy"]
checks = {
    "contract_schema_is_r144": contract.get("schema") == "bres-live-critical-pair-collection-checkpoint-contract-r144-v1",
    "preserve_r140_ids_required": req.get("preserve_r140_work_item_ids") is True,
    "compact_export_required": req.get("compact_export_omits_immutable_r140_item_payload") is True,
    "mutable_state_fields_required": req.get("export_records_mutable_status_block_reason_and_change_count") is True,
    "history_and_sequence_required": req.get("export_records_history_and_next_event_sequence") is True,
    "payload_hash_required": req.get("checkpoint_payload_has_sha256_integrity_guard") is True and "checkpoint_payload_sha256" in source,
    "same_queue_required": req.get("resume_requires_same_r140_queue") is True and "r144_source_queue_drift" in source,
    "same_sheet_required": req.get("resume_requires_same_r139_correction_sheet") is True and "r144_source_correction_sheet_drift" in source,
    "exact_state_sha_required": req.get("reconstructed_r141_r142_state_must_match_export_sha256") is True and "r144_reconstructed_state_mismatch" in source,
    "dependency_sha_required": req.get("dependency_projection_must_match_export_sha256") is True and "r144_dependency_snapshot_mismatch" in source,
    "hierarchy_sha_required": req.get("r143_hierarchy_projection_must_match_export_sha256") is True and "r144_hierarchy_snapshot_mismatch" in source,
    "next_action_guard_required": req.get("next_executable_work_item_id_must_match") is True and "r144_next_action_mismatch" in source,
    "runtime_pinned_to_r116": policy.get("active_test_runtime") == "V2.28 TEST R116" and '"active_test_runtime": "V2.28 TEST R116"' in source,
    "stable_pinned_to_v227": policy.get("stable_version") == "V2.27" and '"stable_version": "V2.27"' in source,
    "documentary_only": policy.get("checkpoint_is_documentary_only") is True and '"checkpoint_is_documentary_only": True' in source,
    "evidence_credit_forbidden": policy.get("evidence_credit") == 0 and policy.get("counts_as_real_physical_evidence") is False and '"evidence_credit": 0' in source,
    "measurements_not_used": policy.get("measurements_used_for_checkpoint") is False and '"measurements_used_for_checkpoint": False' in source,
    "recognition_score_not_used": policy.get("recognition_score_used_for_checkpoint") is False and '"recognition_score_used_for_checkpoint": False' in source,
    "no_decision_authority": policy.get("decision_authority") == "NONE" and '"decision_authority": "NONE"' in source,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False and '"canonical_catalogue_write_allowed": False' in source,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False and '"runtime_mutation_allowed": False' in source,
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False and '"automatic_validation_allowed": False' in source,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False and '"candidate_selection_allowed": False' in source,
    "validated_reference_remains_none": policy.get("validated_reference") is None and '"validated_reference": None' in source,
    "module_has_no_file_write_side_effect": ".write_text(" not in source and ".write_bytes(" not in source and "open(" not in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-checkpoint-boundary-guard-r144-v1",
    "milestone": "BRES Cles catalogue audit R144",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_BOUNDARY_GUARD_R144.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_BOUNDARY_GUARD_R144.txt").write_text("\n".join([
    "BRES CLES — GARDE FRONTIERE CHECKPOINT R144", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
