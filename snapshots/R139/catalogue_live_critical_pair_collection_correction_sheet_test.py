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

completeness = load_module(ROOT / "critical_pair_collection_completeness_r138.py", "r138_completeness_for_r139")
mod = load_module(ROOT / "correction_sheet_r139.py", "r139_correction")

template = json.loads((ROOT / "catalogue/evidence/live_critical_pair_collection_workspace_template_r137.json").read_text(encoding="utf-8")) if (ROOT / "catalogue/evidence/live_critical_pair_collection_workspace_template_r137.json").exists() else None
if template is None:
    # R137 generated template is stored at snapshot root.
    template = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
original = copy.deepcopy(template)
empty_report = completeness.analyze_collection_workspace(template)
empty_sheet = mod.build_correction_sheet(empty_report)

# A controlled fixture that is complete except for one duplicated source across two faces.
fixture = copy.deepcopy(template)
key = fixture["workspaces"][0]["prepared_key_slots"][0]
key["physical_key_id"] = "PHYS-R139-A"
key["physical_key_identity_confirmed"] = True
key["key_workspace_complete"] = True
key["key_workspace_verified"] = True
for si, session in enumerate(key["sessions"], start=1):
    session["real_session_id"] = f"R139-S{si}"
    session["session_complete"] = True
    session["session_verified"] = True
    for fi, face in enumerate(session["faces"], start=1):
        face["capture_id"] = f"R139-CAP-{si}-{fi}"
        face["source_path"] = f"photos/r139-{si}-{fi}.jpg"
        face["source_file_sha256"] = (f"{si}{fi}" * 32)[:64]
        face["captured"] = True
        face["verified"] = True
# Force both provenance collisions on the second face of S1.
faces = key["sessions"][0]["faces"]
faces[1]["capture_id"] = faces[0]["capture_id"]
faces[1]["source_file_sha256"] = faces[0]["source_file_sha256"]
fixture_report = completeness.analyze_collection_workspace(fixture)
fixture_sheet = mod.build_correction_sheet(fixture_report)
problem_face = fixture_sheet["pair_sheets"][0]["keys"][0]["sessions"][0]["faces"][1]

# Unknown reasons remain visible rather than silently disappearing.
unknown_report = copy.deepcopy(empty_report)
unknown_report["pair_reports"][0]["keys"][0]["reasons"].append("future_reason_r999")
unknown_sheet = mod.build_correction_sheet(unknown_report)
unknown_actions = unknown_sheet["pair_sheets"][0]["keys"][0]["actions"]

checks = {
    "source_workspace_not_mutated": template == original,
    "all_17_pairs_have_correction_sheet": len(empty_sheet["pair_sheets"]) == 17,
    "empty_workspace_marks_34_keys_for_correction": empty_sheet["affected_key_slots"] == 34,
    "empty_workspace_has_actionable_items": empty_sheet["action_count"] > 0,
    "missing_identity_has_explicit_action": any(a["action"] == "RENSEIGNER_IDENTITE_CLE" for a in empty_sheet["pair_sheets"][0]["keys"][0]["actions"]),
    "missing_session_id_has_explicit_action": any(a["action"] == "RENSEIGNER_ID_SEANCE" for a in empty_sheet["pair_sheets"][0]["keys"][0]["sessions"][0]["actions"]),
    "missing_capture_provenance_has_explicit_actions": {a["action"] for a in empty_sheet["pair_sheets"][0]["keys"][0]["sessions"][0]["faces"][0]["actions"]} >= {"RENSEIGNER_ID_CAPTURE", "RENSEIGNER_SOURCE", "CALCULER_SHA256_SOURCE"},
    "duplicate_capture_and_sha_require_independent_recapture": sum(1 for a in problem_face["actions"] if a["action"] == "REFAIRE_CAPTURE_INDEPENDANTE") == 2,
    "recapture_counter_tracks_duplicate_provenance": fixture_sheet["recapture_action_count"] >= 2,
    "unknown_reason_is_not_dropped": any(a["reason"] == "future_reason_r999" and a["action"] == "CONTROLER_MANUELLEMENT" for a in unknown_actions),
    "correction_sheet_never_becomes_evidence": all(s["counts_as_real_physical_evidence"] is False and s["evidence_credit"] == 0 for s in [empty_sheet, fixture_sheet, unknown_sheet]),
    "runtime_and_policy_remain_non_authoritative": fixture_sheet["active_test_runtime"] == "V2.28 TEST R116" and fixture_sheet["decision_authority"] == "NONE" and fixture_sheet["policy_status"] == "A_CONFIRMER" and fixture_sheet["canonical_catalogue_write_allowed"] is False and fixture_sheet["runtime_mutation_allowed"] is False and fixture_sheet["automatic_validation_allowed"] is False and fixture_sheet["acceptance_threshold_authorized"] is False and fixture_sheet["candidate_selection_allowed"] is False and fixture_sheet["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-correction-sheet-test-r139-v1",
    "milestone": "BRES Cles catalogue audit R139",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_SHEET_R139.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_SHEET_R139.txt").write_text("\n".join(["BRES CLES — FICHE DE CORRECTION COLLECTE R139", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_CORRECTION_EMPTY_R139.json").write_text(json.dumps(empty_sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
