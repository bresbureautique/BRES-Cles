#!/usr/bin/env python3
"""R381 test-only patch, applied to R380; stable V2.27 never touched."""
from pathlib import Path
import sys
A=Path(__file__).resolve().parent
p=A/'index.html';base=(A/'index_R380_BASE.html').read_text('utf8')
anchor='async function runOCR(){'
new='''// R381 TEST: an explicit OCR attempt with missing prerequisites (no published
// main geometry / no head photograph) must invalidate older OCR-derived UI.
// This is deliberately fail-closed and never changes the manually typed values.
function rejectMissingOCRInputR381(source,statusId,reason){
 beginFreshCatalogueQa2OcrCycleR171(source);
 const request=beginOCRRequest(); // invalidate any in-flight recognition
 invalidateOCRDiagnosticForNewRequestR251(request.requestEpoch,source);
 clearOCRReferenceIfCurrent();
 clearOCRBrandIfCurrent();
 invalidateIdentificationOutputs("Ancien résultat rendu obsolète : données nécessaires à la lecture OCR absentes.");
 const target=el(statusId);
 target.className="status bad";
 target.textContent=String(reason||"Lecture OCR impossible : données manquantes.");
 return {blocked:true,source,requestEpoch:request.requestEpoch};
}
'''
assert base.count(anchor)==1
assert base.count('el("ocrStatus").className="status bad";el("ocrStatus").textContent=geometryDecisionUnavailableMessageR215();return;')==1
assert base.count('el("headSearchStatus").className="status bad";\n    el("headSearchStatus").textContent="Ajoutez au moins une photo rapprochée de la tête.";\n    return;')==1
out=base.replace(anchor,new+anchor,1)
out=out.replace('el("ocrStatus").className="status bad";el("ocrStatus").textContent=geometryDecisionUnavailableMessageR215();return;',
                'rejectMissingOCRInputR381("ocr-main","ocrStatus",geometryDecisionUnavailableMessageR215());return;',1)
out=out.replace('el("headSearchStatus").className="status bad";\n    el("headSearchStatus").textContent="Ajoutez au moins une photo rapprochée de la tête.";\n    return;',
                'rejectMissingOCRInputR381("ocr-head","headSearchStatus","Ajoutez au moins une photo rapprochée de la tête. Aucune ancienne lecture OCR ne reste valable.");\n    return;',1)
assert out!=base
p.write_text(out,'utf8')
print('R381 patch applied, bytes:',len(out.encode()))
