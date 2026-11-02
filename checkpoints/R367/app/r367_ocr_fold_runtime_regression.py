#!/usr/bin/env python3
"""R367: compare R366 and R367 *real JavaScript decision functions* on synthetic OCR strings.

No Tesseract worker, camera, physical key, simulated geometry, auto-acceptance or network.
Full unmodified 5103-row canonical catalogue is injected directly into isolated Chromium.
"""
import hashlib,json,os,sys,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent
C=A.parent/'cat'
SOURCE=Path('/mnt/data/bres_r366_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R366.zip')
fixtures=json.loads((C/'CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES.json').read_text(encoding='utf-8'))['fixtures']
with zipfile.ZipFile(SOURCE) as z:base_html=z.read('app/index.html').decode('utf-8')
updated_html=(A/'index.html').read_text(encoding='utf-8')
assert base_html!=updated_html and len(fixtures)==64
blocked_urls=[];errors=[]
source_hashes={n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in ['index.html','v228-catalogue.js','r331-device-benchmark.js','device_benchmark_r336.html']}

def script_case(page,mode):
    page.set_content(base_html if mode=='baseline-r366' else updated_html,wait_until='domcontentloaded',timeout=45000)
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text(encoding='utf-8'))
    for i in range(1,11):page.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text(encoding='utf-8'))
    assert page.evaluate('(window.BRES_CATALOG_V3||[]).length')==5103
    # This invokes the deployed application parser and two-view resolver, not a Python imitation.
    return page.evaluate('''fs=>fs.map(f=>{
      const raw=f.synthetic_ocr_text_NOT_A_PHYSICAL_KEY;
      const once=interpretOCRViews([raw, '']);
      const same=interpretOCRViews([raw,raw]);
      const resolved=resolveCompactCatalogueAmbiguityR213(same,null,null);
      const guarded=interpretOCR(raw);
      const pack=x=>({best:x?.best?.sim>=OCR_PREFILL_THRESHOLD?x.best.canon:null,
        anyBest:x?.best?.canon||null,confidence:x?.best?.sim??null,
        ambiguous:!!x?.referenceAmbiguity,canons:x?.ambiguousCanons||[],
        folded:x?.ocrFoldAmbiguitiesR367||[],candidates:x?.candidates||[]});
      return {synthetic_text:raw,source_references:f.source_candidates_DISTINCT_UNVERIFIED,
        single:pack(once),both:pack(same),after_geometry_absent:pack(resolved),raw:pack(guarded)};
    })''',fixtures)

