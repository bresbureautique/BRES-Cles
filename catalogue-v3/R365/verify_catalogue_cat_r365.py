#!/usr/bin/env python3
"""CAT-R365 independent check: immutable R364 parents, repeatable review queue."""
import csv,hashlib,json,os,subprocess,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    old={name:d for d,name in (s.split('  ',1) for s in (R/'SNAPSHOT_MANIFEST_CAT_R364.sha256').read_text(encoding='utf-8').splitlines())}
    changed=sorted(n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h)
    outputs=['CAT_R365_REVIEW_QUEUE.json','CAT_R365_REVIEW_QUEUE.csv','CAT_R365_REVIEW_QUEUE.txt']
    base={n:sha(R/n) for n in outputs}
    before={p.name:sha(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    proc=subprocess.run([sys.executable,str(R/'catalogue_r365_review_queue.py')],cwd=R,capture_output=True,text=True,timeout=100,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    after={p.name:sha(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    review=json.loads((R/'CAT_R365_REVIEW_QUEUE.json').read_text(encoding='utf-8'))
    with (R/'CAT_R365_REVIEW_QUEUE.csv').open('r',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    canon,hashes,_=load_records(R.parent/'app')
    checks={
      'R364_parent_all_1497_files_immutable':not changed and len(old)>=1490,
      'R364_parent_prior_pass':json.loads((R/'CAT_R364_VERIFICATION.json').read_text())['ok'],
      'deterministic_3_exports':proc.returncode==0 and all(sha(R/n)==base[n] for n in outputs),
      'new_queue_11_checks_PASS':review['ok'] and len(review['checks'])==11,
      'source_5103_distinct':len(canon)==len(set(x[0] for x in canon))==5103,
      'canonical_10_SHA_unmodified':len(hashes)==10 and before==after==hashes==review['canonical_sha256'],
      'CSV_exact_68_pairs':len(rows)==len(review['pairs'])==68 and all(c['reference_a_UNVERIFIED']==r['reference_a_UNVERIFIED'] and c['reference_b_UNVERIFIED']==r['reference_b_UNVERIFIED'] for c,r in zip(rows,review['pairs'])),
      'three_theoretical_overlaps_only':sum(x['geometry_theoretical_1mm_each_axis_overlap_NOT_KEY_EQUIVALENCE'] for x in review['pairs'])==3,
      'same_68_unverified_as_R364':{(x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED']) for x in review['pairs']}=={tuple(x) for x in json.loads((R/'CAT_R364_OCR_FOLD_AUDIT.json').read_text())['folded_pair_sources']},
      'no_new_alias_or_physical_claim':not review['physical_validation'] and not review['OCR_rule_modified'] and not review['manufacturer_attribution'] and not review['catalogue_modified']
    }
    out={'schema':'bres-cat-r365-independent-verification-v1','milestone':'CAT-R365','changed_parent_files':changed,'checks':checks,'ok':all(checks.values()),'generator_stdout':proc.stdout,'limitations':['Geometry dimensions source-only and ±1mm theoretical','No known reference specimens, no real OCR, no manufacturer confirmed']}
    (R/'CAT_R365_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R365_VERIFICATION.txt').write_text('CAT-R365 '+('PASS' if out['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} independent controls; 68 pair review, 0 merges.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(verify())