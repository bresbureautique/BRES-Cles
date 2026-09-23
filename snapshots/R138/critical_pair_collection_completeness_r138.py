from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple

_WORKSPACE_SCHEMA = "bres-live-critical-pair-collection-workspace-r137-v1"
_COMPLETENESS_SCHEMA = "bres-live-critical-pair-collection-completeness-r138-v1"
_REQUIRED_SESSIONS_PER_KEY = 3
_REQUIRED_FACES = ("RECTO", "VERSO")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _face_status(face: Dict[str, Any]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    label = _text(face.get("face"))
    if label not in _REQUIRED_FACES:
        reasons.append("face_label_invalid")
    if not _text(face.get("capture_id")):
        reasons.append("capture_id_missing")
    if not _text(face.get("source_path")):
        reasons.append("source_path_missing")
    sha = _text(face.get("source_file_sha256"))
    if not sha:
        reasons.append("source_file_sha256_missing")
    elif not _SHA256_RE.fullmatch(sha):
        reasons.append("source_file_sha256_invalid")
    if face.get("captured") is not True:
        reasons.append("captured_flag_not_true")
    if face.get("verified") is not True:
        reasons.append("verified_flag_not_true")
    return not reasons, reasons


def analyze_collection_workspace(workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Describe metadata completeness of an R137 collection workspace.

    The output is deliberately non-evidentiary and non-decisional. It verifies
    only identity/provenance/completeness metadata needed before a separate real
    physical ingestion step. It never evaluates dimensions, selects a reference,
    grants evidence credit, or mutates catalogue/runtime data.
    """
    if workspace.get("schema") != _WORKSPACE_SCHEMA:
        raise ValueError("r137_workspace_schema_invalid")
    if workspace.get("active_test_runtime") != "V2.28 TEST R116":
        raise ValueError("runtime_not_r116")
    policy_expectations = {
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurements_used_for_workspace": False,
    }
    for key, expected in policy_expectations.items():
        if workspace.get(key) != expected:
            raise ValueError(f"r137_workspace_policy_escalation:{key}")

    source = copy.deepcopy(workspace)
    rows = source.get("workspaces")
    if not isinstance(rows, list) or len(rows) != 17:
        raise ValueError("critical_pair_count_invalid")

    seen_capture_ids: set[str] = set()
    seen_hashes: set[str] = set()
    seen_key_ids: set[str] = set()
    pair_reports: List[Dict[str, Any]] = []
    total_slots = complete_keys = complete_sessions = complete_faces = 0
    incomplete_keys = incomplete_sessions = incomplete_faces = 0

    for pair in rows:
        pair_key = _text(pair.get("pair_key"))
        if not pair_key:
            raise ValueError("pair_key_missing")
        if pair.get("decision_authority") != "NONE" or pair.get("policy_status") != "A_CONFIRMER":
            raise ValueError("pair_policy_escalation")
        if pair.get("candidate_selection") is not None or pair.get("validated_reference") is not None:
            raise ValueError("pair_decision_escalation")
        if pair.get("acceptance_threshold_mm") is not None or pair.get("physical_measurement_assessment") is not None:
            raise ValueError("pair_measurement_escalation")
        if pair.get("measurements_used_for_workspace") is not False:
            raise ValueError("pair_measurements_used")

        key_reports: List[Dict[str, Any]] = []
        for key_slot in pair.get("prepared_key_slots", []):
            total_slots += 1
            key_reasons: List[str] = []
            physical_key_id = _text(key_slot.get("physical_key_id"))
            if not physical_key_id:
                key_reasons.append("physical_key_id_missing")
            elif physical_key_id in seen_key_ids:
                key_reasons.append("physical_key_id_duplicate")
            else:
                seen_key_ids.add(physical_key_id)
            if key_slot.get("physical_key_identity_confirmed") is not True:
                key_reasons.append("physical_key_identity_not_confirmed")

            sessions = key_slot.get("sessions")
            if not isinstance(sessions, list) or len(sessions) != _REQUIRED_SESSIONS_PER_KEY:
                key_reasons.append("session_count_invalid")
                sessions = sessions if isinstance(sessions, list) else []

            session_reports: List[Dict[str, Any]] = []
            seen_session_slots: set[str] = set()
            seen_real_session_ids: set[str] = set()
            for session in sessions:
                session_reasons: List[str] = []
                slot = _text(session.get("session_slot"))
                if slot not in {"S1", "S2", "S3"} or slot in seen_session_slots:
                    session_reasons.append("session_slot_invalid_or_duplicate")
                else:
                    seen_session_slots.add(slot)
                real_session_id = _text(session.get("real_session_id"))
                if not real_session_id:
                    session_reasons.append("real_session_id_missing")
                elif real_session_id in seen_real_session_ids:
                    session_reasons.append("real_session_id_duplicate_within_key")
                else:
                    seen_real_session_ids.add(real_session_id)

                faces = session.get("faces")
                if not isinstance(faces, list) or len(faces) != 2:
                    session_reasons.append("face_count_invalid")
                    faces = faces if isinstance(faces, list) else []

                labels = [_text(f.get("face")) for f in faces if isinstance(f, dict)]
                if sorted(labels) != sorted(_REQUIRED_FACES):
                    session_reasons.append("recto_verso_set_incomplete")

                face_reports: List[Dict[str, Any]] = []
                for face in faces:
                    if not isinstance(face, dict):
                        incomplete_faces += 1
                        face_reports.append({"complete": False, "reasons": ["face_record_invalid"]})
                        continue
                    ok, reasons = _face_status(face)
                    capture_id = _text(face.get("capture_id"))
                    sha = _text(face.get("source_file_sha256")).lower()
                    if capture_id:
                        if capture_id in seen_capture_ids:
                            reasons.append("capture_id_reused_across_workspace")
                        else:
                            seen_capture_ids.add(capture_id)
                    if sha and _SHA256_RE.fullmatch(sha):
                        if sha in seen_hashes:
                            reasons.append("source_file_sha256_reused_across_workspace")
                        else:
                            seen_hashes.add(sha)
                    ok = not reasons
                    if ok:
                        complete_faces += 1
                    else:
                        incomplete_faces += 1
                    face_reports.append({
                        "face": _text(face.get("face")),
                        "capture_id": capture_id or None,
                        "complete": ok,
                        "reasons": sorted(set(reasons)),
                    })

                session_ok = not session_reasons and len(face_reports) == 2 and all(f["complete"] for f in face_reports)
                if session.get("session_complete") is not True:
                    session_reasons.append("session_complete_flag_not_true")
                    session_ok = False
                if session.get("session_verified") is not True:
                    session_reasons.append("session_verified_flag_not_true")
                    session_ok = False
                if session_ok:
                    complete_sessions += 1
                else:
                    incomplete_sessions += 1
                session_reports.append({
                    "session_slot": slot or None,
                    "real_session_id": real_session_id or None,
                    "complete": session_ok,
                    "reasons": sorted(set(session_reasons)),
                    "faces": face_reports,
                })

            key_ok = (
                not key_reasons
                and len(session_reports) == _REQUIRED_SESSIONS_PER_KEY
                and all(s["complete"] for s in session_reports)
                and key_slot.get("key_workspace_complete") is True
                and key_slot.get("key_workspace_verified") is True
            )
            if key_slot.get("key_workspace_complete") is not True:
                key_reasons.append("key_workspace_complete_flag_not_true")
            if key_slot.get("key_workspace_verified") is not True:
                key_reasons.append("key_workspace_verified_flag_not_true")
            if key_ok:
                complete_keys += 1
            else:
                incomplete_keys += 1
            key_reports.append({
                "workspace_key_slot_id": _text(key_slot.get("workspace_key_slot_id")) or None,
                "physical_key_id": physical_key_id or None,
                "metadata_complete_for_separate_ingestion": key_ok,
                "reasons": sorted(set(key_reasons)),
                "sessions": session_reports,
                "counts_as_real_physical_evidence": False,
                "evidence_credit": 0,
            })

        pair_reports.append({
            "pair_key": pair_key,
            "prepared_key_slots": len(key_reports),
            "metadata_complete_key_slots": sum(1 for k in key_reports if k["metadata_complete_for_separate_ingestion"]),
            "metadata_incomplete_key_slots": sum(1 for k in key_reports if not k["metadata_complete_for_separate_ingestion"]),
            "keys": key_reports,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        })

    return {
        "schema": _COMPLETENESS_SCHEMA,
        "source_workspace_schema": _WORKSPACE_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "prepared_key_slots_checked": total_slots,
        "metadata_complete_key_slots": complete_keys,
        "metadata_incomplete_key_slots": incomplete_keys,
        "metadata_complete_sessions": complete_sessions,
        "metadata_incomplete_sessions": incomplete_sessions,
        "metadata_complete_faces": complete_faces,
        "metadata_incomplete_faces": incomplete_faces,
        "all_prepared_slots_metadata_complete": total_slots > 0 and incomplete_keys == 0,
        "ready_for_separate_physical_ingestion": total_slots > 0 and incomplete_keys == 0,
        "pair_reports": pair_reports,
        "completeness_is_not_evidence": True,
        "evidence_credit": 0,
        "counts_as_real_physical_evidence": False,
        "measurements_used_for_completeness": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
