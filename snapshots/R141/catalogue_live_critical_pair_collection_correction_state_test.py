from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r141")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r141")
r141 = load_module(ROOT / "correction_state_tracker_r141.py", "r141_state")

workspace = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
queue = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").read_text(encoding="utf-8"))
empty_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(workspace))
state0 = r141.create_tracking_state(queue, empty_sheet)

first_pair = workspace["workspaces"][0]
first_key = first_pair["prepared_key_slots"][0]
key_slot_id = first_key["workspace_key_slot_id"]
identity_item = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["action"] == "RENSEIGNER_IDENTITE_CLE")
confirm_identity_item = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["action"] == "CONFIRMER_IDENTITE_CLE")
unresolved_capture_item = next(i for i in queue["items"] if i["workspace_key_slot_id"] == key_slot_id and i["action"] == "RENSEIGNER_ID_CAPTURE")

partial_workspace = copy.deepcopy(workspace)
partial_key = partial_workspace["workspaces"][0]["prepared_key_slots"][0]
partial_key["physical_key_id"] = "R141-PHYSICAL-KEY-0001"
partial_key["physical_key_identity_confirmed"] = True
partial_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(partial_workspace))

state1 = r141.apply_status_updates(state0, queue, partial_sheet, [
    {"work_item_id": identity_item["work_item_id"], "status": "REALISEE", "note": "Identité renseignée dans l'espace de collecte."},
    {"work_item_id": confirm_identity_item["work_item_id"], "status": "REALISEE", "note": "Identité physique confirmée."},
    {"work_item_id": unresolved_capture_item["work_item_id"], "status": "BLOQUEE", "block_reason": "PHOTO_PHYSIQUE_NON_ENCORE_DISPONIBLE"},
])
state1_roundtrip = json.loads(json.dumps(state1, ensure_ascii=False))
resumed = r141.reconcile_tracking_state(state1_roundtrip, queue, partial_sheet)


def raises_value_error(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


unresolved_completion_rejected = raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, empty_sheet,
    [{"work_item_id": unresolved_capture_item["work_item_id"], "status": "REALISEE"}],
))
duplicate_batch_rejected = raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, empty_sheet,
    [
        {"work_item_id": unresolved_capture_item["work_item_id"], "status": "BLOQUEE", "block_reason": "A"},
        {"work_item_id": unresolved_capture_item["work_item_id"], "status": "BLOQUEE", "block_reason": "B"},
    ],
))
invalid_status_rejected = raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, empty_sheet,
    [{"work_item_id": unresolved_capture_item["work_item_id"], "status": "TERMINEE"}],
))
missing_block_reason_rejected = raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, empty_sheet,
    [{"work_item_id": unresolved_capture_item["work_item_id"], "status": "BLOQUEE"}],
))
unknown_id_rejected = raises_value_error(lambda: r141.apply_status_updates(
    state0, queue, empty_sheet,
    [{"work_item_id": "R140-WORK-99999", "status": "BLOQUEE", "block_reason": "X"}],
))

drifted_queue = copy.deepcopy(queue)
drifted_queue["items"][0]["instruction"] += " DRIFT"
source_drift_rejected = raises_value_error(lambda: r141.reconcile_tracking_state(state0, drifted_queue, empty_sheet))

duplicate_queue = copy.deepcopy(queue)
duplicate_queue["items"][1]["work_item_id"] = duplicate_queue["items"][0]["work_item_id"]
duplicate_source_id_rejected = raises_value_error(lambda: r141.create_tracking_state(duplicate_queue, empty_sheet))

duplicate_semantic_queue = copy.deepcopy(queue)
for field in ["pair_key", "workspace_key_slot_id", "session_slot", "face", "scope", "action", "reason"]:
    duplicate_semantic_queue["items"][1][field] = duplicate_semantic_queue["items"][0].get(field)
duplicate_semantic_rejected = raises_value_error(lambda: r141.create_tracking_state(duplicate_semantic_queue, empty_sheet))

