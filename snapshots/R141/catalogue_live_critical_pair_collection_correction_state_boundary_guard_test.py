from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_correction_state_contract_r141.json").read_text(encoding="utf-8"))
source = (ROOT / "correction_state_tracker_r141.py").read_text(encoding="utf-8")

requirements = contract.get("requirements", {})
policy = contract.get("policy", {})
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-collection-correction-state-contract-r141-v1",
    "source_queue_is_r140": contract.get("source_queue_schema") == "bres-live-critical-pair-collection-correction-work-queue-r140-v1",
    "current_issue_source_is_r139": contract.get("source_correction_schema") == "bres-live-critical-pair-collection-correction-sheet-r139-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "four_statuses_declared": requirements.get("allowed_statuses") == ["A_FAIRE", "REALISEE", "A_REFAIRE", "BLOQUEE"],
    "r140_ids_must_be_preserved": requirements.get("preserve_r140_work_item_ids") is True,
    "completion_requires_real_resolution": requirements.get("completion_requires_current_issue_absent") is True,
    "reappearance_requires_redo": requirements.get("automatic_reopen_to_redo_when_issue_reappears") is True,
    "duplicate_updates_and_actions_rejected": all(requirements.get(k) is True for k in ["duplicate_update_in_same_batch_rejected", "duplicate_source_work_item_ids_rejected", "duplicate_semantic_actions_rejected"]),
    "invalid_transitions_rejected": requirements.get("invalid_state_transitions_rejected") is True,
    "blocked_reason_required": requirements.get("blocked_status_requires_reason") is True,
    "source_queue_and_item_provenance_guarded": requirements.get("source_queue_drift_rejected") is True and requirements.get("source_item_provenance_hashes_verified") is True,
    "atomic_batch_declared": requirements.get("atomic_update_batch") is True,
    "completion_never_counts_as_evidence": requirements.get("completion_counts_as_real_physical_evidence") is False and requirements.get("evidence_credit") == 0,
    "measurements_and_scores_forbidden": requirements.get("measurements_used_for_state") is False and requirements.get("recognition_score_used_for_state") is False,
    "decision_authority_none": policy.get("decision_authority") == "NONE",
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False,
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False,
    "threshold_forbidden": policy.get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False,
    "validated_reference_null": policy.get("validated_reference") is None,
    "module_has_no_file_write_side_effect": all(token not in source for token in ["write_text(", "write_bytes(", "open(", "Path.write"]),
    "module_has_no_numeric_measurement_field_reads": not re.search(r"(?:width|height|length|depth|thickness|pitch|spacing|measurement|uncertainty)_mm", source),
    "module_requires_r140_queue_schema": "bres-live-critical-pair-collection-correction-work-queue-r140-v1" in source,
    "module_requires_r139_correction_schema": "bres-live-critical-pair-collection-correction-sheet-r139-v1" in source,
    "module_preserves_evidence_credit_zero": '"evidence_credit": 0' in source,
    "module_keeps_candidate_selection_forbidden": '"candidate_selection_allowed": False' in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-state-boundary-guard-r141-v1",
    "milestone": "BRES Cles catalogue audit R141",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_STATE_BOUNDARY_GUARD_R141.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_STATE_BOUNDARY_GUARD_R141.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE SUIVI ETAT R141", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
