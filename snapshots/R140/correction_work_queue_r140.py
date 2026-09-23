from __future__ import annotations

from typing import Any, Dict, List, Tuple

_CORRECTION_SCHEMA = "bres-live-critical-pair-collection-correction-sheet-r139-v1"
_QUEUE_SCHEMA = "bres-live-critical-pair-collection-correction-work-queue-r140-v1"

# Lower values are handled first. This is a documentary workflow order only;
# it is never a key-recognition score or a physical-acceptance threshold.
_ACTION_PHASE: Dict[str, Tuple[int, str]] = {
    "CORRIGER_IDENTITE_CLE": (10, "STRUCTURE_IDENTITE"),
    "RENSEIGNER_IDENTITE_CLE": (10, "STRUCTURE_IDENTITE"),
    "CONFIRMER_IDENTITE_CLE": (11, "CONFIRMATION_IDENTITE"),
    "RECONSTITUER_SEANCES": (15, "STRUCTURE_SEANCES"),
    "CORRIGER_NUMERO_SEANCE": (15, "STRUCTURE_SEANCES"),
    "RENSEIGNER_ID_SEANCE": (20, "IDENTITE_SEANCE"),
    "CORRIGER_ID_SEANCE": (20, "IDENTITE_SEANCE"),
    "RECREER_ENREGISTREMENT_FACE": (25, "STRUCTURE_FACE"),
    "CORRIGER_FACE": (25, "STRUCTURE_FACE"),
    "RECONSTITUER_RECTO_VERSO": (25, "STRUCTURE_FACE"),
    "REFAIRE_CAPTURE_INDEPENDANTE": (30, "CAPTURE_SOURCE"),
    "RENSEIGNER_ID_CAPTURE": (31, "PROVENANCE_CAPTURE"),
    "RENSEIGNER_SOURCE": (31, "PROVENANCE_CAPTURE"),
    "CALCULER_SHA256_SOURCE": (31, "PROVENANCE_CAPTURE"),
    "RECALCULER_SHA256_SOURCE": (31, "PROVENANCE_CAPTURE"),
    "CONFIRMER_CAPTURE": (32, "CONFIRMATION_CAPTURE"),
    "VERIFIER_CAPTURE": (40, "VERIFICATION_CAPTURE"),
    "FINALISER_SEANCE": (50, "FINALISATION_SEANCE"),
    "VERIFIER_SEANCE": (51, "VERIFICATION_SEANCE"),
    "FINALISER_DOSSIER_CLE": (60, "FINALISATION_CLE"),
    "VERIFIER_DOSSIER_CLE": (61, "VERIFICATION_CLE"),
    "CONTROLER_MANUELLEMENT": (90, "CONTROLE_MANUEL"),
}

_FACE_ORDER = {"RECTO": 0, "VERSO": 1}
_SESSION_ORDER = {"S1": 0, "S2": 1, "S3": 2}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _policy_guard(sheet: Dict[str, Any]) -> None:
    if sheet.get("schema") != _CORRECTION_SCHEMA:
        raise ValueError("r139_correction_schema_invalid")
    expected = {
        "active_test_runtime": "V2.28 TEST R116",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurements_used_for_correction": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
    }
    for key, expected_value in expected.items():
        if sheet.get(key) != expected_value:
            raise ValueError(f"r139_correction_policy_escalation:{key}")


def _phase(action: str) -> Tuple[int, str]:
    return _ACTION_PHASE.get(action, (90, "CONTROLE_MANUEL"))


def _session_rank(slot: Any) -> int:
    return _SESSION_ORDER.get(_text(slot).upper(), 99)


def _face_rank(face: Any) -> int:
    return _FACE_ORDER.get(_text(face).upper(), 99)


