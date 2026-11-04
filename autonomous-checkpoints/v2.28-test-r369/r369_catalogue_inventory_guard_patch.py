#!/usr/bin/env python3
"""R369 TEST only: ordered catalogue reference/maker/dimension inventory guard.
This detects accidental partial, duplicate, reordered or modified lists with length 5103;
it does NOT authenticate catalogue JS, geometry or physical identifications.
"""
from pathlib import Path
import hashlib

A=Path(__file__).resolve().parent

def patch(src:str)->str:
    a='''function ocrLossyGlyphGroupsR367(candidates){
  const db=Array.isArray(globalThis.BRES_CATALOG_V3)?globalThis.BRES_CATALOG_V3:null;
  if(!db||db.length!==5103)return []; // cannot assert a full-catalogue collision'''
    b='''// R369 TEST: inventory check, not cryptographic authenticity. Two independent
// 32-bit checksums cover ordered canonical reference, manufacturer, class and
// dimensions (columns 0..4). This fails closed on accidental repeated/modified
// chunks that otherwise produce exactly 5103 rows. Recomputed per call to catch
// in-place edits even if the global array object and row count do not change.
function ocrCatalogueInventoryR369(){
  const db=globalThis.BRES_CATALOG_V3;
  if(!Array.isArray(db)||db.length!==5103)return {ok:false,reason:'count-not-5103'};
  let h=2166136261>>>0,g=5381>>>0;
  for(const row of db){
    if(!Array.isArray(row)||row.length<5)return {ok:false,reason:'malformed-row'};
    const s=JSON.stringify(row.slice(0,5))+'\\n';
    for(let i=0;i<s.length;i++){
      const x=s.charCodeAt(i);
      h=Math.imul(h^x,16777619)>>>0;
      g=(Math.imul(g,33)^x)>>>0;
    }
  }
  return h===2511607957&&g===2549944249
    ?{ok:true,reason:'expected-inventory'}
    :{ok:false,reason:'inventory-mismatch'};
}
function ocrLossyGlyphGroupsR367(candidates,inventoryReady=false){
  const db=Array.isArray(globalThis.BRES_CATALOG_V3)?globalThis.BRES_CATALOG_V3:null;
  if(!inventoryReady||!db||db.length!==5103)return []; // no unsupported collision claims'''
    assert src.count(a)==1,('missing initial function',src.count(a))
    src=src.replace(a,b,1)
    a='''  const ocrCatalogueReadyR368=Array.isArray(globalThis.BRES_CATALOG_V3)&&
    globalThis.BRES_CATALOG_V3.length===5103;
  const ocrFoldAmbiguitiesR367=ocrLossyGlyphGroupsR367(candidates).filter(g=>'''
    b='''  const catalogueInventoryR369=ocrCatalogueInventoryR369();
  const ocrCatalogueReadyR368=catalogueInventoryR369.ok;
  const ocrCatalogueStatusR369=catalogueInventoryR369.reason;
  const ocrFoldAmbiguitiesR367=ocrLossyGlyphGroupsR367(candidates,ocrCatalogueReadyR368).filter(g=>'''
    assert src.count(a)==1,('missing readiness',src.count(a));src=src.replace(a,b,1)
    a='''ocrFoldAmbiguitiesR367,ocrCatalogueReadyR368};'''
    b='''ocrFoldAmbiguitiesR367,ocrCatalogueReadyR368,ocrCatalogueStatusR369};'''
    assert src.count(a)==2,('return placements',src.count(a));src=src.replace(a,b,2) # interpretOCR and interpretOCRViews returns
    a='''  const ocrCatalogueReadyR368=infos.every(i=>i.ocrCatalogueReadyR368===true);
  if(ocrFoldAmbiguitiesR367.length||!ocrCatalogueReadyR368)best=null;'''
    b='''  const ocrCatalogueReadyR368=infos.every(i=>i.ocrCatalogueReadyR368===true);
  const ocrCatalogueStatusR369=ocrCatalogueReadyR368?'expected-inventory':
    (infos.find(i=>i.ocrCatalogueReadyR368===false)?.ocrCatalogueStatusR369||'inventory-unavailable');
  if(ocrFoldAmbiguitiesR367.length||!ocrCatalogueReadyR368)best=null;'''
    assert src.count(a)==1;src=src.replace(a,b,1)
    a='''  if(info.ocrCatalogueReadyR368===false)text+=`<b>Catalogue incomplet :</b> attendre le chargement des 10 fichiers — sélection OCR automatique désactivée.<br>`;'''
    b='''  if(info.ocrCatalogueReadyR368===false)text+=`<b>Catalogue incomplet ou non conforme :</b> chargement / inventaire à vérifier (${info.ocrCatalogueStatusR369||'inconnu'}) — sélection OCR automatique désactivée.<br>`;'''
    assert src.count(a)==1;src=src.replace(a,b,1)
    a='''    if(info.ocrCatalogueReadyR368===false)out+=`<b>Catalogue incomplet :</b> sélection OCR automatique désactivée.<br>`;'''
    b='''    if(info.ocrCatalogueReadyR368===false)out+=`<b>Catalogue incomplet ou non conforme :</b> sélection OCR automatique désactivée.<br>`;'''
    assert src.count(a)==1;src=src.replace(a,b,1)
    a='''<b>Checkpoint de travail : R368 (catalogue complet requis pour OCR)</b>'''
    b='''<b>Checkpoint de travail : R369 (inventaire catalogue contrôlé)</b>'''
    assert src.count(a)==1;src=src.replace(a,b,1)
    return src

if __name__=='__main__':
    p=A/'index.html';p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
    print(hashlib.sha256(p.read_bytes()).hexdigest())
