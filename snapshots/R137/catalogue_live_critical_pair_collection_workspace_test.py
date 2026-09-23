from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("workspace137", ROOT / "critical_pair_collection_workspace_r137.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

plan = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_QUEUE_R135.json").read_text(encoding="utf-8"))
original = copy.deepcopy(plan)
out = mod.build_collection_workspace(plan)

pairs = out["workspaces"]
key_slots = [k for p in pairs for k in p["prepared_key_slots"]]
sessions = [s for k in key_slots for s in k["sessions"]]
faces = [f for s in sessions for f in s["faces"]]
slot_ids = [k["workspace_key_slot_id"] for k in key_slots]

checks = {
    "source_plan_not_mutated": plan == original,
    "all_17_pairs_have_workspace_rows": len(pairs) == 17 and out["critical_pair_count"] == 17,
    "current_empty_queue_prepares_34_missing_key_slots": len(key_slots) == 34 and out["prepared_missing_key_slots"] == 34,
    "three_sessions_per_key_prepares_102_sessions": len(sessions) == 102 and out["prepared_session_slots"] == 102,
    "recto_verso_prepares_204_capture_slots": len(faces) == 204 and out["prepared_face_capture_slots"] == 204,
    "workspace_key_slot_ids_are_unique": len(slot_ids) == len(set(slot_ids)),
    "all_key_identities_start_empty": all(k["physical_key_id"] is None and k["physical_key_identity_confirmed"] is False for k in key_slots),
    "all_real_session_ids_start_empty": all(s["real_session_id"] is None for s in sessions),
    "all_capture_provenance_starts_empty": all(f["capture_id"] is None and f["source_path"] is None and f["source_file_sha256"] is None for f in faces),
    "all_capture_and_session_completion_flags_start_false": all(not f["captured"] and not f["verified"] for f in faces) and all(not s["session_complete"] and not s["session_verified"] for s in sessions),
    "all_prepared_slots_have_zero_evidence_credit": all(k["evidence_credit"] == 0 for k in key_slots) and all(s["evidence_credit"] == 0 for s in sessions) and all(f["evidence_credit"] == 0 for f in faces),
    "prepared_workspace_never_counts_as_real_evidence": out["workspace_counts_as_real_physical_evidence"] is False and out["prepared_slots_must_not_be_counted_as_evidence"] is True and all(k["counts_as_real_physical_evidence"] is False for k in key_slots),
    "measurements_never_drive_workspace": out["measurements_used_for_workspace"] is False and all(p["measurements_used_for_workspace"] is False for p in pairs),
    "runtime_is_r116_and_workspace_is_non_authoritative": out["active_test_runtime"] == "V2.28 TEST R116" and out["decision_authority"] == "NONE" and out["policy_status"] == "A_CONFIRMER" and out["validated_reference"] is None and out["canonical_catalogue_write_allowed"] is False and out["runtime_mutation_allowed"] is False and out["automatic_validation_allowed"] is False and out["acceptance_threshold_authorized"] is False and out["candidate_selection_allowed"] is False,
}

# A row already satisfied by documented real keys must not get a fake new slot.
partial = copy.deepcopy(plan)
row = partial["collection_queue"][0]
row["missing_independent_physical_keys"] = 0
row["missing_documented_sessions"] = 0
row["collection_action"] = "NO_ADDITIONAL_COLLECTION_REQUIRED_FOR_DESCRIPTIVE_REVIEW"
partial_out = mod.build_collection_workspace(partial)
checks["satisfied_pair_gets_no_empty_slot"] = len(partial_out["workspaces"][0]["prepared_key_slots"]) == 0 and partial_out["prepared_missing_key_slots"] == 32

# Prepared workspaces may only originate from a REAL_PHYSICAL collection plan.
bad_origin = copy.deepcopy(plan)
bad_origin["evidence_origin"] = "SYNTHETIC_TEST"
try:
    mod.build_collection_workspace(bad_origin)
    checks["synthetic_plan_is_rejected_for_real_capture_workspace"] = False
except ValueError as exc:
    checks["synthetic_plan_is_rejected_for_real_capture_workspace"] = "real_physical" in str(exc)

# Spoofed authority is rejected before any workspace is created.
bad_authority = copy.deepcopy(plan)
bad_authority["collection_queue"][0]["validated_reference"] = bad_authority["collection_queue"][0]["candidate_pair"]["a"]
try:
    mod.build_collection_workspace(bad_authority)
    checks["spoofed_reference_authority_is_rejected"] = False
except ValueError as exc:
    checks["spoofed_reference_authority_is_rejected"] = "decision_escalation" in str(exc)

errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-workspace-test-r137-v1",
    "milestone": "BRES Cles catalogue audit R137",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_R137.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_R137.txt").write_text("\n".join(["BRES CLES — ESPACES DE COLLECTE R137", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
