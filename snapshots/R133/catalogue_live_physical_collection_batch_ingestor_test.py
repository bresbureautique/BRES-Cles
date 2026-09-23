from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("batch_ingestor", ROOT / "physical_collection_batch_ingestor_r133.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base = json.loads((ROOT / "catalogue/evidence/live_discriminant_collection_packet_r125.json").read_text(encoding="utf-8"))


def make_folder(root: Path, name: str, key_id: str, pair=("VAC104", "VAC105"), token="A"):
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    p = copy.deepcopy(base)
    p["physical_key_id"] = key_id
    p["candidate_pair"] = {"a": pair[0], "b": pair[1]}
    p["gabarit"].update({"id":"BRES-A4","version":"R124","zero_mode":"BUTEE_ZERO","calibration_source":"manual-scale-check","calibration_documented":True,"calibration_ok":True})
    p["gabarit"]["scale_checks"][0]["measured_mm"] = 50.0
    p["gabarit"]["scale_checks"][1]["measured_mm"] = 100.0
    p["collection_sessions"] = []
    for i, slot in enumerate(p["session_slots"], 1):
        s = copy.deepcopy(slot); s["slot_status"] = "FILLED"; s["captured_at"] = f"2026-09-23T0{i}:30:00+02:00"; s["device_model"] = "SAMSUNG-TEST"
        for face_key, face_code, suffix in (("recto","RECTO","R"),("verso","VERSO","V")):
            rel = Path("captures") / f"S{i}_{face_key}.jpg"; path = folder / rel; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"R133-{token}-{key_id}-{i}-{face_key}-unique-source".encode("utf-8")); sha = hashlib.sha256(path.read_bytes()).hexdigest()
            cap = s["captures"][face_key]; cap.update({"side":face_code,"capture_id":f"{key_id}-{token}-S{i}-{suffix}","source_file_relpath":rel.as_posix(),"source_file_sha256":sha,"geometry_signature":f"geom-{token}-{i}-{face_key}"})
        s["stop_or_shoulder"].update({"position_mm":12.0+i/10,"uncertainty_mm":0.2,"measurement_method":"manual-gabarit"}); s["dual_face"]["measurement_method"]="independent-photo-geometry"; s["quality"].update({"focus_ok":True,"alignment_ok":True,"calibration_ok":True,"occlusion_ok":True}); p["collection_sessions"].append(s)
    p["collection_summary"].update({"complete_sessions":3,"all_capture_ids_unique":True,"all_capture_hashes_unique":True,"calibration_documented":True,"decision_authority":"NONE","policy_status":"A_CONFIRMER","packet_ready_for_review":False})
    (folder / "packet.json").write_text(json.dumps(p, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return folder,p

def rewrite_packet(folder, packet): (folder / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

checks={}
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"key-a","SYNTH-R133-A",token="A"); f2,p2=make_folder(root,"key-b","SYNTH-R133-B",token="B"); r=mod.import_collection_folders([f1,f2]); ps=r["pair_summary"]["VAC104::VAC105"]
    checks["two_independent_keys_same_pair_are_kept_separate"] = r["accepted_folder_count"]==2 and r["distinct_physical_keys"]==2 and ps["distinct_physical_keys"]==2
    checks["pair_becomes_ready_for_traceable_descriptive_review"] = ps["traceable_descriptive_review_ready"] is True
    checks["r130_registry_receives_two_entries"] = r["registry"]["pairs"]["VAC104::VAC105"]["summary"]["diagnostic_entries"]==2
    checks["identity_is_preserved"] = set(ps["physical_key_ids"])=={"SYNTH-R133-A","SYNTH-R133-B"}
    checks["batch_remains_non_authoritative"] = r["decision_authority"]=="NONE" and r["policy_status"]=="A_CONFIRMER" and r["validated_reference"] is None and r["automatic_validation_allowed"] is False and r["canonical_catalogue_write_allowed"] is False and r["runtime_mutation_allowed"] is False and r["acceptance_threshold_authorized"] is False and r["candidate_selection_allowed"] is False
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"key-a","SYNTH-R133-C",token="C1"); f2,p2=make_folder(root,"key-b","SYNTH-R133-D",token="C2"); c1=p1["collection_sessions"][0]["captures"]["recto"]; c2=p2["collection_sessions"][0]["captures"]["recto"]; src1=f1/c1["source_file_relpath"]; src2=f2/c2["source_file_relpath"]; src2.write_bytes(src1.read_bytes()); c2["source_file_sha256"]=hashlib.sha256(src2.read_bytes()).hexdigest(); rewrite_packet(f2,p2); r=mod.import_collection_folders([f1,f2]); errs=[e for row in r["rejected_folders"] for e in row["errors"]]; checks["cross_folder_source_bytes_reuse_is_rejected"] = r["accepted_folder_count"]==1 and "source_file_sha256_reused_across_folders" in errs
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"key-a","SYNTH-R133-E",token="E1"); f2,p2=make_folder(root,"key-b","SYNTH-R133-F",token="E2"); p2["collection_sessions"][2]["captures"]["recto"]["capture_id"]=p1["collection_sessions"][1]["captures"]["verso"]["capture_id"]; rewrite_packet(f2,p2); r=mod.import_collection_folders([f1,f2]); errs=[e for row in r["rejected_folders"] for e in row["errors"]]; checks["cross_folder_capture_id_reuse_is_rejected"] = r["accepted_folder_count"]==1 and "capture_id_reused_across_folders" in errs
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"same-key-first","SYNTH-R133-G",pair=("VAC104","VAC105"),token="G1"); f2,p2=make_folder(root,"same-key-second","SYNTH-R133-G",pair=("GV1","GV3"),token="G2"); r=mod.import_collection_folders([f1,f2]); errs=[e for row in r["rejected_folders"] for e in row["errors"]]; checks["same_physical_key_cannot_switch_candidate_pair"] = r["accepted_folder_count"]==1 and "physical_key_id_mapped_to_multiple_pairs" in errs
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"pair-1","SYNTH-R133-H",pair=("VAC104","VAC105"),token="H1"); f2,p2=make_folder(root,"pair-2","SYNTH-R133-I",pair=("GV1","GV3"),token="H2"); r=mod.import_collection_folders([f1,f2]); checks["different_pairs_remain_separate"] = r["accepted_folder_count"]==2 and set(r["pair_summary"])=={"VAC104::VAC105","GV1::GV3"} and len(r["registry"]["pairs"])==2
with tempfile.TemporaryDirectory() as td:
    root=Path(td); f1,p1=make_folder(root,"valid","SYNTH-R133-J",token="J1"); f2,p2=make_folder(root,"broken","SYNTH-R133-K",token="J2"); (f2/p2["collection_sessions"][1]["captures"]["verso"]["source_file_relpath"]).unlink(); r=mod.import_collection_folders([f1,f2]); checks["r132_rejected_folder_never_reaches_registry"] = r["accepted_folder_count"]==1 and r["rejected_folder_count"]==1 and r["registry"]["pairs"]["VAC104::VAC105"]["summary"]["diagnostic_entries"]==1
errors=[k for k,v in checks.items() if not v]; out={"schema":"bres-live-physical-collection-batch-ingestor-test-r133-v1","milestone":"BRES Cles catalogue audit R133","checks":checks,"errors":errors,"ok":not errors}; print(json.dumps(out,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
