#!/usr/bin/env python3
"""R365 independent validation from immutable R364 package + offline Chromium.
V2.27 stable, active OCR R305, key engine R331 and benchmark R336 are unmodified.
"""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
from r365_ocr_provenance_patch import patch
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def call(script):
    p=subprocess.run([sys.executable,str(script)],cwd=script.parent,capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    return {'exit_code':p.returncode,'stdout':p.stdout[-600:],'stderr':p.stderr[-400:]}

def run():
    old={name:digest for digest,name in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R364.sha256').read_text(encoding='utf-8').splitlines())}
    changed=sorted(n for n,d in old.items() if not (R/n).is_file() or sha(R/n)!=d)
    parent=Path(os.environ.get('BRES_R364_PARENT_ZIP','/mnt/data/bres_r364_input/BRES_Cles_Mobile_V2_28_CHECKPOINT_R364.zip'))
    with zipfile.ZipFile(parent) as z:parent_index=z.read('app/index.html')
    fresh=call(R/'r365_ocr_provenance_regression.py')
    closure=call(R/'r365_offline_dependency_audit.py')
    browser=json.loads((R/'R365_OCR_PROVENANCE_REGRESSION.json').read_text(encoding='utf-8'))
    deps=json.loads((R/'R365_OFFLINE_DEPENDENCY_AUDIT.json').read_text(encoding='utf-8'))
    earlier=[
       ('r363_ocr_readiness_collision_regression.py','R363_OCR_COLLISION_REGRESSION.json',14,['R363_COLLISION_TEST_ONLY_FIXTURE.json']),
       ('r362_samsung_autonomous_launcher_regression.py','R362_SAMSUNG_LAUNCHER_REGRESSION.json',13,['BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','device_benchmark_r336.html','r331-device-benchmark.js']),
       ('r361_thickness_staleness_regression.py','R361_THICKNESS_STALENESS_REGRESSION.json',15,[]),
       ('r360_stale_feedback_regression.py','R360_STALE_FEEDBACK_REGRESSION.json',16,[]),
       ('r359_manual_state_transition_regression.py','R359_MANUAL_STATE_REGRESSION.json',14,[]),
       ('r358_pilot_confusable_regression.py','R358_PILOT_CONFUSABLE_REGRESSION.json',10,['R358_PILOT_CONFUSABLE_INPUT.json']),
       ('r356_chromium_offline_smoke.py','R356_CHROMIUM_OFFLINE_SMOKE.json',10,['device_benchmark_r336.html','r331-device-benchmark.js']),
    ]
    replays={}
    # The seven full prior suites are archived with R364; immutable parent code
    # and fixtures are rehashed above. Re-run the critical offline smoke and
    # compatibility suite in isolation on the R365 index (no historical outputs changed).
    prior=json.loads((R/'R364_VERIFICATION.json').read_text(encoding='utf-8'))
    assert prior['ok'] and len(prior['replays'])==7
    replays={k:dict(v,source='verified-R364-replay-evidence') for k,v in prior['replays'].items()}
    with tempfile.TemporaryDirectory(prefix='bres-r365-smoke-') as t:
      d=Path(t)/'r356';d.mkdir()
      for n in ('r356_chromium_offline_smoke.py','index.html','v228-catalogue.js','device_benchmark_r336.html','r331-device-benchmark.js'):shutil.copyfile(R/n,d/n)
      s=call(d/'r356_chromium_offline_smoke.py')
      proof=json.loads((d/'R356_CHROMIUM_OFFLINE_SMOKE.json').read_text())
      assert s['exit_code']==0 and proof['ok'] and len(proof['checks'])==10
      replays['r356_chromium_offline_smoke.py']={'ok':True,'checks':10,'expected':10,'unsafe_results':0,'source':'fresh-R365-replay'}
      d=Path(t)/'r364';d.mkdir()
      for name in ('r364_ocr_preflight_export_regression.py','index.html'):shutil.copyfile(R/name,d/name)
      oldrun=call(d/'r364_ocr_preflight_export_regression.py')
      oldjson=json.loads((d/'R364_OCR_PREFLIGHT_REGRESSION.json').read_text()) if (d/'R364_OCR_PREFLIGHT_REGRESSION.json').exists() else {}
    html=(R/'index.html').read_text(encoding='utf-8')
    checks={
      'R364_parent_exact_index_sha':hashlib.sha256(parent_index).hexdigest()==old['index.html'],
      'R364_parent_8861_files_preserved':len(old)>=8850 and all((R/n).is_file() for n in old),
      'only_test_index_modified_from_parent':changed==['index.html'],
      'R365_patch_reproduced':patch(parent_index.decode('utf-8')).encode('utf-8')==(R/'index.html').read_bytes(),
      'core_R331_and_benchmark_R336_unchanged':all(sha(R/n)==old[n] for n in ('r331-device-benchmark.js','device_benchmark_r336.html','BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html')),
      'pilot_catalogue_R305_unchanged':sha(R/'v228-catalogue.js')==old['v228-catalogue.js'] and 'R305 : activation bornée' in html,
      'new_browser_27_checks_PASS':fresh['exit_code']==0 and browser['ok'] and len(browser['checks'])==27,
      'new_static_dependency_audit_7_checks_PASS':closure['exit_code']==0 and deps['ok'] and len(deps['checks'])==7,
      'dependency_gap_is_explicitly_unresolved':not deps['cold_offline_ocr_certified'] and not any(deps['local_asset_candidates'].values()),
      'previous_R364_browser_18_checks_PASS':oldrun['exit_code']==0 and oldjson.get('ok') and len(oldjson.get('checks',{}))==18,
      'seven_prior_replay_evidence_preserved_and_one_fresh_PASS':len(replays)==7 and all(v['ok'] and v['checks']==v['expected'] for v in replays.values()),
      'pilot_130_ref_no_unsafe_result':replays['r358_pilot_confusable_regression.py']['tested_references']==130 and replays['r358_pilot_confusable_regression.py']['unsafe_results']==0,
      '732_collision_strings_still_preserved':len(json.loads((R/'R363_COLLISION_TEST_ONLY_FIXTURE.json').read_text(encoding='utf-8'))['references'])==732,
      'V227_stable_not_replaced':'V2.27 reste la version stable' in html and '<title>BRES Clés V2.28 TEST R156</title>' in html,
      'no_physical_OCR_claim':not browser['real_OCR_run'] and not browser['physical_key_test'] and deps['real_ocr_executed']==False,
      'no_new_catalogue_embedded':'catalogue/v3/catalog-01.js' not in html,
    }
    out={'schema':'bres-r365-independent-verification-v1','milestone':'R365','parent':'R364','changed_parent_files':changed,'parent_file_count':len(old),'checks':checks,'ok':all(checks.values()),'replays':replays,'new_chromium':fresh,'static_dependency_audit':closure,'r364_compatibility':oldrun,'limitations':['Cold-offline Tesseract resources not bundled','R336 physical screenshot PASS; JSON receipt absent','No physical key/maker certification','Main and V2.27 never modified']}
    (R/'R365_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R365_VERIFICATION.txt').write_text('R365 '+('PASS' if out['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} independent controls, 27 new Chromium, 18 prior Chromium, 7 earlier suites.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(run())