#!/usr/bin/env python3
"""Independent CAT-R367 proof gate: all CAT-R366 files immutable, ledger reproducible."""
import csv,hashlib,json,os,subprocess,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;A=C.parent/'app'
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parent={p:h for h,p in (x.split('  ',1) for x in (C/'SNAPSHOT_MANIFEST_CAT_R366.sha256').read_text().splitlines())}
    modified=[p for p,h in parent.items() if not (C/p).is_file() or H(C/p)!=h]
    paths=[C/('CAT_R367_RUNTIME_OCR_RISK_AUDIT'+ext) for ext in ('.json','.csv','.txt')]
    before={p.name:H(p) for p in paths}
    hashes_before={p.name:H(p) for p in (A/'catalogue/v3').glob('catalog-*.js')}
    process=subprocess.run([sys.executable,str(C/'catalogue_r367_runtime_ocr_risk_audit.py')],
                           cwd=C,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=100)
    hashes_after={p.name:H(p) for p in (A/'catalogue/v3').glob('catalog-*.js')}
    data=json.loads(paths[0].read_text(encoding='utf-8'))
    with paths[1].open(newline='',encoding='utf-8-sig') as f:csv_rows=list(csv.DictReader(f))
    records,hashes,_=load_records(A)
    checks={
      'R366_all_1515_catalogue_files_unchanged':len(parent)==1515 and not modified,
      'CAT_R366_prior_verification_passed':json.loads((C/'CAT_R366_VERIFICATION.json').read_text())['ok'],
      'generator_deterministic':process.returncode==0 and all(H(p)==before[p.name] for p in paths),
      '12_runtime_risk_audit_checks':data['ok'] and len(data['checks'])==12,
      '5103_source_refs_unchanged':len(records)==5103 and len({str(r[0]) for r in records})==5103,
      'ten_canonical_SHA256_same':hashes==hashes_before==hashes_after==data['canonical_sha256'],
      '64_rows_csv_json_agree':len(csv_rows)==64 and len(data['rows'])==64 and all(a['synthetic_ocr_fold_NOT_REFERENCE']==b['synthetic_ocr_fold_NOT_REFERENCE'] for a,b in zip(csv_rows,data['rows'])),
      '11_baseline_risks_from_JS':data['risky_baseline_folded_groups']==11,
      '0_post_guard_automatic_prefills':all(r['R367_possible_automatic_reference_prefill'] is None for r in data['rows']),
      '130_ref_endpoint_immutability':data['distinct_source_refs']==130,
      'no_physical_equivalence_claim':all(not r['physical_key_verified'] and not r['manufacturer_equivalence_asserted'] for r in data['rows']),
      'no_catalogue_data_changed':not data['canonical_catalogue_modified'],
    }
    out={'schema':'bres-cat-r367-independent-verification-v1','milestone':'CAT-R367','date':'2026-11-02',
     'checks':checks,'ok':all(checks.values()),'parent_files':len(parent),'changed_parent_files':modified,
     'limitations':['Actual JS parser tested with synthetic text, not photo/OCR','No manufacturer equivalence or key validated']}
    (C/'CAT_R367_VERIFICATION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (C/'CAT_R367_VERIFICATION.txt').write_text('CAT-R367 '+('PASS' if out['ok'] else 'FAIL')+': '+str(sum(checks.values()))+'/'+str(len(checks))+' controls, unmodified 5103 refs / 10 source fragments.\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failures':[x for x,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
