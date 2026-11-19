#!/usr/bin/env python3
"""R384: real offline Chromium script-load failures, retries, integrity, concurrency.
No actual photo/Tesseract validation; does not touch the stable V2.27.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
import json,re,os,sys,hashlib,time
from playwright.sync_api import sync_playwright
A=Path(__file__).resolve().parent
CHUNKS={f'catalog-{i:02}.js':(A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_text('utf8') for i in range(1,11)}
checks={}; details={}; browser_errors=[]; start=time.monotonic()

def scenario(browser,label,mode):
    context=browser.new_context(offline=True,service_workers='block')
    context.route('**/*',lambda r:r.abort('blockedbyclient'))
    page=context.new_page()
    page.on('pageerror',lambda e:browser_errors.append(f'{label}: {e}'))
    page.set_content((A/'index.html').read_text('utf8'),wait_until='domcontentloaded',timeout=60000)
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
    page.expose_function('__bresChunkPayloadR384',lambda name: CHUNKS[name])
    page.evaluate(r'''(mode)=>{
      // Simulate the network transport, not the loaded JS code. Every canonical
      // catalogue chunk is executed by the actual Chromium JS engine.
      window.__chunkRequestsR384={};
      const nativeAppend=document.head.appendChild.bind(document.head);
      document.head.appendChild=function(node){
        const src=String(node&&node.src||'');
        const match=src.match(/(?:^|\/)catalogue\/v3\/(catalog-\d\d\.js)(?:[?#]|$)/);
        if(!match)return nativeAppend(node);
        const name=match[1],counts=window.__chunkRequestsR384;
        counts[name]=(counts[name]||0)+1;
        const attempt=counts[name];
        Promise.resolve().then(async()=>{
          if(mode==='network-fail'&&name==='catalog-04.js'&&attempt===1){node.onerror?.(new Event('error'));return;}
          if(mode==='short-payload'&&name==='catalog-09.js'&&attempt===1){node.onload?.(new Event('load'));return;}
          const js=await window.__bresChunkPayloadR384(name);
          (0,eval)(js);
          node.onload?.(new Event('load'));
        }).catch(()=>node.onerror?.(new Event('error')));
        return node;
      };
    }''',mode)
    def requests():
        return page.evaluate('window.__chunkRequestsR384')
    def state_js():
        return page.evaluate('''()=>({len:Array.isArray(window.BRES_CATALOG_V3)?window.BRES_CATALOG_V3.length:null,
         integrity:(typeof ocrCatalogueAllFieldsR371==='function')?ocrCatalogueAllFieldsR371().ok:false,
         unique:Array.isArray(window.BRES_CATALOG_V3)?new Set(window.BRES_CATALOG_V3.map(r=>r[0])).size:0,
         first:window.BRES_CATALOG_V3?.[0]?.[0]||null})''')
    try:
        if mode in ('network-fail','short-payload'):
            first=page.evaluate('''async()=>{try{await window.ensureBresCatalogueR208();return 'resolved'}catch(e){return String(e.message||e)}}''')
            zero=state_js()
            checks[label+'_first_load_failed']=first!='resolved' and (('Chargement impossible' in first) if mode=='network-fail' else ('inventaire R371' in first))
            checks[label+'_partial_rows_discarded']=zero['len']==0 and zero['unique']==0
            second=page.evaluate('''async()=>{try{const db=await window.ensureBresCatalogueR208();return db.length}catch(e){return String(e)}}''')
            after=state_js()
            checks[label+'_retry_complete_5103']=second==5103 and after['len']==5103 and after['integrity'] and after['unique']==5103
            expected_count=14 if mode=='network-fail' else 20
            checks[label+'_no_duplicate_unnecessary_chunk_loads']=sum(requests().values())==expected_count
            details[label]={'first_error':first,'first_state':zero,'second_state':after,'chunk_requests':requests()}
        elif mode=='two-call-single-flight':
            first=page.evaluate('''async()=>{const [a,b]=await Promise.all([window.ensureBresCatalogueR208(),window.ensureBresCatalogueR208()]);return {same:a===b,len:a.length}}''')
            after=state_js()
            checks[label+'_same_payload_for_concurrent_clients']=first['same'] and first['len']==5103
            checks[label+'_exactly_ten_chunk_loads']=sum(requests().values())==10 and len(requests())==10
            checks[label+'_integrity_true']=after['integrity'] and after['unique']==5103
            again=page.evaluate('''async()=>{const first=window.BRES_CATALOG_V3,second=await window.ensureBresCatalogueR208();return first===second}''')
            checks[label+'_cached_canonical_no_reload']=again and sum(requests().values())==10
            details[label]={'after':after,'loads':requests()}
        elif mode=='corrupted-loaded':
            page.evaluate('''async()=>{await window.ensureBresCatalogueR208()}''')
            page.evaluate('''()=>{window.BRES_CATALOG_V3[0][1]='ATTENTION-CORRUPTION'}''')
            corrupt=state_js()
            checks[label+'_mutation_detected']=corrupt['len']==5103 and not corrupt['integrity']
            page.evaluate('''async()=>{await window.ensureBresCatalogueR208()}''')
            after=state_js()
            checks[label+'_full_rebuild_recovers']=after['len']==5103 and after['integrity'] and after['unique']==5103
            checks[label+'_fresh_ten_chunks_loaded']=sum(requests().values())==20
            details[label]={'corrupt':corrupt,'recovered':after,'loads':requests()}
        elif mode=='no-api':
            page.evaluate('''()=>{window.ocrCatalogueAllFieldsR371=undefined}''')
            failure=page.evaluate('''async()=>{try{await window.ensureBresCatalogueR208();return 'resolved'}catch(e){return String(e.message||e)}}''')
            checks[label+'_fail_closed_without_integrity_api']='inventaire R371' in failure
            checks[label+'_partial_rows_cleared']=state_js()['len']==0
            details[label]={'failure':failure}
        else:raise ValueError(mode)
    finally:
        context.close()

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        for mode in ('network-fail','short-payload','two-call-single-flight','corrupted-loaded','no-api'):
            scenario(b,mode,mode)
    finally:b.close()
checks['all_browser_errors_avoided']=not browser_errors
checks['canonical_chunk_10_unchanged']=len(CHUNKS)==10 and all('window.BRES_CATALOG_V3.push' in x for x in CHUNKS.values())
report={'schema':'bres-r384-catalogue-retry-real-chromium-v1','date':'2026-11-19','milestone':'R384','ok':all(checks.values()),
        'checks':checks,'details':details,'browser_errors':browser_errors,'duration_seconds':round(time.monotonic()-start,2),
        'r383_js_sha256':hashlib.sha256((A/'v228-catalogue_R383.js').read_bytes()).hexdigest(),
        'r384_js_sha256':hashlib.sha256((A/'v228-catalogue.js').read_bytes()).hexdigest(),
        'limits':['Real Chromium / local fulfilled script requests; network exceptions simulated','Canonical catalogue content loaded from immutable R383 fragments','No cold-offline Tesseract or physical Samsung recognition tested']}
(A/'R384_CATALOGUE_RETRY_CHROMIUM.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(A/'R384_CATALOGUE_RETRY_CHROMIUM.txt').write_text(f"R384 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'checks':len(checks),'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v],'seconds':report['duration_seconds'],'errors':browser_errors[:3]},ensure_ascii=False))
if not report['ok']:sys.exit(1)
