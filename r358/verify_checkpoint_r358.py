#!/usr/bin/env python3
"""R358 integrity gate built upon security-patched R357, without touching the stable."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run(name,timeout=150):
    p=subprocess.run([sys.executable,str(R/name)],cwd=R,text=True,capture_output=True,timeout=timeout)
    return {'exit_code':p.returncode,'stdout':p.stdout[-1200:],'stderr':p.stderr[-1200:]}

def main():
    jobs={'R357_security_and_browser_regressions':run('verify_checkpoint_r357.py'),
          'R358_full_130_reference_browser_regression':run('r358_pilot_confusable_regression.py')}
    manifest=(R/'SNAPSHOT_MANIFEST_R357.sha256').read_text(encoding='utf-8').splitlines()
    bad=[]
    for line in manifest:
        digest,name=line.split('  ',1)
        if not (R/name).is_file() or sha(R/name)!=digest:bad.append(name)
    sec=json.loads((R/'R357_MANUAL_INPUT_SECURITY.json').read_text(encoding='utf-8'))
    parent=json.loads((R/'R357_VERIFICATION.json').read_text(encoding='utf-8'))
    current=json.loads((R/'R358_PILOT_CONFUSABLE_REGRESSION.json').read_text(encoding='utf-8'))
    inp=json.loads((R/'R358_PILOT_CONFUSABLE_INPUT.json').read_text(encoding='utf-8'))
    checks={
      'R357_security_fix_and_historic_browser_replay':parent['ok'] and jobs['R357_security_and_browser_regressions']['exit_code']==0,
      'R357_11_security_tests_still_pass':sec['ok'] and len(sec['checks'])==11 and all(sec['checks'].values()),
      'all_8794_R357_parent_files_preserved':len(manifest)==8794 and not bad,
      'security_patched_index_preserved':sha(R/'index.html')==parent['index_test_updated_sha256'] and 'escapeManualHtmlR357' in (R/'index.html').read_text(encoding='utf-8'),
      'R358_full_browser_test_passes':jobs['R358_full_130_reference_browser_regression']['exit_code']==0 and current['ok'],
      '130_ambiguous_refs_with_source_hash':len(set(inp['references']))==inp['references_count']==130 and len(inp['source_sha256'])==64,
      'no_unsafe_manual_pilot_references':not current['unsafe_results'] and current['tested_references']==130,
      'coverage_gap_observed':len(current['not_found_in_pilot'])==130 and not current['found_in_pilot'],
      'new_10_browser_invariants':len(current['checks'])==10 and all(current['checks'].values()),
      'unchanged_test_engine_R156':current['source_sha256']['index.html']==sha(R/'index.html') and 'V2.28 TEST R156' in (R/'index.html').read_text(encoding='utf-8')[:500],
      'OCR_offline_and_Samsung_not_certified':current['OCR_offline_certified'] is False and current['samsung_verified'] is False,
      'V2_27_stable_not_promoted':parent['stable_V2_27_modified'] is False and parent['R305_rule_changed'] is False,
    }
    out={'schema':'bres-r358-verification-v1','milestone':'R358','parent':'R357','checks':checks,
         'jobs':jobs,'parent_files':len(manifest),'parent_hash_mismatches':bad,'ok':all(checks.values())}
    (R/'R358_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R358_VERIFICATION.txt').write_text('R358 '+('PASS' if out['ok'] else 'FAIL')+'\n'+
        '\n'.join(('PASS ' if b else 'FAIL ')+name for name,b in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'parent_files':len(manifest),'unsafe':len(current['unsafe_results'])}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())