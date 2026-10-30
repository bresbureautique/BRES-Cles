#!/usr/bin/env python3
"""R364 offline Chromium: diagnostic JSON export; fail-closed and no sensitive payload.
No real recognition or physical key testing. Tesseract mock may not be invoked.
"""
from __future__ import annotations
import json,hashlib,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    html=(R/'index.html').read_text(encoding='utf-8')
    errors=[];network=[];checks={};evidence={}
    with sync_playwright() as pl:
        browser=pl.chromium.launch(executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        try:
            context=browser.new_context(offline=True,service_workers='block',accept_downloads=True)
            context.route('**/*',lambda r:r.abort('blockedbyclient'))
            p=context.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
            p.on('request',lambda req:network.append(req.url))
            p.set_content(html,wait_until='domcontentloaded',timeout=45000)
            checks['application_still_test_and_not_stable']=p.title()=='BRES Clés V2.28 TEST R156' and 'V2.27 reste la version stable' in html
            checks['old_noncertification_banner_preserved']='non chargé' in p.locator('#ocrDependencyStatusR363').inner_text()
            checks['export_aria_status_and_button']=p.locator('#ocrPreflightExportR364').count()==1 and p.locator('#ocrPreflightResultR364[role="status"]').count()==1
            checks['no_benchmark_auto_run']=p.locator('#r362BenchmarkStandaloneDownload').count()==1
            checks['cold_OCR_missing_status_advisory_only']=p.locator('#ocrDependencyStatusR363').get_attribute('data-library-state-r363')=='missing'
            with p.expect_download(timeout=10000) as d:p.locator('#ocrPreflightExportR364').click()
            dl=d.value;content=Path(dl.path()).read_bytes();obj=json.loads(content)
            evidence['download']={'name':dl.suggested_filename,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
            checks['download_has_correct_name']=dl.suggested_filename=='BRES_Cles_R364_Diagnostic_OCR_Local.json'
            checks['JSON_schema_and_checkpoint']=obj['schema']=='bres-r364-ocr-preflight-local-v1' and obj['checkpoint']=='R364'
            checks['no_false_offline_certification']=obj['coldOfflineOcrCertified'] is False and obj['wasmVerified'] is False and obj['languageDataVerified'] is False
            checks['no_worker_attempt']=obj['workerInitialized'] is False and obj['checkMode']=='read-only-no-worker-no-requests'
            checks['no_confirmation_or_identification']=obj['physicalKeyVerified'] is False and obj['autoIdentificationPermitted'] is False
            checks['missing_library_reported_as_missing']=obj['scriptApiPresent'] is False
            checks['no_personal_data_images_or_reference_values']=set(obj)=={'schema','checkpoint','engine','stable','recordedAtUtc','checkMode','scriptApiPresent','scriptOriginClass','workerInitialized','wasmVerified','languageDataVerified','coldOfflineOcrCertified','physicalKeyVerified','autoIdentificationPermitted','nextStep'} and not any(s in content.decode('utf-8') for s in ('data:image','SM-F','userAgent','clientName','reference_a','photoRecto'))
            checks['export_status_is_explicitly_unverified']='NON certifié' in p.locator('#ocrPreflightResultR364').inner_text()
            checks['no_auto_validation_from_export']='en attente' in p.locator('#finalDecision').inner_text().lower()
            # Mocked loaded API: genuine worker MUST NOT be called from a read-only report.
            mock='''<script>window.__r364WorkerCalls=0;window.Tesseract={createWorker:()=>{window.__r364WorkerCalls++;throw new Error('worker cannot be used by diagnostic');}};</script>'''
            alt=context.new_page();alt.on('pageerror',lambda e:errors.append(str(e)))
            alt.set_content(html.replace('<script id="r363-ocr-dependency-status">',mock+'\n<script id="r363-ocr-dependency-status">',1),wait_until='domcontentloaded',timeout=45000)
            checks['loaded_Tesseract_still_not_certified']='NON certifié' in alt.locator('#ocrDependencyStatusR363').inner_text()
            with alt.expect_download(timeout=10000) as d2:alt.locator('#ocrPreflightExportR364').click()
            o2=json.loads(Path(d2.value.path()).read_text(encoding='utf-8'))
            checks['loaded_API_does_not_invoke_worker_or_certify']=o2['scriptApiPresent'] is True and o2['coldOfflineOcrCertified'] is False and alt.evaluate('window.__r364WorkerCalls')==0
            checks['no_new_network_by_export']=(len(network)>=1) and all('tesseract' in u or 'catalogue' in u for u in network) # original script requests only
            checks['no_JS_runtime_error']=len(errors)==0
            context.close()
        finally:browser.close()
    result={'schema':'bres-r364-ocr-preflight-export-test-v1','milestone':'R364','parent':'R363','checks':checks,'ok':all(checks.values()),'failed':[k for k,v in checks.items() if not v], 'errors':errors,'requests':network[:5], 'evidence':evidence,'source_sha256':{'index':sha(R/'index.html'),'Tesseract_local_assets':'not_bundled'},'real_OCR_run':False,'physical_test':False,'claim_offline_certification':False}
    (R/'R364_OCR_PREFLIGHT_REGRESSION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R364_OCR_PREFLIGHT_REGRESSION.txt').write_text(f'R364 {"PASS" if result["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} Chromium local checks; no OCR worker, no Samsung retest.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':result['failed'],'errors':errors},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
