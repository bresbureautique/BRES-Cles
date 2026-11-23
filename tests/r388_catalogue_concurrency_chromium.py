#!/usr/bin/env python3
"""BRES Clés R388: 10 injected transient loader faults, concurrent safe retry, cache invalidation.
Offline synthetic Chromium only. Never modifies canonical chunks or stable V2.27.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,time,hashlib,os,sys
A=Path(__file__).resolve().parent
CHUNKS={f'catalog-{i:02}.js':(A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_text('utf8') for i in range(1,11)}
checks={};proofs={};errors=[];beg=time.monotonic()
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True, executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 try:
  for fail_at in range(1,11):
   case=f'chunk-{fail_at:02d}'
   ctx=browser.new_context(offline=True,service_workers='block')
   ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
   page=ctx.new_page();page.on('pageerror',lambda error:errors.append(f'{case}: {error}'))
   page.set_content((A/'index.html').read_text('utf8'),wait_until='domcontentloaded',timeout=60000)
   page.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
   page.expose_function('__r388GetChunk',lambda name:CHUNKS[name])
   page.evaluate('''(target)=>{
     window.__r388Calls=[];window.__r388Failures=0;
     const original=document.head.appendChild.bind(document.head);
     document.head.appendChild=function(s){
       const match=String(s?.src||'').match(/(?:^|\\/)catalogue\\/v3\\/(catalog-\\d\\d\\.js)(?:[?#]|$)/);
       if(!match)return original(s);
       const name=match[1],part=Number(name.slice(8,10));
       window.__r388Calls.push(name);
       s.type='application/x-r388-injected-canonical';original(s);
       Promise.resolve().then(async()=>{
         if(!s.isConnected)return;
         // Exactly one transient failure at the chosen position.
         if(part===target && window.__r388Failures++===0){s.onerror?.(new Event('error'));return;}
         const source=await window.__r388GetChunk(name);
         if(!s.isConnected)return;
         (0,eval)(source);
         s.onload?.(new Event('load'));
       }).catch(e=>s.onerror?.(new Event('error')));
       return s;
     };
   }''',fail_at)
   # First request must fail cleanly. All three concurrent retries share one promise.
   out=page.evaluate('''async()=>{
     const first=await window.ensureBresCatalogueR208().then(()=>({ok:true}),e=>({ok:false,error:String(e.message||e)}));
     const cleared={size:window.BRES_CATALOG_V3.length,tags:document.querySelectorAll('script[src*="catalogue/v3/catalog-"]').length,verified:ocrCatalogueAllFieldsR371().ok};
     const beforeCalls=window.__r388Calls.length;
     const all=await Promise.all(Array.from({length:3},()=>window.ensureBresCatalogueR208()));
     const clean={same:all.every(x=>x===all[0]),rows:all[0].length,unique:new Set(all[0].map(r=>r[0])).size,verified:ocrCatalogueAllFieldsR371().ok,calls:window.__r388Calls.length-beforeCalls};
     // Deliberately corrupt an already cached interior field. The next load must
     // reject the polluted cache and rebuild it from intact canonical chunks.
     const old=window.BRES_CATALOG_V3;
     old[1][3]+=0.125;
     const detects=!ocrCatalogueAllFieldsR371().ok;
     const beforeRestore=window.__r388Calls.length;
     const newRows=await window.ensureBresCatalogueR208();
     const restored={detects,newArray:old!==newRows,rows:newRows.length,unique:new Set(newRows.map(r=>r[0])).size,verified:ocrCatalogueAllFieldsR371().ok,calls:window.__r388Calls.length-beforeRestore};
     return {first,cleared,clean,restored,allCalls:window.__r388Calls};
   }''')
   checks[f'{case}_first_fault_detected']=(not out['first']['ok'] and 'Chargement impossible' in out['first']['error'])
   checks[f'{case}_failed_load_purged']=(out['cleared']=={'size':0,'tags':0,'verified':False})
   checks[f'{case}_three_concurrent_retries']=(out['clean']=={'same':True,'rows':5103,'unique':5103,'verified':True,'calls':10})
   checks[f'{case}_mutated_cache_rebuilt']=(out['restored']=={'detects':True,'newArray':True,'rows':5103,'unique':5103,'verified':True,'calls':10})
   proofs[case]={k:v for k,v in out.items() if k!='allCalls'}
   ctx.close()
 finally:browser.close()
checks['no_uncaught_browser_exceptions']=not errors
checks['canonical_chunk_count_is_ten']=len(CHUNKS)==10
report={'schema':'bres-r388-catalogue-concurrency-chromium-v1','date':'2026-11-23','version':'V2.28 TEST R388 (R387 runtime, expanded regressions)',
        'ok':all(checks.values()),'checks':checks,'proofs':proofs,'errors':errors,'elapsed_seconds':round(time.monotonic()-beg,2),
        'runtime_sha256':hashlib.sha256((A/'v228-catalogue.js').read_bytes()).hexdigest(),
        'limits':['Synthetic fault injection in offline Chromium; no claim of physical Samsung identification or offline Tesseract OCR.',
                  'V2.27 is left untouched. Canonical chunks never modified.']}
(A/'R388_CATALOGUE_CONCURRENCY_CHROMIUM.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n','utf8')
(A/'R388_CATALOGUE_CONCURRENCY_CHROMIUM.txt').write_text(f"R388 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v], 'seconds':report['elapsed_seconds'], 'errors':errors[:3]}))
sys.exit(0 if report['ok'] else 1)
