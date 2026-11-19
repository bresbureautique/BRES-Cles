#!/usr/bin/env python3
"""Build experimental R384 from verified R383 source, never touch V2.27."""
from pathlib import Path
import hashlib,difflib
A=Path(__file__).resolve().parent
base=(A/'v228-catalogue_R383.js').read_text('utf8')
old='''  async function ensureCatalogue(status){
    if(window.BRES_CATALOG_V3 && window.BRES_CATALOG_V3.length>5000)return window.BRES_CATALOG_V3;
    if(loadingPromise)return loadingPromise;
    window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];
    loadingPromise=(async()=>{
      for(let i=0;i<CHUNKS.length;i++){
        if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
        await loadScript(CHUNKS[i]);
      }
      catalogueStatsFor(window.BRES_CATALOG_V3);
      return window.BRES_CATALOG_V3;
    })();
    return loadingPromise;
  }
'''
new='''  // R384 TEST: a transient chunk failure must never poison the loader forever.
  // A retry starts from a fresh array (no duplicate partial rows), preserves
  // the single-flight promise, and accepts only the COMPLETE canonical inventory.
  // This guard does not infer compatibility, manufacturers or OCR identity.
  function catalogueIsCompleteR384(db){
    if(!Array.isArray(db)||db.length!==5103)return false;
    // When the app's all-field inventory verifier is present, use its fixed
    // expected hashes rather than trusting an arbitrary 5103-row array.
    const verify=globalThis.ocrCatalogueAllFieldsR371;
    if(typeof verify!=="function")return false;
    try{return verify().ok===true;}catch(_){return false;}
  }
  async function ensureCatalogue(status){
    // An in-flight loader takes precedence over a partially populated array.
    if(loadingPromise)return loadingPromise;
    if(catalogueIsCompleteR384(window.BRES_CATALOG_V3))return window.BRES_CATALOG_V3;
    // Do not reuse rows left by a failed attempt or a mutated complete array.
    window.BRES_CATALOG_V3=[];
    catalogueStats=null;lastCatalogueDb=null;
    let pending=null;
    pending=(async()=>{
      try{
        for(let i=0;i<CHUNKS.length;i++){
          if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
          await loadScript(CHUNKS[i]);
        }
        if(!catalogueIsCompleteR384(window.BRES_CATALOG_V3))
          throw new Error("Catalogue incomplet ou altéré : inventaire R371 non conforme");
        catalogueStatsFor(window.BRES_CATALOG_V3);
        return window.BRES_CATALOG_V3;
      }catch(error){
        // A rejected script has completed; there is no outstanding chunk
        // belonging to this sequential loader. The next call may retry safely.
        if(loadingPromise===pending){
          window.BRES_CATALOG_V3=[];
          catalogueStats=null;lastCatalogueDb=null;
        }
        throw error;
      }finally{
        if(loadingPromise===pending)loadingPromise=null;
      }
    })();
    loadingPromise=pending;
    return pending;
  }
'''
assert base.count(old)==1,(base.count(old),'loader signature changed')
out=base.replace(old,new,1)
(A/'v228-catalogue.js').write_text(out,'utf8')
(A/'v228-catalogue_R384.js').write_text(out,'utf8')
(A/'R384_APPLY.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),out.splitlines(True),fromfile='v228-catalogue_R383.js',tofile='v228-catalogue_R384.js')),'utf8')
print('R383',hashlib.sha256(base.encode()).hexdigest());print('R384',hashlib.sha256(out.encode()).hexdigest())