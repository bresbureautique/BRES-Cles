from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
module = (ROOT / "physical_pair_coverage_matrix_r134.py").read_text(encoding="utf-8")
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_physical_coverage_contract_r134.json").read_text(encoding="utf-8"))

checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-physical-coverage-contract-r134-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "source_is_r133_batch": contract.get("source_batch_schema") == "bres-live-physical-collection-batch-ingestion-r133-v1",
    "critical_pairs_source_is_r121": contract.get("critical_pair_registry_schema") == "bres-catalogue-ocr-critical-pair-registry-r121-v1",
    "all_17_pairs_expected": contract.get("critical_pair_count_expected") == 17,
    "no_data_pairs_must_be_listed": contract.get("no_data_pairs_must_be_listed") is True,
    "rejection_reasons_preserved": contract.get("rejected_dossier_reasons_must_be_preserved") is True,
    "physical_key_identity_preserved": contract.get("accepted_physical_key_identity_must_be_preserved") is True,
    "measurements_forbidden_for_coverage": contract.get("measurement_values_used_for_coverage") is False,
    "decision_authority_none": contract.get("decision_authority") == "NONE",
    "policy_a_confirmer": contract.get("policy_status") == "A_CONFIRMER",
    "automatic_validation_forbidden": contract.get("automatic_validation_allowed") is False,
    "catalogue_write_forbidden": contract.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("runtime_mutation_allowed") is False,
    "threshold_forbidden": contract.get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("candidate_selection_allowed") is False,
    "module_loads_r121_registry": "catalogue_ocr_critical_pair_registry_r121.json" in module,
    "module_requires_r133_schema": "bres-live-physical-collection-batch-ingestion-r133-v1" in module,
    "module_lists_no_data_status": "NO_ACCEPTED_DOSSIER" in module,
    "module_preserves_rejection_errors": "rejected_reason_counts" in module and "rejected_dossier_details" in module,
    "module_does_not_read_measurement_fields": "position_mm" not in module and "uncertainty_mm" not in module and "stop_or_shoulder" not in module,
    "module_has_no_catalogue_write_api": "write_catalogue" not in module and "save_catalogue" not in module,
    "module_has_no_runtime_write_api": "write_runtime" not in module and "save_runtime" not in module,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module,
    "module_keeps_candidate_selection_null": '"candidate_selection": None' in module,
}
errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-critical-pair-physical-coverage-boundary-guard-r134-v1",
    "milestone": "BRES Cles catalogue audit R134",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_PHYSICAL_COVERAGE_BOUNDARY_GUARD_R134.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_PHYSICAL_COVERAGE_BOUNDARY_GUARD_R134.txt").write_text(
    "\n".join(["BRES CLES — GARDE-FEU COUVERTURE PAIRES CRITIQUES R134", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
