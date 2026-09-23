from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_correction_work_queue_contract_r140.json").read_text(encoding="utf-8"))
source = (ROOT / "correction_work_queue_r140.py").read_text(encoding="utf-8")

checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-collection-correction-work-queue-contract-r140-v1",
    "source_is_r139_correction_sheet": contract.get("source_correction_schema") == "bres-live-critical-pair-collection-correction-sheet-r139-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "deterministic_resumable_queue_declared": contract.get("requirements", {}).get("deterministic_order") is True and contract.get("requirements", {}).get("resumable_work_item_ids") is True,
    "dependency_order_declared": all(contract.get("requirements", {}).get(k) is True for k in ["identity_before_capture", "capture_before_verification", "verification_before_finalisation"]),
    "unknown_actions_require_manual_control": contract.get("requirements", {}).get("unknown_actions_go_to_manual_control") is True,
    "completion_requires_real_correction": contract.get("requirements", {}).get("queue_completion_requires_real_correction") is True,
    "queue_never_counts_as_evidence": contract.get("requirements", {}).get("queue_completion_counts_as_real_physical_evidence") is False and contract.get("requirements", {}).get("evidence_credit") == 0,
    "measurements_forbidden_as_priority": contract.get("requirements", {}).get("measurements_used_for_priority") is False,
    "recognition_score_forbidden_as_priority": contract.get("requirements", {}).get("recognition_score_used_for_priority") is False,
    "decision_authority_none": contract.get("policy", {}).get("decision_authority") == "NONE",
    "canonical_write_forbidden": contract.get("policy", {}).get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("policy", {}).get("runtime_mutation_allowed") is False,
    "automatic_validation_forbidden": contract.get("policy", {}).get("automatic_validation_allowed") is False,
    "threshold_forbidden": contract.get("policy", {}).get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("policy", {}).get("candidate_selection_allowed") is False,
    "validated_reference_null": contract.get("policy", {}).get("validated_reference") is None,
    "module_has_no_file_write_side_effect": all(token not in source for token in ["write_text(", "write_bytes(", "open(", "Path.write"]),
    "module_has_no_numeric_measurement_field_reads": not re.search(r"(?:width|height|length|depth|thickness|pitch|spacing|measurement|uncertainty)_mm", source),
    "module_requires_r139_schema": "bres-live-critical-pair-collection-correction-sheet-r139-v1" in source,
    "module_keeps_evidence_credit_zero": '"evidence_credit": 0' in source,
    "module_keeps_candidate_selection_forbidden": '"candidate_selection_allowed": False' in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-work-queue-boundary-guard-r140-v1",
    "milestone": "BRES Cles catalogue audit R140",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_BOUNDARY_GUARD_R140.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_BOUNDARY_GUARD_R140.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE FILE CORRECTION R140", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
