#!/usr/bin/env python3
"""R385: real Chromium tests of never-settling catalogue script requests and recovery.
Only scripted transport is simulated. Canonical JS executes in real browser;
no Tesseract/Samsung/physical recognition claim.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os,sys,time,hashlib
A=Path(__file__).resolve().parent
CHUNKS={f'catalog-{i:02}.js':(A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_text('utf8') for i in range(1,11)}
checks={};evidence={};errors=[];started=time.monotonic()

def run(browser,mode):
  c=browser.new_context(offline=True,service_workers='block')
  c.route('**/*',lambda route:route.abort('blockedbyclient'))
  p=c.new_page();p.on('pageerror',lambda e:errors.append(f'{mode}: {e}'))
  p.set_content((A/'index.html').read_text('utf8'),wait_until='domcontentloaded',timeout=60000)
  p.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
  p.expose_function('__getChunkR385',lambda name:CHUNKS[name])
  p.evaluate(r'''(mode)=>{
    window.__r385Requests={};window.__r385Hung=[];
    const nativeAppend=document.head.appendChild.bind(document.head);
    document.head.appendChild=function(s){
      const m=String(s?.src||'').match(/(?:^|\/)catalogue\/v3\/(catalog-\d\d\.js)(?:[?#]|$)/);
      if(!m)return nativeAppend(s);
      const name=m[1],n=(window.__r385Requests[name]=(window.__r385Requests[name]||0)+1);
      // DOM must have contained this tag before a failed timeout removes it.
      s.type='application/x-bres-test-payload'; // inert DOM script, no real fetch
      nativeAppend(s);
      const hung=(mode==='hang-first'&&name==='catalog-01.js'&&n===1) ||
                 (mode==='hang-fourth'&&name==='catalog-04.js'&&n===1);
      if(hung){window.__r385Hung.push(s);return s;}
      Promise.resolve().then(async()=>{
        const js=await window.__getChunkR385(name);
        if(!s.isConnected)return; // Browser cancellation after script removal
        (0,eval)(js);
        s.onload?.(new Event('load'));
      }).catch(()=>s.onerror?.(new Event('error')));
      return s;
    };
  }''',mode)
  try:
    start=time.monotonic()
    first=p.evaluate('''async()=>{try{await window.ensureBresCatalogueR208();return 'resolved'}catch(e){return e.message}}''')
    seconds=time.monotonic()-start
    state=p.evaluate('''()=>({len:window.BRES_CATALOG_V3?.length||0,verified:ocrCatalogueAllFieldsR371().ok,
        hanging:window.__r385Hung.map(s=>({connected:s.isConnected,onload:s.onload===null,onerror:s.onerror===null})),
        scriptCount:document.querySelectorAll('script[src*="catalogue/v3/catalog-"]').length,
        requests:window.__r385Requests})''')
    checks[f'{mode}_bounded_timeout'] = first.startswith('Délai de chargement dépassé') and 3.7<=seconds<=7.0
    checks[f'{mode}_partial_catalogue_discarded'] = state['len']==0 and state['verified'] is False
    checks[f'{mode}_timed_out_script_detached'] = len(state['hanging'])==1 and all(not x['connected'] and x['onload'] and x['onerror'] for x in state['hanging'])
    # The stale events cannot resolve/reject a future attempt.
    p.evaluate('''()=>{for(const node of window.__r385Hung){node.onload?.(new Event('load'));node.onerror?.(new Event('error'))}}''')
    got=p.evaluate('''async()=>{const [a,b]=await Promise.all([window.ensureBresCatalogueR208(),window.ensureBresCatalogueR208()]);return {same:a===b,len:a.length}}''')
    after=p.evaluate('''()=>({verified:ocrCatalogueAllFieldsR371().ok,
        rows:window.BRES_CATALOG_V3.length,distinct:new Set(window.BRES_CATALOG_V3.map(x=>x[0])).size,
        scriptCount:document.querySelectorAll('script[src*="catalogue/v3/catalog-"]').length,
        requests:window.__r385Requests})''')
    checks[f'{mode}_retry_5103_and_singleflight'] = got['same'] and got['len']==5103 and after['rows']==after['distinct']==5103 and after['verified']
    expected=11 if mode=='hang-first' else 14
    checks[f'{mode}_only_expected_script_requests']=sum(after['requests'].values())==expected
    checks[f'{mode}_no_stale_script_tags']=after['scriptCount']==0 and state['scriptCount']==0
    again=p.evaluate('''async()=>{const a=window.BRES_CATALOG_V3,b=await window.ensureBresCatalogueR208();return a===b}''')
    checks[f'{mode}_valid_cached_inventory_no_reload']=again and sum(p.evaluate('window.__r385Requests').values())==expected
    evidence[mode]={'first_error':first,'elapsed_seconds':round(seconds,2),'after_timeout':state,'after_retry':after}
  finally:c.close()

with sync_playwright() as s:
  b=s.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
  try:
    run(b,'hang-first');run(b,'hang-fourth')
  finally:b.close()
checks['no_uncaught_chromium_exceptions']=not errors
checks['source_canonical_chunks_unchanged']=len(CHUNKS)==10 and all('window.BRES_CATALOG_V3.push' in raw for raw in CHUNKS.values())
report={'schema':'bres-r385-stalled-chunk-retry-chromium-v1','date':'2026-11-20','milestone':'R385','ok':all(checks.values()),'checks':checks,'evidence':evidence,'errors':errors,
        'r384_js_sha256':hashlib.sha256((A/'v228-catalogue_R384.js').read_bytes()).hexdigest(),
        'r385_js_sha256':hashlib.sha256((A/'v228-catalogue.js').read_bytes()).hexdigest(),
        'elapsed_seconds':round(time.monotonic()-started,2),
        'limits':['Chromium offline with simulated stalled script events, actual canonical JS evaluated in browser',
                  'No cold-offline Tesseract proof or physical Samsung photo test',
                  'Removing a stalled script cancels normal browser fetch; externally injected late code remains out of scope']}
(A/'R385_CHUNK_TIMEOUT_CHROMIUM.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(A/'R385_CHUNK_TIMEOUT_CHROMIUM.txt').write_text(f"R385 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'seconds':report['elapsed_seconds'],'failed':[k for k,v in checks.items() if not v],'errors':errors[:3]},ensure_ascii=False))
if not report['ok']:sys.exit(1)
