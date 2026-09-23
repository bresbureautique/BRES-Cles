from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_correction_sheet_contract_r139.json").read_text(encoding="utf-8"))
source = (ROOT / "correction_sheet_r139.py").read_text(encoding="utf-8")

checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-critical-pair-collection-correction-sheet-contract-r139-v1",
    "source_is_r138_completeness": contract.get("source_completeness_schema") == "bres-live-critical-pair-collection-completeness-r138-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "all_three_action_levels_declared": all(contract.get("requirements", {}).get(k) is True for k in ["key_level_actions", "session_level_actions", "face_level_actions"]),
    "identity_session_and_provenance_actions_declared": all(contract.get("requirements", {}).get(k) is True for k in ["missing_identity_action", "missing_session_action", "missing_provenance_action", "invalid_sha256_action"]),
    "duplicate_capture_requires_independent_recapture": contract.get("requirements", {}).get("duplicate_capture_action_requires_independent_recapture") is True,
    "unknown_reason_kept_for_manual_control": contract.get("requirements", {}).get("unknown_reason_requires_manual_control") is True,
    "correction_never_counts_as_evidence": contract.get("requirements", {}).get("correction_counts_as_real_physical_evidence") is False and contract.get("requirements", {}).get("evidence_credit") == 0,
    "measurements_forbidden_as_correction_driver": contract.get("requirements", {}).get("measurements_used_for_correction") is False,
    "decision_authority_none": contract.get("policy", {}).get("decision_authority") == "NONE",
    "canonical_write_forbidden": contract.get("policy", {}).get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("policy", {}).get("runtime_mutation_allowed") is False,
    "automatic_validation_forbidden": contract.get("policy", {}).get("automatic_validation_allowed") is False,
    "threshold_forbidden": contract.get("policy", {}).get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("policy", {}).get("candidate_selection_allowed") is False,
    "validated_reference_null": contract.get("policy", {}).get("validated_reference") is None,
    "module_has_no_file_write_side_effect": all(token not in source for token in ["write_text(", "write_bytes(", "open(", "Path.write"]),
    "module_has_no_numeric_measurement_field_reads": not re.search(r"(?:width|height|length|depth|thickness|pitch|spacing|measurement|uncertainty)_mm", source),
    "module_requires_r138_schema": "bres-live-critical-pair-collection-completeness-r138-v1" in source,
    "module_keeps_validated_reference_null": '"validated_reference": None' in source,
    "module_keeps_evidence_credit_zero": '"evidence_credit": 0' in source,
    "module_has_explicit_independent_recapture_action": "REFAIRE_CAPTURE_INDEPENDANTE" in source,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-sheet-boundary-guard-r139-v1",
    "milestone": "BRES Cles catalogue audit R139",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_SHEET_BOUNDARY_GUARD_R139.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_SHEET_BOUNDARY_GUARD_R139.txt").write_text("\n".join(["BRES CLES — GARDE FRONTIERE FICHE CORRECTION R139", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
