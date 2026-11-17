#!/usr/bin/env python3
"""R382: demonstrate real browser race baseline and after patch, without physical OCR."""
import json, hashlib, os, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
A=Path(__file__).resolve().parent
checks={}; errors=[]; snapshots={}; requests=[]
js_init=r'''(cfg)=>{
  window.__pending=[];
  window.ensureBresCatalogueR208=()=>new Promise(res=>window.__pending.push(res));
  window.Tesseract={createWorker:()=>{throw Error('Worker must not run in pending catalogue test')}};
  getHeadPhoto=()=>cfg.missing ? null : {name:'fake-head.jpg'};
  captureDecisionGeometryEvidenceR215=()=>cfg.missing ? null : {sig:{top:[],bot:[],colFill:[]},source:'synthetic'};
  fileToCanvas=()=>new Promise(()=>{});
  getOCRCanvas=()=>new Promise(()=>{});
  document.getElementById('manualRef').value='TE8D';
  document.getElementById('manualBrand').value='JMA';
  manualRefSource=manualBrandSource=cfg.source;
  document.getElementById('finalDecision').innerHTML='<b>VALIDÉ ANCIEN</b>';
  document.getElementById('catalogResult').innerHTML='<b>CATALOGUE ANCIEN</b>';
  document.getElementById('catalogVisual').textContent='VISUEL ANCIEN';
  document.getElementById('xref').innerHTML='<a href="https://ecatalogo.jma.es/old">LIEN ANCIEN</a>';
  document.getElementById('ocrStatus').textContent='OCR MAIN ANCIEN';
  document.getElementById('headSearchStatus').textContent='OCR HEAD ANCIEN';
  lastOCRDiagnosticExport={schema:'old'};
  document.getElementById('ocrDiagnosticExportBtn').disabled=false;
  window.__start=ocrRequestEpoch;
  window.__run=cfg.flow==='main'?runOCR():searchFromHeadPhotos();
  return true;
}'''
js_state=r'''()=>({epoch:ocrRequestEpoch,start:window.__start, pending:window.__pending.length,
  final:document.getElementById('finalDecision').textContent,
  catalog:document.getElementById('catalogResult').textContent,
  visual:document.getElementById('catalogVisual').textContent,
  xref:document.getElementById('xref').textContent,
  ref:document.getElementById('manualRef').value,
  maker:document.getElementById('manualBrand').value,
  refSource:manualRefSource,makerSource:manualBrandSource,
  diagCleared:lastOCRDiagnosticExport===null,
  diagButtonDisabled:document.getElementById('ocrDiagnosticExportBtn').disabled,
  head:document.getElementById('headSearchStatus').textContent,
  main:document.getElementById('ocrStatus').textContent,
  rows:typeof BRES_CATALOG_V3==='undefined'?-1:BRES_CATALOG_V3.length,
  integrity:ocrCatalogueAllFieldsR371().ok})'''
t0=time.monotonic()
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 try:
  for tag,fn in [('R381', 'index_R381_BASE.html'), ('R382','index.html')]:
   ctx=b.new_context(offline=True,service_workers='block');ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
   page=ctx.new_page();page.on('pageerror',lambda e:errors.append(f'{tag}: {e}'));page.on('request',lambda r:requests.append(r.url))
   page.set_content((A/fn).read_text('utf8'),wait_until='domcontentloaded',timeout=65000)
   page.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
   for i in range(1,11):page.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text('utf8'))
   snapshots[tag]={}
   for flow in ('main','head'):
    for source in ('ocr','manual'):
     for missing in (False,True):
      scenario=f'{flow}_{source}_{"missing" if missing else "pending"}'
      page.evaluate(js_init,{'flow':flow,'source':source,'missing':missing})
      state=page.evaluate(js_state);snapshots[tag][scenario]=state
      if tag=='R381':
       checks[f'{tag}_{scenario}_reproduces_wait_gap']=state['epoch']==state['start'] and 'ANCIEN' in state['final']
       checks[f'{tag}_{scenario}_retains_old_diag']=not state['diagCleared']
      else:
       checks[f'{tag}_{scenario}_no_stale_approval']=all('ANCIEN' not in state[k] for k in ('final','catalog','visual','xref'))
       checks[f'{tag}_{scenario}_preempt_epoch']=state['epoch']>state['start']
       checks[f'{tag}_{scenario}_revokes_old_diagnostic']=state['diagCleared'] and state['diagButtonDisabled']
       checks[f'{tag}_{scenario}_canonical_integrity']=state['rows']==5103 and state['integrity']
       if source=='manual':checks[f'{tag}_{scenario}_manual_kept']=state['ref']=="TE8D" and state['maker']=="JMA" and state['refSource']==state['makerSource']=='manual'
       else:checks[f'{tag}_{scenario}_ocr_automated_field_cleared']=state['ref']==state['maker']==state['refSource']==state['makerSource']==''
       if missing:
        checks[f'{tag}_{scenario}_missing_rejects_before_await']=state['pending']==0 and ('photo' in (state['main'] if flow=='main' else state['head']).lower() or 'géométrie' in state['main'].lower())
       else:checks[f'{tag}_{scenario}_wait_still_pending']=state['pending']==1
   # Controlled two-request reordering, confirm old resolver cannot steal ownership.
   page.evaluate(js_init,{'flow':'main','source':'ocr','missing':False})
   page.evaluate('''()=>{window.__first=window.__run;window.__second=searchFromHeadPhotos();}''')
   before=page.evaluate('''()=>({epoch:ocrRequestEpoch,pending:window.__pending.length})''')
   page.evaluate('''async()=>{window.__pending[1]();await Promise.resolve();await Promise.resolve();}''')
   after_second=page.evaluate('''()=>ocrRequestEpoch''')
   page.evaluate('''async()=>{window.__pending[0]();await Promise.resolve();await Promise.resolve();}''')
   after_first=page.evaluate('''()=>ocrRequestEpoch''')
   snapshots[tag]['reorder']={'before':before,'afterSecond':after_second,'afterFirst':after_first}
   if tag=='R381':checks['R381_old_request_can_reclaim_epoch']=after_first>after_second
   else:checks['R382_old_request_cannot_reclaim_epoch']=after_first==after_second==before['epoch'] and before['pending']==2
   ctx.close()
 finally:b.close()
checks['no_browser_page_errors']=not errors
checks['attempted_external_resources_only_expected_cdn']=all('cdn.jsdelivr.net/npm/tesseract.js@5/' in u for u in requests)
report={'schema':'bres-r382-catalogue-await-race-browser-v1','date':'2026-11-17','milestone':'R382','ok':all(checks.values()),'checks':checks,'snapshots':snapshots,'errors':errors,'attempted_requests':sorted(set(requests)),'elapsed_seconds':round(time.monotonic()-t0,2),'limits':['Real Chromium, mocked catalogue delay and OCR prerequisites','No worker, no real recognition, no physical key, no offline-ready certification']}
(A/'R382_CATALOGUE_WAIT_CHROMIUM.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(A/'R382_CATALOGUE_WAIT_CHROMIUM.txt').write_text(f'R382 {"PASS" if report["ok"] else "FAIL"} {sum(checks.values())}/{len(checks)}\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
print(json.dumps({'ok':report['ok'],'pass':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v],'duration':report['elapsed_seconds']},ensure_ascii=False))
if not report['ok']:sys.exit(1)