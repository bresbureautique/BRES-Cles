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


r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r142")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r142")
r141 = load_module(ROOT / "correction_state_tracker_r141.py", "r141_for_r142")
r142 = load_module(ROOT / "correction_dependency_guard_r142.py", "r142_dependency")

workspace = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
queue = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").read_text(encoding="utf-8"))
empty_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(workspace))
state0 = r141.create_tracking_state(queue, empty_sheet)

first_key = workspace["workspaces"][0]["prepared_key_slots"][0]
key_slot_id = first_key["workspace_key_slot_id"]
finalise_s1 = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["session_slot"] == "S1" and i["action"] == "FINALISER_SEANCE")
verify_s1 = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["session_slot"] == "S1" and i["action"] == "VERIFIER_SEANCE")
finalise_key = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["action"] == "FINALISER_DOSSIER_CLE")


def sheet_for(ws):
    return r139.build_correction_sheet(r138.analyze_collection_workspace(ws))


def raises_value_error(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# Demonstrate the R141 gap R142 closes: setting only the finalisation flag makes
# the finalisation issue disappear, while capture/provenance work is still open.
premature = copy.deepcopy(workspace)
premature_key = premature["workspaces"][0]["prepared_key_slots"][0]
premature_key["sessions"][0]["session_complete"] = True
premature_sheet = sheet_for(premature)
r141_allows_flag_only_completion = not raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, premature_sheet,
    [{"work_item_id": finalise_s1["work_item_id"], "status": "REALISEE"}],
))
r142_rejects_flag_only_completion = raises_value_error(lambda: r142.apply_dependency_guarded_status_updates(
    state0, queue, premature_sheet,
    [{"work_item_id": finalise_s1["work_item_id"], "status": "REALISEE"}],
))

# Build one genuinely metadata-complete S1 (documentary only; no evidence credit).
complete_s1 = copy.deepcopy(workspace)
key = complete_s1["workspaces"][0]["prepared_key_slots"][0]
key["physical_key_id"] = "R142-PHYSICAL-KEY-0001"
key["physical_key_identity_confirmed"] = True
s1 = key["sessions"][0]
s1["real_session_id"] = "R142-SESSION-S1-0001"
for idx, face in enumerate(s1["faces"], start=1):
    face["capture_id"] = f"R142-CAPTURE-{idx:02d}"
    face["source_path"] = f"captures/r142_s1_{face['face'].lower()}.jpg"
    face["source_file_sha256"] = ("a" if idx == 1 else "b") * 64
    face["captured"] = True
    face["verified"] = True
s1["session_complete"] = True
s1["session_verified"] = True
complete_s1_sheet = sheet_for(complete_s1)

# Complete, in one externally atomic batch, every prerequisite for S1 plus
# FINALISER_SEANCE and VERIFIER_SEANCE. R142 sorts by R140 phase/sequence.
s1_updates = []
for item in queue["items"]:
    if item["workspace_key_slot_id"] != key_slot_id:
        continue
    is_key_identity = item["scope"] == "KEY" and int(item["phase_rank"]) < 50
    is_s1_chain = item.get("session_slot") == "S1" and int(item["phase_rank"]) <= 51
    if is_key_identity or is_s1_chain:
        s1_updates.append({"work_item_id": item["work_item_id"], "status": "REALISEE"})
state_s1 = r142.apply_dependency_guarded_status_updates(state0, queue, complete_s1_sheet, s1_updates)
report_s1 = r142.build_dependency_report(state_s1, queue, complete_s1_sheet)
rows_by_id = {row["work_item_id"]: row for row in report_s1["items"]}
state_s1_by_id = {item["work_item_id"]: item for item in state_s1["items"]}

# Even if the key-level "complete" flag is toggled early, S2/S3 open work must
# prevent key-folder finalisation.
premature_key_done = copy.deepcopy(complete_s1)
premature_key_done["workspaces"][0]["prepared_key_slots"][0]["key_workspace_complete"] = True
premature_key_sheet = sheet_for(premature_key_done)
key_finalisation_rejected_while_s2_s3_open = raises_value_error(lambda: r142.apply_dependency_guarded_status_updates(
    state_s1, queue, premature_key_sheet,
    [{"work_item_id": finalise_key["work_item_id"], "status": "REALISEE"}],
))

