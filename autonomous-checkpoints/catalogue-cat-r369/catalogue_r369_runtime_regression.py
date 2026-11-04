#!/usr/bin/env python3
"""CAT-R369: 732 text-only endpoints from 393 known theoretical review edges.
Compare real offline Chromium parser decisions R368 vs test R369; no physical OCR.
"""
import hashlib,json,os,zipfile,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;A=C.parent/'app'
ledger=json.loads((C/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text())
texts=sorted({str(x[k]) for x in ledger['pairs'] for k in ('reference_a','reference_b')})
assert len(texts)==732 and len(ledger['pairs'])==393
with zipfile.ZipFile('/mnt/data/bres_r368_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R368.zip') as z:old=z.read('app/index.html').decode('utf8')
new=(A/'index.html').read_text(encoding='utf8');errors=[]
def parse(browser,html):
 ctx=browser.new_context(offline=True,service_workers='block');ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
 pg=ctx.new_page();pg.on('pageerror',lambda e:errors.append(str(e)))
 pg.set_content(html,wait_until='domcontentloaded')
 pg.add_script_tag(content=(A/'v228-catalogue.js').read_text(encoding='utf8'))
 for n in range(1,11):pg.add_script_tag(content=(A/f'catalogue/v3/catalog-{n:02}.js').read_text(encoding='utf8'))
 out=pg.evaluate('''ss=>ss.map(t=>{let v=interpretOCRViews([t,t]);return {raw:t,ref:v.best?.canon||null,
 eligible:!!(v.best&&v.best.sim>=OCR_PREFILL_THRESHOLD),ambiguous:!!v.referenceAmbiguity,
 compact:(v.compactAmbiguities||[]).length,fold:(v.ocrFoldAmbiguitiesR367||[]).length,
 ready:v.ocrCatalogueReadyR368};})''',texts)
 ctx.close();return out
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 try:baseline=parse(b,old);updated=parse(b,new)
 finally:b.close()
changed=[{'ref':a['raw'],'before':a,'after':b} for a,b in zip(baseline,updated) if a!=b]
checks={'all_732_endpoints_compared':len(baseline)==len(updated)==732,
 'all_393_theoretical_edges_loaded':len(ledger['pairs'])==393,
 'no_R368_to_R369_changes':not changed,
 'all_complete_catalogue_ready':all(x['ready'] is True for x in updated),
 'no_js_errors':not errors,
 'not_physical_OCR_or_manufacturer_proof':True}
report={'schema':'bres-cat-r369-js-text-regression-v1','date':'2026-11-04','milestone':'CAT-R369',
 'ok':all(checks.values()),'checks':checks,'distinct_endpoints':len(texts),'pairs':len(ledger['pairs']),
 'changed_decisions':len(changed),'changed_examples':changed[:12],'js_errors':errors,
 'parent_r368_html_sha256':hashlib.sha256(old.encode()).hexdigest(),
 'new_r369_html_sha256':hashlib.sha256(new.encode()).hexdigest(),
 'actual_ocr_executed':False,'physical_validation':False,'catalogue_modified':False}
(C/'CAT_R369_RUNTIME_REGRESSION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
(C/'CAT_R369_RUNTIME_REGRESSION.txt').write_text(f"CAT-R369 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}; 732 textual endpoints, {len(changed)} changes in R368->R369, no physical OCR.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
print(json.dumps({'ok':report['ok'],'checks':len(checks),'changed':len(changed),'errors':errors[:2]},ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
