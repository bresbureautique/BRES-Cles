from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
errors=[]

def block_between(start_marker,end_marker,start=0):
    a=html.find(start_marker,start); b=html.find(end_marker,a+1) if a>=0 else -1
    if a<0 or b<0: raise RuntimeError(f'missing block {start_marker!r}')
    return html[a:b]

series=block_between('const OCR_REPEATABILITY_MAX_SAMPLES=5;','function buildOCRHumanDiagnostic(reads,info,repeatability=null){')
js=r'''
let currentSig=null,ocrCaptureCycleEpoch=0,identificationEpoch=0;
function el(){return {className:'',textContent:'',innerHTML:''};}
function escapeOCRDiagnosticText(v){return String(v??'');}
function buildCloseReferenceDiagnostic(info){return info.close;}
''' + series + r'''
const mkInfo=(canon='TE8D',status='agreement')=>({close:{status,decisiveCanon:canon,decisiveCanons:canon?[canon]:[],competingCanons:['TE8D','TE8I'],views:[
 {side:'recto',topCanon:canon,topSimilarity:.91,secondCanon:'TE8I',secondSimilarity:.74,margin:.17,ambiguous:false},
 {side:'verso',topCanon:canon,topSimilarity:.90,secondCanon:'TE8I',secondSimilarity:.73,margin:.17,ambiguous:false}
]}});
const geomA={width_mm:42,height_mm:23,area:.42,bladeFill:.43,headFill:.68};
const geomA2={width_mm:43.2,height_mm:22.5,area:.44,bladeFill:.45,headFill:.66};
const geomB={width_mm:73,height_mm:41,area:.78,bladeFill:.81,headFill:.19};
currentSig=geomA;ocrCaptureCycleEpoch=1;
const start1=startOCRCaptureSeries(); const id1=ocrCaptureSeriesId;
const accepted1=recordOCRCaptureSeries(mkInfo(),id1);
currentSig=geomA2;ocrCaptureCycleEpoch=2;
const accepted2=recordOCRCaptureSeries(mkInfo(),id1);
const start2=startOCRCaptureSeries(); const id2=ocrCaptureSeriesId;
ocrCaptureCycleEpoch=3;
const stale=recordOCRCaptureSeries(mkInfo(),id1);
currentSig=geomB;ocrCaptureCycleEpoch=4;
const mismatch=recordOCRCaptureSeries(mkInfo('TE8I'),id2);
currentSig=geomA2;ocrCaptureCycleEpoch=5;
const acceptedAfterReject=recordOCRCaptureSeries(mkInfo(),id2);
ocrCaptureSeriesActive=false;ocrCaptureSeriesAnchor=null;ocrCaptureSeriesHistory=[];currentSig=geomA;ocrCaptureCycleEpoch=6;
ocrCaptureSeriesId=10;ocrCaptureSeriesActive=true;
const firstAnchors=recordOCRCaptureSeries(mkInfo(),10);
console.log(JSON.stringify({start1,id1,accepted1,accepted2,start2,id2,stale,mismatch,acceptedAfterReject,firstAnchors,anchor:ocrCaptureSeriesAnchor}));
'''
cp=subprocess.run(['node','-e',js],capture_output=True,text=True,timeout=30)
if cp.returncode:
    errors.append('node:'+cp.stderr.strip()); cases={}
else:
    cases=json.loads(cp.stdout)

checks={
 'request_captures_series_id':'captureSeriesId:ocrCaptureSeriesActive?ocrCaptureSeriesId:null' in html,
 'same_series_accepts':cases.get('accepted1',{}).get('rejectedCycle') is False and cases.get('accepted2',{}).get('cycleCount')==2,
 'small_geometry_drift_allowed':cases.get('accepted2',{}).get('sessionGuard',{}).get('geometryMismatch') is False,
 'old_series_result_rejected':cases.get('stale',{}).get('status')=='session-changed' and cases.get('stale',{}).get('rejectedCycle') is True and cases.get('stale',{}).get('cycleCount')==0,
 'different_key_geometry_rejected':cases.get('mismatch',{}).get('status')=='key-mismatch-suspected' and cases.get('mismatch',{}).get('sessionGuard',{}).get('geometryMismatch') is True and cases.get('mismatch',{}).get('cycleCount')==0,
 'rejected_cycles_do_not_pollute_history':cases.get('acceptedAfterReject',{}).get('cycleCount')==1,
 'first_cycle_can_create_anchor':cases.get('firstAnchors',{}).get('rejectedCycle') is False and cases.get('anchor',{}).get('width_mm')==42,
 'diagnostic_only':all(cases.get(k,{}).get('decisionInfluence') is False for k in ('accepted1','accepted2','stale','mismatch','acceptedAfterReject','firstAnchors')),
 'export_contains_session_guard':'lastOCRDiagnosticExport.captureSeriesGuard=captureSeries.sessionGuard||null;' in html,
 'ocr_calls_bind_request':html.count('enableOCRDiagnosticExport(reads,info,request);')>=2,
 'visible_rejection_messages':'résultat OCR d\'une ancienne série ignoré' in html and 'géométrie paraît appartenir à une autre clé' in html,
 'thresholds_unchanged':'const OCR_PREFILL_THRESHOLD=0.70;' in html and 'const OCR_DECISION_THRESHOLD=0.88;' in html,
 'active_version_r154':'V2.28 TEST R154' in html and 'BRES_diagnostic_OCR_R154_' in html,
}
for k,v in checks.items():
    if not v: errors.append(k)
report={'schema':'bres-ocr-capture-session-guard-v1','milestone':'V2.28 TEST R154','checks':checks,'cases':cases,'errors':errors,'ok':not errors}
(ROOT/'OCR_CAPTURE_SESSION_GUARD_TEST_R154.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS V2.28 TEST R154 — GARDE DE SESSION MULTI-PRISES OCR','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['','SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'OCR_CAPTURE_SESSION_GUARD_TEST_R154.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines)); sys.exit(1 if errors else 0)
