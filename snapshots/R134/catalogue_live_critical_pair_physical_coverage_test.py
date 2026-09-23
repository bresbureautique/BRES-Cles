from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coverage_r134", ROOT / "physical_pair_coverage_matrix_r134.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def pair_report(keys, ready_keys, pair_ready, status):
    return {
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "validated_reference": None,
        "candidate_selection": None,
        "physical_measurement_assessment": None,
        "acceptance_threshold_mm": None,
        "documentation_status": status,
        "pair_summary": {
            "distinct_physical_keys": len(keys),
            "physical_key_ids": list(keys),
            "keys_ready_for_within_key_traceable_descriptive_review": ready_keys,
            "pair_traceable_descriptive_review_ready": pair_ready,
        },
    }


batch = {
    "schema": "bres-live-physical-collection-batch-ingestion-r133-v1",
    "batch_status": "DIAGNOSTIC_ONLY",
    "evidence_status": "MEASURED_UNVALIDATED",
    "decision_authority": "NONE",
    "policy_status": "A_CONFIRMER",
    "canonical_catalogue_write_allowed": False,
    "runtime_mutation_allowed": False,
    "automatic_validation_allowed": False,
    "acceptance_threshold_authorized": False,
    "candidate_selection_allowed": False,
    "validated_reference": None,
    "accepted_folders": [
        {"folder": "vac-key-a", "physical_key_id": "VAC-PHYS-A", "candidate_pair": {"a": "VAC104", "b": "VAC105"}},
        {"folder": "gv-key-a", "physical_key_id": "GV-PHYS-A", "candidate_pair": {"a": "GV1", "b": "GV3"}},
        {"folder": "gv-key-b", "physical_key_id": "GV-PHYS-B", "candidate_pair": {"a": "GV3", "b": "GV1"}},
    ],
    "rejected_folders": [
        {
            "folder": "vac-reused-source",
            "physical_key_id": "VAC-PHYS-B",
            "candidate_pair": {"a": "VAC105", "b": "VAC104"},
            "errors": ["source_file_sha256_reused_across_folders"],
        },
        {
            "folder": "unassigned-invalid-pair",
            "physical_key_id": "BAD-1",
            "candidate_pair": {"a": "NOT", "b": "CRITICAL"},
            "errors": ["r132:candidate_pair_invalid"],
        },
    ],
    "pair_reports": {
        "VAC104::VAC105": pair_report(
            ["VAC-PHYS-A"], 1, False, "READY_FOR_WITHIN_KEY_TRACEABLE_DESCRIPTIVE_REVIEW"
        ),
        "GV1::GV3": pair_report(
            ["GV-PHYS-A", "GV-PHYS-B"], 2, True, "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW"
        ),
    },
}

out = mod.build_critical_pair_coverage(batch)
rows = {r["pair_key"]: r for r in out["pair_coverage"]}
checks = {
    "all_17_r121_critical_pairs_are_listed": out["critical_pair_count"] == 17 and len(rows) == 17,
    "no_evidence_pair_is_explicit": rows["CIS2::CIS4"]["coverage_status"] == "NO_ACCEPTED_DOSSIER" and rows["CIS2::CIS4"]["accepted_dossiers"] == 0,
    "one_traceable_key_is_not_pair_ready": rows["VAC104::VAC105"]["coverage_status"] == "ONE_TRACEABLE_PHYSICAL_KEY_ONLY" and rows["VAC104::VAC105"]["traceable_descriptive_review_ready"] is False,
    "rejected_reuse_reason_is_preserved": rows["VAC104::VAC105"]["rejected_reason_counts"].get("source_file_sha256_reused_across_folders") == 1,
    "two_distinct_keys_can_be_descriptively_ready": rows["GV1::GV3"]["distinct_accepted_physical_keys"] == 2 and rows["GV1::GV3"]["coverage_status"] == "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW",
    "pair_order_is_canonicalized": rows["GV1::GV3"]["accepted_physical_key_ids"] == ["GV-PHYS-A", "GV-PHYS-B"],
    "noncritical_rejection_is_kept_but_not_mapped_to_critical_pair": len(out["unassigned_rejected_dossiers"]) == 1 and out["unassigned_rejected_dossiers"][0]["folder"] == "unassigned-invalid-pair",
    "coverage_counts_are_documentary": out["pairs_with_accepted_dossiers"] == 2 and out["pairs_ready_for_traceable_descriptive_review"] == 1 and out["pairs_with_one_traceable_physical_key_only"] == 1,
    "measurement_values_never_drive_coverage": out["measurement_values_used_for_coverage"] is False and all(r["measurement_values_used_for_coverage"] is False for r in out["pair_coverage"]),
    "matrix_remains_non_authoritative": out["decision_authority"] == "NONE" and out["policy_status"] == "A_CONFIRMER" and out["validated_reference"] is None and out["automatic_validation_allowed"] is False and out["canonical_catalogue_write_allowed"] is False and out["runtime_mutation_allowed"] is False and out["acceptance_threshold_authorized"] is False and out["candidate_selection_allowed"] is False,
}

# Guard against a spoofed R131 escalation being silently summarized.
escalated = json.loads(json.dumps(batch))
escalated["pair_reports"]["VAC104::VAC105"]["validated_reference"] = "VAC104"
try:
    mod.build_critical_pair_coverage(escalated)
    checks["r131_policy_escalation_is_rejected"] = False
except ValueError as exc:
    checks["r131_policy_escalation_is_rejected"] = "policy_escalation" in str(exc)

errors = [k for k, v in checks.items() if not v]
report = {
    "schema": "bres-live-critical-pair-physical-coverage-test-r134-v1",
    "milestone": "BRES Cles catalogue audit R134",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_PHYSICAL_COVERAGE_R134.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_PHYSICAL_COVERAGE_R134.txt").write_text(
    "\n".join(["BRES CLES — COUVERTURE PHYSIQUE PAIRES CRITIQUES R134", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
