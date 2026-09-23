from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent

spec_reg = importlib.util.spec_from_file_location("reg", ROOT / "diagnostic_pair_registry_r127.py")
reg = importlib.util.module_from_spec(spec_reg)
spec_reg.loader.exec_module(reg)

spec_suf = importlib.util.spec_from_file_location("suf", ROOT / "observation_sufficiency_analyzer_r129.py")
suf = importlib.util.module_from_spec(spec_suf)
spec_suf.loader.exec_module(suf)


def accepted(mean=12.2, session_ids=("S1", "S2", "S3"), suffix="A"):
    positions = [mean - 0.1, mean, mean + 0.1]
    records = [
        {
            "capture_session_id": sid,
            "recto": f"r-{suffix}-{idx}",
            "verso": f"v-{suffix}-{idx}",
        }
        for idx, sid in enumerate(session_ids, 1)
    ]
    return {
        "schema": "bres-live-discriminant-diagnostic-ingestion-r126-v1",
        "active_test_runtime": "V2.28 TEST R116",
        "ingestion_status": "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS",
        "accepted_for_diagnostics": True,
        "source_validation_ok": True,
        "errors": [],
        "warnings": [],
        "candidate_pair": {"a": "VAC104", "b": "VAC105"},
        "diagnostics": {
            "scale_deltas_mm": [0.0, 0.0],
            "stop_positions_mm": positions,
            "declared_uncertainties_mm": [0.2, 0.2, 0.2],
            "recto_verso_geometry_signatures": records,
            "stop_mean_mm": mean,
            "stop_spread_mm": 0.2,
            "physical_tolerance_decision": None,
        },
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "validated_reference": None,
    }


checks = {}
empty = suf.assess_observation_sufficiency(reg.new_registry(), "VAC104", "VAC105")
checks["empty_pair_is_no_data"] = empty["documentation_status"] == "NO_DATA" and empty.get("analysis_note") == "NO_DIAGNOSTIC_DATA_FOR_PAIR"

single = reg.add_diagnostic_result(reg.new_registry(), accepted(mean=10.0, suffix="SINGLE"), "SYNTH-KEY-001")
single_before = copy.deepcopy(single)
single_report = suf.assess_observation_sufficiency(single, "VAC105", "VAC104")
checks["registry_not_mutated"] = single == single_before
checks["pair_order_canonicalized"] = single_report["candidate_pair"] == {"a": "VAC104", "b": "VAC105"}
checks["one_documented_key_ready_for_within_key_review_only"] = (
    single_report["documentation_status"] == "READY_FOR_WITHIN_KEY_DESCRIPTIVE_REVIEW"
    and single_report["pair_summary"]["pair_descriptive_review_ready"] is False
)
checks["three_distinct_sessions_required"] = single_report["per_physical_key"]["SYNTH-KEY-001"]["three_session_coverage_complete"] is True
checks["r127_capture_hash_limit_exposed"] = single_report["source_capture_sha256_provenance_preserved_by_r127"] is False

pair = reg.add_diagnostic_result(single, accepted(mean=90.0, suffix="SECOND"), "SYNTH-KEY-002")
pair_report = suf.assess_observation_sufficiency(pair, "VAC104", "VAC105")
checks["two_documented_keys_ready_for_pair_descriptive_review"] = (
    pair_report["documentation_status"] == "READY_FOR_PAIR_DESCRIPTIVE_REVIEW"
    and pair_report["pair_summary"]["distinct_physical_keys"] == 2
    and pair_report["pair_summary"]["keys_ready_for_within_key_descriptive_review"] == 2
)
checks["extreme_measurement_difference_does_not_block_documentation_status"] = pair_report["measurement_values_used_for_status"] is False

incomplete = reg.add_diagnostic_result(
    reg.new_registry(),
    accepted(mean=12.0, session_ids=("S1", "S2"), suffix="SHORT"),
    "SYNTH-KEY-003",
)
incomplete_report = suf.assess_observation_sufficiency(incomplete, "VAC104", "VAC105")
checks["two_sessions_are_documentation_incomplete"] = (
    incomplete_report["documentation_status"] == "WITHIN_KEY_DOCUMENTATION_INCOMPLETE"
    and incomplete_report["per_physical_key"]["SYNTH-KEY-003"]["three_session_coverage_complete"] is False
)

base_low = reg.add_diagnostic_result(reg.new_registry(), accepted(mean=1.0, suffix="LOW"), "SYNTH-KEY-A")
base_low = reg.add_diagnostic_result(base_low, accepted(mean=2.0, suffix="LOW2"), "SYNTH-KEY-B")
base_high = reg.add_diagnostic_result(reg.new_registry(), accepted(mean=1001.0, suffix="HIGH"), "SYNTH-KEY-A")
base_high = reg.add_diagnostic_result(base_high, accepted(mean=2002.0, suffix="HIGH2"), "SYNTH-KEY-B")
low_report = suf.assess_observation_sufficiency(base_low, "VAC104", "VAC105")
high_report = suf.assess_observation_sufficiency(base_high, "VAC104", "VAC105")
checks["numeric_measurements_do_not_change_structural_readiness"] = (
    low_report["documentation_status"] == high_report["documentation_status"] == "READY_FOR_PAIR_DESCRIPTIVE_REVIEW"
    and low_report["pair_summary"]["keys_ready_for_within_key_descriptive_review"] == high_report["pair_summary"]["keys_ready_for_within_key_descriptive_review"] == 2
)
checks["no_candidate_threshold_or_validation_output"] = (
    pair_report["candidate_selection"] is None
    and pair_report["validated_reference"] is None
    and pair_report["physical_measurement_assessment"] is None
    and pair_report["acceptance_threshold_mm"] is None
    and pair_report["decision_authority"] == "NONE"
    and pair_report["policy_status"] == "A_CONFIRMER"
)
checks["no_runtime_or_catalogue_authority"] = (
    pair_report["runtime_mutation_allowed"] is False
    and pair_report["canonical_catalogue_write_allowed"] is False
    and pair_report["automatic_validation_allowed"] is False
    and pair_report["acceptance_threshold_authorized"] is False
)

bad = copy.deepcopy(pair)
bad["pairs"]["VAC104::VAC105"]["entries"][0]["validated_reference"] = "VAC104"
try:
    suf.assess_observation_sufficiency(bad, "VAC104", "VAC105")
    checks["tampered_authority_rejected"] = False
except ValueError:
    checks["tampered_authority_rejected"] = True

errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-observation-sufficiency-test-r129-v1",
    "milestone": "BRES Cles catalogue audit R129",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_OBSERVATION_SUFFICIENCY_R129.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_OBSERVATION_SUFFICIENCY_R129.txt").write_text(
    "\n".join(["BRES CLES — SUFFISANCE DOCUMENTAIRE R129", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
