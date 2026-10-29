#!/usr/bin/env python3
"""R363 additive, non-decision OCR dependency visibility in V2.28 test only.

Never represent a loaded CDN JS as a certified cold/offline OCR install.
Safe replay requires exactly the verified R362 index bytes.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
EXPECTED_R362_INDEX_SHA='312b5201fea52fd92adc1a87aed592ac2dce7aba3dccab898bd537a694fced00'
OLD_HEADING='<h2>2. Lire la marque et la référence</h2>'
NEW_HEADING='''<h2>2. Lire la marque et la référence</h2>
<div id="ocrDependencyStatusR363" role="status" aria-live="polite" class="status warn">OCR : vérification locale des dépendances…</div>'''
OLD_CHECKPOINT='<div id="checkpointTrace" class="status ok"><b>Checkpoint de travail : R362 (outil Samsung)</b> — moteur V2.28 TEST R156 conservé ; V2.27 reste la version stable. La sortie du benchmark R336 est désormais autonome. Les exports métier historiques conservent leur provenance R319 (moteur R156).</div>'
NEW_CHECKPOINT='<div id="checkpointTrace" class="status ok"><b>Checkpoint de travail : R363 (visibilité des dépendances OCR)</b> — moteur V2.28 TEST R156 et téléchargement benchmark R336 conservés ; V2.27 reste la version stable. Les exports métier historiques conservent leur provenance R319 (moteur R156). Aucun statut de disponibilité OCR hors ligne n’est présumé.</div>'
TAIL='</script></body></html>'
ADD_SCRIPT='''</script>
<script id="r363-ocr-dependency-status">
/* R363: information only. No OCR invocation, reference decision or network request. */
(function(){
 const status=document.getElementById('ocrDependencyStatusR363');
 if(!status)return;
 function renderDependencyState(){
   const lib=globalThis.Tesseract;
   const hasApi=!!(lib&&typeof lib.createWorker==='function');
   status.className='status warn'; // yellow even when library is loaded: workers/assets NOT certified.
   status.dataset.libraryStateR363=hasApi?'loaded-not-certified':'missing';
   status.textContent=hasApi
     ? 'OCR : bibliothèque Tesseract chargée, mais fonctionnement hors ligne NON certifié. Le worker, le moteur WebAssembly et les données linguistiques peuvent nécessiter Internet. Une lecture OCR ne prouve jamais l’identité physique d’une clé.'
     : 'OCR : moteur Tesseract non chargé. La lecture automatique peut être indisponible (connexion ou ressource distante). Vous pouvez saisir la référence manuellement ; aucune identification n’est validée par ce message.';
 }
 renderDependencyState();
 window.addEventListener('load',renderDependencyState,{once:true});
})();
</script></body></html>'''

def patch(src):
    for token in (OLD_HEADING,OLD_CHECKPOINT,TAIL):
        if src.count(token)!=1:raise ValueError(f'Unexpected R362 marker count {src.count(token)} for {token[:50]}')
    return src.replace(OLD_HEADING,NEW_HEADING,1).replace(OLD_CHECKPOINT,NEW_CHECKPOINT,1).replace(TAIL,ADD_SCRIPT,1)

def main():
    p=R/'index.html';raw=p.read_bytes();actual=hashlib.sha256(raw).hexdigest()
    if actual!=EXPECTED_R362_INDEX_SHA:raise RuntimeError(f'Unexpected R362 index SHA {actual}')
    new=patch(raw.decode('utf-8')).encode('utf-8');p.write_bytes(new)
    print('R363 UI patch OK',len(new),'sha256',hashlib.sha256(new).hexdigest())
if __name__=='__main__':main()