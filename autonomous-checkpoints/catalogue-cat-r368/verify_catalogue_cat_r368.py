#!/usr/bin/env python3
"""Independent CAT-R368 gate: read-only 325 typing-only pair audit, no catalogue edits."""
import csv,hashlib,json,subprocess,sys,os
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;A=C.parent/'app'
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old={name:digest for digest,name in (x.split('  ',1) for x in (C/'SNAPSHOT_MANIFEST_CAT_R367.sha256').read_text().splitlines())}
    modified=[p for p,h in old.items() if not (C/p).is_file() or H(C/p)!=h]
    paths=[C/('CAT_R368_TYPING_RUNTIME_AUDIT'+ext) for ext in ('.json','.csv','.txt')]
    saved=[H(x) for x in paths]
    generated=subprocess.run([sys.executable,str(C/'catalogue_r368_typing_runtime_audit.py')],cwd=C,capture_output=True,text=True,timeout=150,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    audit=json.loads(paths[0].read_text())
    with paths[1].open(newline='',encoding='utf-8-sig') as f:csv_rows=list(csv.DictReader(f))
    records,hashes,_=load_records(A)
    checks={
      'CAT_R367_1524_parent_files_unchanged':len(old)==1524 and not modified,
      'CAT_R367_parent_gate_passed':json.loads((C/'CAT_R367_VERIFICATION.json').read_text())['ok'],
      'generator_reproducible_sha256':generated.returncode==0 and [H(x) for x in paths]==saved,
      'audit_9_checks_all_pass':audit['ok'] and len(audit['checks'])==9,
      '325_pairs_match_csv_rows':len(csv_rows)==audit['typing_pairs']==325,
      '635_distinct_endpoints':audit['distinct_typing_endpoints']==635,
      'R367_to_R368_full_text_decisions_unchanged':audit['r367_to_r368_regression_pair_count']==0,
      '10_canonical_fragments_sha256_stable':hashes==audit['canonical_sha256'] and len(hashes)==10,
      '5103_distinct_references_stable':len(records)==len({str(r[0]) for r in records})==5103,
      'no_physical_equivalence_or_OCR_claim':not audit['physical_validation'] and not audit['real_OCR_performed'] and not audit['catalogue_mutated'],
    }
    result={'schema':'bres-cat-r368-independent-verification-v1','milestone':'CAT-R368','date':'2026-11-03',
      'ok':all(checks.values()),'checks':checks,'parent_files':len(old),'changed_parent_files':modified,
      'limitations':['All 325 edit-neighbour pairs are theoretical text-only review candidates, not manufacturer or physical key validations']}
    (C/'CAT_R368_VERIFICATION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (C/'CAT_R368_VERIFICATION.txt').write_text(f"CAT-R368 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} checks; 325 typing-only pairs / 635 endpoints, source fragments unchanged.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
