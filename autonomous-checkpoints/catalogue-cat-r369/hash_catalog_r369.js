const fs=require('fs'), vm=require('vm'); const path=require('path'); const a=path.resolve(__dirname,'..','app','catalogue','v3')+path.sep;
const w={BRES_CATALOG_V3:[]};let sandbox={window:w};vm.createContext(sandbox);
for(let i=1;i<=10;i++)vm.runInContext(fs.readFileSync(a+'catalog-'+String(i).padStart(2,'0')+'.js','utf8'),sandbox);
let h=2166136261>>>0, g=5381>>>0;for(const row of w.BRES_CATALOG_V3){let s=JSON.stringify(row.slice(0,5))+'\n';for(let i=0;i<s.length;i++){const code=s.charCodeAt(i);h=Math.imul(h^code,16777619)>>>0;g=(Math.imul(g,33)^code)>>>0;}}
console.log(JSON.stringify({length:w.BRES_CATALOG_V3.length,hash1:h,hash2:g,expectedHex:h.toString(16).padStart(8,'0')+g.toString(16).padStart(8,'0'),rows:w.BRES_CATALOG_V3.slice(0,2).map(r=>r.slice(0,5))}));
