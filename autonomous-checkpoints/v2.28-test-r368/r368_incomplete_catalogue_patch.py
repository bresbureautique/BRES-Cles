#!/usr/bin/env python3
"""R368 TEST ONLY: fail-closed OCR prefill until the whole V3 catalogue is loaded.

Do NOT alter V2.27 stable, canonical data, source images or OCR engine.
"""
import hashlib
from pathlib import Path
A=Path(__file__).resolve().parent
OLD=hashlib.sha256((A/'index.html').read_bytes()).hexdigest()
# The parent SHA is checked against the R367 distributed archive in the verifier.

def patch(src):
    p='''  const ocrFoldAmbiguitiesR367=ocrLossyGlyphGroupsR367(candidates).filter(g=>'''
    q='''  // R368 TEST: do not trust a text-only candidate while any V3 fragment is
  // missing. The glyph-collision gate is only meaningful for all 5103 rows.
  // Manual reference entry stays available. This checks completeness, not
  // catalogue authenticity or the accuracy of a photographic recognition.
  const ocrCatalogueReadyR368=Array.isArray(globalThis.BRES_CATALOG_V3)&&
    globalThis.BRES_CATALOG_V3.length===5103;
  const ocrFoldAmbiguitiesR367=ocrLossyGlyphGroupsR367(candidates).filter(g=>'''
    assert src.count(p)==1
    src=src.replace(p,q,1)
    p='''  return {txt,makers,candidates,best,aliasMakers:detectedAliasMakers,aliasMakerConflict,referenceAmbiguity,ambiguousCanons,referenceRanking:referenceRanking.slice(0,4),compactAmbiguities,ocrFoldAmbiguitiesR367};'''
    q='''  if(!ocrCatalogueReadyR368){
    // Incomplete catalogue: never prefill, including pilot/XREF guesses.
    // This is a readiness guard, not a claim that the catalogue is authentic.
    best=null;
    if(candidates.length)referenceAmbiguity=true;
  }
  return {txt,makers,candidates,best,aliasMakers:detectedAliasMakers,aliasMakerConflict,referenceAmbiguity,ambiguousCanons,referenceRanking:referenceRanking.slice(0,4),compactAmbiguities,ocrFoldAmbiguitiesR367,ocrCatalogueReadyR368};'''
    assert src.count(p)==1;src=src.replace(p,q,1)
    p='''  if(info?.ocrFoldAmbiguitiesR367?.length)return info;'''
    q='''  if(info?.ocrCatalogueReadyR368===false)return info; // incomplete catalogue cannot release any automatic OCR guess
  if(info?.ocrFoldAmbiguitiesR367?.length)return info;'''
    assert src.count(p)==1;src=src.replace(p,q,1)
    p='''  if(ocrFoldAmbiguitiesR367.length)best=null; // conflict in either view blocks the other view's exact text
  return {txt:infos.map(i=>i.txt).filter(Boolean).join(" | "),makers,candidates,best,views:infos,crossViewConflict,conflictingCanons:crossViewConflict?strongCanons:[],referenceAmbiguity:infos.some(i=>i.referenceAmbiguity),ambiguousCanons,compactAmbiguities,ocrFoldAmbiguitiesR367};'''
    q='''  const ocrCatalogueReadyR368=infos.every(i=>i.ocrCatalogueReadyR368===true);
  if(ocrFoldAmbiguitiesR367.length||!ocrCatalogueReadyR368)best=null;
  return {txt:infos.map(i=>i.txt).filter(Boolean).join(" | "),makers,candidates,best,views:infos,crossViewConflict,conflictingCanons:crossViewConflict?strongCanons:[],referenceAmbiguity:infos.some(i=>i.referenceAmbiguity),ambiguousCanons,compactAmbiguities,ocrFoldAmbiguitiesR367,ocrCatalogueReadyR368};'''
    assert src.count(p)==1;src=src.replace(p,q,1)
    p='<b>Checkpoint de travail : R367 (anti-confusions OCR expérimentales)</b>'
    q='<b>Checkpoint de travail : R368 (catalogue complet requis pour OCR)</b>'
    assert src.count(p)==1;src=src.replace(p,q,1)
    p='''   if(info.candidates.length)text+=`<b>Code(s) brut(s) lu(s) :</b> ${info.candidates.join(", ")}<br>`;'''
    q='''   if(info.candidates.length)text+=`<b>Code(s) brut(s) lu(s) :</b> ${info.candidates.join(", ")}<br>`;
   if(info.ocrCatalogueReadyR368===false)text+=`<b>Catalogue incomplet :</b> attendre le chargement des 10 fichiers — sélection OCR automatique désactivée.<br>`;'''
    assert src.count(p)==1;src=src.replace(p,q,1)
    p='''    if(info.candidates.length) out+=`<b>Code(s) lu(s) :</b> ${info.candidates.join(", ")}<br>`;'''
    q='''    if(info.candidates.length) out+=`<b>Code(s) lu(s) :</b> ${info.candidates.join(", ")}<br>`;
    if(info.ocrCatalogueReadyR368===false)out+=`<b>Catalogue incomplet :</b> sélection OCR automatique désactivée.<br>`;'''
    assert src.count(p)==1;src=src.replace(p,q,1)
    return src

if __name__=='__main__':
    p=A/'index.html';data=patch(p.read_text(encoding='utf-8'));p.write_text(data,encoding='utf-8')
    print('R368 index',hashlib.sha256(p.read_bytes()).hexdigest())