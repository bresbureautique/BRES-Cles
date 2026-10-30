#!/usr/bin/env python3
"""R364 V2.28 TEST checkpoint: exact-parent patch, 18 offline browser checks,
prior fail-closed regression replays, and immutable OCR/decision engine.
No claim of real Samsung/OCR verification.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,shutil,tempfile,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
from r364_ocr_preflight_export_patch import patch,EXPECTED_R363_INDEX_SHA
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    old={name:digest for digest,name in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R363.sha256').read_text(encoding='utf-8').splitlines())}
    changes=sorted(n for n,d in old.items() if not (R/n).is_file() or sha(R/n)!=d)
    with zipfile.ZipFile('/mnt/data/bres_r363_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R363.zip') as z:
        old_index=z.read('app/index.html')
    run=subprocess.run([sys.executable,str(R/'r364_ocr_preflight_export_regression.py')],cwd=R,capture_output=True,text=True,timeout=100,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    new=json.loads((R/'R364_OCR_PREFLIGHT_REGRESSION.json').read_text(encoding='utf-8'))
    previous=[
       ('r363_ocr_readiness_collision_regression.py','R363_OCR_COLLISION_REGRESSION.json',14,['R363_COLLISION_TEST_ONLY_FIXTURE.json']),
       ('r362_samsung_autonomous_launcher_regression.py','R362_SAMSUNG_LAUNCHER_REGRESSION.json',13,['BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','device_benchmark_r336.html','r331-device-benchmark.js']),
       ('r361_thickness_staleness_regression.py','R361_THICKNESS_STALENESS_REGRESSION.json',15,[]),
       ('r360_stale_feedback_regression.py','R360_STALE_FEEDBACK_REGRESSION.json',16,[]),
       ('r359_manual_state_transition_regression.py','R359_MANUAL_STATE_REGRESSION.json',14,[]),
       ('r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_REGRESSION.json',10,['R358_PILOT_CONFUSABLE_INPUT.json']),
       ('r356_chromium_offline_smoke.py','R356_CHROMIUM_OFFLINE_SMOKE.json',10,['device_benchmark_r336.html','r331-device-benchmark.js']),
    ]
    replays={}
    if os.environ.get('BRES_R364_REUSE_VERIFIED_REPLAYS')=='1':
        preserved=json.loads((R/'R364_VERIFICATION.json').read_text(encoding='utf-8'))
        assert preserved['parent']=='R363' and preserved['changed_parent_files']==['index.html']
        assert len(preserved['replays'])==7 and all(x['ok'] and x['checks']==x['expected'] for x in preserved['replays'].values())
        assert new['source_sha256']['index']==sha(R/'index.html')
        replays=preserved['replays']
    else:
      with tempfile.TemporaryDirectory(prefix='bres-r364-smokes-') as tmp:
        for script,out_file,n,extra in previous:
            f=Path(tmp)/script.replace('.py','');f.mkdir()
            for x in [script,'index.html','v228-catalogue.js',*extra]:shutil.copyfile(R/x,f/x)
            p=subprocess.run([sys.executable,str(f/script)],cwd=f,capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            if not (f/out_file).exists():raise RuntimeError(f'No test report from {script}: {p.stdout[-250:]} / {p.stderr[-250:]}')
            data=json.loads((f/out_file).read_text(encoding='utf-8'))
            replays[script]={'ok':p.returncode==0 and data['ok'],'checks':len(data['checks']),'expected':n,'unsafe_results':len(data.get('unsafe_results',[])), 'tested_references':data.get('tested_references'), 'stderr':p.stderr[-200:]}
            print('REPLAY',script,replays[script]['ok'],len(data['checks']),flush=True)
    cat=json.loads((R.parent/'cat/CAT_R364_OCR_FOLD_AUDIT.json').read_text(encoding='utf-8'))
    html=(R/'index.html').read_text(encoding='utf-8')
    checks={
      'R363_index_parent_sha256_exact':hashlib.sha256(old_index).hexdigest()==EXPECTED_R363_INDEX_SHA==old['index.html'],
      'all_R363_parent_files_present':len(old)>8800 and all((R/name).is_file() for name in old),
      'only_index_modified_from_parent':changes==['index.html'],
      'patch_is_identical_to_source_replay':patch(old_index.decode('utf-8')).encode('utf-8')==(R/'index.html').read_bytes(),
      'R331_core_benchmark_unchanged':sha(R/'r331-device-benchmark.js')==old['r331-device-benchmark.js'],
      'R336_benchmark_unchanged':sha(R/'device_benchmark_r336.html')==old['device_benchmark_r336.html'],
      'R336_autonomous_unchanged':sha(R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html')==old['BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html'],
      'R305_OCR_rule_and_pilot_unchanged':sha(R/'v228-catalogue.js')==old['v228-catalogue.js'] and 'R305 : activation bornée' in html,
      'new_offline_18_checks_PASS':run.returncode==0 and new['ok'] and len(new['checks'])==18,
      'preflight_has_no_recognition_validation':not new['real_OCR_run'] and not new['physical_test'] and not new['claim_offline_certification'],
      'seven_prior_regression_replays_PASS':all(x['ok'] and x['checks']==x['expected'] for x in replays.values()),
      'prior_130_cases_without_unsafe_result':replays['r358_pilot_confusable_regression.py']['tested_references']==130 and replays['r358_pilot_confusable_regression.py']['unsafe_results']==0,
      'parent_732_text_collisions_still_fail_closed':len(json.loads((R/'R363_COLLISION_TEST_ONLY_FIXTURE.json').read_text())['references'])==732,
      'full_V3_catalogue_not_embedded':cat['ok'] and cat['canonical_reference_count']==5103 and 'catalogue/v3/catalog-01.js' not in html,
      'offline_dependency_gap_not_hidden':'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js' in html and 'coldOfflineOcrCertified:false' in html,
      'V227_still_stable_V228_only_test': 'V2.27 reste la version stable' in html and '<title>BRES Clés V2.28 TEST R156</title>' in html,
    }
    report={'schema':'bres-r364-checkpoint-verification-v1','milestone':'R364','parent':'R363','parent_file_count':len(old),'changed_parent_files':changes,'checks':checks,'replays':replays,'new_browser_test':{'returncode':run.returncode,'stdout':run.stdout.strip()},'ok':all(checks.values()),'limitations':['Cold offline Tesseract worker/WASM/traineddata not bundled','R336 Android local screenshot PASS; raw JSON receipt absent','No real known key validation or manufacturer proof','No V2.27 deployment, no GitHub main change']}
    (R/'R364_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R364_VERIFICATION.txt').write_text(f'R364 {"PASS" if report["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} checks; 18 new Chromium, seven replay suites.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'parent_files':len(old),'replay_count':len(replays)},ensure_ascii=False))
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(verify())