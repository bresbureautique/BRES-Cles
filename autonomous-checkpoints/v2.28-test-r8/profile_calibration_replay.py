#!/usr/bin/env python3
"""BRES Clés V2.28 TEST R8 - replay/sweep robuste des sessions de calibration profil.

R8 accepte les anciens exports v1 et les exports v2. Il écarte les sessions
manifestement contaminées (référence instable, moins de deux captures, référence
absente du catalogue lorsqu'un contrôle R8 est disponible) et refuse de présenter
un réglage de seuil comme recommandation globale avec trop peu de références distinctes.
Aucune photo brute n'est lue : uniquement les mesures dérivées exportées.
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
ACCEPTED_SCHEMAS = {"bres-profile-calibration-v1", "bres-profile-calibration-v2"}


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
        if obj.get("schema") not in ACCEPTED_SCHEMAS:
            continue
        obj["_source"] = str(f)
        out.append(obj)
    return out


def session_integrity(session: dict[str, Any]) -> tuple[bool, str]:
    truth = normalize_ref(session.get("knownReference"))
    caps = session.get("captures") or []
    if not truth:
        return False, "référence certaine absente"
    if len(caps) < 2:
        return False, "moins de deux captures"

    integ = session.get("integrity") or {}
    if session.get("schema") == "bres-profile-calibration-v2":
        if integ.get("referenceStable") is False:
            return False, "référence modifiée pendant la session"
        if integ.get("referenceExistsInCatalogue") is False:
            return False, "référence certaine absente du catalogue"
        if integ.get("sufficientCaptures") is False:
            return False, "captures insuffisantes"
        if integ.get("validForReplay") is False:
            return False, "session R8 marquée non exploitable"

    cap_refs = {normalize_ref(c.get("knownReference")) for c in caps if normalize_ref(c.get("knownReference"))}
    if len(cap_refs) > 1:
        return False, "références différentes dans les captures"
    if cap_refs and truth not in cap_refs:
        return False, "référence de session différente des captures"
    return True, "ok"


def filter_eligible(sessions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    ok, skipped = [], []
    for s in sessions:
        good, reason = session_integrity(s)
        if good:
            ok.append(s)
        else:
            skipped.append({"source": s.get("_source", "(mémoire)"), "reason": reason})
    return ok, skipped


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
    correct = false = rejected = 0
    details = []
    for s in sessions:
        truth = normalize_ref(s.get("knownReference"))
        pred, reason = session_decision(s, t)
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
    return {"tested": tested, "correct": correct, "false": false, "rejected": rejected, "details": details}


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


def evidence_status(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    refs = sorted({normalize_ref(s.get("knownReference")) for s in sessions if normalize_ref(s.get("knownReference"))})
    n = len(refs)
    if n < 3:
        level = "OBSERVATION_ONLY"
        msg = "Trop peu de références distinctes pour modifier les seuils globaux. Conserver les seuils R8 actuels."
    elif n < 10:
        level = "PROVISIONAL"
        msg = "Échantillon encore limité : un jeu de seuils candidat peut être calculé, mais il ne doit pas remplacer les seuils globaux."
    else:
        level = "THRESHOLD_TUNING_READY"
        msg = "Diversité suffisante pour proposer un réglage global provisoire, toujours avec priorité à zéro faux accepté."
    return {"level": level, "distinct_known_references": n, "references": refs, "message": msg}


def synthetic_sessions() -> list[dict[str, Any]]:
    def cap(ref, q, score, margin, cross=None, known=None):
        return {"quality": {"score": q}, "topRef": ref, "topScore": score, "margin": margin,
                "crossCaptureSimilarity": cross, "photoProfileHex": "0" * 32, "knownReference": known}
    def s(truth, a, b, schema="bres-profile-calibration-v2", valid=True):
        integ = {"referenceStable": True, "referenceExistsInCatalogue": True, "sufficientCaptures": True, "validForReplay": valid}
        return {"schema": schema, "knownReference": truth, "integrity": integ if schema.endswith("v2") else None,
                "captures": [a, b]}
    out = [
        s("TE8D", cap("TE8D", 82, .73, .18, known="TE8D"), cap("TE8D", 85, .75, .20, .72, "TE8D")),
        s("AB12", cap("AB12", 76, .68, .14, known="AB12"), cap("AB12", 79, .70, .15, .63, "AB12")),
        s("CD34", cap("ZZ99", 88, .79, .20, known="CD34"), cap("ZZ99", 90, .81, .21, .39, "CD34")),
        s("EF56", cap("EF56", 42, .64, .12, known="EF56"), cap("EF56", 45, .66, .13, .65, "EF56")),
    ]
    bad = s("GH78", cap("GH78", 80, .70, .15, known="GH78"), cap("GH78", 82, .72, .16, .70, "ZZ00"))
    bad["integrity"]["referenceStable"] = False
    bad["integrity"]["validForReplay"] = False
    out.append(bad)
    return out


def selftest() -> None:
    sessions = synthetic_sessions()
    eligible, skipped = filter_eligible(sessions)
    assert len(eligible) == 4, (len(eligible), skipped)
    assert len(skipped) == 1 and "référence" in skipped[0]["reason"], skipped
    rec, metrics = sweep(eligible)
    assert metrics["false"] == 0, metrics
    assert metrics["correct"] >= 2, metrics
    ev = evidence_status(eligible)
    assert ev["level"] == "PROVISIONAL" and ev["distinct_known_references"] == 4, ev
    assert all("photoProfileHex" in c for s in eligible for c in s["captures"])
    print("SELFTEST OK")
    print(json.dumps({"eligible": len(eligible), "skipped": len(skipped), "candidate": rec,
                      "metrics": {k: v for k, v in metrics.items() if k != "details"}, "evidence": ev}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path, help="JSON R7/R8 ou dossiers contenant des sessions")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    sessions = load_sessions(args.paths)
    if not sessions:
        print("Aucune session bres-profile-calibration-v1/v2 trouvée.")
        return 2
    eligible, skipped = filter_eligible(sessions)
    if not eligible:
        print(json.dumps({"sessions_loaded": len(sessions), "eligible_sessions": 0, "skipped": skipped,
                          "message": "Aucune session exploitable pour le replay."}, ensure_ascii=False, indent=2))
        return 3
    base = evaluate(eligible, DEFAULTS)
    candidate, metrics = sweep(eligible)
    ev = evidence_status(eligible)
    report = {
        "sessions_loaded": len(sessions),
        "eligible_sessions": len(eligible),
        "skipped_sessions": skipped,
        "evidence": ev,
        "current_thresholds": DEFAULTS,
        "current_metrics": {k: v for k, v in base.items() if k != "details"},
        "candidate_thresholds": candidate,
        "recommended_thresholds": candidate if ev["level"] == "THRESHOLD_TUNING_READY" else None,
        "candidate_metrics": {k: v for k, v in metrics.items() if k != "details"},
        "recommendation_rule": "zéro faux accepté prioritaire ; une recommandation globale exige au moins 10 références certaines distinctes",
        "details": metrics["details"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
