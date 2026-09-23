from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_correction_dependency_contract_r142.json").read_text(encoding="utf-8"))
source = (ROOT / "correction_dependency_guard_r142.py").read_text(encoding="utf-8")
req = contract["requirements"]
policy = contract["policy"]
checks = {
    "contract_schema_is_r142": contract.get("schema") == "bres-live-critical-pair-collection-correction-dependency-contract-r142-v1",
    "preserve_r140_ids_required": req.get("preserve_r140_work_item_ids") is True,
    "session_finalisation_dependency_guard_required": req.get("finalise_session_only_after_key_identity_and_same_session_lower_phase_items_realisee") is True,
    "session_verification_dependency_guard_required": req.get("verify_session_only_after_session_finalisation_and_lower_phase_items_realisee") is True,
    "key_finalisation_dependency_guard_required": req.get("finalise_key_only_after_all_lower_phase_items_for_key_realisee") is True,
    "key_verification_dependency_guard_required": req.get("verify_key_only_after_key_finalisation_and_lower_phase_items_realisee") is True,
    "dependency_regression_reopen_required": req.get("dependency_regression_reopens_completed_parent") is True,
    "batch_atomicity_required": req.get("batch_update_is_externally_atomic") is True,
    "runtime_pinned_to_r116": policy.get("active_test_runtime") == "V2.28 TEST R116" and '"active_test_runtime": "V2.28 TEST R116"' in source,
    "critical_pair_count_pinned": policy.get("critical_pair_count") == 17 and '"critical_pair_count": 17' in source,
    "dependency_is_documentary_only": policy.get("dependency_order_is_documentary_only") is True and '"dependency_order_is_documentary_only": True' in source,
    "evidence_credit_forbidden": policy.get("evidence_credit") == 0 and policy.get("counts_as_real_physical_evidence") is False and '"evidence_credit": 0' in source,
    "measurements_not_used": policy.get("measurements_used_for_dependency") is False and '"measurements_used_for_dependency": False' in source,
    "recognition_score_not_used": policy.get("recognition_score_used_for_dependency") is False and '"recognition_score_used_for_dependency": False' in source,
    "no_decision_authority": policy.get("decision_authority") == "NONE" and '"decision_authority": "NONE"' in source,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False and '"canonical_catalogue_write_allowed": False' in source,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False and '"runtime_mutation_allowed": False' in source,
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False and '"automatic_validation_allowed": False' in source,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False and '"candidate_selection_allowed": False' in source,
    "validated_reference_remains_none": policy.get("validated_reference") is None and '"validated_reference": None' in source,
    "r141_guard_is_reused": "r141.reconcile_tracking_state" in source and "r141.apply_status_updates" in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-dependency-boundary-guard-r142-v1",
    "milestone": "BRES Cles catalogue audit R142",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_DEPENDENCY_BOUNDARY_GUARD_R142.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_DEPENDENCY_BOUNDARY_GUARD_R142.txt").write_text("\n".join([
    "BRES CLES — GARDE FRONTIERE DEPENDANCES R142", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
