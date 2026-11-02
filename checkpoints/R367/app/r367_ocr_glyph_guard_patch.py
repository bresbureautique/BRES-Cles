#!/usr/bin/env python3
"""R367 TEST ONLY: fail-closed for lossy OCR glyph collisions in full catalogue.

This changes V2.28 test's text-to-candidate logic, not V2.27 stable,
not image OCR, geometry, benchmark, or canonical catalogue sources.
"""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent/'index.html'
PARENT_SHA='d53be834808bb1634d68f3ac6aa085c7e8b644e0f90c07e2ed023830b7ac9ff3'
PREFIX='''function interpretOCR(raw){
  let txt=cleanOCR(raw);
  const makerWords=["JMA","SILCA"'''
GUARD='''  // R367 TEST: a lossy OCR reading can be an exact catalogue reference *and*
  // another canonical spelling when glyphs O/0, I/L/1, S/5, B/8 are confused.
  // Do not publish an automatic reference based solely on this text. The full
  // read-only catalogue must be present; neither aliases nor makers are merged.
  const ocrFoldAmbiguitiesR367=ocrLossyGlyphGroupsR367(candidates).filter(g=>
    !g.canons.every(canon=>compactAmbiguities.some(a=>(a.canons||[]).includes(canon)))
  );
'''
LABEL_OLD='<b>Checkpoint de travail : R366 (diagnostic OCR conservateur)</b>'
LABEL_NEW='<b>Checkpoint de travail : R367 (anti-confusions OCR expérimentales)</b>'
FUNCTION='''// R367 TEST: read-only index of non-equivalent canonical spellings sharing a
// LOSSY glyph transcript. Only a complete 5103-row catalogue can supply evidence.
// This is NOT a physical key equivalence, OCR accuracy claim or maker inference.
let ocrFoldIndexR367Cache=null,ocrFoldIndexR367Source=null;
function ocrLossyGlyphGroupsR367(candidates){
  const db=Array.isArray(globalThis.BRES_CATALOG_V3)?globalThis.BRES_CATALOG_V3:null;
  if(!db||db.length!==5103)return []; // cannot assert a full-catalogue collision
  if(!ocrFoldIndexR367Cache||ocrFoldIndexR367Source!==db){
    const groups=new Map(), fold=ref=>compactRef(ref).replace(/[OILSB]/g,c=>({O:'0',I:'1',L:'1',S:'5',B:'8'})[c]);
    for(const row of db){
      const canon=String(row?.[0]||'').toUpperCase().trim();
      if(!canon)continue;
      const key=fold(canon);if(!groups.has(key))groups.set(key,new Set());
      groups.get(key).add(canon);
    }
    ocrFoldIndexR367Cache=groups;
    ocrFoldIndexR367Source=db;
  }
  const fold=ref=>compactRef(ref).replace(/[OILSB]/g,c=>({O:'0',I:'1',L:'1',S:'5',B:'8'})[c]);
  const out=new Map();
  for(const cand of candidates||[]){
    const key=fold(cand),canons=[...(ocrFoldIndexR367Cache.get(key)||[])].sort();
    if(canons.length>1)out.set(key,{foldedText:key,canons,policy:'manual-review-required',source:'full-catalogue-only'});
  }
  return [...out.values()];
}
'''
OLD_RETURN='''  return {txt,makers,candidates,best,aliasMakers:detectedAliasMakers,aliasMakerConflict,referenceAmbiguity,ambiguousCanons,referenceRanking:referenceRanking.slice(0,4),compactAmbiguities};'''
NEW_RETURN='''  if(ocrFoldAmbiguitiesR367.length){
    referenceAmbiguity=true;
    ambiguousCanons=[...new Set([...ambiguousCanons,...ocrFoldAmbiguitiesR367.flatMap(g=>g.canons)])];
    best=null; // never accept an exact or fuzzy tie-broken spelling of lossy glyphs
  }
  return {txt,makers,candidates,best,aliasMakers:detectedAliasMakers,aliasMakerConflict,referenceAmbiguity,ambiguousCanons,referenceRanking:referenceRanking.slice(0,4),compactAmbiguities,ocrFoldAmbiguitiesR367};'''
OLD_MERGE='''  const compactAmbiguities=[...compactAmbiguityMap.values()];
  return {txt:infos.map(i=>i.txt).filter(Boolean).join(" | "),makers,candidates,best,views:infos,crossViewConflict,conflictingCanons:crossViewConflict?strongCanons:[],referenceAmbiguity:infos.some(i=>i.referenceAmbiguity),ambiguousCanons,compactAmbiguities};'''
NEW_MERGE='''  const compactAmbiguities=[...compactAmbiguityMap.values()];
  const ocrFoldAmbiguitiesR367=[...new Map(infos.flatMap(i=>i.ocrFoldAmbiguitiesR367||[]).map(g=>[g.foldedText,g])).values()];
  if(ocrFoldAmbiguitiesR367.length)best=null; // conflict in either view blocks the other view's exact text
  return {txt:infos.map(i=>i.txt).filter(Boolean).join(" | "),makers,candidates,best,views:infos,crossViewConflict,conflictingCanons:crossViewConflict?strongCanons:[],referenceAmbiguity:infos.some(i=>i.referenceAmbiguity),ambiguousCanons,compactAmbiguities,ocrFoldAmbiguitiesR367};'''
OLD_RESOLVE='''  if(!info||info.best||!sig||typeof globalThis.bresCatalogueAmbiguityGeometryR227!=="function")return info;'''
NEW_RESOLVE='''  // R367: no geometry promotion of *lossy glyph* identities without a verified key.
  if(info?.ocrFoldAmbiguitiesR367?.length)return info;
  if(!info||info.best||!sig||typeof globalThis.bresCatalogueAmbiguityGeometryR227!=="function")return info;'''

def patch(src):
    # Match the second interpretOCR, not the older historical definition.
    for marker in (PREFIX,OLD_RETURN,OLD_MERGE,OLD_RESOLVE,LABEL_OLD):
        assert src.count(marker)==1, (marker[:60],src.count(marker))
    return (src.replace(PREFIX,FUNCTION+PREFIX,1)
        .replace('''  const compactAmbiguities=[];
  for(const cand of candidates){''', '''  const compactAmbiguities=[];
  for(const cand of candidates){''',1)
        .replace('''  // R49: qualify XREF aliases by manufacturer and exclude descriptive metadata.''', GUARD+'\n  // R49: qualify XREF aliases by manufacturer and exclude descriptive metadata.',1)
        .replace(OLD_RETURN,NEW_RETURN,1)
        .replace(OLD_MERGE,NEW_MERGE,1)
        .replace(OLD_RESOLVE,NEW_RESOLVE,1)
        .replace(LABEL_OLD,LABEL_NEW,1))

def main():
    original=P.read_bytes()
    if PARENT_SHA and hashlib.sha256(original).hexdigest()!=PARENT_SHA:raise SystemExit('Wrong R366 parent index')
    result=patch(original.decode('utf-8'))
    P.write_text(result,encoding='utf-8')
    print('PATCH R367',hashlib.sha256(P.read_bytes()).hexdigest())
if __name__=='__main__':main()