reappeared_workspace = copy.deepcopy(partial_workspace)
reappeared_key = reappeared_workspace["workspaces"][0]["prepared_key_slots"][0]
reappeared_key["physical_key_id"] = None
reappeared_key["physical_key_identity_confirmed"] = False
reappeared_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(reappeared_workspace))
reopened = r141.reconcile_tracking_state(state1, queue, reappeared_sheet)
reopened_by_id = {i["work_item_id"]: i for i in reopened["items"]}
state1_by_id = {i["work_item_id"]: i for i in state1["items"]}
resumed_by_id = {i["work_item_id"]: i for i in resumed["items"]}

checks = {
    "empty_queue_all_items_initially_to_do": state0["work_item_count"] == 1462 and state0["status_counts"]["A_FAIRE"] == 1462,
    "all_r140_work_item_ids_preserved": [i["work_item_id"] for i in state0["items"]] == [i["work_item_id"] for i in queue["items"]],
    "partial_real_correction_can_be_completed": state1_by_id[identity_item["work_item_id"]]["status"] == "REALISEE" and state1_by_id[confirm_identity_item["work_item_id"]]["status"] == "REALISEE",
    "completion_is_verified_against_current_sheet": state1_by_id[identity_item["work_item_id"]]["completion_verified_against_current_sheet"] is True,
    "unresolved_item_cannot_be_marked_completed": unresolved_completion_rejected,
    "blocked_item_requires_reason_and_keeps_issue_active": state1_by_id[unresolved_capture_item["work_item_id"]]["status"] == "BLOQUEE" and state1_by_id[unresolved_capture_item["work_item_id"]]["block_reason"] == "PHOTO_PHYSIQUE_NON_ENCORE_DISPONIBLE",
    "resume_roundtrip_preserves_ids_status_and_history": resumed["history"] == state1["history"] and resumed_by_id[identity_item["work_item_id"]]["status"] == "REALISEE" and resumed_by_id[unresolved_capture_item["work_item_id"]]["status"] == "BLOQUEE",
    "reappearing_issue_reopens_completed_item_to_redo": reopened_by_id[identity_item["work_item_id"]]["status"] == "A_REFAIRE" and reopened_by_id[confirm_identity_item["work_item_id"]]["status"] == "A_REFAIRE",
    "reopen_adds_audit_events": len(reopened["history"]) == len(state1["history"]) + 2 and reopened["history"][-1]["event_type"] == "REOUVERTURE_AUTOMATIQUE_ANOMALIE_REAPPARUE",
    "duplicate_batch_updates_rejected_atomically": duplicate_batch_rejected and state0["status_counts"]["A_FAIRE"] == 1462 and len(state0["history"]) == 0,
    "invalid_status_rejected": invalid_status_rejected,
    "missing_block_reason_rejected": missing_block_reason_rejected,
    "unknown_work_item_id_rejected": unknown_id_rejected,
    "source_queue_drift_rejected": source_drift_rejected,
    "duplicate_source_work_item_id_rejected": duplicate_source_id_rejected,
    "duplicate_semantic_source_action_rejected": duplicate_semantic_rejected,
    "completed_items_never_grant_evidence_credit": state1["evidence_credit"] == 0 and state1["completion_counts_as_real_physical_evidence"] is False and all(event["evidence_credit_granted"] is False for event in state1["history"]),
    "runtime_and_policy_remain_non_authoritative": state1["active_test_runtime"] == "V2.28 TEST R116" and state1["decision_authority"] == "NONE" and state1["policy_status"] == "A_CONFIRMER" and state1["canonical_catalogue_write_allowed"] is False and state1["runtime_mutation_allowed"] is False and state1["automatic_validation_allowed"] is False and state1["acceptance_threshold_authorized"] is False and state1["candidate_selection_allowed"] is False and state1["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-state-test-r141-v1",
    "milestone": "BRES Cles catalogue audit R141",
    "work_item_count": state0["work_item_count"],
    "partial_state_status_counts": state1["status_counts"],
    "history_events_after_partial_update": len(state1["history"]),
    "history_events_after_reopen": len(reopened["history"]),
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_STATE_R141.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_STATE_R141.txt").write_text("\n".join(["BRES CLES — SUIVI ETAT CORRECTIONS R141", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", f"WORK ITEMS {state0['work_item_count']}", f"PARTIAL HISTORY EVENTS {len(state1['history'])}", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_STATE_EMPTY_R141.json").write_text(json.dumps(state0, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
