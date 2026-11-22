#!/usr/bin/env python3
"""Independent CAT-R387 audit: per-fragment digest parity and mutation sensitivity.
Canonical sources are never changed; app and catalogue remain separate products.
"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import hashlib,json,subprocess,re,time,sys
C=Path(__file__).resolve().parent; A=C.parent/'app';start=time.monotonic()
prior=json.loads((C/'CAT_R386_FRAGMENT_CONTRACT.json').read_text('utf8'))
app=(A/'v228-catalogue_R387.js').read_text('utf8')
m=re.search(r'const fragmentDigestsR387=(\[.*?\]);',app,re.S)
assert m, 'Expected R387 digest contract not found'
expected=json.loads(m.group(1));checks={};stats={};rows=[]
node=r'''
const fs=require('fs'),vm=require('vm'),path=require('path');
const base=process.argv[1];
function sum(rows){let h=2166136261>>>0,g=5381>>>0;
 for(let i=0;i<rows.length;i++){let item=JSON.stringify(rows[i])+'\n';
  for(const ch of item){const code=ch.charCodeAt(0);h=Math.imul(h^code,16777619)>>>0;g=(Math.imul(g,33)^code)>>>0;}}
 return [h,g];}
let ret=[];
for(let i=1;i<=10;i++){
 const ctx={window:{BRES_CATALOG_V3:[]}};
 vm.runInNewContext(fs.readFileSync(path.join(base,'catalogue','v3','catalog-'+String(i).padStart(2,'0')+'.js'),'utf8'),ctx);
 const r=ctx.window.BRES_CATALOG_V3;
 const orig=sum(r), alt=[];
 for(const type of ['maker','profile','dimension','key']){
  const copy=JSON.parse(JSON.stringify(r)),row=copy[1];
  if(type==='maker')row[1]='UNVERIFIED_MAKER_R387';
  if(type==='profile')row[6][3]+=0.001;
  if(type==='dimension')row[3]+=0.01;
  if(type==='key')row[0]+='R387';
  alt.push({kind:type,changed:JSON.stringify(copy)!==JSON.stringify(r),digest:sum(copy)});
 }
 ret.push({length:r.length,first:r[0][0],last:r[r.length-1][0],original:orig,mutations:alt});
}
process.stdout.write(JSON.stringify(ret));
'''
actual=json.loads(subprocess.run(['node','-e',node,str(A)],capture_output=True,text=True,check=True).stdout)
checks['ten_complete_expected_digests']=len(expected)==len(actual)==10
for i,r in enumerate(actual,1):
 name=f'catalog-{i:02}.js';raw=(A/'catalogue'/'v3'/name).read_bytes()
 chunk=json.loads(re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw.strip(),re.S).group(1))
 rows.extend(chunk);digest=hashlib.sha256(raw).hexdigest()
 checks[f'{name}_sha256_unchanged']=digest==prior['chunks'][name]['sha256']
 checks[f'{name}_shape_contract_unchanged']=[r['length'],r['first'],r['last']]==prior['app_fragment_guard_contract'][i-1]
 checks[f'{name}_runtime_digest_parity']=r['original']==expected[i-1]
 checks[f'{name}_all_4_mutations_detected']=all(x['changed'] and x['digest']!=r['original'] for x in r['mutations'])
 stats[name]={'sha256':digest,'rows':r['length'],'digest':r['original'],'mutation_types':[x['kind'] for x in r['mutations']]}
checks['5103_unique_refs_12_columns']=len(rows)==5103 and len({row[0] for row in rows})==5103 and all(len(row)==12 for row in rows)
checks['164_missing_makers_remain_unassigned']=sum(not row[1] for row in rows)==164
fold_map=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def fold(s):return re.sub('[^A-Z0-9]','',s.upper().strip()).translate(fold_map)
by=defaultdict(set)
for row in rows:by[fold(row[0])].add(row[0])
collisions={k:sorted(v) for k,v in by.items() if len(v)>1}
checks['66_groups_70_pairs_unchanged']=len(collisions)==66 and sum(len(v)*(len(v)-1)//2 for v in collisions.values())==70
makers={r[0]:r[1] for r in rows}
part=Counter('missing' if not makers[a] or not makers[b] else ('same' if makers[a]==makers[b] else 'different') for vals in collisions.values() for a,b in combinations(vals,2))
checks['maker_ambiguity_partition_63_6_1']=(part['different'],part['same'],part['missing'])==(63,6,1)
checks['R371_all_fields_remains_final_authority']='catalogueIsCompleteR384(window.BRES_CATALOG_V3)' in app and 'ocrCatalogueAllFieldsR371' in app
checks['catalogue_chunks_not_rewritten']=all(hashlib.sha256((A/'catalogue'/'v3'/name).read_bytes()).hexdigest()==meta['sha256'] for name,meta in stats.items())
report={'schema':'bres-cat-r387-fragment-digest-audit-v1','milestone':'CAT-R387','date':'2026-11-22','ok':all(checks.values()),'checks':checks,'chunks':stats,
        'summary':{'references':len(rows),'fields':12,'chunks':10,'missing_makers':sum(not row[1] for row in rows),'ocr_fold_groups':len(collisions),'ocr_fold_pairs':sum(len(v)*(len(v)-1)//2 for v in collisions.values()),'maker_pair_partition':dict(part),'equivalences_added':0,'makers_assigned':0},
        'elapsed_seconds':round(time.monotonic()-start,3),
        'limits':['Digest collision remains theoretically possible; this is not cryptographic authentication.',
                  'OCR fold collisions are not physical equivalence and require real key evidence.',
                  'No off-network Tesseract worker or Samsung camera validation performed.']}
(C/'CAT_R387_FRAGMENT_DIGEST_AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n','utf8')
(C/'CAT_R387_FRAGMENT_DIGEST_AUDIT.txt').write_text('CAT-R387 '+('PASS' if report['ok'] else 'FAIL')+f" {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if ok else 'FAIL ')+name for name,ok in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'summary':report['summary'],'failed':[k for k,v in checks.items() if not v]}))
if not report['ok']:sys.exit(1)