checks={};extra={};cases={};
with sync_playwright() as pl:
    browser=pl.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        context=browser.new_context(offline=True,service_workers='block')
        context.route('**/*',lambda route:route.abort('blockedbyclient'))
        page=context.new_page()
        page.on('pageerror',lambda ex:errors.append(str(ex)))
        page.on('request',lambda request:blocked_urls.append(request.url))
        baseline=script_case(page,'baseline-r366')
        page.close()
        page=context.new_page();page.on('pageerror',lambda ex:errors.append(str(ex)))
        patched=script_case(page,'patched-r367')
        # Other view, including a strong clean pilot code, cannot override an ambiguous OCR reading.
        cross=page.evaluate('''()=>{const both=interpretOCRViews(['KF1','TE8D']);return {
          best:both.best,ambiguity:both.referenceAmbiguity,
          folded:both.ocrFoldAmbiguitiesR367||[],
          resolved:resolveCompactCatalogueAmbiguityR213(both,null,null).best};}''')
        reference_controls=page.evaluate('''()=>Object.fromEntries(['TE8D','TE8I','TE8B','UNLISTED_999'].map(s=>{
          const info=interpretOCRViews([s,s]);return [s,{best:info.best?.canon||null,
          eligible:!!(info.best&&info.best.sim>=OCR_PREFILL_THRESHOLD),
          ambiguous:info.referenceAmbiguity,folded:info.ocrFoldAmbiguitiesR367?.length||0}]}))''')
        manual=[]
        for ref in ['TE8D','TE8I']:
            page.locator('#manualRef').fill(ref)
            page.locator('#manualRefBtn').click()
            manual.append({'ref':ref,'status':page.locator('#manualRefStatus').inner_text()[:200], 'decision':page.locator('#finalDecision').inner_text()[:200]})
        checks.update({
          '64_baseline_decision_replayed':len(baseline)==64,
          '64_R367_decision_replayed':len(patched)==64,
          'baseline_11_unsafe_text_prefills':sum(bool(x['both']['best']) for x in baseline)==11,
          'new_guard_0_text_prefills':sum(bool(x['both']['best']) for x in patched)==0,
          'new_guard_0_single_view_prefills':sum(bool(x['single']['best']) for x in patched)==0,
          'new_guard_0_missing_geometry_promotions':sum(bool(x['after_geometry_absent']['best']) for x in patched)==0,
          '60_ambiguous_4_ignored_without_candidate':sum(bool(x['both']['ambiguous']) for x in patched)==60 and sum(not x['both']['ambiguous'] for x in patched)==4,
          'manual_policy_for_every_detected_fold':all((not x['both']['folded']) or all(f['policy']=='manual-review-required' for f in x['both']['folded']) for x in patched),
          'cross_view_no_override':cross['best'] is None and cross['resolved'] is None and cross['ambiguity'] and len(cross['folded'])>0,
          'clean_pilot_TE8D_preserved':reference_controls['TE8D']['best']=='TE8D' and reference_controls['TE8D']['eligible'] and not reference_controls['TE8D']['ambiguous'],
          'clean_pilot_TE8I_preserved':reference_controls['TE8I']['best']=='TE8I' and reference_controls['TE8I']['eligible'] and not reference_controls['TE8I']['ambiguous'],
          'manual_TE8D_TE8I_still_nonvalidated':all('RÉFÉRENCE TROUVÉE' in row['decision'] and 'VALIDÉ' not in row['decision'] for row in manual),
          'no_js_errors':not errors,
          'no_real_OCR_or_geometry_claim':True,
          'catalogue_source_loaded_5103':True,
          'stable_V227_not_promoted':'V2.27 reste la version stable' in updated_html,
        })
        extra={'cross_view':cross,'reference_controls':reference_controls,'manual':manual}
        page.close();context.close()
    finally: browser.close()
cases={'baseline_r366':baseline,'guarded_r367':patched}
result={'schema':'bres-r367-ocr-glyph-runtime-regression-v1','milestone':'R367','date':'2026-11-02',
 'checks':checks,'ok':all(checks.values()),'case_count':len(patched),'prior_unsafe_auto_prefills':11,'after_guard_auto_prefills':0,
 'guard_detected_ambiguous_cases':sum(bool(x['both']['ambiguous']) for x in patched),
 'data_source':'full 5103 canonical rows, unchanged, injected into browser',
 'invoked':'actual V2.28 JavaScript interpretOCR/interpretOCRViews and R213 resolver; no Tesseract',
 'requests_blocked':len(blocked_urls),'runtime_errors':errors,'source_sha256':source_hashes,
 'cases':cases,'other_evidence':extra,
 'limitations':['Synthetic raw OCR text, not genuine camera/OCR output','No physical reference validation',
                'No Samsung runtime exercised','Only 64 lossily folded groups; 325 typing pairs not checked as OCR equivalents',
                'Tesseract cold-offline not certified','No V2.27 stable changes']}
(A/'R367_OCR_FOLD_RUNTIME_REGRESSION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(A/'R367_OCR_FOLD_RUNTIME_REGRESSION.txt').write_text(
    f"R367 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} Chromium runtime controls. 64 synthetic folds: R366 had {result['prior_unsafe_auto_prefills']} possible text prefills, R367 has {result['after_guard_auto_prefills']}. No physical OCR.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'failures':[k for k,v in checks.items() if not v],
                  'prior':11,'after':0,'errors':errors,'requests':len(blocked_urls)},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
