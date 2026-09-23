from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

prov = load("prov131", ROOT / "provenance_ingestor_r130.py")
reg = load("reg131", ROOT / "diagnostic_pair_registry_r130.py")
suf = load("suf131", ROOT / "traceable_sufficiency_analyzer_r131.py")
base = json.loads((ROOT / "catalogue/evidence/live_discriminant_collection_packet_r125.json").read_text(encoding="utf-8"))


def fixture(key, offset=0, positions=(12.1, 12.2, 12.3)):
    p = copy.deepcopy(base)
    p["physical_key_id"] = key
    p["candidate_pair"] = {"a": "VAC104", "b": "VAC105"}
    p["gabarit"].update({
        "id": "BRES-A4", "version": "R124", "zero_mode": "BUTEE_ZERO",
        "calibration_source": "manual-scale-check", "calibration_documented": True,
        "calibration_ok": True,
    })
    p["gabarit"]["scale_checks"][0]["measured_mm"] = 50.0
    p["gabarit"]["scale_checks"][1]["measured_mm"] = 100.0
    p["collection_sessions"] = []
    for i, slot in enumerate(p["session_slots"], 1):
        s = copy.deepcopy(slot)
        s["slot_status"] = "FILLED"
        s["captured_at"] = f"2026-09-23T2{i}:00:00+02:00"
        s["device_model"] = "SAMSUNG-TEST"
        s["captures"]["recto"]["capture_id"] = f"{key}-S{i}-R"
        s["captures"]["verso"]["capture_id"] = f"{key}-S{i}-V"
        s["captures"]["recto"]["source_file_sha256"] = (f"{offset+i:02x}" * 32)[:64]
        s["captures"]["verso"]["source_file_sha256"] = (f"{offset+i+20:02x}" * 32)[:64]
        s["captures"]["recto"]["geometry_signature"] = f"{key}-geom-r-{i}"
        s["captures"]["verso"]["geometry_signature"] = f"{key}-geom-v-{i}"
        s["stop_or_shoulder"].update({
            "position_mm": positions[i-1],
            "uncertainty_mm": 0.2,
            "measurement_method": "manual-gabarit",
        })
        s["dual_face"]["measurement_method"] = "independent-photo-geometry"
        s["quality"].update({"focus_ok": True, "alignment_ok": True, "calibration_ok": True, "occlusion_ok": True})
        p["collection_sessions"].append(s)
    p["collection_summary"].update({
        "complete_sessions": 3,
        "all_capture_ids_unique": True,
        "all_capture_hashes_unique": True,
        "calibration_documented": True,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "packet_ready_for_review": False,
    })
    return p


def add(registry, key, offset=0, positions=(12.1, 12.2, 12.3)):
    source = prov.ingest_packet_with_provenance(fixture(key, offset, positions))
    assert source["accepted_for_diagnostics"] is True, source["errors"]
    return reg.add_diagnostic_result(registry, source)

checks = {}
empty = suf.assess_traceable_sufficiency(reg.new_registry(), "VAC104", "VAC105")
checks["empty_pair_is_no_data"] = empty["documentation_status"] == "NO_DATA" and empty.get("analysis_note") == "NO_DIAGNOSTIC_DATA_FOR_PAIR"

single = add(reg.new_registry(), "KEY-R131-A", 0)
single_before = copy.deepcopy(single)
single_report = suf.assess_traceable_sufficiency(single, "VAC105", "VAC104")
checks["registry_not_mutated"] = single == single_before
checks["pair_order_canonicalized"] = single_report["candidate_pair"] == {"a": "VAC104", "b": "VAC105"}
checks["one_key_ready_for_traceable_within_key_review_only"] = (
    single_report["documentation_status"] == "READY_FOR_WITHIN_KEY_TRACEABLE_DESCRIPTIVE_REVIEW"
    and single_report["pair_summary"]["pair_traceable_descriptive_review_ready"] is False
)
entry = single_report["per_physical_key"]["KEY-R131-A"]["entry_traceability"][0]
checks["six_sources_three_dual_face_sessions_required"] = (
    entry["source_capture_record_count"] == 6
    and entry["three_session_recto_verso_coverage_complete"] is True
)
checks["six_sources_have_valid_unique_ids_and_hashes"] = (
    entry["capture_ids_unique_within_entry"] is True
    and entry["source_capture_sha256_unique_within_entry"] is True
    and entry["source_packet_sha256_valid"] is True
    and entry["provenance_digest_sha256_valid"] is True
)
checks["r130_source_hash_provenance_declared"] = single_report["source_capture_sha256_provenance_preserved_by_r130"] is True

