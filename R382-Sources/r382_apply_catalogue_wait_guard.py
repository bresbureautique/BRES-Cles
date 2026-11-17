#!/usr/bin/env python3
"""Apply R382 only to experimental R381 index; never touch stable V2.27."""
from pathlib import Path
import difflib,hashlib
p=Path(__file__).resolve().parent
base=(p/'index_R381_BASE.html').read_text('utf-8')
start_main='''async function runOCR(){
  if(typeof globalThis.ensureBresCatalogueR208==="function"){try{await globalThis.ensureBresCatalogueR208();}catch(_){/* OCR reste utilisable sans catalogue massif */}}
 const geometryEvidenceR215=captureDecisionGeometryEvidenceR215();'''
new_main='''async function runOCR(){
 const geometryEvidenceR215=captureDecisionGeometryEvidenceR215();'''
start_head='''async function searchFromHeadPhotos(){
  if(typeof globalThis.ensureBresCatalogueR208==="function"){try{await globalThis.ensureBresCatalogueR208();}catch(_){/* OCR tête reste utilisable sans catalogue massif */}}
  let fr=getHeadPhoto("recto"), fv=getHeadPhoto("verso");'''
new_head='''async function searchFromHeadPhotos(){
  let fr=getHeadPhoto("recto"), fv=getHeadPhoto("verso");'''
old_main=''' invalidateOCRDiagnosticForNewRequestR251(requestEpoch,"ocr-main");
 const requestIsCurrent=()=>ocrRequestIsCurrent(requestEpoch,epoch);
 const deadline=Date.now()+OCR_ACTION_BUDGET_MS;'''
new_main2=''' invalidateOCRDiagnosticForNewRequestR251(requestEpoch,"ocr-main");
 const requestIsCurrent=()=>ocrRequestIsCurrent(requestEpoch,epoch);
 // R382: new intent takes ownership BEFORE possibly asynchronous catalogue loading.
 // Never display an older OCR approval while a new capture is waiting for scripts.
 clearOCRReferenceIfCurrent();clearOCRBrandIfCurrent();
 invalidateIdentificationOutputs("Nouvelle lecture OCR principale en préparation : résultat précédent annulé.");
 if(typeof globalThis.ensureBresCatalogueR208==="function"){
   try{await globalThis.ensureBresCatalogueR208();}catch(_){/* OCR peut continuer sans catalogue complet */}
 }
 if(!requestIsCurrent())return; // superseded while the catalogue awaited
 const deadline=Date.now()+OCR_ACTION_BUDGET_MS;'''
old_head='''  invalidateOCRDiagnosticForNewRequestR251(requestEpoch,"ocr-head");
  const requestIsCurrent=()=>ocrRequestIsCurrent(requestEpoch,epoch);
  const geometryEvidenceR215=captureDecisionGeometryEvidenceR215();'''
new_head2='''  invalidateOCRDiagnosticForNewRequestR251(requestEpoch,"ocr-head");
  const requestIsCurrent=()=>ocrRequestIsCurrent(requestEpoch,epoch);
  // R382: revoke old OCR conclusions while catalogue load is still pending.
  clearOCRReferenceIfCurrent();clearOCRBrandIfCurrent();
  invalidateIdentificationOutputs("Nouvelle lecture OCR de tête en préparation : résultat précédent annulé.");
  if(typeof globalThis.ensureBresCatalogueR208==="function"){
    try{await globalThis.ensureBresCatalogueR208();}catch(_){/* pas de sélection automatique sur catalogue incomplet */}
  }
  if(!requestIsCurrent())return; // a newer request won the race
  const geometryEvidenceR215=captureDecisionGeometryEvidenceR215();'''
repls=[(start_main,new_main),(start_head,new_head),(old_main,new_main2),(old_head,new_head2)]
out=base
for old,new in repls:
 assert out.count(old)==1, f'Expected exactly 1 anchor, got {out.count(old)} for {old[:70]!r}'
 out=out.replace(old,new,1)
assert 'function rejectMissingOCRInputR381' in out
assert 'function rejectUnavailableOCRR380' in out
(p/'index.html').write_text(out,'utf-8')
(p/'index_R382.html').write_text(out,'utf-8')
(p/'R382_APPLY.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),out.splitlines(True),fromfile='index_R381_BASE.html',tofile='index_R382.html')),'utf-8')
print('R382 applied',len(out.encode()),hashlib.sha256(out.encode()).hexdigest())