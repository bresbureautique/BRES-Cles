from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("folder_adapter", ROOT / "physical_collection_folder_adapter_r132.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base = json.loads((ROOT / "catalogue/evidence/live_discriminant_collection_packet_r125.json").read_text(encoding="utf-8"))


def fixture(root: Path):
    p = copy.deepcopy(base)
    p["physical_key_id"] = "SYNTH-R132-001"
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
        s = copy.deepcopy(slot); s["slot_status"] = "FILLED"
        s["captured_at"] = f"2026-09-23T0{i}:00:00+02:00"; s["device_model"] = "SAMSUNG-TEST"
        for face_key, face_code, suffix in (("recto", "RECTO", "R"), ("verso", "VERSO", "V")):
            rel = Path("captures") / f"S{i}_{face_key}.jpg"
            path = root / rel; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"R132-{i}-{face_key}-unique-source".encode("utf-8"))
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            cap = s["captures"][face_key]
            cap.update({
                "side": face_code,
                "capture_id": f"SYNTH-R132-001-S{i}-{suffix}",
                "source_file_relpath": rel.as_posix(),
                "source_file_sha256": sha,
                "geometry_signature": f"geom-{i}-{face_key}",
            })
        s["stop_or_shoulder"].update({"position_mm": 12.0 + i/10, "uncertainty_mm": 0.2, "measurement_method": "manual-gabarit"})
        s["dual_face"]["measurement_method"] = "independent-photo-geometry"
        s["quality"].update({"focus_ok": True, "alignment_ok": True, "calibration_ok": True, "occlusion_ok": True})
        p["collection_sessions"].append(s)
    p["collection_summary"].update({
        "complete_sessions": 3, "all_capture_ids_unique": True, "all_capture_hashes_unique": True,
        "calibration_documented": True, "decision_authority": "NONE", "policy_status": "A_CONFIRMER",
        "packet_ready_for_review": False,
    })
    (root / "packet.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def fresh_case():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    packet = fixture(root)
    return tmp, root, packet

checks = {}

tmp, root, packet = fresh_case()
r = mod.import_collection_folder(root)
checks["complete_folder_is_accepted"] = r["accepted_for_diagnostics"] is True and r["import_status"] == "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS"
checks["three_sessions_six_files_verified"] = len(r["source_folder_manifest"]) == 6 and len({x["capture_session_id"] for x in r["source_folder_manifest"]}) == 3
checks["actual_source_sha256_preserved"] = all(len(x["source_file_sha256"]) == 64 for x in r["source_folder_manifest"])
checks["folder_digest_present"] = isinstance(r["source_folder_digest_sha256"], str) and len(r["source_folder_digest_sha256"]) == 64
checks["handoff_reaches_r130_provenance"] = r["diagnostic_envelope"]["schema"] == "bres-live-discriminant-provenance-ingestion-r130-v1" and r["diagnostic_envelope"]["accepted_for_diagnostics"] is True
checks["adapter_remains_non_authoritative"] = r["decision_authority"] == "NONE" and r["policy_status"] == "A_CONFIRMER" and r["validated_reference"] is None and r["automatic_validation_allowed"] is False and r["canonical_catalogue_write_allowed"] is False and r["runtime_mutation_allowed"] is False and r["acceptance_threshold_authorized"] is False
checks["manifest_uses_relative_paths_only"] = all(not Path(x["source_file_relpath"]).is_absolute() for x in r["source_folder_manifest"])
tmp.cleanup()

tmp, root, packet = fresh_case()
missing = root / packet["collection_sessions"][1]["captures"]["verso"]["source_file_relpath"]
missing.unlink()
r = mod.import_collection_folder(root)
checks["missing_photo_is_rejected"] = r["accepted_for_diagnostics"] is False and any("source_file_missing" in e for e in r["errors"])
tmp.cleanup()

tmp, root, packet = fresh_case()
a = packet["collection_sessions"][0]["captures"]["recto"]
b = packet["collection_sessions"][2]["captures"]["verso"]
(root / b["source_file_relpath"]).write_bytes((root / a["source_file_relpath"]).read_bytes())
b["source_file_sha256"] = hashlib.sha256((root / b["source_file_relpath"]).read_bytes()).hexdigest()
(root / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
r = mod.import_collection_folder(root)
checks["reused_photo_bytes_are_rejected"] = r["accepted_for_diagnostics"] is False and "source_file_sha256_reused_across_folder" in r["errors"]
tmp.cleanup()

tmp, root, packet = fresh_case()
packet["collection_sessions"][0]["captures"]["recto"]["side"] = "VERSO"
(root / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
r = mod.import_collection_folder(root)
checks["wrong_recto_verso_metadata_is_rejected"] = r["accepted_for_diagnostics"] is False and "session_1_recto_side_mismatch" in r["errors"]
tmp.cleanup()

tmp, root, packet = fresh_case()
packet["collection_sessions"][1]["captures"]["recto"]["source_file_sha256"] = "0" * 64
(root / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
r = mod.import_collection_folder(root)
checks["declared_sha256_mismatch_is_rejected"] = r["accepted_for_diagnostics"] is False and "session_2_recto_source_file_sha256_mismatch" in r["errors"]
tmp.cleanup()

tmp, root, packet = fresh_case()
packet["collection_sessions"][0]["captures"]["verso"]["source_file_relpath"] = "../outside.jpg"
(root / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
r = mod.import_collection_folder(root)
checks["path_traversal_is_rejected"] = r["accepted_for_diagnostics"] is False and "session_1_verso_source_file_relpath_invalid" in r["errors"]
tmp.cleanup()

errors = [k for k, v in checks.items() if not v]
out = {
    "schema": "bres-live-physical-collection-folder-adapter-test-r132-v1",
    "milestone": "BRES Cles catalogue audit R132",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_PHYSICAL_COLLECTION_FOLDER_ADAPTER_R132.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_PHYSICAL_COLLECTION_FOLDER_ADAPTER_R132.txt").write_text(
    "\n".join(["BRES CLES — ADAPTATEUR DOSSIER COLLECTE PHYSIQUE R132", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n",
    encoding="utf-8",
)
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
