#!/usr/bin/env python3
"""R383 timeout of experimental OCR catalogue wait; no stable source is touched."""
from pathlib import Path
import hashlib,difflib
A=Path(__file__).resolve().parent
base=(A/'index_R382.html').read_text('utf-8')
wait_helper='''// R383: a missing/hung catalogue script must not hold OCR forever. A late
// rejection is handled, and each caller still owns its request epoch check.
const OCR_CATALOGUE_WAIT_MAX_MS_R383=3000;
async function waitForOCRCatalogueR383(){
 if(typeof globalThis.ensureBresCatalogueR208!=="function")return "unavailable";
 let timer=null;
 try{
   return await Promise.race([
     Promise.resolve().then(()=>globalThis.ensureBresCatalogueR208()).then(()=>"loaded",()=>"failed"),
     new Promise(resolve=>{timer=setTimeout(()=>resolve("timeout"),OCR_CATALOGUE_WAIT_MAX_MS_R383);})
   ]);
 }finally{if(timer!==null)clearTimeout(timer);}
}
'''
needle='const OCR_ACTION_BUDGET_MS=25000;'
assert base.count(needle)==1
out=base.replace(needle,needle+'\n'+wait_helper,1)
old_main=''' if(typeof globalThis.ensureBresCatalogueR208==="function"){
   try{await globalThis.ensureBresCatalogueR208();}catch(_){/* OCR peut continuer sans catalogue complet */}
 }
 if(!requestIsCurrent())return; // superseded while the catalogue awaited'''
new_main=''' const catalogueWaitR383=await waitForOCRCatalogueR383();
 if(!requestIsCurrent())return; // superseded while the catalogue awaited
 if(catalogueWaitR383!=="loaded"){
   el("ocrStatus").className="status warn";
   el("ocrStatus").textContent="Catalogue non disponible ou trop lent : OCR poursuivi sans sélection catalogue non vérifiée.";
 }'''
old_head='''  if(typeof globalThis.ensureBresCatalogueR208==="function"){
    try{await globalThis.ensureBresCatalogueR208();}catch(_){/* pas de sélection automatique sur catalogue incomplet */}
  }
  if(!requestIsCurrent())return; // a newer request won the race'''
new_head='''  const catalogueWaitR383=await waitForOCRCatalogueR383();
  if(!requestIsCurrent())return; // a newer request won the race
  if(catalogueWaitR383!=="loaded"){
    el("headSearchStatus").className="status warn";
    el("headSearchStatus").textContent="Catalogue non disponible ou trop lent : OCR poursuivi sans sélection catalogue non vérifiée.";
  }'''
for old,new in [(old_main,new_main),(old_head,new_head)]:
 assert out.count(old)==1, (old[:60],out.count(old))
 out=out.replace(old,new,1)
(A/'index.html').write_text(out,'utf-8')
(A/'index_R383.html').write_text(out,'utf-8')
(A/'R383_APPLY.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),out.splitlines(True),fromfile='index_R382.html',tofile='index_R383.html')),'utf-8')
print(hashlib.sha256(base.encode()).hexdigest(),hashlib.sha256(out.encode()).hexdigest())
