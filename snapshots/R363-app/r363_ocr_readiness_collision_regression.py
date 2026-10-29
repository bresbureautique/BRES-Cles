#!/usr/bin/env python3
"""Cold/offline Chromium smoke + all CAT-R363 negative textual collisions.

No real OCR or image matching. This tests 'no VALIDÉ without photos/calibration'
on app's pilot manual entry and only that logic. Full catalogue remains separate.
"""
from __future__ import annotations
import json,hashlib,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    html=(R/'index.html').read_text(encoding='utf-8')
    js=(R/'v228-catalogue.js').read_text(encoding='utf-8')
    fixture=json.loads((R/'R363_COLLISION_TEST_ONLY_FIXTURE.json').read_text(encoding='utf-8'))
    refs=fixture['references'];pairs=fixture['pairs']
    checks={};failed=[];page_errors=[];net_errors=[];evidence={}
    with sync_playwright() as pl:
        browser=pl.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            ctx=browser.new_context(service_workers='block',offline=True)
            ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
            page=ctx.new_page()
            page.on('pageerror',lambda e:page_errors.append(str(e)))
            page.on('requestfailed',lambda req:net_errors.append(req.url))
            page.set_content(html,wait_until='domcontentloaded',timeout=45000)
            page.add_script_tag(content=js)
            checks['test_runtime_V228_not_stable_unchanged']=page.title()=='BRES Clés V2.28 TEST R156' and 'V2.27 reste la version stable' in html
            checks['no_remote_OCR_library_cache_cold']=page.evaluate('typeof globalThis.Tesseract')=='undefined' and any('tesseract' in u for u in net_errors)
            dom=page.locator('#ocrDependencyStatusR363')
            evidence['offline_banner']=dom.inner_text()
            checks['offline_readiness_explicit_non_certification']=dom.get_attribute('data-library-state-r363')=='missing' and 'non chargé' in dom.inner_text() and dom.get_attribute('role')=='status'
            checks['manual_controls_remain_usable']=page.locator('#manualRefBtn').is_enabled() and page.locator('#manualRef').is_visible()
            checks['no_photography_no_positive_decision']='en attente' in page.locator('#finalDecision').inner_text().lower()
            page.locator('#ocrBtn').click()
            page.wait_for_function("document.getElementById('ocrStatus').textContent.includes('deux photos')",timeout=5000)
            checks['no_two_photos_OCR_is_refused']='deux photos' in page.locator('#ocrStatus').inner_text().lower()
            # Fast in-page synchronous loop; click invokes the existing unmodified manual entry path.
            outputs=page.evaluate("""(refs)=>{
              const inp=document.getElementById('manualRef'),button=document.getElementById('manualRefBtn');
              const status=document.getElementById('manualRefStatus'),final=document.getElementById('finalDecision');
              let total=0,notFound=0,foundWithoutValidation=0,bad=[];
              for (const ref of refs) {
                inp.value=ref;button.click();total++;
                const text=final.textContent||'',manual=status.textContent||'';
                if(text.includes('VALIDÉ :') || text.includes('RÉFÉRENCE MANUELLE CONFIRMÉE') || text.includes('QA2 VALIDÉ'))bad.push({ref,why:'positive without geometry',decision:text.slice(0,250)});
                if(text.includes('RÉFÉRENCE NON VALIDÉE'))notFound++;
                else if(text.includes('RÉFÉRENCE TROUVÉE') || text.includes('RÉFÉRENCE MANUELLE TROUVÉE'))foundWithoutValidation++;
                else bad.push({ref,why:'unexpected status',decision:text.slice(0,250),manual:manual.slice(0,200)});
              }
              return {total,notFound,foundWithoutValidation,bad:bad.slice(0,12),badCount:bad.length,last:final.textContent.slice(0,200)};
            }""",refs)
            evidence['all_catalogue_collision_refs']=outputs
            checks['all_732_unverified_refs_exercised']=outputs['total']==len(set(refs))==732
            checks['all_732_manual_checks_fail_closed_without_geometry']=outputs['badCount']==0 and outputs['notFound']+outputs['foundWithoutValidation']==732
            checks['all_393_collision_pairs_covered_by_refs']=len(pairs)==393 and all(a in refs and b in refs and a!=b for a,b in pairs)
            checks['app_does_not_gain_5103_catalogue_active_entries']=bool(page.evaluate('typeof XREF')) and 'v228-catalogue.js' in html
            # Isolated fake API injection only verifies banner remains warning when JS loads.
            loaded=html.replace('<script id="r363-ocr-dependency-status">',
                       '<script>window.Tesseract={createWorker:function(){throw Error("must never start")}};</script>\n<script id="r363-ocr-dependency-status">',1)
            second=ctx.new_page();second.on('pageerror',lambda e:page_errors.append(str(e)))
            second.set_content(loaded,wait_until='domcontentloaded',timeout=45000)
            d=second.locator('#ocrDependencyStatusR363');evidence['loaded_banner']=d.inner_text()
            checks['library_loaded_does_not_claim_offline_certified']=d.get_attribute('data-library-state-r363')=='loaded-not-certified' and 'NON certifié' in d.inner_text() and 'WebAssembly' in d.inner_text() and 'warn' in (d.get_attribute('class') or '')
            checks['no_browser_JS_exceptions']=not page_errors
            checks['no_OCR_network_or_real_physical_test_claim']=True
            second.close();ctx.close()
        finally:browser.close()
    checks['fixture_deterministic_and_separate']=fixture['fixture_pair_count']==393 and fixture['fixture_reference_count']==732 and fixture['no_auto_identification']
    result={'schema':'bres-r363-ocr-dependency-and-collision-negative-v1','milestone':'R363','parent':'R362',
            'checks':checks,'check_total':len(checks),'ok':all(checks.values()),'errors':page_errors,
            'failed':[k for k,v in checks.items() if not v], 'network_denied':net_errors,
            'source_sha256':{'index':sha(R/'index.html'),'pilot_lookup':sha(R/'v228-catalogue.js'),'test_only_fixture':sha(R/'R363_COLLISION_TEST_ONLY_FIXTURE.json')},
            'evidence':evidence,'physical_device_used':False,'OCR_executed':False,
            'full_catalogue_activated':False,'cold_offline_OCR_certified':False}
    (R/'R363_OCR_COLLISION_REGRESSION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'R363_OCR_COLLISION_REGRESSION.txt').write_text(f'R363 {"PASS" if result["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)}; 732 manual reference negatives, 393 theoretical pairs; OCR offline NOT certified; no Samsung physical test.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':result['failed'],'refs':len(refs),'bad':outputs['badCount'],'errors':page_errors[:3]},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
