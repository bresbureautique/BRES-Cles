from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_diagnostic_traceable_sufficiency_contract_r131.json").read_text(encoding="utf-8"))
module_text = (ROOT / "traceable_sufficiency_analyzer_r131.py").read_text(encoding="utf-8")
policy = contract.get("policy", {})
req = contract.get("documentation_requirements", {})
forbidden_measurement_tokens = [
    "stop_mean_mm",
    "stop_spread_mm",
    "stop_positions_mm",
    "declared_uncertainties_mm",
    "scale_deltas_mm",
    "position_mm",
    "uncertainty_mm",
]
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-diagnostic-traceable-sufficiency-contract-r131-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "source_registry_is_r130": contract.get("source_registry_schema") == "bres-live-diagnostic-pair-registry-r130-v1",
    "documentation_and_provenance_only": policy.get("analysis_status") == "DOCUMENTATION_AND_PROVENANCE_ONLY",
    "three_sessions_required": req.get("within_key_distinct_capture_sessions") == 3,
    "six_source_records_required": req.get("source_capture_records_per_entry") == 6,
    "recto_verso_required": req.get("faces_per_session") == ["RECTO", "VERSO"],
    "source_hash_required": req.get("source_file_sha256_required") is True,
    "packet_and_provenance_digests_required": req.get("source_packet_sha256_required") is True and req.get("provenance_digest_sha256_required") is True,
    "within_entry_uniqueness_required": req.get("capture_ids_unique_within_entry") is True and req.get("source_hashes_unique_within_entry") is True,
    "cross_registry_uniqueness_required": req.get("capture_ids_unique_across_pair_registry") is True and req.get("source_hashes_unique_across_pair_registry") is True,
    "two_keys_required_for_pair_review": req.get("pair_distinct_physical_keys_for_inter_key_review") == 2,
    "measurement_values_ignored": req.get("measurement_values_are_ignored") is True,
    "decision_authority_none": policy.get("decision_authority") == "NONE",
    "policy_a_confirmer": policy.get("policy_status") == "A_CONFIRMER",
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False,
    "measurement_assessment_forbidden": policy.get("physical_measurement_assessment_allowed") is False,
    "threshold_forbidden": policy.get("acceptance_threshold_authorized") is False,
    "canonical_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False,
    "module_has_no_file_write_side_effect": ".write_text(" not in module_text and "open(" not in module_text,
    "module_does_not_read_numeric_measurement_fields": not any(token in module_text for token in forbidden_measurement_tokens),
    "module_requires_r130_registry": '_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r130-v1"' in module_text,
    "module_requires_r130_provenance_source": '_SOURCE_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"' in module_text,
    "module_keeps_candidate_selection_null": '"candidate_selection": None' in module_text,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module_text,
    "module_keeps_measurement_assessment_null": '"physical_measurement_assessment": None' in module_text,
    "module_keeps_threshold_null": '"acceptance_threshold_mm": None' in module_text,
}
errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-traceable-sufficiency-boundary-guard-r131-v1",
    "milestone": "BRES Cles catalogue audit R131",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_TRACEABLE_SUFFICIENCY_BOUNDARY_GUARD_R131.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_TRACEABLE_SUFFICIENCY_BOUNDARY_GUARD_R131.txt").write_text(
    "\n".join(["BRES CLES — GARDE FRONTIERE SUFFISANCE TRAÇABLE R131", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
