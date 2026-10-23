#!/usr/bin/env python3
"""CAT-R357 immutable-parent verification and reproducible review queue checks."""
from __future__ import annotations
import json,hashlib,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parent=(R/'SNAPSHOT_MANIFEST_CAT_R356.sha256').read_text(encoding='utf-8').splitlines()
    mismatches=[fn for dig,fn in (ln.split('  ',1) for ln in parent) if not (R/fn).is_file() or sha(R/fn)!=dig]
    p=subprocess.run([sys.executable,str(R/'catalogue_review_queue_cat_r357.py')],cwd=R,capture_output=True,text=True,timeout=90)
    data=json.loads((R/'CAT_R357_REVIEW_QUEUE.json').read_text(encoding='utf-8'))
    checks={
      'parent_CAT_R356_1425_files_hash_locked':len(parent)==1425 and not mismatches,
      'R357_queue_generated_successfully':p.returncode==0 and data['ok'],
      '11_review_invariants_pass':len(data['checks'])==11 and all(data['checks'].values()),
      '5_synthetic_fixtures_pass':len(data['fixtures'])==5 and all(data['fixtures'].values()),
      '64_review_groups_and_130_references':data['group_count']==64 and data['checks']['130_endpoints_preserved'],
      'all_5103_keys_preserved':data['distinct_references']==5103,
      'no_risky_inference_or_change':data['manufacturers_inferred']==0 and data['aliases_written']==0 and data['active_thresholds_changed'] is False,
      'VI2_VL2_requires_review':data['checks']['unknown_maker_VI2_VL2_is_P0'],
    }
    out={'milestone':'CAT-R357','parent':'CAT-R356','checks':checks,'ok':all(checks.values()),
         'parent_files':len(parent),'parent_mismatches':mismatches,
         'job':{'exit_code':p.returncode,'stdout':p.stdout[-1000:],'stderr':p.stderr[-1000:]}}
    (R/'CAT_R357_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R357_VERIFICATION.txt').write_text('CAT-R357 '+('PASS' if out['ok'] else 'FAIL')+'\n'+
        '\n'.join(('PASS' if ok else 'FAIL')+' '+k for k,ok in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'parent_files_locked':len(parent)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())