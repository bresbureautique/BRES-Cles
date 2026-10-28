#!/usr/bin/env python3
"""Verify R362 derived from immutable R361 + replay UI tests on isolated copies."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from r362_make_standalone_download import patch,PARENT_INDEX_SHA,standalone
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R361.sha256').read_text().splitlines())}
    old_files_modified=sorted(n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h)
    original_pilot=old['v228-catalogue.js'];original_engine=old['r331-device-benchmark.js'];original_benchmark=old['device_benchmark_r336.html']
    browser=subprocess.run([sys.executable,str(R/'r362_samsung_autonomous_launcher_regression.py')],capture_output=True,text=True,cwd=R,timeout=150)
    regression=json.loads((R/'R362_SAMSUNG_LAUNCHER_REGRESSION.json').read_text())
    replays={}
    with tempfile.TemporaryDirectory(prefix='bres-r362-replay-') as d:
        tmp=Path(d)
        # Regenerate R362 index from the exact R361 version by reversing only known edits.
        # R361 index is obtained from R361 archive by its expected SHA, not guessed.
        import zipfile
        parent_zip=Path('/mnt/data/bres_r361_verified_library/BRES_Cles_Mobile_V2_28_CHECKPOINT_R361.zip')
        with zipfile.ZipFile(parent_zip) as z:parent=z.read('app/index.html')
        fresh=(R/'index.html').read_bytes()
        parent_sha=hashlib.sha256(parent).hexdigest()
        replay_expected=patch(parent.decode('utf-8')).encode('utf-8')
        replay_matches=(replay_expected==fresh)
        for script,output in [
          ('r361_thickness_staleness_regression.py','R361_THICKNESS_STALENESS_REGRESSION.json'),
          ('r360_stale_feedback_regression.py','R360_STALE_FEEDBACK_REGRESSION.json'),
          ('r359_manual_state_transition_regression.py','R359_MANUAL_STATE_REGRESSION.json'),
          ('r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_REGRESSION.json')]:
            t=tmp/script.replace('.py','');t.mkdir()
            files=[script,'index.html','v228-catalogue.js']
            if 'r358' in script:files.append('R358_PILOT_CONFUSABLE_INPUT.json')
            for f in files:shutil.copyfile(R/f,t/f)
            r=subprocess.run([sys.executable,str(t/script)],cwd=t,capture_output=True,text=True,timeout=150,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            if not (t/output).exists():raise RuntimeError(f'{script} failed to produce {output}: {r.stderr[-500:]}')
            result=json.loads((t/output).read_text(encoding='utf-8'))
            replays[script]={'returncode':r.returncode,'ok':result['ok'],'checks':len(result['checks']),
                             'tested':result.get('tested_references'),'unsafe':len(result.get('unsafe_results',[])),
                             'stdout':r.stdout[-400:],'stderr':r.stderr[-400:]}
    checks={
       'R361_all_8831_manifest_entries_present':len(old)==8831 and all((R/n).is_file() for n in old),
       'only_R361_index_modified':old_files_modified==['index.html'],
       'parent_R361_index_hash_exact':parent_sha==PARENT_INDEX_SHA==old['index.html'],
       'R362_patch_replayed_identically_from_R361':replay_matches,
       'R331_engine_bytes_unmodified':sha(R/'r331-device-benchmark.js')==original_engine,
       'original_R336_html_unmodified':sha(R/'device_benchmark_r336.html')==original_benchmark,
       'pilot_catalogue_JS_unchanged':sha(R/'v228-catalogue.js')==original_pilot,
       'autonomous_file_has_exact_expected_44345_bytes':len(standalone())==44345 and (R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html').read_bytes()==standalone(),
       'Chromium_R362_13_checks_PASS':browser.returncode==0 and regression['ok'] and len(regression['checks'])==13,
       'prior_R361_15_checks_replayed':replays['r361_thickness_staleness_regression.py']['ok'] and replays['r361_thickness_staleness_regression.py']['checks']==15 and replays['r361_thickness_staleness_regression.py']['returncode']==0,
       'prior_R360_16_checks_replayed':replays['r360_stale_feedback_regression.py']['ok'] and replays['r360_stale_feedback_regression.py']['checks']==16 and replays['r360_stale_feedback_regression.py']['returncode']==0,
       'prior_R359_14_checks_replayed':replays['r359_manual_state_transition_regression.py']['ok'] and replays['r359_manual_state_transition_regression.py']['checks']==14 and replays['r359_manual_state_transition_regression.py']['returncode']==0,
       'prior_R358_130_no_false_acceptances':replays['r358_pilot_confusable_regression.py']['ok'] and replays['r358_pilot_confusable_regression.py']['tested']==130 and replays['r358_pilot_confusable_regression.py']['unsafe']==0 and replays['r358_pilot_confusable_regression.py']['returncode']==0,
       'prior_R361_results_untouched':sha(R/'R361_THICKNESS_STALENESS_REGRESSION.json')==old['R361_THICKNESS_STALENESS_REGRESSION.json'],
       'no_page_errors_or_unhandled_exception':not regression['errors'],
       'stable_V227_not_promoted_and_OCR_R305_not_changed':('V2.27 reste la version stable' in (R/'index.html').read_text() and 'V2.28 TEST R156' in (R/'index.html').read_text() and regression['physical_Samsung_download_retest'] is False),
    }
    obj={'schema':'bres-r362-verification-v1','milestone':'R362','parent':'R361',
         'parent_changed_files':old_files_modified,'parent_manifest_paths':len(old),
         'sha256':{'index_R361':parent_sha,'index_R362':sha(R/'index.html'),'autonomous_R336':sha(R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html')},
         'browser':{'returncode':browser.returncode,'output':browser.stdout[-550:]},'replays':replays,
         'checks':checks,'ok':all(checks.values()),
         'scope':'V2.28 separate test launcher only; no V2.27 main modification',
         'not_certified':['Samsung download from new launcher not re-tested physically','OCR fully offline','physical reference/manufacturer']}
    (R/'R362_VERIFICATION.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R362_VERIFICATION.txt').write_text(f'R362 {"PASS" if obj["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} tests\n'+'\n'.join(('PASS ' if ok else 'FAIL ')+k for k,ok in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':obj['ok'],'checks':len(checks),'failed':[x for x,v in checks.items() if not v],'regressions':replays},ensure_ascii=False))
    return 0 if obj['ok'] else 1
if __name__=='__main__':raise SystemExit(run())