def build_correction_work_queue(correction_sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Build a deterministic, resumable documentary work queue from R139.

    The queue orders correction work by workflow dependency (identity before
    capture provenance, provenance before verification, verification before
    finalisation). Priority is operational only; it is not a recognition score,
    does not inspect measurements, and cannot validate a catalogue reference.
    """
    _policy_guard(correction_sheet)
    pair_sheets = correction_sheet.get("pair_sheets")
    if not isinstance(pair_sheets, list) or len(pair_sheets) != 17:
        raise ValueError("critical_pair_count_invalid")

    raw_items: List[Dict[str, Any]] = []
    pair_summary: List[Dict[str, Any]] = []

    for pair_index, pair in enumerate(pair_sheets):
        pair_key = _text(pair.get("pair_key"))
        if not pair_key:
            raise ValueError("pair_key_missing")
        before_count = len(raw_items)
        keys = pair.get("keys") if isinstance(pair.get("keys"), list) else []

        for key_index, key in enumerate(keys):
            key_slot = _text(key.get("workspace_key_slot_id")) or f"KEY_SLOT_{key_index + 1:02d}"
            physical_key_id = _text(key.get("physical_key_id")) or None

            def add_actions(actions: Any, scope: str, session_slot: str | None = None, face: str | None = None, capture_id: str | None = None) -> None:
                if not isinstance(actions, list):
                    return
                for action_index, item in enumerate(actions):
                    action = _text(item.get("action"))
                    reason = _text(item.get("reason")) or "reason_missing"
                    instruction = _text(item.get("instruction"))
                    if not action:
                        action = "CONTROLER_MANUELLEMENT"
                    phase_rank, phase = _phase(action)
                    raw_items.append({
                        "pair_index": pair_index,
                        "key_index": key_index,
                        "session_rank": _session_rank(session_slot),
                        "face_rank": _face_rank(face),
                        "source_action_index": action_index,
                        "pair_key": pair_key,
                        "workspace_key_slot_id": key_slot,
                        "physical_key_id": physical_key_id,
                        "session_slot": session_slot,
                        "face": face,
                        "capture_id": capture_id,
                        "scope": scope,
                        "reason": reason,
                        "action": action,
                        "instruction": instruction,
                        "phase_rank": phase_rank,
                        "phase": phase,
                    })

            add_actions(key.get("actions"), "KEY")
            sessions = key.get("sessions") if isinstance(key.get("sessions"), list) else []
            for session in sessions:
                session_slot = _text(session.get("session_slot")) or None
                add_actions(session.get("actions"), "SESSION", session_slot=session_slot)
                faces = session.get("faces") if isinstance(session.get("faces"), list) else []
                for face_row in faces:
                    face = _text(face_row.get("face")) or None
                    capture_id = _text(face_row.get("capture_id")) or None
                    add_actions(face_row.get("actions"), "FACE", session_slot=session_slot, face=face, capture_id=capture_id)

        pair_summary.append({
            "pair_key": pair_key,
            "source_pair_index": pair_index,
            "work_item_count": len(raw_items) - before_count,
        })

    raw_items.sort(key=lambda x: (
        x["phase_rank"], x["pair_index"], x["key_index"], x["session_rank"], x["face_rank"],
        x["scope"], x["action"], x["reason"], x["source_action_index"]
    ))

    items: List[Dict[str, Any]] = []
    phase_counts: Dict[str, int] = {}
    for sequence, item in enumerate(raw_items, start=1):
        phase_counts[item["phase"]] = phase_counts.get(item["phase"], 0) + 1
        clean = {k: v for k, v in item.items() if k not in {"pair_index", "key_index", "session_rank", "face_rank", "source_action_index"}}
        clean["sequence"] = sequence
        clean["work_item_id"] = f"R140-WORK-{sequence:05d}"
        clean["status"] = "A_FAIRE"
        clean["completion_requires_real_correction"] = True
        clean["completion_grants_evidence_credit"] = False
        items.append(clean)

    for summary in pair_summary:
        summary["first_work_item_id"] = next((i["work_item_id"] for i in items if i["pair_key"] == summary["pair_key"]), None)
        summary["correction_required"] = summary["work_item_count"] > 0

    return {
        "schema": _QUEUE_SCHEMA,
        "source_correction_schema": _CORRECTION_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "work_item_count": len(items),
        "phase_counts": phase_counts,
        "pair_summary": pair_summary,
        "items": items,
        "ordering_is_documentary_only": True,
        "queue_is_resumable_by_work_item_id": True,
        "completion_requires_real_correction": True,
        "queue_completion_counts_as_real_physical_evidence": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_priority": False,
        "recognition_score_used_for_priority": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
