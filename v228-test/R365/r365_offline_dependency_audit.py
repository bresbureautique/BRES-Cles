#!/usr/bin/env python3
"""R365 static package closure: no network downloads, no claim of offline OCR operation.
Reports only local files and script src provenance; not runtime/worker/recognition proof.
"""
from pathlib import Path
import json,hashlib,re,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    html=(R/'index.html').read_text(encoding='utf-8')
    matches=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I)
    remote=[x for x in matches if re.match(r'https?://',x,re.I)]
    local=[x for x in matches if not re.match(r'(?:https?:|data:|blob:)',x,re.I)]
    local_candidates={
      'tesseract_script': [str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and re.fullmatch(r'tesseract(?:\.min)?\.js',p.name,re.I)],
      'ocr_worker_js': [str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and re.fullmatch(r'worker(?:\.min)?\.js',p.name,re.I)],
      'ocr_wasm': [str(p.relative_to(R)) for p in R.rglob('*.wasm') if p.is_file()],
      'eng_traineddata': [str(p.relative_to(R)) for p in R.rglob('eng.traineddata*') if p.is_file()],
    }
    checks={
      'remote_tesseract_explicit':any('tesseract' in x.lower() for x in remote),
      'no_local_tesseract_bundle':all(not v for v in local_candidates.values()),
      'no_false_claim_of_cold_offline_certification':'coldOfflineOcrCertified:false' in html,
      'stable_not_replaced': 'V2.27 reste la version stable' in html and '<title>BRES Clés V2.28 TEST R156</title>' in html,
      'diagnostic_no_fetch_no_worker':'read-only-no-worker-no-requests' in html,
      'no_remote_loader_added':remote==['https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js'],
      'local_script_paths_exist':all((R/x.split('?',1)[0].split('#',1)[0]).is_file() for x in local),
    }
    out={
      'schema':'bres-r365-static-offline-dependency-closure-v1','checkpoint':'R365',
      'scope':'static ZIP content only (not runtime OCR verification)',
      'script_urls_remote':remote,'script_paths_local':local,
      'local_asset_candidates':local_candidates,
      'cold_offline_ocr_certified':False,'real_ocr_executed':False,
      'required_next_assets':['version-pinned local Tesseract script','version-matched local worker','version-matched WebAssembly core','eng.traineddata language data','real cold-offline recognition test'],
      'canonical_engine_changes':False,'physical_key_test_performed':False,
      'index_sha256':H(R/'index.html'),'checks':checks,'ok':all(checks.values())}
    (R/'R365_OFFLINE_DEPENDENCY_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R365_OFFLINE_DEPENDENCY_AUDIT.txt').write_text('R365 '+('PASS' if out['ok'] else 'FAIL')+': '+str(sum(checks.values()))+'/'+str(len(checks))+' packaging checks; OCR cold offline NOT CERTIFIED.\n'+'Missing local assets: '+', '.join(k for k,v in local_candidates.items() if not v)+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'local_candidates':{k:len(v) for k,v in local_candidates.items()}}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(run())