from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_diagnostic_repeatability_contract_r128.json").read_text(encoding="utf-8"))
module_text = (ROOT / "repeatability_analyzer_r128.py").read_text(encoding="utf-8")
policy = contract.get("policy", {})
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-diagnostic-repeatability-contract-r128-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "source_registry_is_r127": contract.get("source_registry_schema") == "bres-live-diagnostic-pair-registry-r127-v1",
    "analysis_is_descriptive_only": contract.get("analysis", {}).get("descriptive_only") is True,
    "synthetic_data_first": contract.get("analysis", {}).get("synthetic_data_first") is True,
    "physical_keys_remain_distinct": contract.get("separation", {}).get("physical_keys_remain_distinct") is True,
    "decision_authority_none": policy.get("decision_authority") == "NONE",
    "policy_a_confirmer": policy.get("policy_status") == "A_CONFIRMER",
    "evidence_unvalidated": policy.get("evidence_status") == "MEASURED_UNVALIDATED",
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False,
    "repeatability_verdict_forbidden": policy.get("repeatability_assessment_allowed") is False,
    "acceptance_threshold_forbidden": policy.get("acceptance_threshold_authorized") is False,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False,
    "module_has_no_file_write_side_effect": ".write_text(" not in module_text and "open(" not in module_text,
    "module_keeps_repeatability_assessment_null": '"repeatability_assessment": None' in module_text,
    "module_keeps_acceptance_threshold_null": '"acceptance_threshold_mm": None' in module_text,
    "module_keeps_candidate_selection_null": '"candidate_selection": None' in module_text,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module_text,
}
errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-repeatability-boundary-guard-r128-v1",
    "milestone": "BRES Cles catalogue audit R128",
    "checks": checks,
    "errors": errors,
    "ok": not errors
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_REPEATABILITY_BOUNDARY_GUARD_R128.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_REPEATABILITY_BOUNDARY_GUARD_R128.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE REPETABILITE R128", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
