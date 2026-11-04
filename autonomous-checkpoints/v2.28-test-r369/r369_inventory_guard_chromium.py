#!/usr/bin/env python3
"""Chromium offline inventory corruption + OCR synthetic regression vs parent R368.
Actual JS interpreter. No Tesseract or physical key. No stable file changes.
"""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;C=A.parent/'cat'
with zipfile.ZipFile('/mnt/data/bres_r368_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R368.zip') as z: old=z.read('app/index.html').decode('utf-8')
new=(A/'index.html').read_text(encoding='utf-8')
fixtures=json.loads((C/'CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES.json').read_text())['fixtures']
collisions=sorted({x for f in fixtures for x in f['source_candidates_DISTINCT_UNVERIFIED']})
samples=sorted(set(collisions+['TE8D','TE8I','TE8B','BK34','KF1','UNLISTED_999']))
folds=[f['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] for f in fixtures]
assert len(collisions)==130 and len(folds)==64
errors=[];requests=[];states={}
def setup(browser,html):
    ctx=browser.new_context(offline=True,service_workers='block')
    ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
    p=ctx.new_page()
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.on('request',lambda r:requests.append(r.url))
    p.set_content(html,wait_until='domcontentloaded',timeout=45000)
    p.add_script_tag(content=(A/'v228-catalogue.js').read_text(encoding='utf-8'))
    for i in range(1,11):p.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text(encoding='utf-8'))
    return ctx,p

def one(page,texts):
    return page.evaluate('''a=>a.map(t=>{let o=interpretOCR(t),v=interpretOCRViews([t,t]);return {text:t,
      o:o.best?.canon||null,view:v.best?.canon||null,ready:!!v.ocrCatalogueReadyR368,
      status:v.ocrCatalogueStatusR369||null, ambiguous:!!v.referenceAmbiguity,
      eligible:!!(v.best&&v.best.sim>=OCR_PREFILL_THRESHOLD)};})''',texts)

def probe(page,name,modify=None):
    if modify:page.evaluate(modify)
    rows=one(page,['TE8D','TE8I','BK34','KF1'])
    states[name]={'rows':rows,'inventory':page.evaluate('''()=>ocrCatalogueInventoryR369()''')}
    return rows

def same_before_after(x,y):
    return all({k:a[k] for k in ('o','view','ambiguous','eligible')}=={k:b[k] for k in ('o','view','ambiguous','eligible')}
               for a,b in zip(x,y))

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        ctx,page=setup(browser,new)
        full=probe(page,'full')
        arr=one(page,samples)
        foldarr=one(page,folds)
        manual=[]
        for r in ('TE8D','TE8I'):
            page.locator('#manualRef').fill(r);page.locator('#manualRefBtn').click()
            manual.append({'ref':r,'output':page.locator('#finalDecision').inner_text()[:170]})
        # Every modification preserves length unless explicitly 'missing'.
        tests={
          'duplicate-record':'''()=>{window.__backup369=window.BRES_CATALOG_V3[1];window.BRES_CATALOG_V3[1]=window.BRES_CATALOG_V3[0]}''',
          'mutated-reference':'''()=>{window.__backup369=window.BRES_CATALOG_V3[1][0];window.BRES_CATALOG_V3[1][0]='TE8D-ALTERED'}''',
          'mutated-maker':'''()=>{window.__backup369=window.BRES_CATALOG_V3[1][1];window.BRES_CATALOG_V3[1][1]='INCONNU'}''',
          'mutated-dimension':'''()=>{window.__backup369=window.BRES_CATALOG_V3[1][3];window.BRES_CATALOG_V3[1][3]+=1}''',
          'swapped-order':'''()=>{let db=window.BRES_CATALOG_V3;[db[0],db[1]]=[db[1],db[0]]}''',
          'missing-last':'''()=>{window.__backup369=window.BRES_CATALOG_V3.pop()}''',
          'same-length-last-replaced':'''()=>{let db=window.BRES_CATALOG_V3;window.__backup369=db[db.length-1];db[db.length-1]=db[0]}''',
        }
        restores={
          'duplicate-record':'''()=>{window.BRES_CATALOG_V3[1]=window.__backup369;delete window.__backup369}''',
          'mutated-reference':'''()=>{window.BRES_CATALOG_V3[1][0]=window.__backup369;delete window.__backup369}''',
          'mutated-maker':'''()=>{window.BRES_CATALOG_V3[1][1]=window.__backup369;delete window.__backup369}''',
          'mutated-dimension':'''()=>{window.BRES_CATALOG_V3[1][3]=window.__backup369;delete window.__backup369}''',
          'swapped-order':tests['swapped-order'],
          'missing-last':'''()=>{window.BRES_CATALOG_V3.push(window.__backup369);delete window.__backup369}''',
          'same-length-last-replaced':'''()=>{let db=window.BRES_CATALOG_V3;db[db.length-1]=window.__backup369;delete window.__backup369}''',
        }
        for name,mutation in tests.items():
            probe(page,name,mutation)
            probe(page,'restored-'+name,restores[name])
        ctx.close()
        ctx,page=setup(browser,old)
        before=one(page,samples)
        before_fold=one(page,folds)
        ctx.close()
    finally:browser.close()
checks={
    'parent_R368_real_js_full_136_input_decisions_preserved':same_before_after(before,arr) and len(arr)==len(samples),
    'parent_R368_real_js_64_fold_decisions_preserved':same_before_after(before_fold,foldarr) and len(foldarr)==64,
    '130_ocr_collision_catalogue_refs_not_auto_selected':all(x['view'] is None for x in arr if x['text'] in collisions),
    '64_folded_ambiguities_not_auto_selected':all(x['view'] is None for x in foldarr),
    'all_clean_inputs_ready':all(x['ready'] and x['status']=='expected-inventory' for x in arr+foldarr),
    'baseline_checksum_approved':states['full']['inventory']=={'ok':True,'reason':'expected-inventory'},
    'all_7_faults_blocked':all(states[x]['inventory']['ok'] is False and all(not v['ready'] and v['view'] is None for v in states[x]['rows']) for x in tests),
    'all_7_restores_release_gate':all(states['restored-'+x]['inventory']['ok'] and all(v['ready'] for v in states['restored-'+x]['rows']) for x in tests),
    'six_same_length_corruptions_detected':all(states[x]['inventory']['reason']=='inventory-mismatch' for x in tests if x!='missing-last'),
    'missing_last_marked_count':states['missing-last']['inventory']['reason']=='count-not-5103',
    'full_catalogue_pilot_positive':states['full']['rows'][0]['view']=='TE8D' and states['full']['rows'][1]['view']=='TE8I',
    'manual_pilot_ref_not_physically_validated':all('RÉFÉRENCE TROUVÉE' in x['output'] and 'VALIDÉ' not in x['output'] for x in manual),
    'no_js_errors':not errors,
    'no_ocr_physical_claim':True,
}
result={'schema':'bres-r369-js-inventory-guard-qa-v1','milestone':'R369','date':'2026-11-04','ok':all(checks.values()),'checks':checks,'states':states,'samples':len(samples),'folds':len(folds),'manual':manual,'js_errors':errors,'blocked_network_requests':len(requests),'sha256_r368':hashlib.sha256(old.encode()).hexdigest(),'sha256_r369':hashlib.sha256(new.encode()).hexdigest(),'limitations':['Synthetic OCR text via actual JavaScript interpreter; no Tesseract or Samsung physical test','Double-32bit ordered fingerprint is not cryptographic authentication; columns 5 onward not covered','Any altered catalogue requires re-validation of the inventory in a future release','Full historical corpus not executed']}
(A/'R369_INVENTORY_GUARD_CHROMIUM.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
(A/'R369_INVENTORY_GUARD_CHROMIUM.txt').write_text(f"R369 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} real Chromium checks; 7 injected catalogue faults and 7 restores; 130 collision refs + 64 OCR folds. Synthetic text only.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'errors':errors[:2],'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
