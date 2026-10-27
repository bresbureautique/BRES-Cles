#!/usr/bin/env python3
"""CAT-R361 verifies canonical and parent snapshots plus the typo collision audit."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,csv
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    old={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_CAT_R360.sha256').read_text(encoding='utf-8').splitlines())}
    bad=[n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h]
    parent=json.loads((R/'CAT_R360_VERIFICATION.json').read_text(encoding='utf-8'))
    prev=json.loads((R/'CAT_R360_ABSTENTION_AUDIT.json').read_text(encoding='utf-8'))
    p=subprocess.run([sys.executable,str(R/'catalogue_single_edit_collision_cat_r361.py')],cwd=R,capture_output=True,text=True,
                     timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    out=json.loads((R/'CAT_R361_SINGLE_EDIT_COLLISIONS.json').read_text(encoding='utf-8'))
    with (R/'CAT_R361_NEW_TYPING_COLLISIONS.csv').open(encoding='utf-8-sig',newline='') as f:review=list(csv.DictReader(f))
    checks={
      'all_1462_parent_catalogue_files_identical':len(old)==1462 and not bad,
      'parent_CAT_R360_verification_preserved':parent['ok'] and len(parent['checks'])==12,
      'parent_64_OCR_groups_68_edges_recovered':prev['ok'] and prev['ocr_groups']==64 and prev['ocr_edges']==68,
      'ten_original_canonical_hashes_unchanged':out['canonical_sha256']==prev['source_canonical_sha256'] and len(out['canonical_sha256'])==10,
      '5103_unique_refs_preserved':out['catalogue_unique_references']==5103,
      'CAT_R361_12_new_checks_pass':p.returncode==0 and out['ok'] and len(out['checks'])==12,
      '393_pairs_68_previous_325_new':out['variant_pair_count']==393 and out['parent_pairs_matched']==68 and out['new_adjacent_typing_transposition_pairs']==325,
      'all_325_review_rows_present':len(review)==325 and len({(r['reference_a'],r['reference_b']) for r in review})==325,
      'new_pairs_typing_only_and_no_auto_validate':all(r['edit_types']=="['adjacent_transposition']" and r['automatically_validated']=='False' for r in review),
      'no_new_actual_aliases_or_makers_assigned':not any(out[x] for x in ('activated_in_app','reference_merged','threshold_changed','manufacturer_attributed')),
      'no_physical_samsung_or_offline_OCR_claimed':not out['samsung_physical_validated'] and not out['ocr_offline_certified'],
    }
    obj={'schema':'bres-cat-r361-verification-v1','milestone':'CAT-R361','parent':'CAT-R360',
       'parent_mismatches':bad,'checks':checks,'job_stdout':p.stdout,'job_stderr':p.stderr,'ok':all(checks.values())}
    (R/'CAT_R361_VERIFICATION.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R361_VERIFICATION.txt').write_text(f"CAT-R361 {'PASS' if obj['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':obj['ok'],'checks':len(checks),'parent_mismatches':bad,'new_pairs':len(review),'test_output':p.stdout.strip()},ensure_ascii=False))
    return 0 if obj['ok'] else 1
if __name__=='__main__':raise SystemExit(run())