from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent

_BATCH_SCHEMA = "bres-live-physical-collection-batch-ingestion-r133-v1"
_REGISTRY_SCHEMA = "bres-catalogue-ocr-critical-pair-registry-r121-v1"
_COVERAGE_SCHEMA = "bres-live-critical-pair-physical-coverage-r134-v1"


def _canonical_pair(a: Any, b: Any) -> Tuple[str, str]:
    return tuple(sorted((str(a or "").strip(), str(b or "").strip())))


def _pair_key(pair: Tuple[str, str]) -> str:
    return f"{pair[0]}::{pair[1]}"


def _load_critical_registry() -> Dict[str, Any]:
    path = ROOT / "catalogue/evidence/catalogue_ocr_critical_pair_registry_r121.json"
    reg = json.loads(path.read_text(encoding="utf-8"))
    if reg.get("schema") != _REGISTRY_SCHEMA or not reg.get("ok"):
        raise ValueError("critical_pair_registry_invalid")
    pairs = reg.get("critical_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("critical_pair_registry_empty")
    keys = [_pair_key(_canonical_pair(p.get("a"), p.get("b"))) for p in pairs]
    if any(k == "::" or k.startswith("::") or k.endswith("::") for k in keys):
        raise ValueError("critical_pair_registry_pair_invalid")
    if len(keys) != len(set(keys)):
        raise ValueError("critical_pair_registry_duplicate_pair")
    return reg


def _validate_batch(batch: Dict[str, Any]) -> None:
    if batch.get("schema") != _BATCH_SCHEMA:
        raise ValueError("r133_batch_schema_invalid")
    required = {
        "batch_status": "DIAGNOSTIC_ONLY",
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
    for key, expected in required.items():
        if batch.get(key) != expected:
            raise ValueError(f"r133_batch_policy_escalation:{key}")
    if not isinstance(batch.get("accepted_folders", []), list):
        raise ValueError("accepted_folders_invalid")
    if not isinstance(batch.get("rejected_folders", []), list):
        raise ValueError("rejected_folders_invalid")
    if not isinstance(batch.get("pair_reports", {}), dict):
        raise ValueError("pair_reports_invalid")


def _rejection_reasons(row: Dict[str, Any]) -> List[str]:
    errors = row.get("errors", [])
    if not isinstance(errors, list):
        return ["malformed_rejection_errors"]
    reasons = [str(e).strip() for e in errors if str(e).strip()]
    return reasons or ["unspecified_rejection"]


def build_critical_pair_coverage(batch: Dict[str, Any]) -> Dict[str, Any]:
    """Build a documentary coverage matrix for all R121 critical pairs.

    Coverage is derived only from R133 acceptance/rejection metadata and the R131
    traceability report embedded in the batch. Numeric physical measurements are
    intentionally not read. The matrix cannot select a reference, define a physical
    tolerance, validate evidence, mutate runtime, or write the canonical catalogue.
    """
    _validate_batch(batch)
    registry = _load_critical_registry()

    critical_rows = []
    critical_keys: set[str] = set()
    meta_by_key: Dict[str, Dict[str, Any]] = {}
    for p in registry["critical_pairs"]:
        pair = _canonical_pair(p.get("a"), p.get("b"))
        key = _pair_key(pair)
        critical_keys.add(key)
        meta_by_key[key] = {
            "a": pair[0],
            "b": pair[1],
            "maker_a": p.get("maker_a"),
            "maker_b": p.get("maker_b"),
            "family_a": p.get("family_a"),
            "family_b": p.get("family_b"),
        }

    accepted_by_pair: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    rejected_by_pair: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    unassigned_rejections: List[Dict[str, Any]] = []

    for row in copy.deepcopy(batch.get("accepted_folders", [])):
        pair = _canonical_pair((row.get("candidate_pair") or {}).get("a"), (row.get("candidate_pair") or {}).get("b"))
        key = _pair_key(pair)
        if key not in critical_keys:
            raise ValueError("accepted_noncritical_pair_in_r133_batch")
        accepted_by_pair[key].append(row)

    for row in copy.deepcopy(batch.get("rejected_folders", [])):
        pair = _canonical_pair((row.get("candidate_pair") or {}).get("a"), (row.get("candidate_pair") or {}).get("b"))
        key = _pair_key(pair)
        if key in critical_keys:
            rejected_by_pair[key].append(row)
        else:
            unassigned_rejections.append({
                "folder": row.get("folder"),
                "physical_key_id": row.get("physical_key_id"),
                "candidate_pair": copy.deepcopy(row.get("candidate_pair", {})),
                "errors": _rejection_reasons(row),
            })

    pairs_ready = 0
    pairs_with_accepted = 0
    pairs_with_rejected = 0
    pairs_one_key_only = 0

    for key in sorted(critical_keys):
        accepted = accepted_by_pair.get(key, [])
        rejected = rejected_by_pair.get(key, [])
        accepted_key_ids = sorted({str(r.get("physical_key_id", "")).strip() for r in accepted if str(r.get("physical_key_id", "")).strip()})
        reject_counts = Counter(reason for row in rejected for reason in _rejection_reasons(row))

        report = copy.deepcopy((batch.get("pair_reports") or {}).get(key, {}))
        summary = report.get("pair_summary", {}) if isinstance(report, dict) else {}
        report_policy_ok = (not report) or (
            report.get("decision_authority") == "NONE"
            and report.get("policy_status") == "A_CONFIRMER"
            and report.get("validated_reference") is None
            and report.get("candidate_selection") is None
            and report.get("physical_measurement_assessment") is None
            and report.get("acceptance_threshold_mm") is None
        )
        if not report_policy_ok:
            raise ValueError("r131_pair_report_policy_escalation")

        ready_keys = int(summary.get("keys_ready_for_within_key_traceable_descriptive_review", 0) or 0)
        pair_ready = bool(summary.get("pair_traceable_descriptive_review_ready", False))
        documentation_status = report.get("documentation_status") if report else "NO_DATA"

        if not accepted:
            coverage_status = "NO_ACCEPTED_DOSSIER"
        elif pair_ready:
            coverage_status = "READY_FOR_PAIR_TRACEABLE_DESCRIPTIVE_REVIEW"
        elif len(accepted_key_ids) == 1 and ready_keys == 1:
            coverage_status = "ONE_TRACEABLE_PHYSICAL_KEY_ONLY"
        else:
            coverage_status = "ACCEPTED_BUT_TRACEABILITY_INCOMPLETE"

        pairs_ready += int(pair_ready)
        pairs_with_accepted += int(bool(accepted))
        pairs_with_rejected += int(bool(rejected))
        pairs_one_key_only += int(coverage_status == "ONE_TRACEABLE_PHYSICAL_KEY_ONLY")

        meta = meta_by_key[key]
        critical_rows.append({
            "pair_key": key,
            "candidate_pair": {"a": meta["a"], "b": meta["b"]},
            "maker_a": meta["maker_a"],
            "maker_b": meta["maker_b"],
            "family_a": meta["family_a"],
            "family_b": meta["family_b"],
            "accepted_dossiers": len(accepted),
            "rejected_dossiers": len(rejected),
            "distinct_accepted_physical_keys": len(accepted_key_ids),
            "accepted_physical_key_ids": accepted_key_ids,
            "keys_ready_for_within_key_traceable_descriptive_review": ready_keys,
            "traceable_descriptive_review_ready": pair_ready,
            "documentation_status": documentation_status,
            "coverage_status": coverage_status,
            "rejected_reason_counts": dict(sorted(reject_counts.items())),
            "rejected_dossier_details": [
                {
                    "folder": r.get("folder"),
                    "physical_key_id": r.get("physical_key_id"),
                    "errors": _rejection_reasons(r),
                }
                for r in rejected
            ],
            "measurement_values_used_for_coverage": False,
            "candidate_selection": None,
            "validated_reference": None,
            "physical_measurement_assessment": None,
            "acceptance_threshold_mm": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        })

    return {
        "schema": _COVERAGE_SCHEMA,
        "source_batch_schema": _BATCH_SCHEMA,
        "critical_pair_registry_schema": _REGISTRY_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "matrix_status": "DIAGNOSTIC_DOCUMENTARY_COVERAGE_ONLY",
        "critical_pair_count": len(critical_rows),
        "pairs_with_accepted_dossiers": pairs_with_accepted,
        "pairs_without_accepted_dossiers": len(critical_rows) - pairs_with_accepted,
        "pairs_with_rejected_dossiers": pairs_with_rejected,
        "pairs_with_one_traceable_physical_key_only": pairs_one_key_only,
        "pairs_ready_for_traceable_descriptive_review": pairs_ready,
        "total_accepted_dossiers": sum(r["accepted_dossiers"] for r in critical_rows),
        "total_rejected_dossiers_attributed_to_critical_pairs": sum(r["rejected_dossiers"] for r in critical_rows),
        "unassigned_rejected_dossiers": unassigned_rejections,
        "pair_coverage": critical_rows,
        "measurement_values_used_for_coverage": False,
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
