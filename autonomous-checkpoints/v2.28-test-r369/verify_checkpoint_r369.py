#!/usr/bin/env python3
"""R369 independent, source-reproducible proof gate. TEST branch only."""
from pathlib import Path
import hashlib,json,zipfile,sys
from r369_catalogue_inventory_guard_patch import patch
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;C=A.parent/'cat'
P=Path('/mnt/data/bres_r368_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R368.zip')
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old={name:digest for digest,name in (line.split('  ',1) for line in (A/'SNAPSHOT_MANIFEST_R368.sha256').read_text().splitlines())}
    changed=[name for name,h in old.items() if not (A/name).is_file() or H(A/name)!=h]
    with zipfile.ZipFile(P) as z:
        parenthtml=z.read('app/index.html').decode('utf8')
        zipok=z.testzip() is None; parentlen=len(z.namelist())
    current=(A/'index.html').read_text(encoding='utf8')
    run=json.loads((A/'R369_INVENTORY_GUARD_CHROMIUM.json').read_text(encoding='utf8'))
    cat=json.loads((C/'CAT_R369_RUNTIME_REGRESSION.json').read_text(encoding='utf8'))
    fragment=json.loads((C/'CAT_R369_FRAGMENT_RISK_AUDIT.json').read_text(encoding='utf8'))
    canons=[f'catalogue/v3/catalog-{i:02}.js' for i in range(1,11)]
    frozen=['r331-device-benchmark.js','device_benchmark_r336.html','BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html','v228-catalogue.js']
    checks={
      'parent_R368_zip_crc_and_entries':zipok and parentlen==8908,
      'parent_R368_manifest_files_8907':len(old)==8907 and all((A/p).is_file() for p in old),
      'parent_R368_html_equal_its_manifest':hashlib.sha256(parenthtml.encode('utf8')).hexdigest()==old['index.html'],
      'only_index_html_changed_existing':changed==['index.html'],
      'exact_reproducible_R369_patch':patch(parenthtml)==current,
      'new_chromium_checks_all_14':run['ok'] and len(run['checks'])==14,
      'all_seven_faults_and_restores_detected':run['checks']['all_7_faults_blocked'] and run['checks']['all_7_restores_release_gate'],
      'no_130_collision_ref_regression':run['checks']['130_ocr_collision_catalogue_refs_not_auto_selected'],
      'no_64_fold_ocr_regression':run['checks']['64_folded_ambiguities_not_auto_selected'],
      '732_review_endpoints_no_regression':cat['ok'] and cat['distinct_endpoints']==732 and cat['changed_decisions']==0,
      '393_pairs_fragment_audit_pass':fragment['ok'] and fragment['theoretical_ocr_pairs']==68 and fragment['typing_pairs']==325,
      'ten_catalogue_fragments_unchanged':len(canons)==10 and all(H(A/p)==old[p] for p in canons),
      'R331_R336_pilot_unchanged':all(H(A/p)==old[p] for p in frozen),
      'R305_rule_marker_retained':'R305 : activation bornée' in current,
      'V2_28_remains_test':'<title>BRES Clés V2.28 TEST R156</title>' in current,
      'V2_27_stable_label_unmodified':'V2.27 reste la version stable' in current,
      'catalogue_v3_still_opt_in':'catalogue/v3/catalog-01.js' not in current,
      'Tesseract_cold_offline_NOT_CERTIFIED':'coldOfflineOcrCertified:false' in current and 'cdn.jsdelivr.net/npm/tesseract.js@5/' in current,
      'new_inventory_guard_not_cryptographic_claim':'not cryptographic authenticity' in current,
      'no_physical_test_claim':not cat['actual_ocr_executed'] and not fragment['actual_ocr_executed'] and not fragment['physical_validation'],
    }
    out={'schema':'bres-r369-independent-checkpoint-v1','date':'2026-11-04','milestone':'R369',
         'parent':'R368','parent_files':parentlen,'parent_manifest':len(old),'changed_existing_files':changed,
         'ok':all(checks.values()),'checks':checks,'physical_samsung_test':False,'stable_version_changed':False,
         'catalogue_canonical_modified':False,
         'limitations':['Only 14 new Chromium assertions; 136 tested sample inputs plus 64 OCR folds, 732 catalogue endpoints','No real photo, physical key or OCR Tesseract run','Noncryptographic double checksum for ordered columns 0..4, not source authenticity','Older R368 history retained but not all old suites rerun']}
    (A/'R369_VERIFICATION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (A/'R369_VERIFICATION.txt').write_text(f"R369 {'PASS' if out['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} independent structural checks, stable V2.27 untouched.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