pair = add(single, "KEY-R131-B", 40)
pair_report = suf.assess_traceable_sufficiency(pair, "VAC104", "VAC105")
checks["two_keys_ready_for_pair_traceable_review"] = (
    pair_report["documentation_status"] == "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW"
    and pair_report["pair_summary"]["distinct_physical_keys"] == 2
    and pair_report["pair_summary"]["source_capture_records"] == 12
    and pair_report["pair_summary"]["distinct_source_capture_sha256"] == 12
)
checks["global_non_reuse_confirmed"] = (
    pair_report["pair_summary"]["capture_ids_unique_across_pair_registry"] is True
    and pair_report["pair_summary"]["source_capture_sha256_unique_across_pair_registry"] is True
)

low = add(add(reg.new_registry(), "KEY-R131-X", 80, (1.0, 1.1, 1.2)), "KEY-R131-Y", 120, (2.0, 2.1, 2.2))
high = add(add(reg.new_registry(), "KEY-R131-X", 160, (1001.0, 1002.0, 1003.0)), "KEY-R131-Y", 200, (2001.0, 2002.0, 2003.0))
low_report = suf.assess_traceable_sufficiency(low, "VAC104", "VAC105")
high_report = suf.assess_traceable_sufficiency(high, "VAC104", "VAC105")
checks["measurement_values_do_not_change_traceability_status"] = (
    low_report["documentation_status"] == high_report["documentation_status"] == "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW"
    and low_report["measurement_values_used_for_status"] is False
    and high_report["measurement_values_used_for_status"] is False
)

tampered_missing = copy.deepcopy(single)
tampered_missing["pairs"]["VAC104::VAC105"]["entries"][0]["source_capture_provenance"] = tampered_missing["pairs"]["VAC104::VAC105"]["entries"][0]["source_capture_provenance"][:-1]
missing_report = suf.assess_traceable_sufficiency(tampered_missing, "VAC104", "VAC105")
checks["missing_capture_blocks_readiness"] = missing_report["documentation_status"] == "SOURCE_TRACEABILITY_INCOMPLETE"

tampered_hash = copy.deepcopy(single)
tampered_hash["pairs"]["VAC104::VAC105"]["entries"][0]["source_capture_provenance"][0]["source_file_sha256"] = "xyz"
hash_report = suf.assess_traceable_sufficiency(tampered_hash, "VAC104", "VAC105")
checks["invalid_hash_blocks_readiness"] = hash_report["documentation_status"] == "SOURCE_TRACEABILITY_INCOMPLETE"

tampered_side = copy.deepcopy(single)
tampered_side["pairs"]["VAC104::VAC105"]["entries"][0]["source_capture_provenance"][1]["side"] = "RECTO"
side_report = suf.assess_traceable_sufficiency(tampered_side, "VAC104", "VAC105")
checks["missing_recto_verso_pairing_blocks_readiness"] = side_report["documentation_status"] == "SOURCE_TRACEABILITY_INCOMPLETE"

tampered_reuse = copy.deepcopy(pair)
e1, e2 = tampered_reuse["pairs"]["VAC104::VAC105"]["entries"][:2]
e2["source_capture_provenance"][0]["source_file_sha256"] = e1["source_capture_provenance"][0]["source_file_sha256"]
reuse_report = suf.assess_traceable_sufficiency(tampered_reuse, "VAC104", "VAC105")
checks["cross_entry_hash_reuse_blocks_pair_readiness"] = (
    reuse_report["documentation_status"] == "SOURCE_TRACEABILITY_INCOMPLETE"
    and reuse_report["pair_summary"]["source_capture_sha256_unique_across_pair_registry"] is False
)

checks["no_candidate_threshold_validation_or_mutation_authority"] = (
    pair_report["candidate_selection"] is None
    and pair_report["validated_reference"] is None
    and pair_report["physical_measurement_assessment"] is None
    and pair_report["acceptance_threshold_mm"] is None
    and pair_report["decision_authority"] == "NONE"
    and pair_report["policy_status"] == "A_CONFIRMER"
    and pair_report["runtime_mutation_allowed"] is False
    and pair_report["canonical_catalogue_write_allowed"] is False
    and pair_report["automatic_validation_allowed"] is False
    and pair_report["acceptance_threshold_authorized"] is False
)

bad = copy.deepcopy(pair)
bad["pairs"]["VAC104::VAC105"]["entries"][0]["validated_reference"] = "VAC104"
try:
    suf.assess_traceable_sufficiency(bad, "VAC104", "VAC105")
    checks["policy_escalation_rejected"] = False
except ValueError:
    checks["policy_escalation_rejected"] = True

errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-diagnostic-traceable-sufficiency-test-r131-v1",
    "milestone": "BRES Cles catalogue audit R131",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_TRACEABLE_SUFFICIENCY_R131.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_TRACEABLE_SUFFICIENCY_R131.txt").write_text(
    "\n".join(["BRES CLES — SUFFISANCE DOCUMENTAIRE TRAÇABLE R131", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
