#!/usr/bin/env python3
"""R378 real Chromium offline: escaped head-photo OCR *result branches*.
All payloads and readings are synthetic; no camera, key or physical test involved.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os,hashlib,time,zipfile
A=Path(__file__).resolve().parent; C=A.parent/'cat'
checks={}; observations={}; errors=[]; requests=[]
base=(A/'index_R377_BASE.html').read_text('utf8'); now=(A/'index.html').read_text('utf8')
checks['r377_source_differs_and_only_head_photo_function_changed']=(base!=now and base[:base.index('async function searchFromHeadPhotos(){')]==now[:now.index('async function searchFromHeadPhotos(){')] and base[base.index('el("headSearchBtn").onclick=searchFromHeadPhotos;'):]==now[now.index('el("headSearchBtn").onclick=searchFromHeadPhotos;'):])
start=time.monotonic()
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 try:
  ctx=browser.new_context(offline=True,service_workers='block')
  ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  page.set_content(now,wait_until='domcontentloaded',timeout=60000)
  page.add_script_tag(content=(A/'v228-catalogue.js').read_text('utf8'))
  for i in range(1,11):page.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text('utf8'))
  test=page.evaluate(r'''async()=>{
    const payload='<img src=x onerror="window.__r378Executed=1">';
    const svg='<svg onload="window.__r378Executed=1"></svg>';
    const results=[];
    const origX={...XREF.TE8D};
    Tesseract={createWorker:()=>({})};
    getHeadPhoto=()=>({});
    fileToCanvas=async()=>document.createElement('canvas');
    bestOCR=async()=>({text:'SYNTH',rawText:'SYNTH',mode:'test',attempts:1,confidence:87});
    beginFreshCatalogueQa2OcrCycleR171=()=>{};
    beginOCRRequest=()=>({identificationEpoch:0,requestEpoch:0});
    ocrRequestIsCurrent=()=>true;
    mergePassMakerConsensus=x=>x;
    interpretOCRViews=()=>window.__r378Info;
    resolveCompactCatalogueAmbiguityR213=x=>x;
    captureDecisionGeometryEvidenceR215=()=>null;
    enableOCRDiagnosticExport=()=>{};
    syncOCRBrand=()=>{};
    clearOCRReferenceIfCurrent=()=>{};
    setOCRField=()=>{};
    showXref=()=>{};
    renderCatalogVisual=()=>({available:false});
    currentAutoIdentificationCalibrationR227=()=>({ok:true});
    resolvedOCRBrand=()=>window.__r378Maker;
    brandVisualCandidates=()=>window.__r378Brands;
    manualRefSource='';
    const baseInfo={makers:[],passMakerConsensus:[],candidates:[],best:null,ocrCatalogueReadyR368:true,crossViewConflict:false,referenceAmbiguity:false,ambiguousCanons:[],catalogueGeometryResolution:null};
    const examine=(name)=>{
      const targets=['headSearchStatus','catalogResult','finalDecision'].map(x=>document.getElementById(x));
      const active=targets.filter(x=>x.innerHTML.includes('SYNTH')||x.innerHTML.includes('&lt;')||x.innerHTML.includes('Candidats')||x.innerHTML.includes('Marque')||x.innerHTML.includes('Référence catalogue'));
      const injected=targets.some(x=>!!x.querySelector('img,svg,script,iframe'));
      results.push({name,injected,executed:window.__r378Executed===1, visible:active.map(x=>x.textContent),html:active.map(x=>x.innerHTML)});
    };
    // A recognised reference: dangerous catalogue metadata must be rendered as text,
    // and a non-https JMA link must not be created.
    Object.assign(XREF.TE8D,{Pour:payload, JMA:svg, JMA_URL:'javascript:window.__r378Executed=1'});
    window.__r378Info={...baseInfo,best:{canon:'TE8D',sim:.99}};
    window.__r378Maker='JMA';window.__r378Brands=[];
    await searchFromHeadPhotos();examine('best-dangerous-metadata');
    const linkOne=document.getElementById('catalogResult').querySelector('a');
    results[results.length-1].noJavascriptLink=!linkOne;
    // Valid HTTPS link remains usable; its '&' query text must stay intact.
    XREF.TE8D.JMA_URL='https://ecatalogo.jma.es/en/te-8d/11045/?imprimir=1&action=1';
    await searchFromHeadPhotos();examine('best-safe-link');
    const linkTwo=document.getElementById('catalogResult').querySelector('a');
    results[results.length-1].safeLink=!!linkTwo && linkTwo.href.endsWith('imprimir=1&action=1') && linkTwo.rel==='noopener noreferrer';
    Object.assign(XREF.TE8D,origX);
    // A manufacturer match is not an identified physical key: any label, candidate
    // reference or visual counterpart must be text even if polluted.
    window.__r378Info={...baseInfo};window.__r378Maker=payload;
    window.__r378Brands=[{canon:svg,silca:payload,score:91,scorePolicy:{filteringAllowed:true},ambiguity:[]}];
    await searchFromHeadPhotos();examine('strong-maker-branch');
    results[results.length-1].preservedPayload=document.getElementById('headSearchStatus').textContent.includes(payload)&&document.getElementById('catalogResult').textContent.includes(svg);
    // Without validated geometry: still display-only and no code execution.
    currentAutoIdentificationCalibrationR227=()=>({ok:false});
    window.__r378Brands=[{canon:svg,silca:payload,score:77,scorePolicy:{filteringAllowed:false},ambiguity:[]}];
    await searchFromHeadPhotos();examine('weak-maker-branch');
    results[results.length-1].preservedPayload=document.getElementById('headSearchStatus').textContent.includes(svg)&&document.getElementById('catalogResult').textContent.includes(payload);
    return {results,catalogueRows:BRES_CATALOG_V3.length,inventory:ocrCatalogueInventoryR369().ok,fields:ocrCatalogueAllFieldsR371().ok};
  }''')
  r=test['results']; observations['cases']=[{'name':x['name'],'injected':x['injected'],'executed':x['executed']} for x in r]
  checks['four_result_scenarios_no_html_nodes_or_script_execution']=len(r)==4 and all(not x['injected'] and not x['executed'] for x in r)
  checks['non_https_jma_url_rejected']=r[0]['noJavascriptLink']
  checks['safe_https_jma_url_preserved']=r[1]['safeLink']
  checks['strong_maker_branch_escaped']=r[2]['preservedPayload']
  checks['weak_maker_branch_escaped']=r[3]['preservedPayload']
  checks['full_catalogue_5103_and_integrity']=test['catalogueRows']==5103 and test['inventory'] and test['fields']
  # Independence from format: ensure no head result is automatically verified by these mock inputs.
  checks['no_final_verified_claim_for_unverified_branches']=all('VALIDÉ :' not in '\n'.join(x['visible']) for x in r[2:])
  checks['no_browser_js_errors']=not errors
  ctx.close()
 finally:browser.close()
with zipfile.ZipFile('/mnt/data/bres_r377_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R377.zip') as baseline:
 checks['ten_canonical_catalogue_chunks_identical_to_r377_zip']=all((A/f'catalogue/v3/catalog-{i:02}.js').read_bytes()==baseline.read(f'app/catalogue/v3/catalog-{i:02}.js') for i in range(1,11))
report={'schema':'bres-r378-head-ocr-result-escaping-v1','date':'2026-11-13','milestone':'R378','ok':all(checks.values()),'checks':checks,'scenarios':observations,'elapsed_seconds':round(time.monotonic()-start,2),'browser_errors':errors,'network_requests_blocked':len(requests),'limits':['Synthetic strings and mocked OCR photo responses only','No physical Samsung measurement','No offline cold-start OCR certification']}
(A/'R378_HEAD_RESULTS_CHROMIUM.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(A/'R378_HEAD_RESULTS_CHROMIUM.txt').write_text('R378 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if ok else 'FAIL ')+name for name,ok in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v],'errors':errors,'elapsed':report['elapsed_seconds']},ensure_ascii=False))
if not report['ok']:raise SystemExit(1)