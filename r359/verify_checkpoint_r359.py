#!/usr/bin/env python3
"""R359 additive gate: R358 source and evidence immutable, positive manual-state browser test."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    manifest=(R/'SNAPSHOT_MANIFEST_R358.sha256').read_text(encoding='utf-8').splitlines()
    mismatches=[name for dig,name in (ln.split('  ',1) for ln in manifest)
                if not (R/name).is_file() or sha(R/name)!=dig]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,str(R/'r359_manual_state_transition_regression.py')],
                     cwd=R,text=True,capture_output=True,env=env,timeout=100)
    current=json.loads((R/'R359_MANUAL_STATE_REGRESSION.json').read_text(encoding='utf-8'))
    parent=json.loads((R/'R358_VERIFICATION.json').read_text(encoding='utf-8'))
    old=json.loads((R/'R358_PILOT_CONFUSABLE_REGRESSION.json').read_text(encoding='utf-8'))
    checks={
      'all_8803_parent_manifest_entries_unchanged':len(manifest)==8803 and not mismatches,
      'R358_12_checks_still_pass':parent['ok'] and len(parent['checks'])==12 and all(parent['checks'].values()),
      'R358_130_confusable_safe_failures_unchanged':old['ok'] and len(old['not_found_in_pilot'])==130 and not old['unsafe_results'],
      'positive_negative_browser_exit_pass':p.returncode==0 and current['ok'],
      '14_new_browser_checks_pass':len(current['checks'])==14 and all(current['checks'].values()),
      'actual_pilot_source_hashes_match':current['source_sha256']=={n:sha(R/n) for n in ('index.html','v228-catalogue.js')},
      'no_HTML_execution_and_state_invalidation':current['checks']['HTML_payload_never_activates_or_validates'] and current['checks']['unknown_VI2_clears_prior_qualified_state'],
      'engine_R156_and_OCR_R305_not_modified':'BRES Clés V2.28 TEST R156' in (R/'index.html').read_text(encoding='utf-8')[:500] and not mismatches,
      'no_real_samsung_or_offline_claim':not current['samsung_real_pass'] and not current['offline_OCR_certified'],
      'CAT_V3_not_implicitly_integrated':not current['catalogue_V3_imported'] and current['checks']['catalogue_V3_confusable_not_silently_imported'],
    }
    out={'schema':'bres-r359-verification-v1','milestone':'R359','parent':'R358',
         'checks':checks,'parent_entries':len(manifest),'parent_mismatches':mismatches,
         'job':{'exit_code':p.returncode,'stdout':p.stdout[-700:],'stderr':p.stderr[-700:]},'ok':all(checks.values())}
    (R/'R359_VERIFICATION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'R359_VERIFICATION.txt').write_text('R359 '+('PASS' if out['ok'] else 'FAIL')+'\n'+
      '\n'.join(('PASS' if value else 'FAIL')+' '+key for key,value in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'parent_mismatch':len(mismatches)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())