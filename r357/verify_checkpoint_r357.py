#!/usr/bin/env python3
"""R357 release gate; parent R356 hash lock, modified test HTML and regression.

Unlike historic recursive gates, only R356's already accepted browser baseline
is replayed in isolation to avoid deep recursion across hundreds of old scripts.
"""
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
EXPECTED_ORIGINAL_INDEX_SHA='7695301023e526d4cdc92e05fcf7f62df1e56bef1ebc639766e91788849bbeba'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def job(cmd,cwd):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=80)
    return {'exit_code':p.returncode,'stdout':p.stdout[-900:],'stderr':p.stderr[-900:]}

def main():
    parent_lines=(R/'SNAPSHOT_MANIFEST_R356.sha256').read_text(encoding='utf-8').splitlines()
    expected=dict(ln.split('  ',1) for ln in parent_lines)
    # manifest maps digest -> filename; check all inherited files except the deliberately patched HTML.
    missing_or_changed=[filename for digest,filename in (line.split('  ',1) for line in parent_lines)
                        if filename!='index.html' and (not (R/filename).is_file() or sha(R/filename)!=digest)]
    pre_index=next(d for d,fn in (line.split('  ',1) for line in parent_lines) if fn=='index.html')
    new_index=sha(R/'index.html')
    sec=job([sys.executable,str(R/'r357_manual_input_xss_regression.py')],R)
    data=json.loads((R/'R357_MANUAL_INPUT_SECURITY.json').read_text(encoding='utf-8'))
    # Replay prior browser smoke in a separate scratch directory, without rewriting parent R356 evidence.
    with tempfile.TemporaryDirectory(prefix='bres-r357-baseline-') as scratch:
        p=Path(scratch)
        for name in ('r356_chromium_offline_smoke.py','index.html','v228-catalogue.js',
                     'device_benchmark_r336.html','r331-device-benchmark.js'):
            shutil.copy2(R/name,p/name)
        base=job([sys.executable,str(p/'r356_chromium_offline_smoke.py')],p)
        baseline=json.loads((p/'R356_CHROMIUM_OFFLINE_SMOKE.json').read_text(encoding='utf-8')) if base['exit_code']==0 else {}
    test_js=job(['node','--check',str(R/'v228-catalogue.js')],R)
    benchmark_js=job(['node','--check',str(R/'r331-device-benchmark.js')],R)
    checks={
      'R356_hashes_8786_untouched_except_index':len(parent_lines)==8786 and not missing_or_changed,
      'prior_index_hash_known_and_changed':pre_index==EXPECTED_ORIGINAL_INDEX_SHA and new_index!=pre_index,
      '11_security_regressions_pass':sec['exit_code']==0 and data['ok'] and len(data['checks'])==11,
      'prior_R356_browser_smoke_10_10_replayed':base['exit_code']==0 and baseline.get('ok') and len(baseline['checks'])==10,
      'no_JS_parse_changes_catalogue_and_benchmark':test_js['exit_code']==0 and benchmark_js['exit_code']==0,
      'unchanged_application_title_R156':'BRES Clés V2.28 TEST R156' in (R/'index.html').read_text(encoding='utf-8'),
      'manual_field_escaping_present':(R/'index.html').read_text(encoding='utf-8').count('escapeManualHtmlR357')>=8,
      'no_physical_validation_claim':data['OCR_offline_certified'] is False and data['Samsung_validated'] is False,
    }
    out={'milestone':'R357','parent':'R356','checks':checks,'ok':all(checks.values()),
         'parent_files':len(parent_lines),'parent_mismatch_excluding_intentional_HTML':missing_or_changed,
         'index_original_sha256':pre_index,'index_test_updated_sha256':new_index,
         'jobs':{'r357':sec,'r356_browser':base,'catalog_js':test_js,'benchmark_js':benchmark_js},
         'engine':'R156 (test only)','R305_rule_changed':False,'stable_V2_27_modified':False}
    (R/'R357_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R357_VERIFICATION.txt').write_text('R357 '+('PASS' if out['ok'] else 'FAIL')+'\n'+
         '\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'parent_files_locked':len(parent_lines),'baseline_ok':base['exit_code']==0}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())