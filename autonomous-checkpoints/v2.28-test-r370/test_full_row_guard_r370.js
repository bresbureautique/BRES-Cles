/* Standalone offline Node test; node test_full_row_guard_r370.js */
'use strict';
const assert=require('node:assert/strict');
const {bresFullRowGuardR370}=require('./full_row_guard_r370.js');
function prefix(r) {
 let h=2166136261>>>0,g=5381>>>0;
 for (const row of r) {
   const s=JSON.stringify(row.slice(0,5))+'\n';
   for (let i=0;i<s.length;i++) { const x=s.charCodeAt(i); h=Math.imul(h^x,16777619)>>>0;g=(Math.imul(g,33)^x)>>>0; }
 }
 return [h,g];
}
const db=Array.from({length:4},(_,i)=>['TE'+i,'ABUS','KL',25+i,9,'FR'+i,i]);
const expected=JSON.stringify(prefix(db));
const guard=bresFullRowGuardR370(4,rows=>({ok:JSON.stringify(prefix(rows))===expected}));
const checks={};
checks.initial=guard.check(db).ok;
checks.unchanged=guard.check(db).ok;
db[2][6]++;checks.additional_column_changed=!guard.check(db).ok;db[2][6]--;
checks.restored=guard.check(db).ok;
db[0].push('EXTRA');checks.trailing_column_added=!guard.check(db).ok;db[0].pop();
db[1][1]='changed';checks.prefix_field_changed=!guard.check(db).ok;db[1][1]='ABUS';
db[3][6]=NaN;checks.not_finite=!guard.check(db).ok;db[3][6]=3;
db[3][6]=undefined;checks.undefined_value=!guard.check(db).ok;db[3][6]=3;
delete db[3][6];checks.hole=!guard.check(db).ok;db[3][6]=3;
db.pop();checks.missing_row=!guard.check(db).ok;
assert.equal(Object.keys(checks).length,10);
assert.ok(Object.values(checks).every(Boolean),JSON.stringify(checks));
process.stdout.write(JSON.stringify({ok:true,tests:10,scope:'synthetic rows only; integration and real catalogue NOT tested',checks})+'\n');
