#!/usr/bin/env python3
"""R390: test priority catalogue references in real offline Chromium, no photos."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64, csv, hashlib, json, os, sys
A=Path(__file__).resolve().parent
Q=A.parent/'cat'/'CAT_R389_EXACT_REVIEW_QUEUE.csv'
with Q.open(encoding='utf-8-sig') as f: pairs=[(r['ref_a'],r['ref_b']) for r in csv.DictReader(f)]
refs=sorted({a for pair in pairs for a in pair})
chunks={f'catalog-{i:02}.js':'data:text/javascript;base64,'+base64.b64encode((A/'catalogue'/'v3'/f'catalog-{i:02}.js').read_bytes()).decode() for i in range(1,11)}
checks={};errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    ctx=browser.new_context(offline=True,service_workers='block');ctx.route('**/*',lambda r:r.abort())
    page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((A/'index.html').read_text(),wait_until='domcontentloaded')
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text())
    page.evaluate('''chunks=>{const append=document.head.appendChild.bind(document.head);document.head.appendChild=function(s){const m=String(s.src||'').match(/catalog-(\\d\\d)\\.js/);if(m)s.src=chunks[m[0]];return append(s);};}''',chunks)
    out=page.evaluate('''async refs=>{
      const db=await ensureBresCatalogueR208();const complete=ocrCatalogueAllFieldsR371().ok;
      const inp=document.getElementById('manualRef'),btn=document.getElementById('manualRefBtn'),final=document.getElementById('finalDecision');
      const positive=/VALIDÉ\\s*:|RÉFÉRENCE MANUELLE CONFIRMÉE|QA2 VALIDÉ/;
      let found=0,rejected=0,bad=[],prefill=0,ambiguous=0;
      for(const ref of refs){
        inp.value=ref;btn.click();const t=final.textContent;
        if(positive.test(t))bad.push({ref,decision:t});
        if(t.includes('RÉFÉRENCE NON VALIDÉE'))rejected++;else if(t.includes('RÉFÉRENCE TROUVÉE')||t.includes('RÉFÉRENCE MANUELLE TROUVÉE'))found++;else bad.push({ref,decision:t});
        const info=interpretOCR(ref);if(info.best)prefill++;if(info.referenceAmbiguity)ambiguous++;
      }
      db[0][3]+=0.125;
      const corrupt=refs.map(ref=>interpretOCR(ref));const blocked=corrupt.every(x=>!x.best&&x.ocrCatalogueReadyR368===false);
      const restored=await ensureBresCatalogueR208();
      return {complete,rows:restored.length,recovered:ocrCatalogueAllFieldsR371().ok,found,rejected,bad,prefill,ambiguous,blocked,ocrAvailable:typeof globalThis.Tesseract?.createWorker==='function'};
    }''',refs)
    browser.close()
checks.update(priority_coverage=len(pairs)==170 and len(refs)==247,full_catalogue=out['complete'] and out['rows']==5103,manual_without_geometry_no_validation=not out['bad'] and out['found']+out['rejected']==len(refs),corrupted_catalogue_blocks_all_text_guesses=out['blocked'],canonical_recovery=out['recovered'],no_uncaught_error=not errors,no_real_ocr_claim=not out['ocrAvailable'])
report=dict(milestone='R390',ok=all(checks.values()),checks=checks,evidence=out,errors=errors,refs=len(refs),pair_count=len(pairs),fixture_sha256=hashlib.sha256(Q.read_bytes()).hexdigest(),limit='Text simulation only; no physical key, no Samsung, no Tesseract recognition. Requires sibling CAT-R389 queue.')
(A/'R390_PRIORITY_MANUAL_CHROMIUM.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,ensure_ascii=False));sys.exit(not report['ok'])
