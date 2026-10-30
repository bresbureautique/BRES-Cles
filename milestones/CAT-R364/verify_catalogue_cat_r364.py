#!/usr/bin/env python3
"""CAT-R364 independent integrity/reproducibility; no schema rewrite or promotion."""
from __future__ import annotations
import csv,hashlib,json,os,subprocess,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    old={name:digest for digest,name in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_CAT_R363.sha256').read_text(encoding='utf-8').splitlines())}
    changed=sorted(n for n,d in old.items() if not (R/n).is_file() or sha(R/n)!=d)
    r=json.loads((R/'CAT_R364_OCR_FOLD_AUDIT.json').read_text(encoding='utf-8'))
    outputs=['CAT_R364_OCR_FOLD_AUDIT.json','CAT_R364_OCR_FOLD_AUDIT.csv','CAT_R364_OCR_FOLD_AUDIT.txt']
    baseline={n:sha(R/n) for n in outputs}
    before={p.name:sha(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    proc=subprocess.run([sys.executable,str(R/'catalogue_fold_homograph_audit_cat_r364.py')],cwd=R,capture_output=True,text=True,timeout=90,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    after={p.name:sha(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    rows,hashes,_=load_records(R.parent/'app')
    with (R/'CAT_R364_OCR_FOLD_AUDIT.csv').open('r',encoding='utf-8-sig',newline='') as f:csvrows=list(csv.DictReader(f))
    pairs={tuple(p) for p in r['folded_pair_sources']}
    prev=json.loads((R/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text(encoding='utf-8'))
    parent_pairs={(p['reference_a'],p['reference_b']) for p in prev['pairs']}
    checks={
     'all_parent_CAT_R363_files_hash_preserved':not changed and len(old)>=1480,
     'parent_verification_still_passed':json.loads((R/'CAT_R363_VERIFICATION.json').read_text())['ok'] is True,
     'audit_deterministic_byte_for_byte':proc.returncode==0 and all(sha(R/n)==baseline[n] for n in outputs),
     'audit_12_checks_passed':r['ok'] and len(r['checks'])==12,
     'canonical_10_chunks_unchanged':len(hashes)==10 and before==after==hashes==r['canonical_sha256'],
     '5103_distinct_canonical_sources':len(rows)==len(set(row[0] for row in rows))==5103,
     '64_csv_groups_identical_to_JSON':len(csvrows)==len(r['groups'])==64 and all(c['folded_transcription_NOT_REFERENCE']==g['folded_transcription_NOT_REFERENCE'] and c['source_references_distinct'].split(' | ')==g['source_references_distinct'] for c,g in zip(csvrows,r['groups'])),
     '68_pairs_are_prior_review_edges_only':len(pairs)==68 and pairs.issubset(parent_pairs),
     '325_other_typing_pairs_no_auto_equivalence':len(parent_pairs-pairs)==325 and len(parent_pairs)==393,
     'no_physical_key_or_manufacturer_certification':not r['physical_key_review'] and not r['manufacturer_attribution'] and all(not g['physical_equivalence_verified'] for g in r['groups']),
     'no_catalogue_or_active_OCR_change':not r['catalogue_mutation'] and not r['active_OCR_change'],
    }
    out={'schema':'bres-cat-r364-verification-v1','milestone':'CAT-R364','checks':checks,'ok':all(checks.values()),'changed_parent_files':changed,'parent_file_count':len(old),'generator_exit':proc.returncode,'generator_stdout':proc.stdout.strip(),'limitations':['No physical keys, source manufacturer proof, or actual OCR recognition','Do not activate lossy transcription folding in production']}
    (R/'CAT_R364_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R364_VERIFICATION.txt').write_text(f'CAT-R364 {"PASS" if out["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} independent controls.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'parent_files':len(old)},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(verify())