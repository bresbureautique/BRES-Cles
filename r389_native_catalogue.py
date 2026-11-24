#!/usr/bin/env python3
"""R389: browser-native script evaluation and load events with offline data URLs."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os, sys, base64
A=Path(__file__).resolve().parent
chunks={f'catalog-{i:02}.js':'data:text/javascript;base64,'+base64.b64encode((A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_bytes()).decode() for i in range(1,11)}
checks={}; evidence={'file_and_http_navigation':'ERR_BLOCKED_BY_ADMINISTRATOR; not certified'}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    ctx=browser.new_context(offline=True,service_workers='block');ctx.route('**/*',lambda r:r.abort())
    page=ctx.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    page.set_content((A/'index.html').read_text(),wait_until='domcontentloaded')
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text())
    page.evaluate('''(chunks)=>{window.nativeCalls=[];const append=document.head.appendChild.bind(document.head);document.head.appendChild=function(s){const m=String(s.src||'').match(/catalog-(\\d\\d)\\.js/);if(m){nativeCalls.push(m[0]);s.src=chunks[m[0]];}return append(s);};}''',chunks)
    out=page.evaluate('''async()=>{const all=await Promise.all(Array.from({length:3},()=>ensureBresCatalogueR208()));const db=all[0];const clean={rows:db.length,unique:new Set(db.map(r=>r[0])).size,verified:ocrCatalogueAllFieldsR371().ok,shared:all.every(x=>x===db),calls:nativeCalls.length};db[100][3]+=0.125;const detected=!ocrCatalogueAllFieldsR371().ok;const fixed=await ensureBresCatalogueR208();return {clean,detected,repaired:fixed!==db&&ocrCatalogueAllFieldsR371().ok,calls:nativeCalls.length,ocrLoaded:typeof globalThis.Tesseract?.createWorker==='function'};}''')
    checks['canonical']=out['clean']==dict(rows=5103,unique=5103,verified=True,shared=True,calls=10)
    checks['recovery']=out['detected'] and out['repaired'] and out['calls']==20
    checks['no_uncaught_error']=not errors
    checks['no_false_ocr_available']=not out['ocrLoaded']
    evidence['native_data_script']=dict(result=out,errors=errors)
    browser.close()
report=dict(milestone='R389',checks=checks,evidence=evidence,ok=all(checks.values()),limit='Desktop Chromium, data URLs, no external network. Not file/HTTP or Samsung certification.')
(A/'R389_NATIVE_CATALOGUE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));sys.exit(not report['ok'])
