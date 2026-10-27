#!/usr/bin/env python3
"""R361 source, patch replay, Chromium and parent regression verification.

R360 historic test result files are immutable; regressions run in temp folders.
"""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from r361_apply_thickness_patch import BEFORE,AFTER,PARENT_SHA256,patch
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R360.sha256').read_text().splitlines())}
    changed=sorted(n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h)
    fresh=(R/'index.html').read_text(encoding='utf-8')
    initial=hashlib.sha256(fresh.replace(AFTER,BEFORE,1).encode('utf-8')).hexdigest() if fresh.count(AFTER)==1 else None
    outcomes={}
    with tempfile.TemporaryDirectory(prefix='bres-r361-verified-replay-') as temporary:
        t=Path(temporary)
        parent=t/'index.html'
        parent.write_text(fresh.replace(AFTER,BEFORE,1),encoding='utf-8')
        actual_patch_sha=patch(parent)
        for script,output in [('r360_stale_feedback_regression.py','R360_STALE_FEEDBACK_REGRESSION.json'),
                              ('r359_manual_state_transition_regression.py','R359_MANUAL_STATE_REGRESSION.json'),
                              ('r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_REGRESSION.json')]:
            test_dir=t/script.replace('.py','');test_dir.mkdir()
            for n in [script,'index.html','v228-catalogue.js']:
                shutil.copyfile(R/n,test_dir/n)
            if 'r358' in script:shutil.copyfile(R/'R358_PILOT_CONFUSABLE_INPUT.json',test_dir/'R358_PILOT_CONFUSABLE_INPUT.json')
            run_test=subprocess.run([sys.executable,str(test_dir/script)],cwd=test_dir,capture_output=True,text=True,
                                   timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            result=json.loads((test_dir/output).read_text(encoding='utf-8'))
            outcomes[script]={'exit':run_test.returncode,'ok':result['ok'],'checks':len(result['checks']),
                             'tested':result.get('tested_references'),'unsafe':len(result.get('unsafe_results',[])),
                             'stdout':run_test.stdout[-280:],'stderr':run_test.stderr[-300:]}
    # R361 new test is executed on the current source; only its own files are updated.
    current=subprocess.run([sys.executable,str(R/'r361_thickness_staleness_regression.py')],cwd=R,text=True,capture_output=True,
                           timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    report=json.loads((R/'R361_THICKNESS_STALENESS_REGRESSION.json').read_text(encoding='utf-8'))
    checks={
     'parent_manifest_8821_files_only_intended_index_changed':len(old)==8821 and changed==['index.html'],
     'parent_index_patch_reversible_to_R360_SHA':initial==old['index.html']==PARENT_SHA256 and actual_patch_sha==sha(R/'index.html'),
     'R360_pilot_catalogue_js_unchanged':sha(R/'v228-catalogue.js')==old['v228-catalogue.js'],
     'R361_source_contains_single_guard':fresh.count(AFTER)==1 and fresh.count('R361: an edited physical measurement')==1,
     'R361_browser_15_checks_pass':current.returncode==0 and report['ok'] and len(report['checks'])==15,
     'R361_passed_source_hashes_current':report['sha256']=={n:sha(R/n) for n in ('index.html','v228-catalogue.js')},
     'R360_16_browser_checks_replayed_from_isolated_workdir':outcomes['r360_stale_feedback_regression.py']['ok'] and outcomes['r360_stale_feedback_regression.py']['checks']==16 and outcomes['r360_stale_feedback_regression.py']['exit']==0,
     'R359_14_browser_checks_replayed_from_isolated_workdir':outcomes['r359_manual_state_transition_regression.py']['ok'] and outcomes['r359_manual_state_transition_regression.py']['checks']==14 and outcomes['r359_manual_state_transition_regression.py']['exit']==0,
     'R358_130_confusable_input_cases_no_false_validation':outcomes['r358_pilot_confusable_regression.py']['ok'] and outcomes['r358_pilot_confusable_regression.py']['tested']==130 and outcomes['r358_pilot_confusable_regression.py']['unsafe']==0 and outcomes['r358_pilot_confusable_regression.py']['exit']==0,
     'parent_old_result_unchanged':sha(R/'R360_VERIFICATION.json')==old['R360_VERIFICATION.json'] and sha(R/'R360_STALE_FEEDBACK_REGRESSION.json')==old['R360_STALE_FEEDBACK_REGRESSION.json'],
     'stable_and_OCR_rules_not_activated':('V2.28 TEST R156' in fresh[:600] and not report['physical_samsung_tested'] and not report['ocr_offline_certified'] and not report['catalogue_v3_integrated']),
     'no_browser_page_errors':not report['page_errors'] and not report['dialogs'],
    }
    result={'schema':'bres-r361-verification-v1','milestone':'R361','parent':'R360',
        'changed_parent_paths':changed,'sha256':{'index_R361':sha(R/'index.html'),'index_R360':old['index.html'],'pilot':sha(R/'v228-catalogue.js')},
        'replayed':outcomes,'current_test_stdout':current.stdout,'current_test_stderr':current.stderr,
        'checks':checks,'ok':all(checks.values())}
    (R/'R361_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R361_VERIFICATION.txt').write_text(f"R361 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'changed_parent_paths':changed,'parent_replays':outcomes,'current':current.stdout.strip()},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())