from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r143")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r143")
r141 = load_module(ROOT / "correction_state_tracker_r141.py", "r141_for_r143")
r142 = load_module(ROOT / "correction_dependency_guard_r142.py", "r142_for_r143")
r143 = load_module(ROOT / "progress_hierarchy_r143.py", "r143_progress")

workspace = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
queue = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").read_text(encoding="utf-8"))
empty_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(workspace))
state0 = r141.create_tracking_state(queue, empty_sheet)
h0 = r143.build_progress_hierarchy(state0, queue, empty_sheet)

first_pair = h0["pairs"][0]
first_key_node = first_pair["keys"][0]
first_session_node = first_key_node["sessions"][0]
first_face_node = first_session_node["faces"][0]

# Complete one genuine documentary S1 exactly as R142 allows.
complete_s1 = copy.deepcopy(workspace)
key = complete_s1["workspaces"][0]["prepared_key_slots"][0]
key_slot_id = key["workspace_key_slot_id"]
key["physical_key_id"] = "R143-PHYSICAL-KEY-0001"
key["physical_key_identity_confirmed"] = True
s1 = key["sessions"][0]
s1["real_session_id"] = "R143-SESSION-S1-0001"
for idx, face in enumerate(s1["faces"], start=1):
    face["capture_id"] = f"R143-CAPTURE-{idx:02d}"
    face["source_path"] = f"captures/r143_s1_{face['face'].lower()}.jpg"
    face["source_file_sha256"] = ("c" if idx == 1 else "d") * 64
    face["captured"] = True
    face["verified"] = True
s1["session_complete"] = True
s1["session_verified"] = True
sheet_s1 = r139.build_correction_sheet(r138.analyze_collection_workspace(complete_s1))

updates = []
for item in queue["items"]:
    if item["workspace_key_slot_id"] != key_slot_id:
        continue
    is_key_identity = item["scope"] == "KEY" and int(item["phase_rank"]) < 50
    is_s1_chain = item.get("session_slot") == "S1" and int(item["phase_rank"]) <= 51
    if is_key_identity or is_s1_chain:
        updates.append({"work_item_id": item["work_item_id"], "status": "REALISEE"})
state_s1 = r142.apply_dependency_guarded_status_updates(state0, queue, sheet_s1, updates)
h1 = r143.build_progress_hierarchy(state_s1, queue, sheet_s1)

first_pair_h1 = h1["pairs"][0]
key_h1 = next(k for k in first_pair_h1["keys"] if k["workspace_key_slot_id"] == key_slot_id)
s1_h1 = next(s for s in key_h1["sessions"] if s["session_slot"] == "S1")
s2_h1 = next(s for s in key_h1["sessions"] if s["session_slot"] == "S2")

# Regression after completion must surface A_REFAIRE in the hierarchy.
regressed = copy.deepcopy(complete_s1)
regressed["workspaces"][0]["prepared_key_slots"][0]["sessions"][0]["faces"][0]["capture_id"] = None
regressed_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(regressed))
h_regressed = r143.build_progress_hierarchy(state_s1, queue, regressed_sheet)
regressed_key = next(k for k in h_regressed["pairs"][0]["keys"] if k["workspace_key_slot_id"] == key_slot_id)
regressed_s1 = next(s for s in regressed_key["sessions"] if s["session_slot"] == "S1")

checks = {
    "hierarchy_has_17_pairs": h0["critical_pair_count"] == 17 and len(h0["pairs"]) == 17,
    "hierarchy_has_34_keys": h0["key_slot_count"] == 34 and sum(len(p["keys"]) for p in h0["pairs"]) == 34,
    "hierarchy_has_102_sessions": h0["session_slot_count"] == 102,
    "hierarchy_has_204_faces": h0["face_slot_count"] == 204,
    "tracks_all_1462_r140_actions": h0["tracked_work_item_count"] == 1462,
    "empty_state_is_not_ready": h0["global_progress"]["ready"] is False and first_pair["ready"] is False and first_key_node["ready"] is False and first_session_node["ready"] is False and first_face_node["ready"] is False,
    "global_next_action_is_first_r140_identity_action": h0["global_progress"]["next_executable_action"]["work_item_id"] == "R140-WORK-00001",
    "one_completed_s1_becomes_ready": s1_h1["ready"] is True and all(face["ready"] for face in s1_h1["faces"]),
    "key_remains_not_ready_while_s2_s3_open": key_h1["ready"] is False and s2_h1["ready"] is False,
    "pair_remains_not_ready_while_other_work_open": first_pair_h1["ready"] is False,
    "next_action_remains_deterministic_after_partial_completion": h1["global_progress"]["next_executable_action"]["work_item_id"] == "R140-WORK-00002",
    "regression_is_visible_as_a_refaire": regressed_s1["progress_state"] == "A_REFAIRE" and regressed_s1["ready"] is False,
    "runtime_and_policy_remain_non_authoritative": h1["active_test_runtime"] == "V2.28 TEST R116" and h1["stable_version"] == "V2.27" and h1["evidence_credit"] == 0 and h1["counts_as_real_physical_evidence"] is False and h1["decision_authority"] == "NONE" and h1["canonical_catalogue_write_allowed"] is False and h1["runtime_mutation_allowed"] is False and h1["automatic_validation_allowed"] is False and h1["candidate_selection_allowed"] is False and h1["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-progress-hierarchy-test-r143-v1",
    "milestone": "BRES Cles catalogue audit R143",
    "counts": {
        "pairs": h0["critical_pair_count"],
        "keys": h0["key_slot_count"],
        "sessions": h0["session_slot_count"],
        "faces": h0["face_slot_count"],
        "work_items": h0["tracked_work_item_count"]
    },
    "initial_global_next_action": h0["global_progress"]["next_executable_action"],
    "after_one_s1_global_next_action": h1["global_progress"]["next_executable_action"],
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_PROGRESS_HIERARCHY_R143.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_PROGRESS_HIERARCHY_R143.txt").write_text("\n".join([
    "BRES CLES — HIERARCHIE AVANCEMENT R143", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    f"PAIRES {h0['critical_pair_count']}",
    f"CLES {h0['key_slot_count']}",
    f"SEANCES {h0['session_slot_count']}",
    f"FACES {h0['face_slot_count']}",
    f"ACTIONS {h0['tracked_work_item_count']}",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
# Persist a compact but complete current-state hierarchy for actual operational use.
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_PROGRESS_HIERARCHY_EMPTY_R143.json").write_text(json.dumps(h0, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
