from __future__ import annotations

import copy
import math
from collections import defaultdict
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple

_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r127-v1"
_REPORT_SCHEMA = "bres-live-diagnostic-repeatability-report-r128-v1"


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _canonical_pair(a: str, b: str) -> Tuple[str, str]:
    return tuple(sorted((str(a).strip(), str(b).strip())))


def _validate_registry(registry: Dict[str, Any]) -> None:
    if registry.get("schema") != _REGISTRY_SCHEMA:
        raise ValueError("registry_schema_invalid")
    fixed = {
        "registry_status": "DIAGNOSTIC_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
    }
    for key, expected in fixed.items():
        if registry.get(key) != expected:
            raise ValueError(f"registry_policy_escalation:{key}")


def _entry_policy_ok(entry: Dict[str, Any]) -> bool:
    return (
        entry.get("source_schema") == "bres-live-discriminant-diagnostic-ingestion-r126-v1"
        and entry.get("ingestion_status") == "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS"
        and entry.get("evidence_status") == "MEASURED_UNVALIDATED"
        and entry.get("decision_authority") == "NONE"
        and entry.get("policy_status") == "A_CONFIRMER"
        and entry.get("validated_reference") is None
    )


def _safe_span(values: Iterable[float]) -> float | None:
    rows = [float(v) for v in values if _finite(v)]
    return max(rows) - min(rows) if rows else None


def _key_summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    entry_means: List[float] = []
    entry_spreads: List[float] = []
    session_positions: List[float] = []
    session_ids: List[str] = []
    geometry_pairs: List[Tuple[str, str]] = []

    for entry in entries:
        diagnostics = entry.get("diagnostics", {})
        m = diagnostics.get("stop_mean_mm")
        s = diagnostics.get("stop_spread_mm")
        if _finite(m):
            entry_means.append(float(m))
        if _finite(s):
            entry_spreads.append(float(s))
        for pos in diagnostics.get("stop_positions_mm", []):
            if _finite(pos):
                session_positions.append(float(pos))
        for record in diagnostics.get("recto_verso_geometry_signatures", []):
            sid = str(record.get("capture_session_id", "")).strip()
            if sid:
                session_ids.append(sid)
            recto = str(record.get("recto", "")).strip()
            verso = str(record.get("verso", "")).strip()
            if recto or verso:
                geometry_pairs.append((recto, verso))

    return {
        "diagnostic_entries": len(entries),
        "session_stop_observations": len(session_positions),
        "observed_session_stop_min_mm": min(session_positions) if session_positions else None,
        "observed_session_stop_max_mm": max(session_positions) if session_positions else None,
        "observed_session_stop_span_mm": _safe_span(session_positions),
        "observed_entry_mean_min_mm": min(entry_means) if entry_means else None,
        "observed_entry_mean_max_mm": max(entry_means) if entry_means else None,
        "observed_entry_mean_span_mm": _safe_span(entry_means),
        "observed_entry_mean_average_mm": mean(entry_means) if entry_means else None,
        "observed_within_entry_spread_max_mm": max(entry_spreads) if entry_spreads else None,
        "geometry_session_records": len(geometry_pairs),
        "distinct_capture_session_ids": sorted(set(session_ids)),
        "distinct_recto_verso_signature_pairs": len(set(geometry_pairs)),
        "repeatability_assessment": None,
        "acceptance_threshold_mm": None,
        "candidate_selection": None,
        "validated_reference": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }


def analyze_pair_repeatability(registry: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    """Build a descriptive R128 repeatability report from one R127 pair bucket.

    R128 observes within-key and between-key variation only. It does not decide whether
    a variation is acceptable, does not create a tolerance, does not select a candidate,
    and has no authority to mutate the catalogue or runtime.
    """
    _validate_registry(registry)
    pair = _canonical_pair(a, b)
    pair_key = f"{pair[0]}::{pair[1]}"
    bucket = copy.deepcopy(registry.get("pairs", {}).get(pair_key))

    report: Dict[str, Any] = {
        "schema": _REPORT_SCHEMA,
        "source_registry_schema": _REGISTRY_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "candidate_pair": {"a": pair[0], "b": pair[1]},
        "analysis_status": "DESCRIPTIVE_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
        "candidate_selection_allowed": False,
        "repeatability_assessment": None,
        "acceptance_threshold_mm": None,
        "candidate_selection": None,
        "validated_reference": None,
        "per_physical_key": {},
        "pair_summary": {
            "diagnostic_entries": 0,
            "distinct_physical_keys": 0,
            "physical_key_ids": [],
            "inter_key_comparison_available": False,
            "observed_key_mean_min_mm": None,
            "observed_key_mean_max_mm": None,
            "observed_key_mean_span_mm": None,
            "observed_within_entry_spread_max_mm": None,
            "repeatability_assessment": None,
            "acceptance_threshold_mm": None,
            "candidate_selection": None,
            "validated_reference": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        },
    }
    if not bucket:
        report["analysis_note"] = "NO_DIAGNOSTIC_DATA_FOR_PAIR"
        return report

    if bucket.get("decision_authority") != "NONE" or bucket.get("policy_status") != "A_CONFIRMER":
        raise ValueError("pair_bucket_policy_escalation")

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in bucket.get("entries", []):
        if not _entry_policy_ok(entry):
            raise ValueError("entry_policy_escalation_or_invalid_source")
        key_id = str(entry.get("physical_key_id", "")).strip()
        if not key_id:
            raise ValueError("physical_key_id_missing")
        grouped[key_id].append(entry)

    key_means: List[float] = []
    max_spreads: List[float] = []
    for key_id in sorted(grouped):
        ks = _key_summary(grouped[key_id])
        report["per_physical_key"][key_id] = ks
        if _finite(ks.get("observed_entry_mean_average_mm")):
            key_means.append(float(ks["observed_entry_mean_average_mm"]))
        if _finite(ks.get("observed_within_entry_spread_max_mm")):
            max_spreads.append(float(ks["observed_within_entry_spread_max_mm"]))

    total_entries = sum(len(v) for v in grouped.values())
    ids = sorted(grouped)
    report["pair_summary"] = {
        "diagnostic_entries": total_entries,
        "distinct_physical_keys": len(ids),
        "physical_key_ids": ids,
        "inter_key_comparison_available": len(ids) >= 2 and len(key_means) >= 2,
        "observed_key_mean_min_mm": min(key_means) if key_means else None,
        "observed_key_mean_max_mm": max(key_means) if key_means else None,
        "observed_key_mean_span_mm": _safe_span(key_means),
        "observed_within_entry_spread_max_mm": max(max_spreads) if max_spreads else None,
        "repeatability_assessment": None,
        "acceptance_threshold_mm": None,
        "candidate_selection": None,
        "validated_reference": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }
    return report
