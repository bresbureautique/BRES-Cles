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


r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r145")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r145")
r141 = load_module(ROOT / "correction_state_tracker_r141.py", "r141_for_r145")
r142 = load_module(ROOT / "correction_dependency_guard_r142.py", "r142_for_r145")
r144 = load_module(ROOT / "collection_checkpoint_r144.py", "r144_for_r145")
r145 = load_module(ROOT / "collection_checkpoint_delta_r145.py", "r145_delta")

workspace = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
queue = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").read_text(encoding="utf-8"))
empty_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(workspace))
state0 = r141.create_tracking_state(queue, empty_sheet)
before = r144.export_checkpoint(state0, queue, empty_sheet)

# Simulate genuine documentary progress using one real-looking, but synthetic-test-only,
# prepared workspace. This never counts as physical evidence; it exists only in the test.
partial_workspace = copy.deepcopy(workspace)
key = partial_workspace["workspaces"][0]["prepared_key_slots"][0]
key_slot_id = key["workspace_key_slot_id"]
key["physical_key_id"] = "R145-TEST-PHYSICAL-KEY-0001"
key["physical_key_identity_confirmed"] = True
s1 = key["sessions"][0]
s1["real_session_id"] = "R145-TEST-SESSION-S1-0001"
for idx, face in enumerate(s1["faces"], start=1):
    face["capture_id"] = f"R145-TEST-CAPTURE-{idx:02d}"
    face["source_path"] = f"captures/r145_test_s1_{face['face'].lower()}.jpg"
    face["source_file_sha256"] = ("a" if idx == 1 else "b") * 64
    face["captured"] = True
    face["verified"] = True
s1["session_complete"] = True
s1["session_verified"] = True
partial_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(partial_workspace))

updates = []
for item in queue["items"]:
    if item["workspace_key_slot_id"] != key_slot_id:
        continue
    is_key_identity = item["scope"] == "KEY" and int(item["phase_rank"]) < 50
    is_s1_chain = item.get("session_slot") == "S1" and int(item["phase_rank"]) <= 51
    if is_key_identity or is_s1_chain:
        updates.append({"work_item_id": item["work_item_id"], "status": "REALISEE"})
partial_state = r142.apply_dependency_guarded_status_updates(state0, queue, partial_sheet, updates)
after = r144.export_checkpoint(partial_state, queue, partial_sheet)
delta = r145.compare_checkpoints(before, after)
no_change = r145.compare_checkpoints(before, before)


def rehash(cp):
    cp["checkpoint_payload_sha256"] = r144._canonical_sha256(r144._payload_without_self_hash(cp))
    return cp


def rejected(fn, token):
    try:
        fn()
    except ValueError as exc:
        return token in str(exc)
    return False


tampered = copy.deepcopy(after)
tampered["mutable_items"][0]["status"] = "BLOQUEE"

queue_drift = copy.deepcopy(after)
queue_drift["source_queue_sha256"] = "0" * 64
rehash(queue_drift)

history_rewrite = copy.deepcopy(after)
if history_rewrite["history"]:
    history_rewrite["history"][0] = copy.deepcopy(history_rewrite["history"][0])
    history_rewrite["history"][0]["work_item_id"] = "R140-WORK-FORGED"
rehash(history_rewrite)

count_regression = copy.deepcopy(after)
changed_id = delta["changed_work_items"][0]["work_item_id"]
for item in count_regression["mutable_items"]:
    if item["work_item_id"] == changed_id:
        item["status_change_count"] = -1
        break
rehash(count_regression)

policy_escalation = copy.deepcopy(after)
policy_escalation["evidence_credit"] = 1
rehash(policy_escalation)

checks = {
    "tracks_all_1462_items": delta["tracked_work_item_count"] == 1462,
    "genuine_progress_produces_changes": delta["changed_work_item_count"] > 0,
    "correction_sheet_change_is_explicit": delta["correction_sheet_changed"] is True,
    "history_growth_is_reported": delta["history_events_added_count"] > 0,
    "transitions_are_counted": sum(delta["transition_counts"].values()) == delta["changed_work_item_count"],
    "no_change_delta_is_empty": no_change["changed_work_item_count"] == 0 and no_change["history_events_added_count"] == 0,
    "tampered_checkpoint_is_rejected": rejected(lambda: r145.compare_checkpoints(before, tampered), "payload_hash_mismatch"),
    "queue_drift_is_rejected": rejected(lambda: r145.compare_checkpoints(before, queue_drift), "source_queue_drift"),
    "history_rewrite_is_rejected": rejected(lambda: r145.compare_checkpoints(after, history_rewrite), "history_not_append_only"),
    "negative_or_regressing_change_counter_is_rejected": rejected(lambda: r145.compare_checkpoints(before, count_regression), "status_change_count_invalid") or rejected(lambda: r145.compare_checkpoints(before, count_regression), "status_change_count_regression"),
    "policy_escalation_is_rejected": rejected(lambda: r145.compare_checkpoints(before, policy_escalation), "policy_escalation:evidence_credit"),
    "delta_has_integrity_fingerprint": len(delta["delta_report_sha256"]) == 64,
    "delta_never_grants_evidence": delta["evidence_credit"] == 0 and delta["counts_as_real_physical_evidence"] is False,
    "runtime_and_catalogue_remain_read_only": delta["active_test_runtime"] == "V2.28 TEST R116" and delta["stable_version"] == "V2.27" and delta["canonical_catalogue_write_allowed"] is False and delta["runtime_mutation_allowed"] is False,
    "no_reference_decision_is_created": delta["decision_authority"] == "NONE" and delta["automatic_validation_allowed"] is False and delta["candidate_selection_allowed"] is False and delta["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-checkpoint-delta-test-r145-v1",
    "milestone": "BRES Cles catalogue audit R145",
    "changed_work_item_count": delta["changed_work_item_count"],
    "history_events_added_count": delta["history_events_added_count"],
    "transition_counts": delta["transition_counts"],
    "correction_sheet_changed": delta["correction_sheet_changed"],
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_DELTA_R145.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_DELTA_R145.txt").write_text("\n".join([
    "BRES CLES — DELTA CHECKPOINT R145", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    f"ACTIONS MODIFIEES {delta['changed_work_item_count']}",
    f"EVENEMENTS AJOUTES {delta['history_events_added_count']}",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
