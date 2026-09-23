from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
module = (ROOT / "physical_collection_batch_ingestor_r133.py").read_text(encoding="utf-8")
contract = json.loads((ROOT / "catalogue/evidence/live_physical_collection_batch_ingestion_contract_r133.json").read_text(encoding="utf-8"))
checks = {
    "contract_schema_exact": contract.get("schema") == "bres-live-physical-collection-batch-ingestion-contract-r133-v1",
    "runtime_r116_declared": contract.get("active_test_runtime") == "V2.28 TEST R116",
    "input_is_r132_folder_adapter": contract.get("source_folder_schema") == "bres-live-physical-collection-folder-import-r132-v1",
    "downstream_registry_is_r130": contract.get("diagnostic_registry_schema") == "bres-live-diagnostic-pair-registry-r130-v1",
    "pair_readiness_is_r131": contract.get("readiness_schema") == "bres-live-diagnostic-traceable-sufficiency-r131-v1",
    "cross_folder_capture_id_reuse_forbidden": contract.get("cross_folder_capture_id_reuse_allowed") is False,
    "cross_folder_source_sha_reuse_forbidden": contract.get("cross_folder_source_sha256_reuse_allowed") is False,
    "folder_digest_reuse_forbidden": contract.get("source_folder_digest_reuse_allowed") is False,
    "physical_key_pair_conflict_forbidden": contract.get("physical_key_id_pair_conflict_allowed") is False,
    "same_key_same_pair_multiple_dossiers_allowed": contract.get("same_physical_key_same_pair_multiple_dossiers_allowed") is True,
    "decision_authority_none": contract.get("decision_authority") == "NONE",
    "policy_a_confirmer": contract.get("policy_status") == "A_CONFIRMER",
    "automatic_validation_forbidden": contract.get("automatic_validation_allowed") is False,
    "catalogue_write_forbidden": contract.get("canonical_catalogue_write_allowed") is False,
    "runtime_mutation_forbidden": contract.get("runtime_mutation_allowed") is False,
    "threshold_forbidden": contract.get("acceptance_threshold_authorized") is False,
    "candidate_selection_forbidden": contract.get("candidate_selection_allowed") is False,
    "module_calls_r132": "_r132.import_collection_folder" in module,
    "module_calls_r130_registry": "_r130_registry.add_diagnostic_result" in module,
    "module_calls_r131_readiness": "_r131_sufficiency.assess_traceable_sufficiency" in module,
    "module_guards_capture_id_cross_folder_reuse": "capture_id_reused_across_folders" in module,
    "module_guards_sha_cross_folder_reuse": "source_file_sha256_reused_across_folders" in module,
    "module_guards_identity_pair_conflict": "physical_key_id_mapped_to_multiple_pairs" in module,
    "module_no_catalogue_write_api": "write_catalogue" not in module and "save_catalogue" not in module,
    "module_keeps_validated_reference_null": '"validated_reference": None' in module,
}
errors=[k for k,v in checks.items() if not v]; out={"schema":"bres-live-physical-collection-batch-boundary-guard-r133-v1","milestone":"BRES Cles catalogue audit R133","checks":checks,"errors":errors,"ok":not errors}; print(json.dumps(out,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
