#!/usr/bin/env python3
"""R368 real Chromium JS, no network, no Tesseract, no physical key.

Proves incomplete catalogue must never automatically select any text OCR guess.
R367 baseline full-catalogue decisions stay identical for audited samples.
"""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent; C=A.parent/'cat'
parent_zip=Path('/mnt/data/bres_r367_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R367.zip')
with zipfile.ZipFile(parent_zip) as z: old=z.read('app/index.html').decode('utf-8')
new=(A/'index.html').read_text(encoding='utf-8')
fixtures=json.loads((C/'CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES.json').read_text())['fixtures']
collision=sorted({x for f in fixtures for x in f['source_candidates_DISTINCT_UNVERIFIED']})
import sys
sys.path.insert(0,str(C))
from catalogue_audit_cat_r349 import load_records
rows, hashes, _=load_records(A)
controls=sorted(set(str(x[0]) for x in rows)-set(collision),key=lambda s:(hashlib.sha256(s.encode()).hexdigest(),s))[:250]
refs=collision+controls+['TE8D','TE8I','TE8B','BK34','KF1','UNLISTED_999']
assert len(fixtures)==64 and len(collision)==130 and len(controls)==250 and len(rows)==5103
errors=[];requests=[]

def load_app(browser,html):
    context=browser.new_context(offline=True,service_workers='block')
    context.route('**/*',lambda r:r.abort('blockedbyclient'))
    page=context.new_page()
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.set_content(html,wait_until='domcontentloaded',timeout=45000)
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text(encoding='utf-8'))
    return context,page

def add_chunks(page,a,b):
    for i in range(a,b+1):page.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text(encoding='utf-8'))

def sample(page,ss):
    return page.evaluate('''ss=>ss.map(raw=>{const one=interpretOCR(raw),pair=interpretOCRViews([raw,raw]);return {raw,
        one:one.best?.canon||null,pair:pair.best?.canon||null,
        eligible:!!(pair.best&&pair.best.sim>=OCR_PREFILL_THRESHOLD),
        incomplete:pair.ocrCatalogueReadyR368===false,
        groups:pair.ocrFoldAmbiguitiesR367?.length||0,
        ambiguous:!!pair.referenceAmbiguity,
        candidates:pair.candidates?.length||0,
        changed_geometry_absent:!!resolveCompactCatalogueAmbiguityR213(pair,null,null).best
    }});''',ss)

checks={};stages={};other={}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        ctx,page=load_app(browser,new)
        stages['zero']=sample(page,['TE8D','TE8I','KF1','BK34'])
        add_chunks(page,1,1)
        stages['one']=sample(page,['TE8D','TE8I','KF1','BK34'])
        add_chunks(page,2,5)
        stages['five']=sample(page,['TE8D','TE8I','KF1','BK34'])
        add_chunks(page,6,9)
        stages['nine']=sample(page,['TE8D','TE8I','KF1','BK34'])
        add_chunks(page,10,10)
        stages['ten']=sample(page,['TE8D','TE8I','KF1','BK34'])
        full_updated=sample(page,refs)
        folds_updated=sample(page,[f['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] for f in fixtures])
        manual=[]
        for ref in ('TE8D','TE8I'):
            page.locator('#manualRef').fill(ref);page.locator('#manualRefBtn').click()
            manual.append({'ref':ref,'decision':page.locator('#finalDecision').inner_text()[:200]})
        # Perturb completeness *after* a full index was cached, then restore.
        page.evaluate('window.__tempCatalogR368=window.BRES_CATALOG_V3.pop()')
        stages['temporarily_missing_one']=sample(page,['TE8D','KF1'])
        page.evaluate('window.BRES_CATALOG_V3.push(window.__tempCatalogR368);delete window.__tempCatalogR368')
        stages['restored']=sample(page,['TE8D','KF1'])
        page.close();ctx.close()
        ctx,page=load_app(browser,old);add_chunks(page,1,10)
        full_baseline=sample(page,refs)
        folds_baseline=sample(page,[f['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] for f in fixtures])
        page.close();ctx.close()
    finally:browser.close()

naked=lambda r:{k:v for k,v in r.items() if k!='incomplete'}
changed=[(x['raw'],naked(x),naked(y)) for x,y in zip(full_baseline,full_updated) if naked(x)!=naked(y)]
foldchanged=[(x['raw'],naked(x),naked(y)) for x,y in zip(folds_baseline,folds_updated) if naked(x)!=naked(y)]
checks={
    '0_chunks_no_auto_prefill':all(x['pair'] is None and x['incomplete'] for x in stages['zero']),
    '1_chunk_no_auto_prefill':all(x['pair'] is None and x['incomplete'] for x in stages['one']),
    '5_chunks_no_auto_prefill':all(x['pair'] is None and x['incomplete'] for x in stages['five']),
    '9_chunks_no_auto_prefill':all(x['pair'] is None and x['incomplete'] for x in stages['nine']),
    '10_chunks_detect_complete':all(not x['incomplete'] for x in stages['ten']),
    'full_catalogue_pilot_TE8D_TE8I_preserved':all(any(x['raw']==r and x['pair']==r and not x['incomplete'] for x in stages['ten']) for r in ('TE8D','TE8I')),
    'full_130_collision_250_control_plus_smoke_decisions_unchanged':not changed and len(full_updated)==386,
    'full_64_fold_decisions_unchanged':not foldchanged and len(folds_updated)==64,
    'full_64_fold_no_automatic_prefill':all(x['pair'] is None for x in folds_updated),
    '130_collision_refs_remain_blocked':all(x['pair'] is None for x in full_updated[:130]),
    'after_cached_9_fragment_state_reblocked':all(x['pair'] is None and x['incomplete'] for x in stages['temporarily_missing_one']),
    'after_restore_full_behavior_restored':stages['restored'][0]['pair']=='TE8D' and all(not x['incomplete'] for x in stages['restored']),
    'manual_TE8D_TE8I_not_validated':all('RÉFÉRENCE TROUVÉE' in x['decision'] and 'VALIDÉ' not in x['decision'] for x in manual),
    'no_js_runtime_errors':not errors,
    'no_physical_OCR_claim':True,
    'canonical_data_unchanged_5103_10':len(rows)==5103 and len(hashes)==10,
}
result={'schema':'bres-r368-catalogue-readiness-chromium-v1','date':'2026-11-03','milestone':'R368',
 'ok':all(checks.values()),'checks':checks,'stages':stages,'complete_rows':5103,
 'changed_full_catalogue_decisions':changed[:10],'changed_full_fold_decisions':foldchanged[:10],
 'manual':manual,'errors':errors,'network_attempts_blocked':len(requests),
 'r367_baseline_sha256':hashlib.sha256(old.encode()).hexdigest(),
 'r368_html_sha256':hashlib.sha256(new.encode()).hexdigest(),'canonical_sha256':hashes,
 'limitations':['Real JavaScript parser, synthetic text only, no photograph or Tesseract','Catalogue length is a completeness precondition, NOT a cryptographic authentication','Manual entry remains possible; no physical equivalence claimed','Stable V2.27 unchanged']}
(A/'R368_CATALOGUE_READINESS_CHROMIUM.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(A/'R368_CATALOGUE_READINESS_CHROMIUM.txt').write_text(
 f"R368 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}: 0/1/5/9 chunks block auto OCR, 10 chunks preserve 386 + 64 full-catalogue decisions. No real OCR.\n"+
 '\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],
 'full_changes':len(changed),'fold_changes':len(foldchanged),'errors':errors[:2]},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)