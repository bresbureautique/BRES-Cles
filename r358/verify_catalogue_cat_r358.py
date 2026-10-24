#!/usr/bin/env python3
"""CAT-R358 additive exact-parent gate, theoretical margin queue only."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(name):
    p=subprocess.run([sys.executable,str(R/name)],cwd=R,text=True,capture_output=True,timeout=180)
    return {'exit_code':p.returncode,'stdout':p.stdout[-1000:],'stderr':p.stderr[-1000:]}

def main():
    jobs={'CAT_R357_security_review_replay':run('verify_catalogue_cat_r357.py'),
          'CAT_R358_margin_queue':run('catalogue_margin_frontier_cat_r358.py')}
    manifest=(R/'SNAPSHOT_MANIFEST_CAT_R357.sha256').read_text(encoding='utf-8').splitlines()
    bad=[]
    for l in manifest:
        digest,rel=l.split('  ',1)
        if not (R/rel).is_file() or sha(R/rel)!=digest:bad.append(rel)
    original=json.loads((R/'CAT_R357_REVIEW_QUEUE.json').read_text(encoding='utf-8'))
    previous=json.loads((R/'CAT_R357_VERIFICATION.json').read_text(encoding='utf-8'))
    new=json.loads((R/'CAT_R358_DIMENSION_PRIORITY.json').read_text(encoding='utf-8'))
    checks={
      'CAT_R357_original_review_replay':jobs['CAT_R357_security_review_replay']['exit_code']==0 and previous['ok'] and original['ok'],
      'CAT_R358_new_independent_margin_replay':jobs['CAT_R358_margin_queue']['exit_code']==0 and new['ok'],
      'all_1434_prior_cat_files_byte_identical':len(manifest)==1434 and not bad,
      'historical_R357_priorities_untouched':original['group_count']==64 and original['distinct_references']==5103,
      'source_5103_unique_and_10_canons':len(new['canonical_sha256'])==10 and all(sha(R.parent/'app/catalogue/v3'/file)==digest for file,digest in new['canonical_sha256'].items()),
      '68_OCR_edges_130_refs_64_groups':(new['edges'],new['references'],new['groups'])==(68,130,64),
      'margin_only_first_eight_priorities':new['priority_up_to_half_mm']==8 and new['priority_distribution']=={'P0':2,'P1':2,'P2':4,'P3':56},
      'adversarial_fixtures':len(new['fixtures'])==4 and all(new['fixtures'].values()),
      'new_nine_queue_invariants':len(new['checks'])==9 and all(new['checks'].values()),
      'no_unapproved_reference_decisions':not new['manufacturer_inferred'] and not new['OCR_rules_changed'] and not new['physical_measurements_used'],
    }
    out={'schema':'bres-cat-r358-verification-v1','milestone':'CAT-R358','parent':'CAT-R357',
         'checks':checks,'jobs':jobs,'parent_files':len(manifest),'parent_hash_mismatches':bad,'ok':all(checks.values())}
    (R/'CAT_R358_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R358_VERIFICATION.txt').write_text('CAT-R358 '+('PASS' if out['ok'] else 'FAIL')+'\n'+
        '\n'.join(('PASS ' if b else 'FAIL ')+k for k,b in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'parent_files':len(manifest)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())