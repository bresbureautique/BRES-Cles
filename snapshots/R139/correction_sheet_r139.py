from __future__ import annotations

import copy
from typing import Any, Dict, List

_COMPLETENESS_SCHEMA = "bres-live-critical-pair-collection-completeness-r138-v1"
_CORRECTION_SCHEMA = "bres-live-critical-pair-collection-correction-sheet-r139-v1"

# Human-readable collection actions only. They do not score a key, select a
# catalogue reference, define a physical tolerance, or grant evidence credit.
_REASON_ACTIONS: Dict[str, Dict[str, str]] = {
    "physical_key_id_missing": {"action": "RENSEIGNER_IDENTITE_CLE", "instruction": "Renseigner un identifiant physique unique pour cette clé."},
    "physical_key_id_duplicate": {"action": "CORRIGER_IDENTITE_CLE", "instruction": "Attribuer un identifiant physique unique et vérifier qu'il ne désigne pas une autre clé."},
    "physical_key_identity_not_confirmed": {"action": "CONFIRMER_IDENTITE_CLE", "instruction": "Confirmer l'identité physique de la clé avant de poursuivre."},
    "session_count_invalid": {"action": "RECONSTITUER_SEANCES", "instruction": "Reconstituer exactement les trois séances S1, S2 et S3."},
    "key_workspace_complete_flag_not_true": {"action": "FINALISER_DOSSIER_CLE", "instruction": "Marquer le dossier clé complet uniquement après correction de tous les éléments."},
    "key_workspace_verified_flag_not_true": {"action": "VERIFIER_DOSSIER_CLE", "instruction": "Vérifier le dossier clé après correction, puis confirmer sa vérification documentaire."},
    "session_slot_invalid_or_duplicate": {"action": "CORRIGER_NUMERO_SEANCE", "instruction": "Corriger le numéro de séance pour obtenir une seule S1, une seule S2 et une seule S3."},
    "real_session_id_missing": {"action": "RENSEIGNER_ID_SEANCE", "instruction": "Renseigner un identifiant réel et unique pour cette séance."},
    "real_session_id_duplicate_within_key": {"action": "CORRIGER_ID_SEANCE", "instruction": "Attribuer un identifiant de séance différent des autres séances de la même clé."},
    "face_count_invalid": {"action": "RECONSTITUER_RECTO_VERSO", "instruction": "Reconstituer exactement deux faces pour cette séance : RECTO et VERSO."},
    "recto_verso_set_incomplete": {"action": "RECONSTITUER_RECTO_VERSO", "instruction": "Ajouter ou corriger la face manquante afin d'avoir un RECTO et un VERSO."},
    "session_complete_flag_not_true": {"action": "FINALISER_SEANCE", "instruction": "Marquer la séance complète uniquement lorsque le recto et le verso sont complets."},
    "session_verified_flag_not_true": {"action": "VERIFIER_SEANCE", "instruction": "Vérifier la séance après correction du recto et du verso."},
    "face_record_invalid": {"action": "RECREER_ENREGISTREMENT_FACE", "instruction": "Recréer l'enregistrement de cette face avant toute ingestion."},
    "face_label_invalid": {"action": "CORRIGER_FACE", "instruction": "Corriger le libellé de la face : RECTO ou VERSO uniquement."},
    "capture_id_missing": {"action": "RENSEIGNER_ID_CAPTURE", "instruction": "Renseigner l'identifiant unique de la capture."},
    "source_path_missing": {"action": "RENSEIGNER_SOURCE", "instruction": "Renseigner le chemin du fichier photo source."},
    "source_file_sha256_missing": {"action": "CALCULER_SHA256_SOURCE", "instruction": "Calculer et enregistrer le SHA-256 du fichier photo source."},
    "source_file_sha256_invalid": {"action": "RECALCULER_SHA256_SOURCE", "instruction": "Recalculer le SHA-256 depuis le fichier photo source et enregistrer 64 caractères hexadécimaux."},
    "captured_flag_not_true": {"action": "CONFIRMER_CAPTURE", "instruction": "Confirmer que la photo source a réellement été capturée/importée."},
    "verified_flag_not_true": {"action": "VERIFIER_CAPTURE", "instruction": "Vérifier la photo et sa provenance avant de confirmer la face."},
    "capture_id_reused_across_workspace": {"action": "REFAIRE_CAPTURE_INDEPENDANTE", "instruction": "Refaire cette photo : son identifiant de capture est déjà utilisé ailleurs dans l'espace de collecte."},
    "source_file_sha256_reused_across_workspace": {"action": "REFAIRE_CAPTURE_INDEPENDANTE", "instruction": "Refaire cette photo avec un fichier source indépendant : son SHA-256 est déjà utilisé ailleurs."},
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _action_items(reasons: Any, scope: str) -> List[Dict[str, str]]:
    if not isinstance(reasons, list):
        return []
    items: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for reason in reasons:
        reason_text = _text(reason)
        mapped = _REASON_ACTIONS.get(reason_text, {
            "action": "CONTROLER_MANUELLEMENT",
            "instruction": f"Contrôler manuellement l'anomalie documentaire : {reason_text or 'motif non renseigné'}."
        })
        key = (reason_text, mapped["action"])
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "scope": scope,
            "reason": reason_text or "reason_missing",
            "action": mapped["action"],
            "instruction": mapped["instruction"],
        })
    return items


