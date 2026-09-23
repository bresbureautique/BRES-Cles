from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_workspace_contract_r137.json").read_text(encoding="utf-8"))
source = (ROOT / "critical_pair_collection_workspace_r137.py").read_text(encoding="utf-8")

checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-collection-workspace-contract-r137-v1",
    "source_is_r135_plan": contract.get("source_plan_schema") == "bres-live-critical-pair-collection-plan-r135-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "three_sessions_declared": contract.get("requirements", {}).get("sessions_per_missing_key") == 3,
    "recto_verso_declared": contract.get("requirements", {}).get("faces_per_session") == ["RECTO", "VERSO"],
    "key_identity_starts_null": contract.get("requirements", {}).get("physical_key_id_initial") is None,
    "capture_identity_starts_null": contract.get("requirements", {}).get("capture_id_initial") is None,
    "source_hash_starts_null": contract.get("requirements", {}).get("source_file_sha256_initial") is None,
    "prepared_workspace_not_real_evidence": contract.get("requirements", {}).get("prepared_workspace_counts_as_real_physical_evidence") is False,
    "decision_authority_none": contract.get("policy", {}).get("decision_authority") == "NONE",
    "canonical_write_forbidden": contract.get("policy", {}).get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("policy", {}).get("runtime_mutation_allowed") is False,
    "automatic_validation_forbidden": contract.get("policy", {}).get("automatic_validation_allowed") is False,
    "threshold_forbidden": contract.get("policy", {}).get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("policy", {}).get("candidate_selection_allowed") is False,
    "measurements_forbidden_as_workspace_driver": contract.get("policy", {}).get("measurements_used_for_workspace") is False,
    "module_has_no_file_write_side_effect": all(token not in source for token in ["write_text(", "write_bytes(", "open(", "Path.write"]),
    "module_has_no_numeric_measurement_field_reads": not re.search(r"(?:width|height|length|depth|thickness|pitch|spacing|measurement|uncertainty)_mm", source),
    "module_keeps_validated_reference_null": '"validated_reference": None' in source,
    "module_keeps_threshold_null": '"acceptance_threshold_mm": None' in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-workspace-boundary-guard-r137-v1",
    "milestone": "BRES Cles catalogue audit R137",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_BOUNDARY_GUARD_R137.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_BOUNDARY_GUARD_R137.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE ESPACES DE COLLECTE R137", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
