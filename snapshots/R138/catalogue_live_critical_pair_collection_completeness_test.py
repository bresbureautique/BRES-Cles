from pathlib import Path
import copy
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("completeness138", ROOT / "critical_pair_collection_completeness_r138.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

template = json.loads((ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_WORKSPACE_TEMPLATE_R137.json").read_text(encoding="utf-8"))
original = copy.deepcopy(template)

# Empty prepared workspaces must remain incomplete and non-evidentiary.
empty_report = mod.analyze_collection_workspace(template)

# Fill one slot with deterministic synthetic metadata solely to test the checker.
fixture = copy.deepcopy(template)
key = fixture["workspaces"][0]["prepared_key_slots"][0]
key["physical_key_id"] = "SYNTHETIC-R138-KEY-001"
key["physical_key_identity_confirmed"] = True
key["key_workspace_complete"] = True
key["key_workspace_verified"] = True
for si, session in enumerate(key["sessions"], start=1):
    session["real_session_id"] = f"SYNTHETIC-R138-SESSION-{si:02d}"
    session["session_complete"] = True
    session["session_verified"] = True
    for fi, face in enumerate(session["faces"], start=1):
        ordinal = (si - 1) * 2 + fi
        face["capture_id"] = f"SYNTHETIC-R138-CAPTURE-{ordinal:02d}"
        face["source_path"] = f"synthetic/r138/capture-{ordinal:02d}.jpg"
        face["source_file_sha256"] = f"{ordinal:064x}"
        face["captured"] = True
        face["verified"] = True
fixture_report = mod.analyze_collection_workspace(fixture)
first_key = fixture_report["pair_reports"][0]["keys"][0]

# Missing VERSO should be detected without becoming evidence.
missing_verso = copy.deepcopy(fixture)
missing_verso["workspaces"][0]["prepared_key_slots"][0]["sessions"][1]["faces"] = [
    missing_verso["workspaces"][0]["prepared_key_slots"][0]["sessions"][1]["faces"][0]
]
missing_report = mod.analyze_collection_workspace(missing_verso)
missing_key = missing_report["pair_reports"][0]["keys"][0]

# Reuse a capture/hash across faces: both provenance collisions must be surfaced.
duplicate = copy.deepcopy(fixture)
faces = duplicate["workspaces"][0]["prepared_key_slots"][0]["sessions"][0]["faces"]
faces[1]["capture_id"] = faces[0]["capture_id"]
faces[1]["source_file_sha256"] = faces[0]["source_file_sha256"]
dup_report = mod.analyze_collection_workspace(duplicate)
dup_face = dup_report["pair_reports"][0]["keys"][0]["sessions"][0]["faces"][1]

# Bad SHA format must be incomplete.
bad_sha = copy.deepcopy(fixture)
bad_sha["workspaces"][0]["prepared_key_slots"][0]["sessions"][2]["faces"][1]["source_file_sha256"] = "badsha"
bad_sha_report = mod.analyze_collection_workspace(bad_sha)
bad_sha_face = bad_sha_report["pair_reports"][0]["keys"][0]["sessions"][2]["faces"][1]

checks = {
    "source_workspace_not_mutated": template == original,
    "empty_template_checks_34_slots": empty_report["prepared_key_slots_checked"] == 34,
    "empty_template_keeps_all_34_slots_incomplete": empty_report["metadata_incomplete_key_slots"] == 34 and empty_report["metadata_complete_key_slots"] == 0,
    "empty_template_is_not_ready_for_ingestion": empty_report["ready_for_separate_physical_ingestion"] is False,
    "synthetic_complete_slot_is_only_metadata_complete": first_key["metadata_complete_for_separate_ingestion"] is True,
    "synthetic_complete_slot_still_has_zero_evidence_credit": first_key["evidence_credit"] == 0 and first_key["counts_as_real_physical_evidence"] is False,
    "whole_workspace_not_ready_when_other_slots_empty": fixture_report["ready_for_separate_physical_ingestion"] is False,
    "missing_verso_is_detected": missing_key["metadata_complete_for_separate_ingestion"] is False and any("face_count_invalid" in s["reasons"] or "recto_verso_set_incomplete" in s["reasons"] for s in missing_key["sessions"]),
    "duplicate_capture_id_is_detected": "capture_id_reused_across_workspace" in dup_face["reasons"],
    "duplicate_sha256_is_detected": "source_file_sha256_reused_across_workspace" in dup_face["reasons"],
    "bad_sha256_is_detected": bad_sha_face["complete"] is False and "source_file_sha256_invalid" in bad_sha_face["reasons"],
    "completeness_never_becomes_evidence": all(r["counts_as_real_physical_evidence"] is False and r["evidence_credit"] == 0 for r in [empty_report, fixture_report, missing_report, dup_report, bad_sha_report]),
    "runtime_and_policy_remain_non_authoritative": fixture_report["active_test_runtime"] == "V2.28 TEST R116" and fixture_report["decision_authority"] == "NONE" and fixture_report["policy_status"] == "A_CONFIRMER" and fixture_report["canonical_catalogue_write_allowed"] is False and fixture_report["runtime_mutation_allowed"] is False and fixture_report["automatic_validation_allowed"] is False and fixture_report["acceptance_threshold_authorized"] is False and fixture_report["candidate_selection_allowed"] is False and fixture_report["validated_reference"] is None,
}
errors = [name for name, ok in checks.items() if not ok]
report = {
    "schema": "bres-live-critical-pair-collection-completeness-test-r138-v1",
    "milestone": "BRES Cles catalogue audit R138",
    "checks": checks,
    "errors": errors,
    "ok": not errors,
}
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_COMPLETENESS_R138.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_COMPLETENESS_R138.txt").write_text("\n".join(["BRES CLES — COMPLETUDE COLLECTE R138", ""] + [("OK  " + k if v else "ECHEC  " + k) for k, v in checks.items()] + ["", "SELFTEST OK" if not errors else "SELFTEST ECHEC"]) + "\n", encoding="utf-8")
(ROOT / "CATALOGUE_LIVE_CRITICAL_PAIR_COLLECTION_COMPLETENESS_EMPTY_REPORT_R138.json").write_text(json.dumps(empty_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)