# Regress one capture after S1 was completed. The direct capture work reopens in
# R141, and R142 must also reopen the completed session parent chain.
regressed = copy.deepcopy(complete_s1)
regressed_face = regressed["workspaces"][0]["prepared_key_slots"][0]["sessions"][0]["faces"][0]
regressed_face["capture_id"] = None
regressed_sheet = sheet_for(regressed)
regressed_state = r142.reconcile_dependency_state(state_s1, queue, regressed_sheet)
regressed_by_id = {item["work_item_id"]: item for item in regressed_state["items"]}
dependency_reopen_events = [e for e in regressed_state["history"] if e.get("event_type") == "REOUVERTURE_AUTOMATIQUE_DEPENDANCE_ACTIVE_R142"]

# A failed batch must not mutate its input state (functions return copies only).
state_s1_before = json.loads(json.dumps(state_s1, ensure_ascii=False, sort_keys=True))
failed_batch_rejected = raises_value_error(lambda: r142.apply_dependency_guarded_status_updates(
    state_s1, queue, premature_key_sheet,
    [
        {"work_item_id": finalise_key["work_item_id"], "status": "REALISEE"},
        {"work_item_id": next(i["work_item_id"] for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i.get("session_slot") == "S2" and i["action"] == "RENSEIGNER_ID_SEANCE"), "status": "BLOQUEE", "block_reason": "TEST"},
    ],
))
input_unchanged_after_failed_batch = state_s1_before == json.loads(json.dumps(state_s1, ensure_ascii=False, sort_keys=True))

checks = {
    "r141_gap_is_reproducible_for_flag_only_session_finalisation": r141_allows_flag_only_completion,
    "r142_rejects_session_finalisation_while_dependencies_active": r142_rejects_flag_only_completion,
    "same_batch_dependencies_then_session_finalisation_are_allowed": state_s1_by_id[finalise_s1["work_item_id"]]["status"] == "REALISEE",
    "session_verification_requires_and_follows_session_finalisation": state_s1_by_id[verify_s1["work_item_id"]]["status"] == "REALISEE",
    "dependency_report_marks_completed_s1_chain_ready": rows_by_id[finalise_s1["work_item_id"]]["dependency_ready"] is True and rows_by_id[verify_s1["work_item_id"]]["dependency_ready"] is True,
    "key_finalisation_still_blocked_by_open_s2_s3_work": rows_by_id[finalise_key["work_item_id"]]["dependency_ready"] is False and key_finalisation_rejected_while_s2_s3_open,
    "capture_regression_reopens_completed_session_finaliser": regressed_by_id[finalise_s1["work_item_id"]]["status"] == "A_REFAIRE",
    "capture_regression_reopens_completed_session_verifier": regressed_by_id[verify_s1["work_item_id"]]["status"] == "A_REFAIRE",
    "dependency_reopen_is_audited": len(dependency_reopen_events) >= 2 and all(e["evidence_credit_granted"] is False for e in dependency_reopen_events),
    "failed_batch_is_externally_atomic": failed_batch_rejected and input_unchanged_after_failed_batch,
    "r140_work_item_ids_are_preserved": [i["work_item_id"] for i in state_s1["items"]] == [i["work_item_id"] for i in queue["items"]],
    "report_has_272_session_or_key_finalisation_verification_items": report_s1["finalisation_or_verification_item_count"] == 272,
    "runtime_and_policy_remain_non_authoritative": report_s1["active_test_runtime"] == "V2.28 TEST R116" and report_s1["evidence_credit"] == 0 and report_s1["counts_as_real_physical_evidence"] is False and report_s1["decision_authority"] == "NONE" and report_s1["canonical_catalogue_write_allowed"] is False and report_s1["runtime_mutation_allowed"] is False and report_s1["automatic_validation_allowed"] is False and report_s1["candidate_selection_allowed"] is False and report_s1["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-dependency-test-r142-v1",
    "milestone": "BRES Cles catalogue audit R142",
    "finalisation_or_verification_item_count": report_s1["finalisation_or_verification_item_count"],
    "dependency_ready_count_after_one_complete_s1": report_s1["dependency_ready_count"],
    "dependency_blocked_count_after_one_complete_s1": report_s1["dependency_blocked_count"],
    "dependency_reopen_event_count": len(dependency_reopen_events),
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_DEPENDENCY_R142.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_DEPENDENCY_R142.txt").write_text("\n".join([
    "BRES CLES — DEPENDANCES FINALISATION R142", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    f"FINALISATION/VERIFICATION ITEMS {report_s1['finalisation_or_verification_item_count']}",
    f"READY AFTER ONE COMPLETE S1 {report_s1['dependency_ready_count']}",
    f"BLOCKED AFTER ONE COMPLETE S1 {report_s1['dependency_blocked_count']}",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
