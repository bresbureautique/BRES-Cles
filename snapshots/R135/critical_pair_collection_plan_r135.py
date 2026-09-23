from __future__ import annotations

import copy
from typing import Any, Dict, List

_COVERAGE_SCHEMA = "bres-live-critical-pair-physical-coverage-r134-v1"
_PLAN_SCHEMA = "bres-live-critical-pair-collection-plan-r135-v1"
_REQUIRED_KEYS_PER_PAIR = 2
_REQUIRED_SESSIONS_PER_KEY = 3
_REQUIRED_SESSIONS_PER_PAIR = _REQUIRED_KEYS_PER_PAIR * _REQUIRED_SESSIONS_PER_KEY
_ALLOWED_ORIGINS = {"REAL_PHYSICAL", "SYNTHETIC_TEST"}


def _validate_coverage(coverage: Dict[str, Any]) -> None:
    if coverage.get("schema") != _COVERAGE_SCHEMA:
        raise ValueError("r134_coverage_schema_invalid")
    required = {
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
        "measurement_values_used_for_coverage": False,
    }
    for key, expected in required.items():
        if coverage.get(key) != expected:
            raise ValueError(f"r134_coverage_policy_escalation:{key}")
    rows = coverage.get("pair_coverage")
    if not isinstance(rows, list) or len(rows) != 17:
        raise ValueError("r134_critical_pair_count_invalid")


def _row_policy_ok(row: Dict[str, Any]) -> bool:
    return (
        row.get("decision_authority") == "NONE"
        and row.get("policy_status") == "A_CONFIRMER"
        and row.get("validated_reference") is None
        and row.get("candidate_selection") is None
        and row.get("physical_measurement_assessment") is None
        and row.get("acceptance_threshold_mm") is None
        and row.get("measurement_values_used_for_coverage") is False
    )


