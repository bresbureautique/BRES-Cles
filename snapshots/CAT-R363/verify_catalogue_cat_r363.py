#!/usr/bin/env python3
"""CAT-R363 standalone ledger reproducibility + canonical immutability proof."""
from __future__ import annotations
import hashlib,json,subprocess,sys,os
sys.dont_write_bytecode=True
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={name:digest for digest,name in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_CAT_R362.sha256').read_text(encoding='utf-8').splitlines())}
    changes=sorted(name for name,dig in old.items() if not (R/name).is_file() or sha(R/name)!=dig)
    ledger=json.loads((R/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text())
    outputs=['CAT_R363_PAIR_REVIEW_LEDGER.json','CAT_R363_PAIR_REVIEW_LEDGER.csv','CAT_R363_PAIR_REVIEW_LEDGER.txt']
    initial={x:sha(R/x) for x in outputs}
    before={f.name:sha(f) for f in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    run=subprocess.run([sys.executable,str(R/'catalogue_pair_review_ledger_cat_r363.py')],capture_output=True,text=True,cwd=R,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    after={f.name:sha(f) for f in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    rows,hashes,_=load_records(R.parent/'app')
    try:
        with (R/'CAT_R363_PAIR_REVIEW_LEDGER.csv').open('r',encoding='utf-8-sig',newline='') as f:
            import csv
            csvrows=list(csv.DictReader(f))
    except Exception:csvrows=[]
    checks={
      'parent_CAT_R362_1481_files_preserved':len(old)==1481 and not changes,
      'parent_CAT_R362_results_unchanged':sha(R/'CAT_R362_VERIFICATION.json')==old['CAT_R362_VERIFICATION.json'],
      'CAT_R363_script_reproducible_byte_for_byte':run.returncode==0 and all(sha(R/x)==initial[x] for x in outputs),
      'new_CAT_R363_all_12_controls_PASS':ledger['ok'] and len(ledger['checks'])==12,
      'canonical_5103_refs_remain_unchanged':len(rows)==5103 and len({r[0] for r in rows})==5103,
      'canonical_10_chunks_exact_hashes':len(before)==10 and before==after==hashes==ledger['canonical_sha256'],
      'all_393_edges_732_refs_345_groups':ledger['edge_count']==len(ledger['pairs'])==393 and ledger['distinct_endpoints']==732 and ledger['review_groups']==345,
      '68_OCR_prior_plus_325_typing':ledger['old_OCR_theoretical_edges']==68 and ledger['new_typing_theoretical_edges']==325,
      'CSV_same_393_pairs_exact_order':len(csvrows)==393 and [(r['reference_a'],r['reference_b']) for r in csvrows]==[(x['reference_a'],x['reference_b']) for x in ledger['pairs']],
      'all_marked_not_physically_validated':all(not x['physical_match_confirmed'] and not x['auto_validate'] and not x['catalogue_merge_allowed'] for x in ledger['pairs']),
      'zero_active_catalogue_or_OCR_change':not ledger['app_rule_activation'] and not ledger['catalogue_modified'] and not ledger['physical_validation'],
    }
    result={'schema':'bres-cat-r363-verification-v1','milestone':'CAT-R363','parent':'CAT-R362',
      'parent_files':len(old),'parent_changed_files':changes,'script_exit':run.returncode,'script_stdout':run.stdout.strip(),
      'checks':checks,'ok':all(checks.values()),'limits':'No photography or real key measurements; do not merge and do not claim an OCR correction'}
    (R/'CAT_R363_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R363_VERIFICATION.txt').write_text(f'CAT-R363 {"PASS" if result["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
