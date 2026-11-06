/* R371 TEST - to insert before ocrLossyGlyphGroupsR367 in R369 index.html.
 * Fixed expected double checksum of ALL canonical rows, not first-use snapshot.
 * Noncryptographic accidental-corruption detection only, NOT physical certification.
 */
function ocrCatalogueAllFieldsR371(){
  const db=globalThis.BRES_CATALOG_V3;
  if(!Array.isArray(db)||db.length!==5103)return {ok:false,reason:'full-count-not-5103'};
  let h=2166136261>>>0,g=5381>>>0;
  for(const row of db){
    if(!Array.isArray(row)||row.length!==12)return {ok:false,reason:'full-row-schema-invalid'};
    for(const i of [0,1,2,9])if(typeof row[i]!=='string')return {ok:false,reason:'full-string-type-invalid'};
    for(const i of [3,4,5,10,11])if(!Number.isFinite(row[i]))return {ok:false,reason:'full-numeric-type-invalid'};
    for(const i of [6,7,8]){
      const a=row[i];
      if(!Array.isArray(a)||a.length!==24)return {ok:false,reason:'full-profile-schema-invalid'};
      for(let k=0;k<24;k++)if(!Object.prototype.hasOwnProperty.call(a,k)||!Number.isFinite(a[k]))
        return {ok:false,reason:'full-profile-value-invalid'};
    }
    const s=JSON.stringify(row)+'\n';
    for(let i=0;i<s.length;i++){
      const x=s.charCodeAt(i);
      h=Math.imul(h^x,16777619)>>>0;
      g=(Math.imul(g,33)^x)>>>0;
    }
  }
  return h===3516111785&&g===1267167717
    ?{ok:true,reason:'expected-all-12-fields'}
    :{ok:false,reason:'full-row-inventory-mismatch'};
}
if(typeof module!=='undefined')module.exports={ocrCatalogueAllFieldsR371};
