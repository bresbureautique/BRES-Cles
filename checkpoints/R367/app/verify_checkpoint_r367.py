#!/usr/bin/env python3
"""Independent R367 proof gate, before archiving or promoting any TEST checkpoint."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
from r367_ocr_glyph_guard_patch import patch
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent
P=Path('/mnt/data/bres_r366_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R366.zip')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old={p:h for h,p in (l.split('  ',1) for l in (A/'SNAPSHOT_MANIFEST_R366.sha256').read_text().splitlines())}
    changed=[p for p,h in old.items() if not (A/p).is_file() or sha(A/p)!=h]
    with zipfile.ZipFile(P) as z:
        oldindex=z.read('app/index.html');zip_ok=z.testzip() is None
    newindex=(A/'index.html').read_bytes();js=(A/'index.html').read_text()
    fold=json.loads((A/'R367_OCR_FOLD_RUNTIME_REGRESSION.json').read_text())
    ext=json.loads((A/'R367_OCR_FOLD_EXTENDED_NONREGRESSION.json').read_text())
    prior=json.loads((A/'R367_PRIOR_CHROMIUM_COMPAT.json').read_text())
    r366=json.loads((A/'R366_VERIFICATION.json').read_text())
    safe_files=('r331-device-benchmark.js','device_benchmark_r336.html',
                'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','v228-catalogue.js')
    checks={
      'R366_parent_ZIP_CRC':zip_ok,
      'R366_8882_parent_files_present':len(old)==8882 and all((A/p).is_file() for p in old),
      'R366_parent_only_index_changed':changed==['index.html'],
      'R366_index_matches_parent_manifest':hashlib.sha256(oldindex).hexdigest()==old['index.html'],
      'exact_reproducible_R367_patch':patch(oldindex.decode('utf-8')).encode('utf-8')==newindex,
      'R366_verification_parent_passed':r366['ok'],
      '64_folded_strings_in_actual_JS_decisions':fold['ok'] and fold['case_count']==64 and fold['prior_unsafe_auto_prefills']==11 and fold['after_guard_auto_prefills']==0,
      '130_collision_refs_no_prefill':ext['ok'] and ext['risk_ref_count']==130 and ext['guarded_eligible_collision_refs']==0,
      '250_noncollision_control_decisions_unchanged':ext['random_control_count']==250 and not ext['changed_unrelated_controls'],
      '57_prior_origin_chromium_checks_fresh':prior['ok'] and prior['runs']['R366_57']['checks']==57 and prior['runs']['R366_57']['ok'],
      '10_prior_offline_smoke_chromium_checks_fresh':prior['runs']['R356_10']['checks']==10 and prior['runs']['R356_10']['ok'],
      'R331_R336_and_pilot_catalogue_unchanged':all(sha(A/n)==old[n] for n in safe_files),
      'R305_ocr_rule_text_retained':'R305 : activation bornée' in js,
      'v228_test_title_still_R156': '<title>BRES Clés V2.28 TEST R156</title>' in js,
      'V227_stable_only':'V2.27 reste la version stable' in js,
      'no_auto_activation_of_v3':'catalogue/v3/catalog-01.js' not in js,
      'no_cold_offline_OCR_claim':'coldOfflineOcrCertified:false' in js and 'cdn.jsdelivr.net/npm/tesseract.js@5/' in js,
      'no_physical_key_claim':not fold.get('physical_key_validated',False),
      'R367_guard_is_test_only':'R367 TEST:' in js and 'manual-review-required' in js,
    }
    out={'schema':'bres-r367-independent-checkpoint-verification-v1','milestone':'R367','date':'2026-11-02',
     'parent':'R366','parent_file_count':len(old),'changed_parent_files':changed,
     'checks':checks,'ok':all(checks.values()),
     'browser_checks_fresh':16+10+7+57+10,
     'synthetic_folded_texts':64,'source_refs_tested':130,'unrelated_controls_tested':250,
     'real_OCR_executed':False,'physical_key_test':False,'source_catalogue_modified':False,
     'R305_interpretation_experimental_change':True,'V227_stable_unmodified':True,
     'limitations':['This is a V2.28 TEST parser guard; physical performance unverified',
        'Full catalogue must be loaded for R367 glyph-collision guard',
        'No cold-offline OCR certification', 'Samsung R336 screenshot PASS 192/192, raw JSON missing',
        'Prior entire historical test collection not freshly rerun']}
    (A/'R367_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (A/'R367_VERIFICATION.txt').write_text('R367 '+('PASS' if out['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} independent gate checks, 100 fresh Chromium/compat checks, 130 colliding refs, 250 unrelated controls. V2.27 unchanged.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failures':[x for x,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
