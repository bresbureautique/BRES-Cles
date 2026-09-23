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

r138 = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_for_r140")
r139 = load_module(ROOT / "correction_sheet_r139.py", "r139_for_r140")
r140 = load_module(ROOT / "correction_work_queue_r140.py", "r140_queue")

template = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
original = copy.deepcopy(template)
completeness = r138.analyze_collection_workspace(template)
sheet = r139.build_correction_sheet(completeness)
queue1 = r140.build_correction_work_queue(sheet)
queue2 = r140.build_correction_work_queue(copy.deepcopy(sheet))

items = queue1["items"]
phases = [i["phase_rank"] for i in items]
ids = [i["work_item_id"] for i in items]
identity_positions = [i for i,x in enumerate(items) if x["action"] == "RENSEIGNER_IDENTITE_CLE"]
capture_positions = [i for i,x in enumerate(items) if x["action"] in {"RENSEIGNER_ID_CAPTURE", "RENSEIGNER_SOURCE", "CALCULER_SHA256_SOURCE"}]
verify_positions = [i for i,x in enumerate(items) if x["action"] == "VERIFIER_CAPTURE"]
final_positions = [i for i,x in enumerate(items) if x["action"] in {"FINALISER_SEANCE", "VERIFIER_SEANCE", "FINALISER_DOSSIER_CLE", "VERIFIER_DOSSIER_CLE"}]

# Inject one future action to verify the safe manual-control fallback.
future_sheet = copy.deepcopy(sheet)
future_sheet["pair_sheets"][0]["keys"][0]["actions"].append({
    "scope": "KEY", "reason": "future_reason_r999", "action": "ACTION_FUTURE_INCONNUE", "instruction": "Inspecter."})
future_queue = r140.build_correction_work_queue(future_sheet)
future_item = next(i for i in future_queue["items"] if i["action"] == "ACTION_FUTURE_INCONNUE")

checks = {
    "workspace_source_not_mutated": template == original,
    "correction_sheet_source_not_mutated": sheet == r139.build_correction_sheet(r138.analyze_collection_workspace(template)),
    "all_17_pairs_are_represented": len(queue1["pair_summary"]) == 17 and queue1["critical_pair_count"] == 17,
    "all_r139_actions_preserved": queue1["work_item_count"] == sheet["action_count"] == len(items),
    "work_item_ids_are_unique_and_contiguous": ids == [f"R140-WORK-{n:05d}" for n in range(1, len(items)+1)] and len(set(ids)) == len(ids),
    "queue_generation_is_deterministic": queue1 == queue2,
    "phase_order_is_monotonic": phases == sorted(phases),
    "identity_precedes_capture_provenance": max(identity_positions) < min(capture_positions),
    "capture_provenance_precedes_capture_verification": max(capture_positions) < min(verify_positions),
    "capture_verification_precedes_finalisation": max(verify_positions) < min(final_positions),
    "empty_workspace_first_phase_is_identity": items[0]["phase"] == "STRUCTURE_IDENTITE",
    "each_pair_has_work_and_first_item_pointer": all(p["work_item_count"] > 0 and p["first_work_item_id"] for p in queue1["pair_summary"]),
    "unknown_action_falls_back_to_manual_control": future_item["phase"] == "CONTROLE_MANUEL" and future_item["phase_rank"] == 90,
    "queue_never_grants_evidence": queue1["counts_as_real_physical_evidence"] is False and queue1["queue_completion_counts_as_real_physical_evidence"] is False and queue1["evidence_credit"] == 0 and all(i["completion_grants_evidence_credit"] is False for i in items),
    "priority_does_not_use_measurements_or_recognition_score": queue1["measurements_used_for_priority"] is False and queue1["recognition_score_used_for_priority"] is False,
    "runtime_and_policy_remain_non_authoritative": queue1["active_test_runtime"] == "V2.28 TEST R116" and queue1["decision_authority"] == "NONE" and queue1["policy_status"] == "A_CONFIRMER" and queue1["canonical_catalogue_write_allowed"] is False and queue1["runtime_mutation_allowed"] is False and queue1["automatic_validation_allowed"] is False and queue1["acceptance_threshold_authorized"] is False and queue1["candidate_selection_allowed"] is False and queue1["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-work-queue-test-r140-v1",
    "milestone": "BRES Cles catalogue audit R140",
    "work_item_count": queue1["work_item_count"],
    "phase_counts": queue1["phase_counts"],
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_R140.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_R140.txt").write_text("\n".join(["BRES CLES — FILE DE TRAVAIL CORRECTION R140", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", f"WORK ITEMS {queue1['work_item_count']}", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_WORK_QUEUE_EMPTY_R140.json").write_text(json.dumps(queue1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