def build_correction_sheet(completeness_report: Dict[str, Any]) -> Dict[str, Any]:
    """Turn an R138 completeness report into a non-decisional collection to-do sheet.

    The sheet is descriptive only: it explains what metadata/capture work must be
    completed or redone. It never interprets physical measurements, scores a key,
    selects a catalogue candidate, validates a reference, or grants evidence credit.
    """
    if completeness_report.get("schema") != _COMPLETENESS_SCHEMA:
        raise ValueError("r138_completeness_schema_invalid")
    policy_expectations = {
        "active_test_runtime": "V2.28 TEST R116",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurements_used_for_completeness": False,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
    }
    for key, expected in policy_expectations.items():
        if completeness_report.get(key) != expected:
            raise ValueError(f"r138_completeness_policy_escalation:{key}")

    source = copy.deepcopy(completeness_report)
    pair_rows = source.get("pair_reports")
    if not isinstance(pair_rows, list) or len(pair_rows) != 17:
        raise ValueError("critical_pair_count_invalid")

    pair_sheets: List[Dict[str, Any]] = []
    action_count = 0
    recapture_count = 0
    affected_key_count = 0
    affected_session_count = 0
    affected_face_count = 0

    for pair in pair_rows:
        pair_key = _text(pair.get("pair_key"))
        if not pair_key:
            raise ValueError("pair_key_missing")
        key_sheets: List[Dict[str, Any]] = []

        for key in pair.get("keys", []):
            key_actions = _action_items(key.get("reasons"), "KEY")
            session_sheets: List[Dict[str, Any]] = []

            for session in key.get("sessions", []):
                session_actions = _action_items(session.get("reasons"), "SESSION")
                face_sheets: List[Dict[str, Any]] = []

                for face in session.get("faces", []):
                    face_actions = _action_items(face.get("reasons"), "FACE")
                    if face_actions:
                        affected_face_count += 1
                    recapture_count += sum(1 for a in face_actions if a["action"] == "REFAIRE_CAPTURE_INDEPENDANTE")
                    action_count += len(face_actions)
                    face_sheets.append({
                        "face": _text(face.get("face")) or None,
                        "capture_id": _text(face.get("capture_id")) or None,
                        "complete": face.get("complete") is True,
                        "correction_required": bool(face_actions),
                        "actions": face_actions,
                    })

                if session_actions or any(f["correction_required"] for f in face_sheets):
                    affected_session_count += 1
                action_count += len(session_actions)
                session_sheets.append({
                    "session_slot": _text(session.get("session_slot")) or None,
                    "real_session_id": _text(session.get("real_session_id")) or None,
                    "complete": session.get("complete") is True,
                    "correction_required": bool(session_actions) or any(f["correction_required"] for f in face_sheets),
                    "actions": session_actions,
                    "faces": face_sheets,
                })

            key_needs_correction = bool(key_actions) or any(s["correction_required"] for s in session_sheets)
            if key_needs_correction:
                affected_key_count += 1
            action_count += len(key_actions)
            key_sheets.append({
                "workspace_key_slot_id": _text(key.get("workspace_key_slot_id")) or None,
                "physical_key_id": _text(key.get("physical_key_id")) or None,
                "metadata_complete_for_separate_ingestion": key.get("metadata_complete_for_separate_ingestion") is True,
                "correction_required": key_needs_correction,
                "actions": key_actions,
                "sessions": session_sheets,
                "counts_as_real_physical_evidence": False,
                "evidence_credit": 0,
            })

        pair_sheets.append({
            "pair_key": pair_key,
            "correction_required": any(k["correction_required"] for k in key_sheets),
            "affected_key_slots": sum(1 for k in key_sheets if k["correction_required"]),
            "keys": key_sheets,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        })

    return {
        "schema": _CORRECTION_SCHEMA,
        "source_completeness_schema": _COMPLETENESS_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "critical_pair_count": 17,
        "affected_key_slots": affected_key_count,
        "affected_sessions": affected_session_count,
        "affected_faces": affected_face_count,
        "action_count": action_count,
        "recapture_action_count": recapture_count,
        "pair_sheets": pair_sheets,
        "correction_sheet_is_descriptive_only": True,
        "correction_never_counts_as_evidence": True,
        "counts_as_real_physical_evidence": False,
        "evidence_credit": 0,
        "measurements_used_for_correction": False,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
