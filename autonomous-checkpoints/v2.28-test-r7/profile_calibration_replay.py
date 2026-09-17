#!/usr/bin/env python3
"""BRES Clés V2.28 TEST R7 - replay/sweep des sessions de calibration profil.

Ce script ne lit aucune photo brute. Il exploite uniquement les JSON R7 exportés
(qualité, scores, marge, cohérence inter-captures et profil binaire dérivé).
"""
from __future__ import annotations
import argparse
import itertools
import json
from pathlib import Path
from typing import Any

DEFAULTS = {"quality": 60, "score": 0.58, "margin": 0.10, "cross": 0.55}
GRIDS = {
    "quality": [50, 55, 60, 65, 70, 75],
    "score": [0.50, 0.54, 0.58, 0.62, 0.66, 0.70],
    "margin": [0.05, 0.08, 0.10, 0.12, 0.15, 0.18],
    "cross": [0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
}


def normalize_ref(x: Any) -> str:
    return "".join(ch for ch in str(x or "").upper() if ch.isalnum())


def load_sessions(paths: list[Path]) -> list[dict[str, Any]]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            files.append(p)
    out = []
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if obj.get("schema") != "bres-profile-calibration-v1":
            continue
        obj["_source"] = str(f)
        out.append(obj)
    return out


def capture_pass(c: dict[str, Any], t: dict[str, float]) -> bool:
    q = float((c.get("quality") or {}).get("score") or 0)
    score = float(c.get("topScore") or 0)
    margin = float(c.get("margin") or 0)
    return q >= t["quality"] and score >= t["score"] and margin >= t["margin"]


def session_decision(session: dict[str, Any], t: dict[str, float]) -> tuple[str | None, str]:
    caps = session.get("captures") or []
    if len(caps) < 2:
        return None, "moins de deux captures"
    for a, b in zip(caps, caps[1:]):
        if not capture_pass(a, t) or not capture_pass(b, t):
            continue
        ra, rb = normalize_ref(a.get("topRef")), normalize_ref(b.get("topRef"))
        if not ra or ra != rb:
            continue
        cross = b.get("crossCaptureSimilarity")
        if cross is None or float(cross) < t["cross"]:
            continue
        return rb, "double capture forte et cohérente"
    return None, "aucune paire forte et cohérente"


def evaluate(sessions: list[dict[str, Any]], t: dict[str, float]) -> dict[str, Any]:
    correct = false = rejected = missing_truth = 0
    details = []
    for s in sessions:
        truth = normalize_ref(s.get("knownReference"))
        pred, reason = session_decision(s, t)
        if not truth:
            missing_truth += 1
            continue
        if pred is None:
            rejected += 1
            state = "REJET"
        elif pred == truth:
            correct += 1
            state = "OK"
        else:
            false += 1
            state = "FAUX"
        details.append({"source": s.get("_source", "(mémoire)"), "truth": truth, "pred": pred, "state": state, "reason": reason})
    tested = correct + false + rejected
    return {"tested": tested, "correct": correct, "false": false, "rejected": rejected, "missing_truth": missing_truth, "details": details}


def default_distance(t: dict[str, float]) -> float:
    return abs(t["quality"] - DEFAULTS["quality"]) / 10 + abs(t["score"] - DEFAULTS["score"]) / .1 + abs(t["margin"] - DEFAULTS["margin"]) / .1 + abs(t["cross"] - DEFAULTS["cross"]) / .1


def sweep(sessions: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, Any]]:
    best = None
    for q, sc, ma, cr in itertools.product(GRIDS["quality"], GRIDS["score"], GRIDS["margin"], GRIDS["cross"]):
        t = {"quality": q, "score": sc, "margin": ma, "cross": cr}
        m = evaluate(sessions, t)
        rank = (m["false"] == 0, -m["false"], m["correct"], -m["rejected"], -default_distance(t))
        if best is None or rank > best[0]:
            best = (rank, t, m)
    assert best is not None
    return best[1], best[2]


def synthetic_sessions() -> list[dict[str, Any]]:
    def cap(ref, q, score, margin, cross=None):
        return {"quality": {"score": q}, "topRef": ref, "topScore": score, "margin": margin, "crossCaptureSimilarity": cross, "photoProfileHex": "0" * 32}
    return [
        {"schema": "bres-profile-calibration-v1", "knownReference": "TE8D", "captures": [cap("TE8D", 82, .73, .18), cap("TE8D", 85, .75, .20, .72)]},
        {"schema": "bres-profile-calibration-v1", "knownReference": "AB12", "captures": [cap("AB12", 76, .68, .14), cap("AB12", 79, .70, .15, .63)]},
        {"schema": "bres-profile-calibration-v1", "knownReference": "CD34", "captures": [cap("ZZ99", 88, .79, .20), cap("ZZ99", 90, .81, .21, .39)]},
        {"schema": "bres-profile-calibration-v1", "knownReference": "EF56", "captures": [cap("EF56", 42, .64, .12), cap("EF56", 45, .66, .13, .65)]},
    ]


def selftest() -> None:
    sessions = synthetic_sessions()
    rec, metrics = sweep(sessions)
    assert metrics["false"] == 0, metrics
    assert metrics["correct"] >= 2, metrics
    assert all("photoProfileHex" in c for s in sessions for c in s["captures"])
    print("SELFTEST OK")
    print(json.dumps({"recommended": rec, "metrics": {k: v for k, v in metrics.items() if k != "details"}}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path, help="JSON R7 ou dossiers contenant des sessions R7")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    sessions = load_sessions(args.paths)
    if not sessions:
        print("Aucune session bres-profile-calibration-v1 trouvée.")
        return 2
    base = evaluate(sessions, DEFAULTS)
    rec, metrics = sweep(sessions)
    report = {
        "sessions": len(sessions),
        "current_thresholds": DEFAULTS,
        "current_metrics": {k: v for k, v in base.items() if k != "details"},
        "recommended_thresholds": rec,
        "recommended_metrics": {k: v for k, v in metrics.items() if k != "details"},
        "recommendation_rule": "zéro faux accepté prioritaire, puis maximum de décisions correctes",
        "details": metrics["details"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
