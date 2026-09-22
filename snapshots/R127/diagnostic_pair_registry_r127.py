from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

ROOT = Path(__file__).resolve().parent
_CRITICAL = json.loads(
    (ROOT / "catalogue/evidence/catalogue_ocr_critical_pair_registry_r121.json").read_text(encoding="utf-8")
)
_ALLOWED_PAIRS = {
    tuple(sorted((str(p["a"]).strip(), str(p["b"]).strip())))
    for p in _CRITICAL.get("critical_pairs", [])
}

_R126_SCHEMA = "bres-live-discriminant-diagnostic-ingestion-r126-v1"
_REGISTRY_SCHEMA = "bres-live-diagnostic-pair-registry-r127-v1"


def _nonnull(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _canonical_pair(pair: Dict[str, Any]) -> Tuple[str, str]:
    a = str(pair.get("a", "")).strip()
    b = str(pair.get("b", "")).strip()
    return tuple(sorted((a, b)))


def new_registry() -> Dict[str, Any]:
    return {
        "schema": _REGISTRY_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "source_ingestion_schema": _R126_SCHEMA,
        "registry_status": "DIAGNOSTIC_ONLY",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "decision_authority": "NONE",
        "automatic_validation_allowed": False,
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "acceptance_threshold_authorized": False,
        "pairs": {},
    }


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


def _validate_ingestion(result: Dict[str, Any]) -> Tuple[str, str]:
    if result.get("schema") != _R126_SCHEMA:
        raise ValueError("source_ingestion_schema_invalid")
    if result.get("accepted_for_diagnostics") is not True:
        raise ValueError("source_ingestion_not_accepted")
    if result.get("ingestion_status") != "ACCEPTED_FOR_DIAGNOSTIC_ANALYSIS":
        raise ValueError("source_ingestion_status_invalid")
    required = {
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
        "evidence_status": "MEASURED_UNVALIDATED",
        "canonical_catalogue_write_allowed": False,
        "runtime_mutation_allowed": False,
        "automatic_validation_allowed": False,
        "acceptance_threshold_authorized": False,
        "validated_reference": None,
    }
    for key, expected in required.items():
        if result.get(key) != expected:
            raise ValueError(f"source_authority_escalation:{key}")

    pair = _canonical_pair(result.get("candidate_pair", {}))
    if not pair[0] or not pair[1] or pair[0] == pair[1]:
        raise ValueError("candidate_pair_invalid")
    if pair not in _ALLOWED_PAIRS:
        raise ValueError("candidate_pair_not_in_r121_critical_registry")
    return pair


def _stable_result_id(physical_key_id: str, pair: Tuple[str, str], result: Dict[str, Any]) -> str:
    payload = {
        "physical_key_id": physical_key_id,
        "pair": list(pair),
        "diagnostics": result.get("diagnostics", {}),
        "warnings": result.get("warnings", []),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _descriptive_summary(entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(entries)
    key_ids = sorted({str(e["physical_key_id"]) for e in rows})
    means = [
        e.get("diagnostics", {}).get("stop_mean_mm")
        for e in rows
        if isinstance(e.get("diagnostics", {}).get("stop_mean_mm"), (int, float))
    ]
    spreads = [
        e.get("diagnostics", {}).get("stop_spread_mm")
        for e in rows
        if isinstance(e.get("diagnostics", {}).get("stop_spread_mm"), (int, float))
    ]
    return {
        "diagnostic_entries": len(rows),
        "distinct_physical_keys": len(key_ids),
        "physical_key_ids": key_ids,
        "observed_stop_mean_min_mm": min(means) if means else None,
        "observed_stop_mean_max_mm": max(means) if means else None,
        "observed_stop_spread_max_mm": max(spreads) if spreads else None,
        "physical_tolerance_decision": None,
        "candidate_selection": None,
        "validated_reference": None,
        "decision_authority": "NONE",
        "policy_status": "A_CONFIRMER",
    }


def add_diagnostic_result(
    registry: Dict[str, Any], ingestion_result: Dict[str, Any], physical_key_id: str
) -> Dict[str, Any]:
    """Return a new R127 diagnostic registry with one accepted R126 result added.

    R127 is intentionally non-authoritative. It stores accepted diagnostic evidence by
    critical pair and by physical key, but it cannot select a candidate, create a
    tolerance, mutate the runtime/catalogue, or turn evidence into a validated result.
    """
    if not _nonnull(physical_key_id):
        raise ValueError("physical_key_id_required")
    _validate_registry(registry)
    pair = _validate_ingestion(ingestion_result)

    out = copy.deepcopy(registry)
    source = copy.deepcopy(ingestion_result)
    key_id = str(physical_key_id).strip()
    pair_key = f"{pair[0]}::{pair[1]}"
    result_id = _stable_result_id(key_id, pair, source)

    bucket = out["pairs"].setdefault(
        pair_key,
        {
            "candidate_pair": {"a": pair[0], "b": pair[1]},
            "policy_status": "A_CONFIRMER",
            "decision_authority": "NONE",
            "entries": [],
            "summary": _descriptive_summary([]),
        },
    )
    if any(e.get("result_id") == result_id for e in bucket["entries"]):
        return out

    bucket["entries"].append(
        {
            "result_id": result_id,
            "physical_key_id": key_id,
            "source_schema": source.get("schema"),
            "ingestion_status": source.get("ingestion_status"),
            "diagnostics": copy.deepcopy(source.get("diagnostics", {})),
            "warnings": copy.deepcopy(source.get("warnings", [])),
            "evidence_status": "MEASURED_UNVALIDATED",
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
            "validated_reference": None,
        }
    )
    bucket["summary"] = _descriptive_summary(bucket["entries"])
    return out


def summarize_pair(registry: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    _validate_registry(registry)
    pair = tuple(sorted((str(a).strip(), str(b).strip())))
    bucket = registry.get("pairs", {}).get(f"{pair[0]}::{pair[1]}")
    if not bucket:
        return _descriptive_summary([])
    return copy.deepcopy(bucket.get("summary", _descriptive_summary([])))
