from __future__ import annotations

import copy
import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_r132 = _load("r132_folder_adapter", "physical_collection_folder_adapter_r132.py")
_r130_registry = _load("r130_registry", "diagnostic_pair_registry_r130.py")
_r131_sufficiency = _load("r131_sufficiency", "traceable_sufficiency_analyzer_r131.py")

_SCHEMA = "bres-live-physical-collection-batch-ingestion-r133-v1"
_R132_SCHEMA = "bres-live-physical-collection-folder-import-r132-v1"
_R130_SCHEMA = "bres-live-discriminant-provenance-ingestion-r130-v1"


def _canonical_pair(pair: Dict[str, Any]) -> Tuple[str, str]:
    return tuple(sorted((str(pair.get("a", "")).strip(), str(pair.get("b", "")).strip())))


def _pair_key(pair: Tuple[str, str]) -> str:
    return f"{pair[0]}::{pair[1]}"


def _safe_folder_label(path: Path) -> str:
    try:
        return path.name or path.as_posix()
    except Exception:
        return str(path)


def _rejected_row(path: Path, errors: Iterable[str], base: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = base or {}
    return {
        "folder": _safe_folder_label(path),
        "folder_path": str(path),
        "accepted": False,
        "physical_key_id": base.get("physical_key_id"),
        "candidate_pair": copy.deepcopy(base.get("candidate_pair", {})),
        "source_folder_digest_sha256": base.get("source_folder_digest_sha256"),
        "errors": list(errors),
    }


def import_collection_folders(folders: Iterable[str | Path]) -> Dict[str, Any]:
    """Import multiple R132 physical collection folders without mixing identities.

    Each folder is first verified by the R132 byte-level adapter. R133 then enforces
    global non-reuse of capture ids, source SHA-256 values and complete-folder
    digests across the batch, while preserving physical-key identity. A physical
    key may have multiple independent dossiers for the same critical pair, but the
    same physical_key_id cannot be mapped to a different pair in the same batch.

    Accepted R130 provenance envelopes are forwarded to the diagnostic registry.
    Pair readiness is assessed by the existing R131 documentary/provenance layer.
    No measurement value can select or validate a catalogue reference here.
    """
    registry = _r130_registry.new_registry()
    accepted_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []

    seen_capture_ids: set[str] = set()
    seen_source_hashes: set[str] = set()
    seen_folder_digests: set[str] = set()
    key_to_pair: Dict[str, Tuple[str, str]] = {}

    for raw_folder in folders:
        path = Path(raw_folder).resolve()
        imported = _r132.import_collection_folder(path)

        if imported.get("schema") != _R132_SCHEMA:
            rejected_rows.append(_rejected_row(path, ["r132_adapter_schema_invalid"], imported))
            continue
        if not imported.get("accepted_for_diagnostics"):
            rejected_rows.append(_rejected_row(path, ["r132:" + str(e) for e in imported.get("errors", [])], imported))
            continue

        envelope = imported.get("diagnostic_envelope") or {}
        if envelope.get("schema") != _R130_SCHEMA or not envelope.get("accepted_for_diagnostics"):
            rejected_rows.append(_rejected_row(path, ["r130_diagnostic_envelope_invalid"], imported))
            continue

        physical_key_id = str(imported.get("physical_key_id", "")).strip()
        pair = _canonical_pair(imported.get("candidate_pair", {}))
        manifest = imported.get("source_folder_manifest", [])
        capture_ids = [str(x.get("capture_id", "")).strip() for x in manifest]
        source_hashes = [str(x.get("source_file_sha256", "")).strip().lower() for x in manifest]
        folder_digest = str(imported.get("source_folder_digest_sha256", "")).strip().lower()

        errors: List[str] = []
        if not physical_key_id:
            errors.append("physical_key_id_missing")
        if not pair[0] or not pair[1] or pair[0] == pair[1]:
            errors.append("candidate_pair_invalid")
        prior_pair = key_to_pair.get(physical_key_id) if physical_key_id else None
        if prior_pair is not None and prior_pair != pair:
            errors.append("physical_key_id_mapped_to_multiple_pairs")
        if any(cid in seen_capture_ids for cid in capture_ids):
            errors.append("capture_id_reused_across_folders")
        if any(sha in seen_source_hashes for sha in source_hashes):
            errors.append("source_file_sha256_reused_across_folders")
        if folder_digest and folder_digest in seen_folder_digests:
            errors.append("source_folder_digest_reused_across_folders")

        if errors:
            rejected_rows.append(_rejected_row(path, errors, imported))
            continue

        try:
            next_registry = _r130_registry.add_diagnostic_result(registry, envelope)
        except Exception as exc:
            rejected_rows.append(_rejected_row(path, ["registry:" + str(exc)], imported))
            continue

        registry = next_registry
        if physical_key_id not in key_to_pair:
            key_to_pair[physical_key_id] = pair
        seen_capture_ids.update(capture_ids)
        seen_source_hashes.update(source_hashes)
        if folder_digest:
            seen_folder_digests.add(folder_digest)

        accepted_rows.append({
            "folder": _safe_folder_label(path),
            "folder_path": str(path),
            "accepted": True,
            "physical_key_id": physical_key_id,
            "candidate_pair": {"a": pair[0], "b": pair[1]},
            "source_folder_digest_sha256": folder_digest or None,
            "source_capture_records": len(manifest),
            "errors": [],
        })

    pair_reports: Dict[str, Any] = {}
    pair_keys = sorted(registry.get("pairs", {}))
    for key in pair_keys:
        a, b = key.split("::", 1)
        pair_reports[key] = _r131_sufficiency.assess_traceable_sufficiency(registry, a, b)

    per_pair_key_ids: Dict[str, set[str]] = defaultdict(set)
    for row in accepted_rows:
        pair = _canonical_pair(row.get("candidate_pair", {}))
        per_pair_key_ids[_pair_key(pair)].add(str(row.get("physical_key_id")))

    pair_summary = {}
    for key in pair_keys:
        report = pair_reports[key]
        summary = report.get("pair_summary", {})
        pair_summary[key] = {
            "accepted_dossiers": sum(1 for r in accepted_rows if _pair_key(_canonical_pair(r.get("candidate_pair", {}))) == key),
            "distinct_physical_keys": len(per_pair_key_ids.get(key, set())),
            "physical_key_ids": sorted(per_pair_key_ids.get(key, set())),
            "traceable_descriptive_review_ready": bool(summary.get("pair_traceable_descriptive_review_ready")),
            "documentation_status": report.get("documentation_status"),
            "candidate_selection": None,
            "validated_reference": None,
            "acceptance_threshold_mm": None,
            "decision_authority": "NONE",
            "policy_status": "A_CONFIRMER",
        }

    return {
        "schema": _SCHEMA,
        "source_folder_schema": _R132_SCHEMA,
        "source_provenance_schema": _R130_SCHEMA,
        "active_test_runtime": "V2.28 TEST R116",
        "batch_status": "DIAGNOSTIC_ONLY",
        "accepted_folder_count": len(accepted_rows),
        "rejected_folder_count": len(rejected_rows),
        "accepted_folders": accepted_rows,
        "rejected_folders": rejected_rows,
        "distinct_physical_keys": len(key_to_pair),
        "distinct_pairs": len(pair_keys),
        "global_capture_ids_unique": True,
        "global_source_sha256_unique": True,
        "global_folder_digests_unique": True,
        "registry": registry,
        "pair_reports": pair_reports,
        "pair_summary": pair_summary,
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
