#!/usr/bin/env python3
"""Offline Chromium: malformed/silent success fragments reject early; clean retry recovers."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import hashlib,json,os,sys,time
A=Path(__file__).resolve().parent
CHUNKS={f'catalog-{i:02}.js':(A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_text('utf8') for i in range(1,11)}
checks={};proofs={};errors=[];t=time.monotonic()
CASES=[
 ('missing-1',1,'drop-last'),('duplicate-1',1,'duplicate'),
 ('swapped-1',1,'swap-next'),('wrong-first-1',1,'wrong-first'),
 ('missing-4',4,'drop-last'),('duplicate-4',4,'duplicate'),
 ('swapped-4',4,'swap-next'),('wrong-last-4',4,'wrong-last'),
 ('invalid-column-10',10,'invalid-column'),('replaced-array-1',1,'replaced-array'),
 ('internal-mutate-1',1,'internal-mutate')
]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 try:
  for case,target,mutation in CASES:
   c=b.new_context(offline=True,service_workers='block'); c.route('**/*',lambda route:route.abort('blockedbyclient'))
   page=c.new_page();page.on('pageerror',lambda e:errors.append(f'{case}:{e}'))
   page.set_content((A/'index.html').read_text('utf8'),wait_until='domcontentloaded',timeout=60000)
   page.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
   page.expose_function('__r386Source',lambda name:CHUNKS[name])
   page.evaluate(r'''({target,mutation})=>{
     window.__r386Counts={}; window.__r386FirstFailure=null;
     const append=document.head.appendChild.bind(document.head);
     document.head.appendChild=function(s){
       const m=String(s?.src||'').match(/(?:^|\/)catalogue\/v3\/(catalog-\d\d\.js)(?:[?#]|$)/);
       if(!m)return append(s);
       const name=m[1],part=Number(name.slice(8,10));
       const n=(window.__r386Counts[name]=(window.__r386Counts[name]||0)+1);
       s.type='application/x-bres-test-payload'; append(s);
       Promise.resolve().then(async()=>{
         const code=await window.__r386Source(name);
         if(!s.isConnected)return;
         const start=window.BRES_CATALOG_V3?.length||0;
         (0,eval)(code);
         if(part===target&&n===1){
           const db=window.BRES_CATALOG_V3;
           if(mutation==='drop-last')db.pop();
           if(mutation==='duplicate')(0,eval)(code);
           if(mutation==='swap-next'){
             db.splice(start);(0,eval)(window.__r386OtherCode);
           }
           if(mutation==='wrong-first')db[start][0]='INVALID_R387_R386_REF';
           if(mutation==='wrong-last')db[db.length-1][0]='INVALID_R387_R386_END';
           if(mutation==='invalid-column')db[db.length-1].pop();
           if(mutation==='replaced-array')window.BRES_CATALOG_V3=db.slice();
           if(mutation==='internal-mutate')db[start+1][1]='CORRUPTED_INNER_MAKER';
         }
         s.onload?.(new Event('load'));
       }).catch(err=>{window.__r386FirstFailure=String(err);s.onerror?.(new Event('error'));});
       return s;
     };
   }''',{'target':target,'mutation':mutation})
   if mutation=='swap-next':
    alt=f'catalog-{(target+1):02}.js'
    page.evaluate('(src)=>{window.__r386OtherCode=src}',CHUNKS[alt])
   first=page.evaluate('''async()=>{try{await window.ensureBresCatalogueR208();return 'resolved'}catch(e){return String(e.message||e)}}''')
   mid=page.evaluate('''()=>({n:window.BRES_CATALOG_V3?.length||0,verified:ocrCatalogueAllFieldsR371().ok,
       requestCount:Object.values(window.__r386Counts).reduce((a,b)=>a+b,0),tagCount:document.querySelectorAll('script[src*="catalogue/v3/catalog-"]').length})''')
   expected_fail=('Fragment catalogue altéré' if mutation=='internal-mutate' else 'Fragment catalogue non conforme')
   checks[case+'_fails_closed'] = first.startswith(expected_fail) and mid['n']==0 and not mid['verified'] and mid['tagCount']==0
   checks[case+'_fast_detection'] = (mid['requestCount']==target)
   second=page.evaluate('''async()=>{const [a,b]=await Promise.all([window.ensureBresCatalogueR208(),window.ensureBresCatalogueR208()]);return {same:a===b,len:a.length,verified:ocrCatalogueAllFieldsR371().ok,distinct:new Set(a.map(x=>x[0])).size}}''')
   checks[case+'_clean_retry'] = second=={'same':True,'len':5103,'verified':True,'distinct':5103}
   checks[case+'_no_remaining_scripts'] = page.evaluate('''()=>document.querySelectorAll('script[src*="catalogue/v3/catalog-"]').length===0''')
   proofs[case]={'first_error':first,'partial':mid,'retry':second}
   c.close()
 finally:b.close()
checks['no_browser_exceptions']=not errors
checks['canonical_10_fragments_present']=len(CHUNKS)==10
report={'schema':'bres-r387-r386-semantic-regression-v1','date':'2026-11-22','milestone':'R387-R386','ok':all(checks.values()),'checks':checks,'proofs':proofs,'errors':errors,'elapsed_seconds':round(time.monotonic()-t,2),
 'limits':['Chromium offline, canonical JS evaluated with synthetic script event mutations',
           'Boundary/count checks are not a cryptographic per-fragment proof: R371 validates full inventory',
           'No real key recognition or Tesseract offline certification']}
(A/'R387_R386_FRAGMENT_INTEGRITY_CHROMIUM.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(A/'R387_R386_FRAGMENT_INTEGRITY_CHROMIUM.txt').write_text(f"R386 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'checks':len(checks),'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v],'seconds':report['elapsed_seconds'],'errors':errors[:2]},ensure_ascii=False))
if not report['ok']:sys.exit(1)
