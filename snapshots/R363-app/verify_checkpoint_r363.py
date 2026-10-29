#!/usr/bin/env python3
"""Check additive R363 V2.28 TEST against the bit-exact R362 archive.

Replays offline Chromium tests on isolated copies to keep previous artefacts
unmodified. All physical and cold-offline OCR assertions remain unclaimed.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,shutil,tempfile,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
from r363_ocr_dependency_status_patch import patch,EXPECTED_R362_INDEX_SHA
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={name:digest for digest,name in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R362.sha256').read_text(encoding='utf-8').splitlines())}
    changes=sorted(name for name,dig in old.items() if not (R/name).is_file() or sha(R/name)!=dig)
    fixture=json.loads((R/'R363_COLLISION_TEST_ONLY_FIXTURE.json').read_text(encoding='utf-8'))
    parent_zip=Path('/mnt/data/bres_r362_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R362.zip')
    with zipfile.ZipFile(parent_zip) as z:old_html=z.read('app/index.html')
    print('START R363 test',flush=True)
    proc=subprocess.run([sys.executable,str(R/'r363_ocr_readiness_collision_regression.py')],cwd=R,capture_output=True,text=True,timeout=160,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    new=json.loads((R/'R363_OCR_COLLISION_REGRESSION.json').read_text(encoding='utf-8'))
    oldscripts=[
      ('r362_samsung_autonomous_launcher_regression.py','R362_SAMSUNG_LAUNCHER_REGRESSION.json',13),
      ('r361_thickness_staleness_regression.py','R361_THICKNESS_STALENESS_REGRESSION.json',15),
      ('r360_stale_feedback_regression.py','R360_STALE_FEEDBACK_REGRESSION.json',16),
      ('r359_manual_state_transition_regression.py','R359_MANUAL_STATE_REGRESSION.json',14),
      ('r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_REGRESSION.json',10),
      ('r356_chromium_offline_smoke.py','R356_CHROMIUM_OFFLINE_SMOKE.json',10),
    ]
    replays={}
    with tempfile.TemporaryDirectory(prefix='bres-r363-replays-') as temp:
        root=Path(temp)
        for script,output,expected in oldscripts:
            print('START replay',script,flush=True)
            folder=root/script.replace('.py','');folder.mkdir()
            required=[script,'index.html','v228-catalogue.js']
            if script.startswith('r362_'):
                required+=['BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','device_benchmark_r336.html','r331-device-benchmark.js']
            if script.startswith('r358_'):required+=['R358_PILOT_CONFUSABLE_INPUT.json']
            if script.startswith('r356_'):required+=['device_benchmark_r336.html','r331-device-benchmark.js']
            for f in required:shutil.copyfile(R/f,folder/f)
            p=subprocess.run([sys.executable,str(folder/script)],cwd=folder,capture_output=True,text=True,timeout=150,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            if not (folder/output).exists():raise RuntimeError(f'{script} failed: {p.stdout[-300:]} {p.stderr[-300:]}')
            print('END replay',script, p.returncode, p.stdout[-150:],p.stderr[-250:],flush=True)
            d=json.loads((folder/output).read_text(encoding='utf-8'))
            replays[script]={'ok':d['ok'] and p.returncode==0,'checks':len(d['checks']), 'expected':expected,
                 'tested':d.get('tested_references'),'unsafe':len(d.get('unsafe_results',[])),
                 'stderr':p.stderr[-300:]}
    # The CAT-R363 data is test-only, its full V3 database is never embedded in index.html.
    cat=R.parent/'cat/CAT_R363_PAIR_REVIEW_LEDGER.json'
    cross=json.loads(cat.read_text()) if cat.exists() else None
    checks={
      'R362_archive_sha_matches_parent_manifest':hashlib.sha256(old_html).hexdigest()==EXPECTED_R362_INDEX_SHA==old['index.html'],
      'R362_8843_parent_files_present':len(old)==8843 and all((R/name).is_file() for name in old),
      'parent_files_only_index_changed':changes==['index.html'],
      'R363_UI_patch_exact_deterministic':patch(old_html.decode('utf-8')).encode('utf-8')==(R/'index.html').read_bytes(),
      'R331_engine_preserved':sha(R/'r331-device-benchmark.js')==old['r331-device-benchmark.js'],
      'R336_benchmark_unchanged':sha(R/'device_benchmark_r336.html')==old['device_benchmark_r336.html'],
      'R336_autonomous_exact_unchanged':sha(R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html')==old['BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html'],
      'pilot_unchanged':sha(R/'v228-catalogue.js')==old['v228-catalogue.js'],
      'browser_14_checks_PASS':proc.returncode==0 and new['ok'] and len(new['checks'])==14,
      'browser_732_references_without_physical_validation':new['evidence']['all_catalogue_collision_refs']['total']==732 and new['evidence']['all_catalogue_collision_refs']['badCount']==0,
      'catalogue_393_pair_fixture_not_integrated':len(fixture['pairs'])==393 and len(fixture['references'])==732 and fixture['no_auto_identification'],
      'independent_CAT_R363_fixture_exact':cross is not None and fixture['source_sha256']==sha(cat) and fixture['references']==cross['all_test_reference_strings'] and fixture['pairs']==[[x['reference_a'],x['reference_b']] for x in cross['pairs']],
      'prior_browser_replays_pass':all(v['ok'] and v['checks']==v['expected'] for v in replays.values()),
      '130_prior_cases_still_safe':replays['r358_pilot_confusable_regression.py']['tested']==130 and replays['r358_pilot_confusable_regression.py']['unsafe']==0,
      'no_active_OCR_rule_or_catalogue_change':not new['full_catalogue_activated'] and not new['cold_offline_OCR_certified'] and not new['physical_device_used'],
      'old_outputs_unchanged':sha(R/'R362_VERIFICATION.json')==old['R362_VERIFICATION.json'],
    }
    out={'schema':'bres-r363-app-verification-v1','milestone':'R363','parent':'R362',
      'parent_changed_files':changes,'parent_files':len(old),'R363_parent_index_sha256':sha(R/'index.html'),
      'checks':checks,'replays':replays,'new_test':{'returncode':proc.returncode,'stdout':proc.stdout.strip()},
      'safe_state':'V2.27 remains stable, V2.28 test R156 unchanged engine; no V3 activation',
      'limitations':['Samsung physical benchmark R336 screenshot PASS 192/192, JSON receipt still absent',
          'No Tesseract worker/wasm/traineddata offline bundle; cannot claim OCR cold offline',
          'Textual collisions are not actual physical key matches'],
      'ok':all(checks.values())}
    (R/'R363_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R363_VERIFICATION.txt').write_text(f'R363 {"PASS" if out["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if x else 'FAIL ')+k for k,x in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v], 'replays':replays},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(run())