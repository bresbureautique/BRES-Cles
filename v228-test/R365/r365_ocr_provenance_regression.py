#!/usr/bin/env python3
"""R365 Playwright offline tests of diagnostics with remote/local/no script tag.
Does not execute real OCR, launch worker, collect photos or validate keys.
"""
import os,sys,json,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
src=(R/'index.html').read_text(encoding='utf-8')
mock="<script>window.__workerCalls=0;window.Tesseract={createWorker:()=>{window.__workerCalls++;throw new Error('unexpected worker creation')}};</script>"
checks={};runtime_errors=[];cases={}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 try:
  ctx=b.new_context(offline=True,service_workers='block',accept_downloads=True)
  requests=[]
  ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
  ctx.on('request',lambda r:requests.append(r.url))
  original='<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>'
  variants={
   'remote_unavailable':(src,None,'remote-cdn-not-embedded',False),
   'remote_fake_api':(src,mock,'remote-cdn-not-embedded',True),
   'local_fake_api':(src.replace(original,'<script src="tesseract.min.js"></script>'),mock,'local-script-tag-unverified',True),
   'script_absent_fake_api':(src.replace(original,''),mock,'script-tag-absent',True)
  }
  for name,(page_src,injection,expected,api_present) in variants.items():
   if injection:page_src=page_src.replace('<script id="r363-ocr-dependency-status">',injection+'\n<script id="r363-ocr-dependency-status">',1)
   pg=ctx.new_page();pg.on('pageerror',lambda e:runtime_errors.append(str(e)))
   pg.set_content(page_src,wait_until='domcontentloaded',timeout=45000)
   with pg.expect_download(timeout=12000) as d:pg.locator('#ocrPreflightExportR364').click()
   obj=json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
   cases[name]=obj
   checks[name+'_origin']=obj['scriptOriginClass']==expected
   checks[name+'_api_detection']=obj['scriptApiPresent']==api_present
   checks[name+'_never_certifies']=not obj['workerInitialized'] and not obj['wasmVerified'] and not obj['languageDataVerified'] and not obj['coldOfflineOcrCertified'] and not obj['autoIdentificationPermitted']
   checks[name+'_no_worker']=not injection or pg.evaluate('window.__workerCalls')==0
   checks[name+'_no_key_reference_or_photo']=not any(x in obj for x in ['reference','photo','deviceId','userAgent'])
   checks[name+'_R364_schema_unchanged']=obj['schema']=='bres-r364-ocr-preflight-local-v1'
   pg.close()
  ctx.close()
 finally:b.close()
checks['no_runtime_errors']=not runtime_errors
checks['no_new_requests_except_original_remote_script']=all('tesseract.min.js' in u or 'catalog' in u for u in requests)
checks['checkpoint_R365_test_only']='R365 (provenance du diagnostic OCR)' in src and 'V2.27 reste la version stable' in src
out={'schema':'bres-r365-ocr-provenance-playwright-v1','checkpoint':'R365','checks':checks,'ok':all(checks.values()),'failed':[k for k,v in checks.items() if not v],'runtime_errors':runtime_errors,'request_count':len(requests),'cases':{k:{'scriptOriginClass':v['scriptOriginClass'],'scriptApiPresent':v['scriptApiPresent'],'certified':v['coldOfflineOcrCertified']} for k,v in cases.items()},'real_OCR_run':False,'physical_key_test':False}
(R/'R365_OCR_PROVENANCE_REGRESSION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'R365_OCR_PROVENANCE_REGRESSION.txt').write_text(f'R365 {"PASS" if out["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} offline Chromium checks; no real OCR.\n',encoding='utf-8')
print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':out['failed'],'errors':runtime_errors}))
raise SystemExit(0 if out['ok'] else 1)