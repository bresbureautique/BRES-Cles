#!/usr/bin/env python3
"""Apply only the reviewed R361 UI guard to a verified R360 TEST index.html.

Does not touch V2.27 or any stable branch. Rejects unknown base hashes.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,sys
R=Path(__file__).resolve().parent
BEFORE='el("manualThickness").addEventListener("input",()=>{bumpTeachThicknessEpochR291();});'
AFTER='''el("manualThickness").addEventListener("input",()=>{
  // R361: an edited physical measurement invalidates BOTH teaching and published ID evidence.
  // Preserve manual reference/brand and photos, but never display a prior catalog verdict or
  // OCR diagnostic as current after the measurement changed (even mid-async OCR).
  bumpTeachThicknessEpochR291();
  bumpIdentificationEpoch();
  clearTimeout(autoVerifyTimer);
  el("manualRefStatus").className="status warn";
  el("manualRefStatus").textContent="Épaisseur modifiée : revérifiez la référence et les mesures.";
  markAllOCRReadoutsStaleForPhotoContextR191("Épaisseur modifiée : relancez la lecture ou revérifiez la décision.");
  invalidateDecisionContextAndDiagnosticR172("Épaisseur modifiée : ancienne décision annulée, nouvelle vérification nécessaire.");
});'''
PARENT_SHA256='e461c52c1e076f61ce814a4545850edac0cfa099bc936436169d2f1898624761'

def patch(path):
    p=Path(path)
    source=p.read_bytes()
    if hashlib.sha256(source).hexdigest()!=PARENT_SHA256:raise ValueError('R360 source hash not matched; patch refused')
    text=source.decode('utf-8')
    if text.count(BEFORE)!=1 or AFTER in text:raise ValueError('unexpected target snippet; patch refused')
    result=text.replace(BEFORE,AFTER,1).encode('utf-8')
    p.write_bytes(result)
    return hashlib.sha256(result).hexdigest()
if __name__=='__main__':
    print('patched index SHA256',patch(sys.argv[1] if len(sys.argv)>1 else R/'index.html'))