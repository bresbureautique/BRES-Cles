from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_diagnostic_observation_sufficiency_contract_r129.json").read_text(encoding="utf-8"))
module_text = (ROOT / "observation_sufficiency_analyzer_r129.py").read_text(encoding="utf-8")
policy = contract.get("policy", {})
req = contract.get("documentation_requirements", {})
limit = contract.get("provenance_limit", {})
forbidden_measurement_tokens = [
    "stop_mean_mm",
    "stop_spread_mm",
    "stop_positions_mm",
    "declared_uncertainties_mm",
    "scale_deltas_mm",
]
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-diagnostic-observation-sufficiency-contract-r129-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "source_registry_is_r127": contract.get("source_registry_schema") == "bres-live-diagnostic-pair-registry-r127-v1",
    "documentation_only": policy.get("analysis_status") == "DOCUMENTATION_ONLY",
    "three_sessions_is_structural_requirement": req.get("within_key_distinct_capture_sessions") == 3,
    "two_keys_is_pair_review_requirement": req.get("pair_distinct_physical_keys_for_inter_key_review") == 2,
    "measurement_values_are_ignored": req.get("measurement_values_are_ignored") is True,
    "r127_capture_hash_limit_declared": limit.get("r127_preserves_source_capture_sha256") is False and limit.get("r129_must_not_claim_full_source_file_provenance") is True,
    "decision_authority_none": policy.get("decision_authority") == "NONE",
    "policy_a_confirmer": policy.get("policy_status") == "A_CONFIRMER",
    "evidence_unvalidated": policy.get("evidence_status") == "MEASURED_UNVALIDATED",
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False,
    "measurement_assessment_forbidden": policy.get("physical_measurement_assessment_allowed") is False,
    "acceptance_threshold_forbidden": policy.get("acceptance_threshold_authorized") is False,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False,
    "module_has_no_file_write_side_effect": ".write_text(" not in module_text and "open(" not in module_text,
    "module_does_not_read_numeric_measurement_fields": not any(token in module_text for token in forbidden_measurement_tokens),
    "module_keeps_candidate_selection_null": '"candidate_selection": None' in module_text,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module_text,
    "module_keeps_measurement_assessment_null": '"physical_measurement_assessment": None' in module_text,
    "module_keeps_threshold_null": '"acceptance_threshold_mm": None' in module_text,
}
errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-observation-sufficiency-boundary-guard-r129-v1",
    "milestone": "BRES Cles catalogue audit R129",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_OBSERVATION_SUFFICIENCY_BOUNDARY_GUARD_R129.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_OBSERVATION_SUFFICIENCY_BOUNDARY_GUARD_R129.txt").write_text(
    "\n".join(["BRES CLES — GARDE FRONTIERE SUFFISANCE DOCUMENTAIRE R129", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
