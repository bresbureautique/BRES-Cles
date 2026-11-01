#!/usr/bin/env python3
"""R366 verifier: exact R365 parent, new 57-check Chromium, fresh offline smoke."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from r366_ocr_origin_scheme_patch import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PARENT=Path('/mnt/data/bres_r365_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R365.zip')

def main():
    parent={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_R365.sha256').read_text().splitlines())}
    changed=sorted(n for n,h in parent.items() if not (R/n).is_file() or H(R/n)!=h)
    with zipfile.ZipFile(PARENT) as z:old_index=z.read('app/index.html')
    regression=json.loads((R/'R366_OCR_ORIGIN_REGRESSION.json').read_text())
    old=json.loads((R/'R365_VERIFICATION.json').read_text())
    deps=json.loads((R/'R365_OFFLINE_DEPENDENCY_AUDIT.json').read_text())
    # A small, isolated fresh execution using R366 index, same pilot and R336 engine.
    with tempfile.TemporaryDirectory(prefix='bres-r366-smoke-') as t:
        d=Path(t)
        for n in ('r356_chromium_offline_smoke.py','index.html','v228-catalogue.js','device_benchmark_r336.html','r331-device-benchmark.js'):
            shutil.copyfile(R/n,d/n)
        run=subprocess.run([sys.executable,str(d/'r356_chromium_offline_smoke.py')],cwd=d,capture_output=True,text=True,timeout=90,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        smoke=json.loads((d/'R356_CHROMIUM_OFFLINE_SMOKE.json').read_text()) if (d/'R356_CHROMIUM_OFFLINE_SMOKE.json').is_file() else {}
    html=(R/'index.html').read_text()
    checks={
      'all_8873_R365_files_preserved':len(parent)>=8850 and all((R/n).is_file() for n in parent),
      'only_index_changed_R365_to_R366':changed==['index.html'],
      'parent_R365_index_sha_matches_ZIP':hashlib.sha256(old_index).hexdigest()==parent['index.html'],
      'exact_R366_patch_reproduced':patch(old_index.decode('utf-8')).encode('utf-8')==(R/'index.html').read_bytes(),
      'R365_verified_baseline':old['ok'],
      'R366_57_new_chromium_checks':regression['ok'] and len(regression['checks'])==57,
      'fresh_R356_10_chromium_smoke':run.returncode==0 and smoke.get('ok')==True and len(smoke.get('checks',{}))==10,
      'R331_and_R336_identical_to_R365':all(H(R/n)==parent[n] for n in ('r331-device-benchmark.js','device_benchmark_r336.html','BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html')),
      'R305_and_pilot_catalogue_unchanged':H(R/'v228-catalogue.js')==parent['v228-catalogue.js'] and 'R305 : activation bornée' in html,
      'V227_stable_not_replaced':'V2.27 reste la version stable' in html and '<title>BRES Clés V2.28 TEST R156</title>' in html,
      'R363_collision_strings_preserved_732':len(json.loads((R/'R363_COLLISION_TEST_ONLY_FIXTURE.json').read_text())['references'])==732,
      'R358_130_reference_proof_preserved':json.loads((R/'R358_PILOT_CONFUSABLE_REGRESSION.json').read_text())['ok'],
      'no_false_claim_of_offline_OCR':not deps['cold_offline_ocr_certified'] and not any(deps['local_asset_candidates'].values()),
      'no_auto_merge_of_catalogue_v3':'catalogue/v3/catalog-01.js' not in html
    }
    out={'schema':'bres-r366-independent-verification-v1','checkpoint':'R366','date':'2026-11-01','parent':'R365','changed_parent_files':changed,'parent_file_count':len(parent),'checks':checks,'ok':all(checks.values()),'new_browser_checks':57,'fresh_smoke_checks':len(smoke.get('checks',{})),'smoke_stdout':run.stdout[-300:],'smoke_stderr':run.stderr[-300:],'limitations':['Other historical suites are preserved, not freshly replayed','No physical keys tested','Samsung R336 screenshot PASS but JSON receipt missing','No bundled worker/WASM/traineddata, cold offline OCR unverified','No V2.27 promotion']}
    (R/'R366_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'R366_VERIFICATION.txt').write_text('R366 '+('PASS' if out['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} independent checks; 57 new browser + '+str(len(smoke.get('checks',{})))+' fresh smoke.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'new_browser':57,'fresh_smoke':len(smoke.get('checks',{}))}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())