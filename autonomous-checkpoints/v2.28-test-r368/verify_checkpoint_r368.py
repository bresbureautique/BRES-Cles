#!/usr/bin/env python3
"""Independent R368 TEST gate: exact R367 parent, no stable/canonical edits."""
import hashlib,json,sys,zipfile
from pathlib import Path
from r368_incomplete_catalogue_patch import patch
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;C=A.parent/'cat'
P=Path('/mnt/data/bres_r367_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R367.zip')
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old={name:digest for digest,name in (x.split('  ',1) for x in (A/'SNAPSHOT_MANIFEST_R367.sha256').read_text().splitlines())}
    assert all(len(v)==64 for v in old.values())
    changed=[p for p,h in old.items() if not (A/p).is_file() or H(A/p)!=h]
    with zipfile.ZipFile(P) as z:parentindex=z.read('app/index.html');crc=(z.testzip() is None);count=len(z.namelist())
    current=(A/'index.html').read_bytes();html=current.decode('utf-8')
    data=json.loads((A/'R368_CATALOGUE_READINESS_CHROMIUM.json').read_text())
    cat=json.loads((C/'CAT_R368_TYPING_RUNTIME_AUDIT.json').read_text())
    parent=json.loads((A/'R367_VERIFICATION.json').read_text())
    safe=('r331-device-benchmark.js','device_benchmark_r336.html','BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','v228-catalogue.js')
    checks={
      'parent_8899_files_crc':count==8899 and crc,
      'parent_8898_manifest_files_present':len(old)==8898 and all((A/p).is_file() for p in old),
      'parent_index_sha_matches_manifest':hashlib.sha256(parentindex).hexdigest()==old['index.html'],
      'only_existing_parent_file_edited_is_index':changed==['index.html'],
      'exact_reproducible_r368_html_patch':patch(parentindex.decode('utf-8')).encode('utf-8')==current,
      'parent_r367_gate_passed':parent.get('ok') is True,
      'runtime_readiness_passes_16':data['ok'] and len(data['checks'])==16,
      '0_1_5_9_fragment_fail_closed':all(data['checks'][k] for k in ('0_chunks_no_auto_prefill','1_chunk_no_auto_prefill','5_chunks_no_auto_prefill','9_chunks_no_auto_prefill')),
      'recovered_full_catalogue_preserves_386_decisions':data['checks']['full_130_collision_250_control_plus_smoke_decisions_unchanged'],
      '64_lossy_glyph_folds_preserved':data['checks']['full_64_fold_decisions_unchanged'],
      '130_collision_refs_still_blocked':data['checks']['130_collision_refs_remain_blocked'],
      'manual_TE8D_TE8I_nonvalidated':data['checks']['manual_TE8D_TE8I_not_validated'],
      '325_typing_pair_audit_passed':cat['ok'] and cat['typing_pairs']==325 and cat['r367_to_r368_regression_pair_count']==0,
      'R331_R336_pilot_unchanged':all(H(A/x)==old[x] for x in safe),
      'R305_rule_marker_retained':'R305 : activation bornée' in html,
      'V228_test_not_promoted':'<title>BRES Clés V2.28 TEST R156</title>' in html,
      'V227_stable_only':'V2.27 reste la version stable' in html,
      'V3_still_opt_in':'catalogue/v3/catalog-01.js' not in html,
      'Tesseract_still_remote_cold_offline_NOT_CERTIFIED':'coldOfflineOcrCertified:false' in html and 'cdn.jsdelivr.net/npm/tesseract.js@5/' in html,
      'actual_physical_or_OCR_claim_absent':not data.get('real_ocr_executed',False) and not cat['real_OCR_performed'] and not cat['physical_validation'],
    }
    out={'schema':'bres-r368-independent-checkpoint-v1','milestone':'R368','date':'2026-11-03',
      'parent':'R367','parent_files':count,'parent_manifest_entries':len(old),
      'changed_parent_files':changed,'checks':checks,'ok':all(checks.values()),
      'fresh_chromium_checks':len(data['checks'])+len(cat['checks']),
      'synthetic_fold_groups':64,'collision_references':130,'unrelated_ref_controls':250,
      'typing_only_review_pairs':325,'Tesseract_cold_offline_certified':False,
      'samsung_physical_test_performed':False,'V227_stable_modified':False,'catalogue_modified':False,
      'limitations':['Tests are synthetic text passed to real JavaScript, not photos or real OCR',
       'The 5103 length readiness gate is not a cryptographic catalogue signature',
       'Cold offline Tesseract not certified; Samsung benchmark JSON not received',
       'Historical entire test corpus not re-executed']}
    (A/'R368_VERIFICATION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    (A/'R368_VERIFICATION.txt').write_text(f"R368 {'PASS' if out['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} independent gate checks; 16 fresh Chromium preflight checks, 635 typing-text controls. Stable V2.27 untouched.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failures':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
