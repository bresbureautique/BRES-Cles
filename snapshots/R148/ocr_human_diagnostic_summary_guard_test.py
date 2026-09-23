from pathlib import Path
import re
s=Path('index.html').read_text(encoding='utf-8')
checks={
 'panel_present':'id="ocrDiagnosticSummary"' in s,
 'summary_builder':'function buildOCRHumanDiagnostic(reads,info)' in s,
 'summary_renderer':'function renderOCRHumanDiagnostic(reads,info)' in s,
 'export_human_summary':'lastOCRDiagnosticExport.humanSummary=human.exportSummary;' in s,
 'per_view_text':'views.map(v=>' in s and 'confiance ${v.confidence} %' in s,
 'maker_visible':'Fabricant(s) détecté(s)' in s,
 'nearby_visible':'Candidats proches' in s,
 'blockers_visible':'Pourquoi :' in s and 'automaticValidationBlocked' in s,
 'thresholds_explained':'OCR_PREFILL_THRESHOLD' in s and 'OCR_DECISION_THRESHOLD' in s,
 'non_decisional_export':'decisionInfluence:false' in s,
 'r148_export_schema':'schema:"bres-ocr-diagnostic-export-v10"' in s and 'version:"V2.28 TEST R148"' in s,
}
m=re.search(r'function buildOCRHumanDiagnostic\(reads,info\)\{(.*?)\n\}',s,re.S)
checks['no_state_write_in_summary']=bool(m) and all(x not in m.group(1) for x in ['setOCRField(','clearOCRReferenceIfCurrent(','verifyManualReference(','renderCatalogVisual('])
for k,v in checks.items(): print(('OK  ' if v else 'FAIL ')+k)
assert all(checks.values()), [k for k,v in checks.items() if not v]
print('SELFTEST OK')
