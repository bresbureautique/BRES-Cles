#!/usr/bin/env python3
"""R364: additive, read-only Tesseract preflight exporter for V2.28 TEST.

Does not call Tesseract or claim cold/offline OCR; no keys/images/client data.
Guard patch source with the exact R363 SHA-256 so replay is unambiguous.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
EXPECTED_R363_INDEX_SHA='f4d080357d57c9f0c0034e63a5544b4c2b4fb8594b10e2988ce84ee4ed24ccb9'
OLD_BANNER='<div id="ocrDependencyStatusR363" role="status" aria-live="polite" class="status warn">OCR : vérification locale des dépendances…</div>'
NEW_BANNER=OLD_BANNER+'''\n<div class="status" style="margin-top:6px"><button type="button" id="ocrPreflightExportR364">Exporter l’état technique OCR (sans photo)</button><div id="ocrPreflightResultR364" role="status" aria-live="polite">Diagnostic local seulement : ni lecture de clé, ni essai de worker, ni certification hors ligne.</div></div>'''
OLD_CHECKPOINT='<b>Checkpoint de travail : R363 (visibilité des dépendances OCR)</b>'
NEW_CHECKPOINT='<b>Checkpoint de travail : R364 (export diagnostic OCR local)</b>'
TAIL='</script></body></html>'
APPEND='''</script>
<script id="r364-ocr-local-preflight-export">
/* Diagnostic d'environnement uniquement : no fetch, no worker, no photos, no identification. */
(function(){
 const button=document.getElementById('ocrPreflightExportR364');
 const status=document.getElementById('ocrPreflightResultR364');
 if(!button||!status)return;
 button.addEventListener('click',function(){
   const libraryPresent=!!(globalThis.Tesseract&&typeof globalThis.Tesseract.createWorker==='function');
   const preflight={
     schema:'bres-r364-ocr-preflight-local-v1',
     checkpoint:'R364',
     engine:'V2.28 TEST R156',
     stable:'V2.27 unchanged',
     recordedAtUtc:new Date().toISOString(),
     checkMode:'read-only-no-worker-no-requests',
     scriptApiPresent:libraryPresent,
     scriptOriginClass:'remote-cdn-not-embedded',
     workerInitialized:false,
     wasmVerified:false,
     languageDataVerified:false,
     coldOfflineOcrCertified:false,
     physicalKeyVerified:false,
     autoIdentificationPermitted:false,
     nextStep:'Full cold-offline OCR requires local worker/WASM/language assets and a separate real recognition test.'
   };
   const content=JSON.stringify(preflight,null,2)+'\\n';
   const url=URL.createObjectURL(new Blob([content],{type:'application/json'}));
   const a=document.createElement('a');a.href=url;
   a.download='BRES_Cles_R364_Diagnostic_OCR_Local.json';
   a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);
   status.textContent='Diagnostic OCR exporté. OCR hors ligne NON certifié. Aucune photo ni référence exportée.';
 });
})();
</script></body></html>'''

def patch(html:str)->str:
    for label,needle in [('OCR banner',OLD_BANNER),('checkpoint',OLD_CHECKPOINT),('tail',TAIL)]:
        if html.count(needle)!=1:raise ValueError(f'{label}: expected exactly one anchor; got {html.count(needle)}')
    return html.replace(OLD_BANNER,NEW_BANNER,1).replace(OLD_CHECKPOINT,NEW_CHECKPOINT,1).replace(TAIL,APPEND,1)

def main():
    p=R/'index.html';old=p.read_bytes();actual=hashlib.sha256(old).hexdigest()
    if actual!=EXPECTED_R363_INDEX_SHA:raise RuntimeError(f'Unexpected parent index: {actual}')
    new=patch(old.decode('utf-8')).encode('utf-8');p.write_bytes(new)
    print('R364 OCR diagnostic-only patch',len(new),hashlib.sha256(new).hexdigest())
if __name__=='__main__':main()