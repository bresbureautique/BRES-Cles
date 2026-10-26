#!/usr/bin/env python3
"""R360 additive verification and historical replay without changing R359 evidence."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R359.sha256').read_text(encoding='utf-8').splitlines())}
    wrong=sorted(n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h)
    fresh=(R/'index.html').read_text(encoding='utf-8')
    reverted=fresh
    for key,message in (
      ('manualRef','Référence modifiée : ancienne correspondance annulée. Vérifiez à nouveau.'),
      ('manualBrand','Marque modifiée : ancienne correspondance annulée. Vérifiez à nouveau.'),
    ):
      addition=('  // R360: cancel the previous green manual lookup feedback synchronously.\n'
                '  el("manualRefStatus").className="status warn";\n'
                f'  el("manualRefStatus").textContent="{message}";\n')
      assert reverted.count(addition)==1,key
      reverted=reverted.replace(addition,'',1)
    restored_hash=hashlib.sha256(reverted.encode('utf-8')).hexdigest()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def launch(path,timeout=150):return subprocess.run([sys.executable,str(path)],cwd=path.parent,text=True,capture_output=True,env=env,timeout=timeout)
    new_test=launch(R/'r360_stale_feedback_regression.py')
    actual=json.loads((R/'R360_STALE_FEEDBACK_REGRESSION.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='bres-r360-replay-') as td:
      t=Path(td)
      for n in ['index.html','v228-catalogue.js','r359_manual_state_transition_regression.py','r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_INPUT.json']:
        shutil.copy2(R/n,t/n)
      replay359=launch(t/'r359_manual_state_transition_regression.py')
      replay358=launch(t/'r358_pilot_confusable_regression.py')
      prev359=json.loads((t/'R359_MANUAL_STATE_REGRESSION.json').read_text(encoding='utf-8'))
      prev358=json.loads((t/'R358_PILOT_CONFUSABLE_REGRESSION.json').read_text(encoding='utf-8'))
    checks={
      'all_8811_R359_files_verified_except_intended_index_change':len(old)==8811 and wrong==['index.html'],
      'patched_index_reversible_to_exact_R359_sha256':restored_hash==old['index.html'],
      'unchanged_R359_pilot_catalogue_source':sha(R/'v228-catalogue.js')==old['v228-catalogue.js'],
      'only_two_event_handlers_changed':fresh.count('R360: cancel the previous green manual lookup feedback synchronously.')==2,
      'browser_R360_success':new_test.returncode==0 and actual['ok'],
      'sixteen_new_browser_checks_pass':len(actual['checks'])==16 and all(actual['checks'].values()),
      'R359_14_checks_replayed_on_patched_runtime':replay359.returncode==0 and prev359['ok'] and len(prev359['checks'])==14,
      'R358_130_confusable_cases_replayed':replay358.returncode==0 and prev358['ok'] and prev358['tested_references']==130 and len(prev358['unsafe_results'])==0,
      'existing_R359_outputs_preserved':sha(R/'R359_VERIFICATION.json')==old['R359_VERIFICATION.json'],
      'source_hashes_match_current_runtime':actual['source_sha256']=={n:sha(R/n) for n in ('index.html','v228-catalogue.js')},
      'historical_R305_and_engine_title_preserved':('BRES Clés V2.28 TEST R156' in fresh[:500] and sha(R/'v228-catalogue.js')==old['v228-catalogue.js']),
      'no_physical_or_offline_OCR_certification':not any(actual[x] for x in ('samsung_real_tested','ocr_offline_certified','catalogue_v3_integrated')),
    }
    report={'schema':'bres-r360-verification-v1','milestone':'R360','parent':'R359',
       'intentional_modified_parent_paths':wrong,'source_index_sha256':sha(R/'index.html'),'parent_index_sha256':old['index.html'],
       'checks':checks,'replayed':{'R359':{'exit':replay359.returncode,'stdout':replay359.stdout[-400:]},
                                 'R358':{'exit':replay358.returncode,'stdout':replay358.stdout[-400:]}},
       'current_test_stdout':new_test.stdout[-500:],'current_test_stderr':new_test.stderr[-500:],'ok':all(checks.values())}
    (R/'R360_VERIFICATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'R360_VERIFICATION.txt').write_text('R360 '+('PASS' if report['ok'] else 'FAIL')+'\n'+
       '\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'checks':len(checks),'R359_replay':replay359.returncode,'R358_replay':replay358.returncode,'parent_wrong':wrong}))
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(run())