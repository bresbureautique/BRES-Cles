from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent

spec_reg = importlib.util.spec_from_file_location("reg", ROOT / "diagnostic_pair_registry_r127.py")
reg = importlib.util.module_from_spec(spec_reg)
spec_reg.loader.exec_module(reg)

spec_rep = importlib.util.spec_from_file_location("rep", ROOT / "repeatability_analyzer_r128.py")
rep = importlib.util.module_from_spec(spec_rep)
spec_rep.loader.exec_module(rep)


def accepted(mean=12.2, spread=0.2, offset=0.0):
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
            "stop_positions_mm": [mean - 0.1 + offset, mean + offset, mean + 0.1 + offset],
            "declared_uncertainties_mm": [0.2, 0.2, 0.2],
            "recto_verso_geometry_signatures": [
                {"capture_session_id": "S1", "recto": f"r1-{offset}", "verso": f"v1-{offset}"},
                {"capture_session_id": "S2", "recto": f"r2-{offset}", "verso": f"v2-{offset}"},
                {"capture_session_id": "S3", "recto": f"r3-{offset}", "verso": f"v3-{offset}"}
            ],
            "stop_mean_mm": mean + offset,
            "stop_spread_mm": spread,
            "physical_tolerance_decision": None
        },
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "validated_reference": None
    }

checks = {}
r0 = reg.new_registry()
r1 = reg.add_diagnostic_result(r0, accepted(mean=12.2), "SYNTH-KEY-001")
r2 = reg.add_diagnostic_result(r1, accepted(mean=12.3), "SYNTH-KEY-001")
r3 = reg.add_diagnostic_result(r2, accepted(mean=12.8), "SYNTH-KEY-002")
source_before = copy.deepcopy(r3)
report = rep.analyze_pair_repeatability(r3, "VAC105", "VAC104")
checks["registry_not_mutated"] = r3 == source_before
checks["pair_order_canonicalized"] = report["candidate_pair"] == {"a": "VAC104", "b": "VAC105"}
checks["same_physical_key_multiple_entries_grouped"] = report["per_physical_key"]["SYNTH-KEY-001"]["diagnostic_entries"] == 2
checks["session_observations_counted_descriptively"] = report["per_physical_key"]["SYNTH-KEY-001"]["session_stop_observations"] == 6
checks["within_key_span_is_observation_not_verdict"] = report["per_physical_key"]["SYNTH-KEY-001"]["observed_entry_mean_span_mm"] > 0 and report["per_physical_key"]["SYNTH-KEY-001"]["repeatability_assessment"] is None
checks["different_physical_keys_remain_distinct"] = report["pair_summary"]["physical_key_ids"] == ["SYNTH-KEY-001", "SYNTH-KEY-002"]
checks["inter_key_span_is_descriptive_only"] = report["pair_summary"]["inter_key_comparison_available"] is True and report["pair_summary"]["observed_key_mean_span_mm"] > 0 and report["pair_summary"]["acceptance_threshold_mm"] is None
checks["no_candidate_or_validation_output"] = report["candidate_selection"] is None and report["validated_reference"] is None and report["decision_authority"] == "NONE" and report["policy_status"] == "A_CONFIRMER"
checks["no_runtime_or_catalogue_authority"] = report["runtime_mutation_allowed"] is False and report["canonical_catalogue_write_allowed"] is False and report["automatic_validation_allowed"] is False and report["acceptance_threshold_authorized"] is False

single = reg.new_registry()
single = reg.add_diagnostic_result(single, accepted(mean=11.0), "SYNTH-ONLY")
single_report = rep.analyze_pair_repeatability(single, "VAC104", "VAC105")
checks["single_key_does_not_fake_inter_key_evidence"] = single_report["pair_summary"]["inter_key_comparison_available"] is False

empty_report = rep.analyze_pair_repeatability(reg.new_registry(), "VAC104", "VAC105")
checks["empty_pair_is_non_authoritative"] = empty_report.get("analysis_note") == "NO_DIAGNOSTIC_DATA_FOR_PAIR" and empty_report["validated_reference"] is None

bad = copy.deepcopy(r3)
bad["pairs"]["VAC104::VAC105"]["entries"][0]["validated_reference"] = "VAC104"
try:
    rep.analyze_pair_repeatability(bad, "VAC104", "VAC105")
    checks["tampered_entry_authority_rejected"] = False
except ValueError:
    checks["tampered_entry_authority_rejected"] = True

errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-repeatability-test-r128-v1",
    "milestone": "BRES Cles catalogue audit R128",
    "checks": checks,
    "errors": errors,
    "ok": not errors
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_REPEATABILITY_R128.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_REPEATABILITY_R128.txt").write_text("\n".join(["BRES CLES — REPETABILITE DIAGNOSTIQUE R128", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
