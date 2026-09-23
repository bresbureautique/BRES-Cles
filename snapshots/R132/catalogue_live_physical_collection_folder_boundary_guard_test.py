from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / "catalogue/evidence/live_physical_collection_folder_adapter_contract_r132.json").read_text(encoding="utf-8"))
module_text = (ROOT / "physical_collection_folder_adapter_r132.py").read_text(encoding="utf-8")
policy = contract.get("policy", {})
req = contract.get("folder_requirements", {})
out_spec = contract.get("verified_output", {})
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-physical-collection-folder-adapter-contract-r132-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "source_packet_is_r125": contract.get("source_packet_schema") == "bres-live-discriminant-collection-packet-r125-v1",
    "downstream_is_r130_provenance": contract.get("downstream_provenance_schema") == "bres-live-discriminant-provenance-ingestion-r130-v1",
    "three_sessions_required": req.get("collection_sessions") == 3,
    "six_source_files_required": req.get("source_files") == 6,
    "recto_verso_required": req.get("faces_per_session") == ["RECTO", "VERSO"],
    "relative_contained_paths_required": req.get("source_paths_must_be_relative") is True and req.get("source_paths_must_stay_inside_collection_folder") is True,
    "actual_file_sha_verification_required": req.get("source_file_sha256_must_match_actual_file_bytes") is True,
    "source_non_reuse_required": req.get("source_paths_unique") is True and req.get("source_file_sha256_unique") is True and req.get("capture_ids_unique") is True,
    "verified_manifest_required": "source_file_sha256" in out_spec.get("source_folder_manifest_preserves", []) and out_spec.get("source_folder_digest_sha256") is True,
    "decision_authority_none": policy.get("decision_authority") == "NONE",
    "policy_a_confirmer": policy.get("policy_status") == "A_CONFIRMER",
    "automatic_validation_forbidden": policy.get("automatic_validation_allowed") is False,
    "catalogue_write_forbidden": policy.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": policy.get("runtime_mutation_allowed") is False,
    "threshold_forbidden": policy.get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": policy.get("candidate_selection_allowed") is False,
    "module_handoff_calls_r130": "_r130.ingest_packet_with_provenance(source)" in module_text,
    "module_hashes_actual_files": "_sha256_file(source_path)" in module_text,
    "module_rejects_path_escape": "target.relative_to(root.resolve())" in module_text,
    "module_no_catalogue_write_api": "canonical_catalogue_write_allowed\": True" not in module_text,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module_text,
}
errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-physical-collection-folder-boundary-guard-r132-v1",
    "milestone": "BRES Cles catalogue audit R132",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_PHYSICAL_COLLECTION_FOLDER_BOUNDARY_GUARD_R132.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_PHYSICAL_COLLECTION_FOLDER_BOUNDARY_GUARD_R132.txt").write_text(
    "\n".join(["BRES CLES — GARDE FRONTIERE ADAPTATEUR DOSSIER R132", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
