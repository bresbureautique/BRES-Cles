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


r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r144")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r144")
r141 = load_module(ROOT / "correction_state_tracker_r141.py", "r141_for_r144")
r142 = load_module(ROOT / "correction_dependency_guard_r142.py", "r142_for_r144")
r143 = load_module(ROOT / "progress_hierarchy_r143.py", "r143_for_r144")
r144 = load_module(ROOT / "collection_checkpoint_r144.py", "r144_checkpoint")

workspace = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
queue = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").read_text(encoding="utf-8"))
empty_sheet = r139.build_correction_sheet(r138.analyze_collection_workspace(workspace))
state0 = r141.create_tracking_state(queue, empty_sheet)

checkpoint0 = r144.export_checkpoint(state0, queue, empty_sheet)
restored0 = r144.import_checkpoint(checkpoint0, queue, empty_sheet)

partial_workspace = copy.deepcopy(workspace)
key = partial_workspace["workspaces"][0]["prepared_key_slots"][0]
key_slot_id = key["workspace_key_slot_id"]
key["physical_key_id"] = "R144-PHYSICAL-KEY-0001"
key["physical_key_identity_confirmed"] = True
s1 = key["sessions"][0]
s1["real_session_id"] = "R144-SESSION-S1-0001"
for idx, face in enumerate(s1["faces"], start=1):
    face["capture_id"] = f"R144-CAPTURE-{idx:02d}"
    face["source_path"] = f"captures/r144_s1_{face['face'].lower()}.jpg"
    face["source_file_sha256"] = ("e" if idx == 1 else "f") * 64
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
partial_h = r143.build_progress_hierarchy(partial_state, queue, partial_sheet)
next_id = partial_h["global_progress"]["next_executable_action"]["work_item_id"]
partial_state = r142.apply_dependency_guarded_status_updates(
    partial_state, queue, partial_sheet,
    [{"work_item_id": next_id, "status": "BLOQUEE", "block_reason": "TEST_R144_ATTENTE_CAPTURE"}],
)

checkpoint_partial = r144.export_checkpoint(partial_state, queue, partial_sheet)
restored_partial = r144.import_checkpoint(checkpoint_partial, queue, partial_sheet)


def rejected(fn, token):
    try:
        fn()
    except ValueError as exc:
        return token in str(exc)
    return False


tampered_payload = copy.deepcopy(checkpoint_partial)
tampered_payload["mutable_items"][0]["status"] = "BLOQUEE"

forged_status = copy.deepcopy(checkpoint_partial)
forged_status["mutable_items"][0]["status"] = "BLOQUEE"
forged_status["mutable_items"][0]["block_reason"] = "FORGED"
forged_status["checkpoint_payload_sha256"] = r144._canonical_sha256(r144._payload_without_self_hash(forged_status))

queue_drift = copy.deepcopy(queue)
queue_drift["items"][0]["instruction"] = "DRIFT"

sheet_drift = copy.deepcopy(partial_sheet)
sheet_drift["pair_sheets"][0]["policy_status"] = "DRIFT"

policy_escalation = copy.deepcopy(checkpoint_partial)
policy_escalation["evidence_credit"] = 1
policy_escalation["checkpoint_payload_sha256"] = r144._canonical_sha256(r144._payload_without_self_hash(policy_escalation))

