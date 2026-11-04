#!/usr/bin/env python3
"""Independent CAT-R369 gate, confirms all prior catalogue files unchanged."""
import hashlib,json,sys,subprocess,os,csv
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;A=C.parent/'app'
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old={name:digest for digest,name in (line.split('  ',1) for line in (C/'SNAPSHOT_MANIFEST_CAT_R368.sha256').read_text().splitlines())}
    changed=[name for name,h in old.items() if not (C/name).exists() or H(C/name)!=h]
    audit=json.loads((C/'CAT_R369_FRAGMENT_RISK_AUDIT.json').read_text(encoding='utf8'))
    runtime=json.loads((C/'CAT_R369_RUNTIME_REGRESSION.json').read_text(encoding='utf8'))
    sources=[C/'CAT_R369_FRAGMENT_RISK_AUDIT.json',C/'CAT_R369_FRAGMENT_RISK_AUDIT.csv',C/'CAT_R369_FRAGMENT_RISK_AUDIT.txt']
    hashes=[H(p) for p in sources]
    re_audit=subprocess.run([sys.executable,str(C/'catalogue_r369_fragment_risk_audit.py')],cwd=C,capture_output=True,text=True,
             timeout=70,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    rows,canon,_=load_records(A)
    with sources[1].open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
    checks={
      'prior_1533_manifest_rows_unchanged':len(old)==1533 and not changed,
      'parent_CAT_R368_passed':json.loads((C/'CAT_R368_VERIFICATION.json').read_text())['ok'],
      'fragment_audit_reproducible':re_audit.returncode==0 and all(H(p)==h for p,h in zip(sources,hashes)),
      'fragment_audit_10_checks_all_pass':audit['ok'] and len(audit['checks'])==10,
      'runtime_comparison_6_checks_pass':runtime['ok'] and len(runtime['checks'])==6,
      '393_csv_review_rows':len(csv_rows)==393,
      '732_distinct_endpoints_real_JS':runtime['distinct_endpoints']==732 and runtime['changed_decisions']==0,
      '10_canonical_hashes_preserved':canon==audit['canonical_sha256'] and len(canon)==10,
      '5103_canonical_unique_references':len(rows)==len({str(x[0]) for x in rows})==5103,
      'no_automatic_ref_merges_or_maker_attribution':not audit['catalogue_modified'] and not audit['physical_validation'] and not audit['manufacturer_inferred'],
    }
    out={'schema':'bres-cat-r369-independent-gate-v1','milestone':'CAT-R369','date':'2026-11-04','ok':all(checks.values()),
         'checks':checks,'parent_files':len(old),'modified_parent_files':changed,
         'cross_fragment_ocr_pairs_UNVERIFIED':audit['cross_fragment_ocr_pairs'],
         'cross_fragment_typing_pairs_UNVERIFIED':audit['cross_fragment_typing_pairs'],
         'limitations':['All pairs are textual review only; no manufacturer or physical validation']}
    (C/'CAT_R369_VERIFICATION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (C/'CAT_R369_VERIFICATION.txt').write_text(f"CAT-R369 {'PASS' if out['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} independent checks, 393 risk pairs, 732 runtime refs, canonical source unchanged.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
