from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "r125_validator", ROOT / "collection_packet_validator_r125.py"
)
_r125 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r125)

_ALLOWED_ZERO_MODES = {"POINTE_ZERO", "BUTEE_ZERO"}
_QUALITY_FIELDS = ("focus_ok", "alignment_ok", "calibration_ok", "occlusion_ok")


def _nonnull(value: Any) -> bool:
    return value is not None and value != ""


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def ingest_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest one R125 packet for descriptive diagnostics only.

    This function is deliberately non-authoritative: it never returns a validated
    decision, never changes R116/runtime state, and never writes to the catalogue.
    """
    source = copy.deepcopy(packet)
    validation = _r125.validate_packet(source)
    errors: List[str] = []
    warnings: List[str] = list(validation.get("warnings", []))

    if not validation.get("ok"):
        errors.extend(f"r125:{e}" for e in validation.get("errors", []))

    pair = source.get("candidate_pair", {})
    pair_a, pair_b = pair.get("a"), pair.get("b")
    if not _nonnull(pair_a) or not _nonnull(pair_b):
        errors.append("candidate_pair_incomplete")
    elif str(pair_a).strip() == str(pair_b).strip():
        errors.append("candidate_pair_not_distinct")

    gabarit = source.get("gabarit", {})
    if gabarit.get("zero_mode") not in _ALLOWED_ZERO_MODES:
        errors.append("zero_mode_not_documented")

    scale_deltas: List[float] = []
    for item in gabarit.get("scale_checks", []):
        target, measured = item.get("target_mm"), item.get("measured_mm")
        if _finite_number(target) and _finite_number(measured):
            scale_deltas.append(float(measured) - float(target))
        else:
            errors.append("scale_check_non_numeric")

    sessions = source.get("collection_sessions", [])
    stop_positions: List[float] = []
    stop_uncertainties: List[float] = []
    geometry_records: List[Dict[str, Any]] = []
    for idx, session in enumerate(sessions, 1):
        prefix = f"session_{idx}"
        if session.get("slot_status") != "FILLED":
            errors.append(prefix + "_slot_not_filled")

        quality = session.get("quality", {})
        for field in _QUALITY_FIELDS:
            if quality.get(field) is not True:
                errors.append(prefix + "_quality_" + field)

        stop = session.get("stop_or_shoulder", {})
        pos, unc = stop.get("position_mm"), stop.get("uncertainty_mm")
        if not _finite_number(pos):
            errors.append(prefix + "_stop_position_missing_or_invalid")
        else:
            stop_positions.append(float(pos))
        if not _finite_number(unc) or float(unc) < 0:
            errors.append(prefix + "_stop_uncertainty_missing_or_invalid")
        else:
            stop_uncertainties.append(float(unc))
        if not _nonnull(stop.get("measurement_method")):
            errors.append(prefix + "_stop_method_missing")

        dual = session.get("dual_face", {})
        if not _nonnull(dual.get("measurement_method")):
            errors.append(prefix + "_dual_face_method_missing")

        caps = session.get("captures", {})
        recto_sig = caps.get("recto", {}).get("geometry_signature")
        verso_sig = caps.get("verso", {}).get("geometry_signature")
        if not _nonnull(recto_sig):
            errors.append(prefix + "_recto_geometry_signature_missing")
        if not _nonnull(verso_sig):
            errors.append(prefix + "_verso_geometry_signature_missing")
        if _nonnull(recto_sig) and _nonnull(verso_sig):
            geometry_records.append(
                {
                    "capture_session_id": session.get("capture_session_id"),
                    "recto": recto_sig,
                    "verso": verso_sig,
                }
            )

    summary = source.get("collection_summary", {})
    if summary.get("decision_authority", "NONE") != "NONE":
        errors.append("summary_decision_authority_escalation")
    if summary.get("policy_status", "A_CONFIRMER") != "A_CONFIRMER":
        errors.append("summary_policy_status_escalation")
    if summary.get("packet_ready_for_review") is True and (
        summary.get("repeatability_reviewed") is not True
        or summary.get("uncertainty_reviewed") is not True
    ):
        errors.append("summary_ready_without_required_reviews")

    declared_complete = summary.get("complete_sessions")
    if declared_complete not in (None, 0, len(sessions)):
        errors.append("summary_complete_sessions_contradiction")
    elif declared_complete == 0 and len(sessions) == 3:
        warnings.append("source_summary_complete_sessions_not_refreshed")

    accepted = not errors
    diagnostics: Dict[str, Any] = {
        "scale_deltas_mm": scale_deltas,
        "stop_positions_mm": stop_positions,
        "declared_uncertainties_mm": stop_uncertainties,
        "recto_verso_geometry_signatures": geometry_records,
        "stop_mean_mm": mean(stop_positions) if accepted and len(stop_positions) == 3 else None,
        "stop_spread_mm": (max(stop_positions) - min(stop_positions)) if accepted and len(stop_positions) == 3 else None,
        "physical_tolerance_decision": None,
    }

    return {
        "schema": "bres-live-discriminant-diagnostic-ingestion-r126-v1",
        "source_schema": source.get("schema"),
        "active_test_runtime": "V2.28 TEST R116",
        "ingestion_status": "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS" if accepted else "REJECTED",
        "accepted_for_diagnostics": accepted,
        "source_validation_ok": bool(validation.get("ok")),
        "errors": errors,
        "warnings": warnings,
        "candidate_pair": copy.deepcopy(pair),
        "diagnostics": diagnostics,
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "validated_reference": None,
    }
