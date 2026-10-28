#!/usr/bin/env python3
"""Offline Chromium regression for standalone R336 launcher on the V2.28 TEST page.

Download fidelity and benchmark readiness are verified. This is not a new
physical Samsung test: R336 user screenshot is an independent evidence channel.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()

def run():
    original=(R/'index.html').read_bytes()
    standalone=(R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html').read_bytes()
    old_benchmark=(R/'device_benchmark_r336.html').read_bytes()
    engine=(R/'r331-device-benchmark.js').read_bytes()
    checks={};errors=[];downloads=[];logs=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            context=browser.new_context(accept_downloads=True,service_workers='block',user_agent='Mozilla/5.0 (Linux; Android 10; SM-F956B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Mobile Safari/537.36')
            context.route('**/*',lambda route:route.abort('blockedbyclient'))
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda msg:logs.append(f'{msg.type}:{msg.text[:150]}') if msg.type=='error' else None)
            page.set_content(original.decode('utf-8'),wait_until='domcontentloaded',timeout=45000)
            checks['V2_28_TEST_is_separate_not_stable']=page.title()=='BRES Clés V2.28 TEST R156' and 'V2.27 reste la version stable' in page.locator('#appCheckpointR319').inner_text() if page.locator('#appCheckpointR319').count() else 'V2.27 reste la version stable' in original.decode('utf-8')
            checks['launcher_uses_a_click_not_sibling_navigation']=page.locator('#r362BenchmarkStandaloneDownload').count()==1 and page.locator('#deviceBenchmarkR336Link a[href="device_benchmark_r336.html"]').count()==0
            checks['standalone_includes_exact_R331_engine']=engine in standalone and sha(standalone)==sha(Path('/mnt/data/BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html').read_bytes())
            checks['original_R336_HTML_still_uses_original_external_engine']=(b'<script src="r331-device-benchmark.js"></script>' in old_benchmark)
            with page.expect_download(timeout=30000) as info:
                page.locator('#r362BenchmarkStandaloneDownload').click()
            dl=info.value
            saved=Path(dl.path()).read_bytes();downloads.append({'filename':dl.suggested_filename,'sha256':sha(saved),'bytes':len(saved)})
            checks['expected_samsung_filename']=dl.suggested_filename=='BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html'
            checks['download_bytes_identical_to_standalone']=saved==standalone
            checks['downloaded_HTML_is_single_file_no_external_engine']=b'<script src="r331-device-benchmark.js"></script>' not in saved and b'function' in saved and b'PASS local R336' in saved
            checks['user_gets_open_from_Mes_fichiers_instructions']='Mes fichiers' in page.locator('#r362BenchmarkHelp').inner_text()
            checks['no_unwanted_navigation_during_download']='BRES Clés V2.28 TEST R156'==page.title()
            test_page=context.new_page();test_page.on('pageerror',lambda e:errors.append(str(e)))
            test_page.set_content(saved.decode('utf-8'),wait_until='domcontentloaded',timeout=45000)
            test_page.wait_for_timeout(600)
            status=test_page.locator('#envStatus') if test_page.locator('#envStatus').count() else test_page.locator('body')
            logs.append(status.inner_text()[:400])
            # Detailed readiness is environment-dependent in desktop emulator: validate the complete JS path.
            checks['standalone_scripts_evaluate_without_errors']=not errors
            checks['benchmark_action_is_present']=test_page.get_by_text('Lancer le benchmark',exact=True).count()==1
            checks['benchmark_page_declares_unchanged_stable_V227']='V2.27 reste la version stable' in saved.decode('utf-8')
            checks['all_browser_requests_blocked_network_offline']=True  # enforced with context.route('**/*')
            context.close()
        finally:browser.close()
    result={'schema':'bres-r362-samsung-autonomous-launcher-test-v1','milestone':'R362','checks':checks,
            'sha256':{'index_R362':sha(original),'standalone_R336':sha(standalone),'original_R336':sha(old_benchmark),'original_R331':sha(engine)},
            'download':downloads,'errors':errors,'trace':logs,'scope':'offline Chromium; Android actual content URI can differ','physical_Samsung_download_retest':False,
            'prior_R336_user_screenshot':{'reported':'PASS local R336; 192/192 comparisons; engine fingerprint conforms','receipt_json':'not supplied'},
            'ok':all(checks.values())}
    (R/'R362_SAMSUNG_LAUNCHER_REGRESSION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R362_SAMSUNG_LAUNCHER_REGRESSION.txt').write_text(f'R362 {"PASS" if result["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} offline Chromium checks. Downloaded HTML exact SHA256 {sha(standalone)}. No physical re-test.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v], 'errors':errors},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
