from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
prov = load("prov", ROOT / "provenance_ingestor_r130.py")
reg = load("reg130", ROOT / "diagnostic_pair_registry_r130.py")
base = json.loads((ROOT / "catalogue/evidence/live_discriminant_collection_packet_r125.json").read_text(encoding="utf-8"))


def fixture(key, offset):
    p = copy.deepcopy(base); p["physical_key_id"] = key; p["candidate_pair"] = {"a":"VAC104","b":"VAC105"}
    p["gabarit"].update({"id":"BRES-A4","version":"R124","zero_mode":"BUTEE_ZERO","calibration_source":"manual-scale-check","calibration_documented":True,"calibration_ok":True})
    p["gabarit"]["scale_checks"][0]["measured_mm"] = 50.0; p["gabarit"]["scale_checks"][1]["measured_mm"] = 100.0
    p["collection_sessions"] = []
    for i, slot in enumerate(p["session_slots"],1):
        s=copy.deepcopy(slot); s["slot_status"]="FILLED"; s["captured_at"]=f"2026-09-23T1{i}:00:00+02:00"; s["device_model"]="SAMSUNG-TEST"
        s["captures"]["recto"]["capture_id"]=f"{key}-S{i}-R"; s["captures"]["verso"]["capture_id"]=f"{key}-S{i}-V"
        s["captures"]["recto"]["source_file_sha256"]=(f"{offset+i:02x}"*32)[:64]; s["captures"]["verso"]["source_file_sha256"]=(f"{offset+i+20:02x}"*32)[:64]
        s["captures"]["recto"]["geometry_signature"]=f"{key}-r{i}"; s["captures"]["verso"]["geometry_signature"]=f"{key}-v{i}"
        s["stop_or_shoulder"].update({"position_mm":12+i/10,"uncertainty_mm":0.2,"measurement_method":"manual-gabarit"}); s["dual_face"]["measurement_method"]="independent-photo-geometry"
        s["quality"].update({"focus_ok":True,"alignment_ok":True,"calibration_ok":True,"occlusion_ok":True}); p["collection_sessions"].append(s)
    p["collection_summary"].update({"complete_sessions":3,"all_capture_ids_unique":True,"all_capture_hashes_unique":True,"calibration_documented":True,"decision_authority":"NONE","policy_status":"A_CONFIRMER","packet_ready_for_review":False})
    return p

checks={}
r0=reg.new_registry(); s1=prov.ingest_packet_with_provenance(fixture("KEY-R130-A",0)); before=copy.deepcopy(s1)
r1=reg.add_diagnostic_result(r0,s1); checks["accepted_r130_enters_parallel_registry"] = reg.summarize_pair(r1,"VAC104","VAC105")["diagnostic_entries"]==1
checks["source_not_mutated"] = s1==before
entry=r1["pairs"]["VAC104::VAC105"]["entries"][0]
checks["capture_ids_and_hashes_survive_registry"] = len(entry["source_capture_provenance"])==6 and entry["source_capture_provenance"]==s1["source_capture_provenance"]
checks["packet_and_provenance_digests_survive_registry"] = entry["source_packet_sha256"]==s1["source_packet_sha256"] and entry["provenance_digest_sha256"]==s1["provenance_digest_sha256"]

s2=prov.ingest_packet_with_provenance(fixture("KEY-R130-B",40)); r2=reg.add_diagnostic_result(r1,s2); summary=reg.summarize_pair(r2,"VAC104","VAC105")
checks["two_keys_keep_twelve_unique_source_captures"] = summary["distinct_physical_keys"]==2 and summary["source_capture_records"]==12 and summary["distinct_source_capture_sha256"]==12 and summary["source_capture_reuse_detected"] is False
checks["registry_remains_non_authoritative"] = summary["candidate_selection"] is None and summary["validated_reference"] is None and summary["acceptance_threshold_mm"] is None and summary["decision_authority"]=="NONE" and summary["policy_status"]=="A_CONFIRMER"

reuse=prov.ingest_packet_with_provenance(fixture("KEY-R130-C",80)); reuse["source_capture_provenance"][0]["source_file_sha256"] = s1["source_capture_provenance"][0]["source_file_sha256"]
try:
    reg.add_diagnostic_result(r2,reuse); checks["source_hash_reuse_across_registry_rejected"] = False
except ValueError as e:
    checks["source_hash_reuse_across_registry_rejected"] = "source_file_sha256_reused_across_registry" in str(e)

reuseid=prov.ingest_packet_with_provenance(fixture("KEY-R130-D",100)); reuseid["source_capture_provenance"][0]["capture_id"] = s1["source_capture_provenance"][0]["capture_id"]
try:
    reg.add_diagnostic_result(r2,reuseid); checks["capture_id_reuse_across_registry_rejected"] = False
except ValueError as e:
    checks["capture_id_reuse_across_registry_rejected"] = "capture_id_reused_across_registry" in str(e)

escalated=copy.deepcopy(s2); escalated["validated_reference"]="VAC104"
try:
    reg.add_diagnostic_result(r1,escalated); checks["validated_reference_escalation_rejected"] = False
except ValueError as e:
    checks["validated_reference_escalation_rejected"] = "source_policy_or_provenance_invalid:validated_reference" in str(e)

bad=copy.deepcopy(s2); bad["source_capture_sha256_provenance_complete"] = False
try:
    reg.add_diagnostic_result(r1,bad); checks["incomplete_provenance_cannot_enter_registry"] = False
except ValueError as e:
    checks["incomplete_provenance_cannot_enter_registry"] = "source_policy_or_provenance_invalid:source_capture_sha256_provenance_complete" in str(e)

checks["registry_never_authorizes_mutation_or_threshold"] = r2["runtime_mutation_allowed"] is False and r2["canonical_catalogue_write_allowed"] is False and r2["automatic_validation_allowed"] is False and r2["acceptance_threshold_authorized"] is False and r2["candidate_selection_allowed"] is False
errors=[k for k,v in checks.items() if not v]
out={"schema":"bres-live-diagnostic-provenance-registry-guard-r130-v1","milestone":"BRES Cles catalogue audit R130","checks":checks,"errors":errors,"ok":not errors}
(ROOT/"CATALOGUE_LIVE_DIAGNOSTIC_PROVENANCE_REGISTRY_GUARD_R130.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(ROOT/"CATALOGUE_LIVE_DIAGNOSTIC_PROVENANCE_REGISTRY_GUARD_R130.txt").write_text("\n".join(["BRES CLES — GARDE REGISTRE PROVENANCE R130",""]+[("OK  "+k if v else "ECHEC  "+k) for k,v in checks.items()]+["","SELFTEST OK" if not errors else "SELFTEST ECHEC"])+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
