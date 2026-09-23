from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
errors=[]

def block_between(start_marker,end_marker,start=0):
    a=html.find(start_marker,start); b=html.find(end_marker,a+1) if a>=0 else -1
    if a<0 or b<0: raise RuntimeError(f'missing block {start_marker!r}')
    return html[a:b]

repeat=block_between('const OCR_REPEATABILITY_MAX_SAMPLES=5;','function buildOCRHumanDiagnostic(reads,info,repeatability=null){')
js=repeat+r'''
const base={epoch:12,status:'agreement',decisiveCanon:'TE8D',decisiveCanons:['TE8D'],views:[
 {side:'recto',topCanon:'TE8D',topSimilarity:.910,secondCanon:'TE8I',secondSimilarity:.750,margin:.160,ambiguous:false},
 {side:'verso',topCanon:'TE8D',topSimilarity:.900,secondCanon:'TE8I',secondSimilarity:.740,margin:.160,ambiguous:false}
]};
const small={epoch:12,status:'agreement',decisiveCanon:'TE8D',decisiveCanons:['TE8D'],views:[
 {side:'recto',topCanon:'TE8D',topSimilarity:.925,secondCanon:'TE8I',secondSimilarity:.763,margin:.162,ambiguous:false},
 {side:'verso',topCanon:'TE8D',topSimilarity:.884,secondCanon:'TE8I',secondSimilarity:.728,margin:.156,ambiguous:false}
]};
const large={epoch:12,status:'agreement',decisiveCanon:'TE8D',decisiveCanons:['TE8D'],views:[
 {side:'recto',topCanon:'TE8D',topSimilarity:.970,secondCanon:'TE8I',secondSimilarity:.750,margin:.220,ambiguous:false},
 {side:'verso',topCanon:'TE8D',topSimilarity:.900,secondCanon:'TE8I',secondSimilarity:.740,margin:.160,ambiguous:false}
]};
const changed={epoch:12,status:'conflict',decisiveCanon:null,decisiveCanons:['TE8D','TE8I'],views:[
 {side:'recto',topCanon:'TE8D',topSimilarity:.910,secondCanon:'TE8I',secondSimilarity:.750,margin:.160,ambiguous:false},
 {side:'verso',topCanon:'TE8I',topSimilarity:.890,secondCanon:'TE8D',secondSimilarity:.780,margin:.110,ambiguous:false}
]};
console.log(JSON.stringify({small:buildOCRRepeatabilitySummary([base,small]),large:buildOCRRepeatabilitySummary([base,large]),changed:buildOCRRepeatabilitySummary([base,changed])}));
'''
cp=subprocess.run(['node','-e',js],capture_output=True,text=True,timeout=30)
if cp.returncode:
    errors.append('node:'+cp.stderr.strip()); cases={}
else:
    cases=json.loads(cp.stdout)
checks={
 'tolerance_is_three_points':'const OCR_REPEATABILITY_SCORE_TOLERANCE=0.03;' in repeat,
 'small_score_drift_stable':cases.get('small',{}).get('status')=='stable' and cases.get('small',{}).get('candidateIdentityStable') is True and cases.get('small',{}).get('scoreWithinTolerance') is True,
 'small_drift_measured':0 < cases.get('small',{}).get('maxScoreDrift',0) <= .03,
 'large_score_drift_variable':cases.get('large',{}).get('status')=='variable' and cases.get('large',{}).get('variationKind')=='score-drift' and cases.get('large',{}).get('candidateIdentityStable') is True,
 'candidate_change_variable':cases.get('changed',{}).get('status')=='variable' and cases.get('changed',{}).get('variationKind')=='candidate-drift' and cases.get('changed',{}).get('candidateIdentityStable') is False,
 'diagnostic_only':all(cases.get(k,{}).get('decisionInfluence') is False for k in ('small','large','changed')),
 'visible_variation_kind':'changement de candidat/statut' in html and 'dérive de score supérieure à la tolérance' in html,
 'schema_v13':'bres-ocr-diagnostic-export-v13' in html and 'V2.28 TEST R151' in html,
 'thresholds_unchanged':'const OCR_PREFILL_THRESHOLD=0.70;' in html and 'const OCR_DECISION_THRESHOLD=0.88;' in html,
}
for k,v in checks.items():
    if not v: errors.append(k)
report={'schema':'bres-ocr-repeatability-tolerance-guard-v1','milestone':'V2.28 TEST R151','checks':checks,'cases':cases,'errors':errors,'ok':not errors}
(ROOT/'OCR_REPEATABILITY_TOLERANCE_GUARD_TEST_R151.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS V2.28 TEST R151 — TOLÉRANCE RÉPÉTABILITÉ OCR','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['','SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'OCR_REPEATABILITY_TOLERANCE_GUARD_TEST_R151.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines)); sys.exit(1 if errors else 0)
