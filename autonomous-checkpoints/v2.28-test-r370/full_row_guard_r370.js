/* R370 experimental guard: only after R369 expected-prefix guard validates canonical rows.
 * Covers all fields after the first verified snapshot; non-cryptographic, NOT yet integrated.
 */
function bresFullRowGuardR370(expectedCount, prefixCheck) {
  if (!Number.isInteger(expectedCount) || expectedCount < 1 || typeof prefixCheck !== 'function') throw Error('invalid guard setup');
  let snapshot = null;
  function check(db) {
    if (!Array.isArray(db) || db.length !== expectedCount) return {ok:false,reason:'count-mismatch'};
    const prefix = prefixCheck(db);
    if (!prefix || prefix.ok !== true) return {ok:false,reason:'prefix-inventory-invalid'};
    let h=2166136261>>>0, g=5381>>>0;
    for (const row of db) {
      if (!Array.isArray(row) || row.length < 5) return {ok:false,reason:'malformed-row'};
      for (let j=0;j<row.length;j++) {
        if (!Object.prototype.hasOwnProperty.call(row,j)) return {ok:false,reason:'sparse-row'};
        const v=row[j];
        if (v!==null && typeof v!=='string' && typeof v!=='boolean' &&
             !(typeof v==='number' && Number.isFinite(v))) return {ok:false,reason:'unsupported-value'};
      }
      const s=JSON.stringify(row)+'\n';
      for (let i=0;i<s.length;i++) {
        const x=s.charCodeAt(i);
        h=Math.imul(h^x,16777619)>>>0;
        g=(Math.imul(g,33)^x)>>>0;
      }
    }
    const key=h.toString(16).padStart(8,'0')+'-'+g.toString(16).padStart(8,'0');
    if (snapshot===null) { snapshot=key; return {ok:true,reason:'prefix-verified-snapshot-initialized'}; }
    return key===snapshot ? {ok:true,reason:'full-row-snapshot-matches'} :
      {ok:false,reason:'full-row-snapshot-mismatch'};
  }
  return Object.freeze({check});
}
if (typeof module !== 'undefined') module.exports={bresFullRowGuardR370};
