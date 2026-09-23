from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("prov", ROOT / "provenance_ingestor_r130.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base = json.loads((ROOT / "catalogue/evidence/live_discriminant_collection_packet_r125.json").read_text(encoding="utf-8"))


def fixture(key="SYNTH-R130-001", pair=("VAC104", "VAC105"), offset=0):
    p = copy.deepcopy(base)
    p["physical_key_id"] = key
    p["candidate_pair"] = {"a": pair[0], "b": pair[1]}
    p["gabarit"].update({
        "id": "BRES-A4", "version": "R124", "zero_mode": "BUTEE_ZERO",
        "calibration_source": "manual-scale-check", "calibration_documented": True,
        "calibration_ok": True,
    })
    p["gabarit"]["scale_checks"][0]["measured_mm"] = 50.0
    p["gabarit"]["scale_checks"][1]["measured_mm"] = 100.0
    p["collection_sessions"] = []
    for i, slot in enumerate(p["session_slots"], 1):
        s = copy.deepcopy(slot); s["slot_status"] = "FILLED"
        s["captured_at"] = f"2026-09-23T0{i}:00:00+02:00"; s["device_model"] = "SAMSUNG-TEST"
        s["captures"]["recto"]["capture_id"] = f"{key}-S{i}-R"
        s["captures"]["verso"]["capture_id"] = f"{key}-S{i}-V"
        n1, n2 = offset + i, offset + i + 20
        s["captures"]["recto"]["source_file_sha256"] = (f"{n1:02x}" * 32)[:64]
        s["captures"]["verso"]["source_file_sha256"] = (f"{n2:02x}" * 32)[:64]
        s["captures"]["recto"]["geometry_signature"] = f"{key}-geom-r-{i}"
        s["captures"]["verso"]["geometry_signature"] = f"{key}-geom-v-{i}"
        s["stop_or_shoulder"].update({"position_mm": 12.0 + i/10, "uncertainty_mm": 0.2, "measurement_method": "manual-gabarit"})
        s["dual_face"]["measurement_method"] = "independent-photo-geometry"
        s["quality"].update({"focus_ok": True, "alignment_ok": True, "calibration_ok": True, "occlusion_ok": True})
        p["collection_sessions"].append(s)
    p["collection_summary"].update({
        "complete_sessions": 3, "all_capture_ids_unique": True, "all_capture_hashes_unique": True,
        "calibration_documented": True, "decision_authority": "NONE", "policy_status": "A_CONFIRMER",
        "packet_ready_for_review": False,
    })
    return p

checks = {}
p = fixture(); before = copy.deepcopy(p); r = mod.ingest_packet_with_provenance(p)
checks["accepted_packet_promoted_with_provenance"] = r["accepted_for_diagnostics"] is True and r["source_capture_sha256_provenance_complete"] is True
checks["source_packet_not_mutated"] = p == before
checks["exactly_six_capture_records_preserved"] = r["source_capture_count"] == 6 and len(r["source_capture_provenance"]) == 6
checks["capture_ids_preserved"] = [x["capture_id"] for x in r["source_capture_provenance"]] == [
    "SYNTH-R130-001-S1-R", "SYNTH-R130-001-S1-V", "SYNTH-R130-001-S2-R", "SYNTH-R130-001-S2-V", "SYNTH-R130-001-S3-R", "SYNTH-R130-001-S3-V"
]
checks["source_hashes_preserved_lowercase"] = all(len(x["source_file_sha256"]) == 64 and x["source_file_sha256"] == x["source_file_sha256"].lower() for x in r["source_capture_provenance"])
checks["packet_and_provenance_digests_present"] = len(r["source_packet_sha256"]) == 64 and len(r["provenance_digest_sha256"]) == 64
checks["no_decision_authority_added"] = r["decision_authority"] == "NONE" and r["policy_status"] == "A_CONFIRMER" and r["validated_reference"] is None and r["candidate_selection_allowed"] is False
checks["no_runtime_catalogue_or_threshold_authority"] = r["runtime_mutation_allowed"] is False and r["canonical_catalogue_write_allowed"] is False and r["acceptance_threshold_authorized"] is False and r["automatic_validation_allowed"] is False

p = fixture(); p["collection_sessions"][2]["captures"]["verso"]["source_file_sha256"] = p["collection_sessions"][0]["captures"]["recto"]["source_file_sha256"]
r = mod.ingest_packet_with_provenance(p)
checks["reused_source_file_rejected"] = r["accepted_for_diagnostics"] is False and any("photo_file_reused_across_packet" in e or "source_file_sha256_reused_within_packet" in e for e in r["errors"])

p = fixture(); p["collection_sessions"][0]["captures"]["recto"]["source_file_sha256"] = "xyz"
r = mod.ingest_packet_with_provenance(p)
checks["invalid_source_hash_rejected"] = r["accepted_for_diagnostics"] is False

errors = [k for k,v in checks.items() if not v]
out = {"schema":"bres-live-diagnostic-capture-provenance-test-r130-v1","milestone":"BRES Cles catalogue audit R130","checks":checks,"errors":errors,"ok":not errors}
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_CAPTURE_PROVENANCE_R130.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_DIAGNOSTIC_CAPTURE_PROVENANCE_R130.txt").write_text("\n".join(["BRES CLES — PROVENANCE CAPTURES R130",""]+[("OK  "+k if v else "ECHEC  "+k) for k,v in checks.items()]+["","SELFTEST OK" if not errors else "SELFTEST ECHEC"])+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