def build_collection_plan(coverage: Dict[str, Any], *, evidence_origin: str) -> Dict[str, Any]:
    """Turn R134 documentary coverage into a non-decision collection checklist.

    A pair needs two independently traceable physical keys. Each qualifying key is
    credited with exactly three documented dual-face sessions because R131 readiness
    requires three sessions / six source captures. Rejected or traceability-incomplete
    dossiers receive zero credit. Numeric key measurements are never read.

    Synthetic data may exercise the planner but is explicitly marked as not counting
    toward real physical collection. Only a REAL_PHYSICAL plan can report real totals.
    """
    _validate_coverage(coverage)
    origin = str(evidence_origin or "").strip().upper()
    if origin not in _ALLOWED_ORIGINS:
        raise ValueError("evidence_origin_invalid")

    plan_rows: List[Dict[str, Any]] = []
    total_ready_keys = 0
    total_credited_sessions = 0
    total_missing_keys = 0
    total_missing_sessions = 0

    seen_pairs: set[str] = set()
    for raw in copy.deepcopy(coverage["pair_coverage"]):
        if not isinstance(raw, dict) or not _row_policy_ok(raw):
            raise ValueError("r134_pair_row_policy_escalation")
        pair_key = str(raw.get("pair_key", "")).strip()
        if not pair_key or pair_key in seen_pairs:
            raise ValueError("pair_key_invalid_or_duplicate")
        seen_pairs.add(pair_key)

        candidate_pair = raw.get("candidate_pair") or {}
        a = str(candidate_pair.get("a", "")).strip()
        b = str(candidate_pair.get("b", "")).strip()
        if not a or not b or a == b:
            raise ValueError("candidate_pair_invalid")

        ready_keys_raw = int(raw.get("keys_ready_for_within_key_traceable_descriptive_review", 0) or 0)
        if ready_keys_raw < 0:
            raise ValueError("ready_key_count_negative")
        credited_keys = min(ready_keys_raw, _REQUIRED_KEYS_PER_PAIR)
        credited_sessions = credited_keys * _REQUIRED_SESSIONS_PER_KEY
        missing_keys = max(0, _REQUIRED_KEYS_PER_PAIR - credited_keys)
        missing_sessions = max(0, _REQUIRED_SESSIONS_PER_PAIR - credited_sessions)

        if missing_keys == 0:
            action = "NO_ADDITIONAL_COLLECTION_REQUIRED_FOR_DESCRIPTIVE_REVIEW"
        elif credited_keys == 1:
            action = "COLLECT_ONE_NEW_INDEPENDENT_PHYSICAL_KEY_WITH_3_SESSIONS"
        else:
            action = "COLLECT_TWO_NEW_INDEPENDENT_PHYSICAL_KEYS_WITH_3_SESSIONS_EACH"

        rejected = int(raw.get("rejected_dossiers", 0) or 0)
        reject_reasons = copy.deepcopy(raw.get("rejected_reason_counts", {}))
        if not isinstance(reject_reasons, dict):
            raise ValueError("rejected_reason_counts_invalid")

        total_ready_keys += credited_keys
        total_credited_sessions += credited_sessions
        total_missing_keys += missing_keys
        total_missing_sessions += missing_sessions

        plan_rows.append({
            "pair_key": pair_key,
            "candidate_pair": {"a": a, "b": b},
            "maker_a": raw.get("maker_a"),
            "maker_b": raw.get("maker_b"),
            "family_a": raw.get("family_a"),
            "family_b": raw.get("family_b"),
            "required_independent_physical_keys": _REQUIRED_KEYS_PER_PAIR,
            "required_documented_sessions_per_key": _REQUIRED_SESSIONS_PER_KEY,
            "required_documented_sessions_total": _REQUIRED_SESSIONS_PER_PAIR,
            "credited_traceable_physical_keys": credited_keys,
            "credited_documented_sessions": credited_sessions,
            "missing_independent_physical_keys": missing_keys,
            "missing_documented_sessions": missing_sessions,
            "collection_action": action,
            "accepted_dossiers_seen": int(raw.get("accepted_dossiers", 0) or 0),
            "rejected_dossiers_seen": rejected,
            "rejected_reason_counts": reject_reasons,
            "rejected_or_incomplete_dossiers_receive_collection_credit": False,
            "measurements_used_for_plan": False,
            "counts_as_real_physical_evidence": origin == "REAL_PHYSICAL",
            "candidate_selection": None,
            "validated_reference": None,
            "acceptance_threshold_mm": None,
            "physical_measurement_assessment": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        })

    if len(seen_pairs) != 17:
        raise ValueError("critical_pair_set_incomplete")

    real_multiplier = 1 if origin == "REAL_PHYSICAL" else 0
    return {
        "schema": _PLAN_SCHEMA,
        "source_coverage_schema": _COVERAGE_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "plan_status": "DOCUMENTARY_COLLECTION_CHECKLIST_ONLY",
        "evidence_origin": origin,
        "synthetic_data_counts_as_real_physical_evidence": False,
        "critical_pair_count": 17,
        "requirements": {
            "independent_physical_keys_per_pair": _REQUIRED_KEYS_PER_PAIR,
            "documented_sessions_per_key": _REQUIRED_SESSIONS_PER_KEY,
            "documented_sessions_per_pair": _REQUIRED_SESSIONS_PER_PAIR,
        },
        "totals": {
            "required_independent_physical_keys": 17 * _REQUIRED_KEYS_PER_PAIR,
            "required_documented_sessions": 17 * _REQUIRED_SESSIONS_PER_PAIR,
            "credited_traceable_physical_keys": total_ready_keys,
            "credited_documented_sessions": total_credited_sessions,
            "missing_independent_physical_keys": total_missing_keys,
            "missing_documented_sessions": total_missing_sessions,
            "real_physical_credited_traceable_keys": total_ready_keys * real_multiplier,
            "real_physical_credited_documented_sessions": total_credited_sessions * real_multiplier,
        },
        "collection_queue": plan_rows,
        "measurements_used_for_plan": False,
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "validated_reference": None,
    }
