from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
html=(ROOT/'index.html').read_text(encoding='utf-8'); errors=[]
def between(a,b):
 i=html.find(a); j=html.find(b,i+1) if i>=0 else -1
 if i<0 or j<0:return ''
 return html[i:j]
combined=between('function combinedDecision(','function setOCRField(')
head=between('if(info.best && info.best.sim>=OCR_PREFILL_THRESHOLD){','showXref(canon);')
checks={'runtime_r116_unchanged_label':'V2.28 TEST R116' in html,'combined_requires_matching_geometry':'geoTop&&geoTop.ref===ocrCanon&&geoTop.score>=55' in combined and 'status:"confirmed"' in combined,'combined_ocr_only_not_confirmed':'return {status:"ocr",ref:ocrCanon' in combined,'combined_conflicting_geometry_blocks':'geoTop&&geoTop.ref!==ocrCanon&&geoTop.score>=78' in combined and 'status:"conflict"' in combined,'head_requires_current_geometry':'if(currentSig)' in head and 'top && top.ref===canon && top.score>=55' in head,'head_without_geometry_candidate_only':'CANDIDAT PAR MARQUAGE' in head and 'validation géométrique' in head,'head_weak_geometry_needs_confirmation':'À CONFIRMER' in head and 'géométrie insuffisante pour valider' in head,'ocr_ambiguity_still_blocks_autoselection':'Référence OCR ambiguë :' in html and 'aucune sélection automatique' in html}
for k,v in checks.items():
 if not v:errors.append(k)
ev=ROOT/'catalogue/evidence/catalogue_ocr_high_risk_family_r119.json'
if not ev.exists(): errors.append('missing_r119_catalogue_evidence'); evidence={}
else:
 evidence=json.loads(ev.read_text(encoding='utf-8'))
 if evidence.get('metrics',{}).get('triple_risk_refs')!=556: errors.append('r119_triple_risk_count_mismatch')
 if evidence.get('ok') is not True: errors.append('r119_catalogue_evidence_not_ok')
report={'schema':'bres-ocr-high-risk-autovalidation-guard-r119-v1','milestone':'V2.28 TEST R116 / audit R119','policy':'Exact or fuzzy OCR text may prefill/propose a catalogue candidate, but final automatic VALIDÉ/confirmed state requires matching independent geometry; OCR-only and weak/conflicting geometry remain candidate/confirm/check states.','checks':checks,'triple_risk_refs':evidence.get('metrics',{}).get('triple_risk_refs'),'errors':errors,'ok':not errors}
(ROOT/'OCR_HIGH_RISK_AUTOVALIDATION_GUARD_R119.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS V2.28 TEST R116 — GARDE-FOU R119 AUTO-VALIDATION OCR À RISQUE','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['',f"Références catalogue triple risque liées au garde-fou: {report.get('triple_risk_refs')}",'SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'OCR_HIGH_RISK_AUTOVALIDATION_GUARD_R119.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines));sys.exit(1 if errors else 0)
