#!/usr/bin/env python3
"""Offline Chromium tests: origin scheme diagnostics are conservative (not OCR)."""
import hashlib,json,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
src=(R/'index.html').read_text(encoding='utf-8')
old='<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>'
assert src.count(old)==1
mock="<script>window.__workerCalls=0;window.Tesseract={createWorker:()=>{window.__workerCalls++;throw Error('unexpected createWorker')}};</script>"
variants={
 'https_cdn':(old,'remote-cdn-not-embedded'),
 'http_non_cdn':('<script src="http://example.test/tesseract.js"></script>','remote-cdn-not-embedded'),
 'protocol_relative':('<script src="//cdn.example.test/tesseract.min.js?v=5"></script>','remote-cdn-not-embedded'),
 'spaced_https':('<script src="  HTTPS://cdn.example.test/tesseract.min.js?cache=1  "></script>','remote-cdn-not-embedded'),
 'local_relative':('<script src="./tesseract.min.js?v=5"></script>','local-script-tag-unverified'),
 'local_rooted':('<script src="/assets/tesseract.js"></script>','local-script-tag-unverified'),
 'file_scheme':('<script src="file:///tmp/tesseract.min.js"></script>','explicit-scheme-not-certifiable'),
 'ftp_scheme':('<script src="ftp://x.test/tesseract.js"></script>','explicit-scheme-not-certifiable'),
 'absent':('','script-tag-absent')
}
checks={};errors=[];requests=[];cases={}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 try:
  ctx=browser.new_context(offline=True,accept_downloads=True,service_workers='block')
  ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
  ctx.on('request',lambda req:requests.append(req.url))
  for name,(tag,expected) in variants.items():
   pg=ctx.new_page();pg.on('pageerror',lambda e:errors.append(str(e)))
   page=src.replace(old,tag).replace('<script id="r363-ocr-dependency-status">',mock+'\n<script id="r363-ocr-dependency-status">',1)
   pg.set_content(page,wait_until='domcontentloaded',timeout=45000)
   with pg.expect_download(timeout=12000) as d:pg.locator('#ocrPreflightExportR364').click()
   obj=json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
   cases[name]={'origin':obj['scriptOriginClass'],'api':obj['scriptApiPresent']}
   checks[name+'_classification']=obj['scriptOriginClass']==expected
   checks[name+'_api_present_is_not_certification']=obj['scriptApiPresent'] and not obj['coldOfflineOcrCertified']
   checks[name+'_never_initialized_worker']=pg.evaluate('window.__workerCalls')==0 and obj['workerInitialized'] is False
   checks[name+'_no_verified_worker_wasm_lang']=obj['wasmVerified'] is False and obj['languageDataVerified'] is False
   checks[name+'_no_identity_or_auto_decision']=obj['physicalKeyVerified'] is False and obj['autoIdentificationPermitted'] is False and not any(k in obj for k in ('reference','photo','deviceId','userAgent'))
   checks[name+'_schema_backward_compatible']=obj['schema']=='bres-r364-ocr-preflight-local-v1'
   pg.close()
  ctx.close()
 finally:browser.close()
checks['no_js_runtime_errors']=not errors
checks['no_extraneous_network_requests']=all('tesseract' in url.lower() or 'catalogue' in url.lower() for url in requests)
checks['checkpoint_test_label']='R366 (diagnostic OCR conservateur)' in src and 'V2.27 reste la version stable' in src
out={'schema':'bres-r366-ocr-script-origin-offline-regression-v1','checkpoint':'R366','checks':checks,'ok':all(checks.values()),'failures':[k for k,v in checks.items() if not v], 'request_count':len(requests),'errors':errors,'cases':cases,'real_OCR_executed':False,'physical_key_test':False,'active_ocr_rule_unchanged':True}
(R/'R366_OCR_ORIGIN_REGRESSION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'R366_OCR_ORIGIN_REGRESSION.txt').write_text('R366 '+('PASS' if out['ok'] else 'FAIL')+': '+str(sum(checks.values()))+'/'+str(len(checks))+' offline Chromium diagnostic checks; no real OCR.\n',encoding='utf-8')
print(json.dumps({'ok':out['ok'],'checks':len(checks),'failures':out['failures'],'requests':len(requests),'runtime_errors':errors}))
raise SystemExit(0 if out['ok'] else 1)