checks = {
    "empty_checkpoint_tracks_all_1462_items": checkpoint0["work_item_count"] == 1462 and len(checkpoint0["mutable_items"]) == 1462,
    "empty_roundtrip_reconstructs_exact_state": restored0["exact_state_reconstructed"] is True and r144._canonical_sha256(restored0["state"]) == checkpoint0["reconstructed_state_sha256"],
    "empty_roundtrip_reconstructs_exact_dependency_projection": r144._canonical_sha256(restored0["dependency_report"]) == checkpoint0["dependency_snapshot_sha256"],
    "empty_roundtrip_reconstructs_exact_hierarchy_projection": r144._canonical_sha256(restored0["progress_hierarchy"]) == checkpoint0["hierarchy_snapshot_sha256"],
    "partial_checkpoint_preserves_completed_and_blocked_state": checkpoint_partial["completed_item_count"] > 0 and checkpoint_partial["blocked_item_count"] == 1,
    "partial_roundtrip_reconstructs_exact_state": r144._canonical_sha256(restored_partial["state"]) == checkpoint_partial["reconstructed_state_sha256"],
    "partial_roundtrip_preserves_history": restored_partial["state"]["history"] == partial_state["history"],
    "partial_roundtrip_preserves_next_action": restored_partial["progress_hierarchy"]["global_progress"]["next_executable_action"]["work_item_id"] == checkpoint_partial["global_next_executable_work_item_id"],
    "payload_tampering_is_rejected": rejected(lambda: r144.import_checkpoint(tampered_payload, queue, partial_sheet), "payload_hash_mismatch"),
    "forged_logically_inconsistent_status_is_rejected_even_with_rehashed_payload": rejected(lambda: r144.import_checkpoint(forged_status, queue, partial_sheet), "reconstructed_state_mismatch") or rejected(lambda: r144.import_checkpoint(forged_status, queue, partial_sheet), "stale_block_reason"),
    "queue_drift_is_rejected": rejected(lambda: r144.import_checkpoint(checkpoint_partial, queue_drift, partial_sheet), "source_queue_drift"),
    "correction_sheet_drift_is_rejected": rejected(lambda: r144.import_checkpoint(checkpoint_partial, queue, sheet_drift), "source_correction_sheet_drift"),
    "policy_escalation_is_rejected": rejected(lambda: r144.import_checkpoint(policy_escalation, queue, partial_sheet), "policy_escalation:evidence_credit"),
    "checkpoint_is_smaller_than_full_r141_state": len(json.dumps(checkpoint0, ensure_ascii=False).encode("utf-8")) < len(json.dumps(state0, ensure_ascii=False).encode("utf-8")),
    "checkpoint_never_grants_evidence": checkpoint_partial["evidence_credit"] == 0 and checkpoint_partial["counts_as_real_physical_evidence"] is False and restored_partial["evidence_credit"] == 0,
    "runtime_and_policy_remain_non_authoritative": checkpoint_partial["active_test_runtime"] == "V2.28 TEST R116" and checkpoint_partial["stable_version"] == "V2.27" and checkpoint_partial["decision_authority"] == "NONE" and checkpoint_partial["canonical_catalogue_write_allowed"] is False and checkpoint_partial["runtime_mutation_allowed"] is False and checkpoint_partial["automatic_validation_allowed"] is False and checkpoint_partial["candidate_selection_allowed"] is False and checkpoint_partial["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-checkpoint-test-r144-v1",
    "milestone": "BRES Cles catalogue audit R144",
    "empty_checkpoint_bytes": len(json.dumps(checkpoint0, ensure_ascii=False).encode("utf-8")),
    "full_empty_state_bytes": len(json.dumps(state0, ensure_ascii=False).encode("utf-8")),
    "partial_checkpoint": {
        "completed_item_count": checkpoint_partial["completed_item_count"],
        "blocked_item_count": checkpoint_partial["blocked_item_count"],
        "history_event_count": len(checkpoint_partial["history"]),
        "global_next_executable_work_item_id": checkpoint_partial["global_next_executable_work_item_id"],
    },
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_R144.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_R144.txt").write_text("\n".join([
    "BRES CLES — CHECKPOINT REPRENABLE R144", "",
    *[("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()], "",
    f"ACTIONS {checkpoint0['work_item_count']}",
    f"TAILLE CHECKPOINT VIDE {report['empty_checkpoint_bytes']} OCTETS",
    f"TAILLE ETAT R141 COMPLET {report['full_empty_state_bytes']} OCTETS",
    "SELFTEST OK" if not errors else "SELFTEST ECHEC",
]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CHECKPOINT_EMPTY_R144.json").write_text(json.dumps(checkpoint0, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
