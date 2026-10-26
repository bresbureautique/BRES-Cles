#!/usr/bin/env python3
"""CAT-R360: full CAT-R359 parent hashing and independent 64-group OCR audit."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    parent={n:h for h,n in (ln.split('  ',1) for ln in (R/'SNAPSHOT_MANIFEST_CAT_R359.sha256').read_text(encoding='utf-8').splitlines())}
    mismatches=[n for n,h in parent.items() if not (R/n).is_file() or sha(R/n)!=h]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,str(R/'catalogue_ocr_abstention_cat_r360.py')],cwd=R,capture_output=True,text=True,timeout=120,env=env)
    out=json.loads((R/'CAT_R360_ABSTENTION_AUDIT.json').read_text(encoding='utf-8'))
    prev=json.loads((R/'CAT_R359_VERIFICATION.json').read_text(encoding='utf-8'))
    canonical={f.name:sha(f) for f in sorted((R.parent/'app/catalogue/v3').glob('catalog-*.js'))}
    checks={
      'all_1453_parent_files_same_byte_hash':len(parent)==1453 and not mismatches,
      'CAT_R359_9_checks_preserved':prev['ok'] and len(prev['checks'])==9,
      'audit_script_execution_pass':p.returncode==0 and out['ok'],
      'seventeen_new_checks_pass':len(out['checks'])==17 and all(out['checks'].values()),
      '5103_unique_reference_records':out['references']==out['distinct_references']==5103,
      'canonical_10_source_hashes_verified':len(canonical)==10 and canonical==out['source_canonical_sha256'],
      '64_groups_68_pairs_protected':out['ocr_groups']==64 and out['ocr_edges']==68,
      'one_VI2_VL2_maker_gap_in_original_catalogue':out['groups_with_missing_source_maker']==1,
      'classification_59_multi_4_mono_1_missing':(out['groups_across_source_makers'],out['groups_same_source_maker'],out['groups_with_missing_source_maker'])==(59,4,1),
      '8_priority_7_cross_maker':out['priority8_multimaker']==7,
      'no_activation_and_no_physical_claim':not out['activated_in_application'] and not out['maker_proven'] and not out['samsung_physical_validated'] and not out['ocr_offline_validated'],
      'original_graph_unchanged':sha(R/'CAT_R356_OCR_COMPONENTS.json')==out['source_graph_sha256'],
    }
    report={'schema':'bres-cat-r360-verification-v1','milestone':'CAT-R360','parent':'CAT-R359',
      'parent_files':len(parent),'parent_mismatches':mismatches,'source_hashes':canonical,
      'job':{'exit_code':p.returncode,'stdout':p.stdout[-500:],'stderr':p.stderr[-500:]},
      'checks':checks,'ok':all(checks.values())}
    (R/'CAT_R360_VERIFICATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'CAT_R360_VERIFICATION.txt').write_text('CAT-R360 '+('PASS' if report['ok'] else 'FAIL')+'\n'+
       '\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'checks':len(checks),'mismatches':len(mismatches)}))
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(run())