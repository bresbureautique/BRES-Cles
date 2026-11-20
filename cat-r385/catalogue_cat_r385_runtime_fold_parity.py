#!/usr/bin/env python3
"""CAT-R385: independently reconstruct glyph-collision groups, compare to app's
runtime detector in offline Chromium, and check fail-closed without inventory.
READ-ONLY: no new makers, equivalences or physical compatibility claims.
"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
from playwright.sync_api import sync_playwright
import json,hashlib,re,os,sys,time
C=Path(__file__).resolve().parent;A=C.parent/'app';beg=time.monotonic()
prior=json.loads((C/'CAT_R384_FRAGMENT_RETRY_AUDIT.json').read_text('utf8'))
rows=[];chunk_sha={};checks={}
for i in range(1,11):
  name=f'catalog-{i:02}.js';src=(A/'catalogue'/'v3'/name).read_bytes();chunk_sha[name]=hashlib.sha256(src).hexdigest()
  m=re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',src.strip(),re.S)
  assert m,name
  rows.extend(json.loads(m.group(1)))
  checks[f'{name}_unaltered_sha256']=chunk_sha[name]==prior['canonical_sha256'][name]
checks['5103_records_12_fields']=len(rows)==5103 and len({r[0] for r in rows})==5103 and all(len(r)==12 for r in rows)
checks['164_makers_unfilled']=sum(not r[1] for r in rows)==164
fold_map=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def fold(v):return re.sub('[^A-Z0-9]','',v.upper().strip()).translate(fold_map)
by_fold=defaultdict(set)
for r in rows:by_fold[fold(r[0])].add(r[0])
collisions={k:sorted(v) for k,v in by_fold.items() if len(v)>1}
checks['66_groups_70_pairs']=len(collisions)==66 and sum(len(a)*(len(a)-1)//2 for a in collisions.values())==70
pairs=[(k,a,b) for k,v in collisions.items() for a,b in combinations(v,2)]
makers={r[0]:r[1] for r in rows}
counts=Counter('missing_maker' if not makers[a] or not makers[b] else ('same_maker' if makers[a]==makers[b] else 'different_maker') for _,a,b in pairs)
checks['maker_partition_63_6_1']=(counts['different_maker'],counts['same_maker'],counts['missing_maker'])==(63,6,1)
js_results={};errors=[]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
  try:
    context=browser.new_context(offline=True,service_workers='block');context.route('**/*',lambda route:route.abort('blockedbyclient'))
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((A/'index.html').read_text('utf8'),wait_until='domcontentloaded',timeout=60000)
    for i in range(1,11):page.add_script_tag(content=(A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_text('utf8'))
    allrefs=[r[0] for r in rows]
    js_results=page.evaluate('''(refs)=>{
      const integrity=ocrCatalogueAllFieldsR371();
      const res=ocrLossyGlyphGroupsR367(refs,true);
      const disabled=ocrLossyGlyphGroupsR367(refs,false);
      const empty=ocrLossyGlyphGroupsR367([],true);
      const uniqueNames=new Set(res.map(x=>x.foldedText));
      const valueOut=res.map(g=>({fold:g.foldedText,refs:g.canons,policy:g.policy}));
      // Operate on a temporary in-memory copy; restore exact original without
      // changing the canonical file on disk.
      const original=window.BRES_CATALOG_V3[0][1];
      window.BRES_CATALOG_V3[0][1]='BROKEN_CANONICAL_MAKER';
      const mutationRejected=ocrCatalogueAllFieldsR371().ok===false;
      window.BRES_CATALOG_V3[0][1]=original;
      return {integrity,groups:valueOut,disabled_count:disabled.length,empty_count:empty.length,
         unique_count:uniqueNames.size,mutationRejected,restored:ocrCatalogueAllFieldsR371().ok};
    }''',allrefs)
    context.close()
  finally:browser.close()
actual={g['fold']:sorted(g['refs']) for g in js_results['groups']}
checks['runtime_reports_all_expected_groups']=actual==collisions
checks['runtime_all_groups_require_review']=all(g['policy']=='manual-review-required' for g in js_results['groups'])
checks['no_runtime_extra_duplicates']=js_results['unique_count']==66 and len(js_results['groups'])==66
checks['runtime_false_inventory_abstains']=js_results['disabled_count']==0
checks['runtime_empty_input_abstains']=js_results['empty_count']==0
checks['full_12_field_inventory_integrity']=js_results['integrity']=={'ok':True,'reason':'expected-all-12-fields'}
checks['maker_mutation_detected_and_restored']=js_results['mutationRejected'] and js_results['restored']
checks['no_browser_errors']=not errors
summary={'collision_groups':len(collisions),'collision_pairs':len(pairs),'maker_partition':dict(counts),'runtime_reported_groups':len(js_results['groups']),
         'missing_or_extra':sorted(set(actual)^set(collisions)),
         'canonical_digests':chunk_sha,'physical_equivalence_created':0,'maker_assigned':0}
report={'schema':'bres-cat-r385-runtime-ocr-fold-parity-v1','date':'2026-11-20','milestone':'CAT-R385','ok':all(checks.values()),'checks':checks,'summary':summary,'errors':errors,
        'elapsed_seconds':round(time.monotonic()-beg,2),
        'limitations':['OCR glyph fold is a synthetic ambiguity screen, not physical key equivalence',
                       'No Samsung photograph or Tesseract offline worker tested',
                       'The comparison assumes the app receives a correctly verified canonical catalogue']}
(C/'CAT_R385_RUNTIME_FOLD_PARITY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(C/'CAT_R385_RUNTIME_FOLD_PARITY.txt').write_text(f"CAT-R385 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'group_count':len(collisions),'pairs':len(pairs),'failed':[k for k,v in checks.items() if not v],'seconds':report['elapsed_seconds']},ensure_ascii=False))
if not report['ok']:sys.exit(1)
