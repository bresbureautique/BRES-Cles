from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_completeness_contract_r138.json").read_text(encoding="utf-8"))
source = (ROOT / "critical_pair_collection_completeness_r138.py").read_text(encoding="utf-8")

checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-collection-completeness-contract-r138-v1",
    "source_is_r137_workspace": contract.get("source_workspace_schema") == "bres-live-critical-pair-collection-workspace-r137-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "three_sessions_required": contract.get("requirements", {}).get("sessions_per_key") == 3,
    "recto_verso_required": contract.get("requirements", {}).get("faces_per_session") == ["RECTO", "VERSO"],
    "key_identity_required": contract.get("requirements", {}).get("physical_key_id_required") is True and contract.get("requirements", {}).get("physical_key_identity_confirmed_required") is True,
    "capture_provenance_required": all(contract.get("requirements", {}).get(k) is True for k in ["real_session_id_required", "capture_id_required", "source_path_required", "source_file_sha256_required"]),
    "sha_format_is_64_hex": contract.get("requirements", {}).get("source_file_sha256_format") == "64_HEX",
    "duplicate_capture_and_hash_forbidden": contract.get("requirements", {}).get("duplicate_capture_id_forbidden") is True and contract.get("requirements", {}).get("duplicate_source_sha256_forbidden") is True,
    "completeness_never_counts_as_evidence": contract.get("requirements", {}).get("completeness_counts_as_real_physical_evidence") is False and contract.get("requirements", {}).get("evidence_credit") == 0,
    "decision_authority_none": contract.get("policy", {}).get("decision_authority") == "NONE",
    "canonical_write_forbidden": contract.get("policy", {}).get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("policy", {}).get("runtime_mutation_allowed") is False,
    "automatic_validation_forbidden": contract.get("policy", {}).get("automatic_validation_allowed") is False,
    "threshold_forbidden": contract.get("policy", {}).get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("policy", {}).get("candidate_selection_allowed") is False,
    "validated_reference_null": contract.get("policy", {}).get("validated_reference") is None,
    "measurements_forbidden_as_completeness_driver": contract.get("policy", {}).get("measurements_used_for_completeness") is False,
    "module_has_no_file_write_side_effect": all(token not in source for token in ["write_text(", "write_bytes(", "open(", "Path.write"]),
    "module_has_no_numeric_measurement_field_reads": not re.search(r"(?:width|height|length|depth|thickness|pitch|spacing|measurement|uncertainty)_mm", source),
    "module_keeps_validated_reference_null": '"validated_reference": None' in source,
    "module_keeps_evidence_credit_zero": '"evidence_credit": 0' in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-completeness-boundary-guard-r138-v1",
    "milestone": "BRES Cles catalogue audit R138",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_COMPLETENESS_BOUNDARY_GUARD_R138.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_COMPLETENESS_BOUNDARY_GUARD_R138.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE COMPLETUDE R138", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
