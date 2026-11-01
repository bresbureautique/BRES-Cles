#!/usr/bin/env python3
"""Independent verification of R366 QA fixture set, immutable CAT-R365 parent."""
import csv,hashlib,itertools,json,os,subprocess,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OUT='CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES'
def main():
 old=dict(line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_CAT_R365.sha256').read_text(encoding='utf-8').splitlines())
 # old mapping is SHA -> path; inversion below avoids false negatives in duplicate hashes.
 baseline={n:sha for sha,n in (x.split('  ',1) for x in (R/'SNAPSHOT_MANIFEST_CAT_R365.sha256').read_text().splitlines())}
 changed=[n for n,sha in baseline.items() if not (R/n).exists() or hashfile(R/n)!=sha]
 output_paths=[R/(OUT+suffix) for suffix in ('.json','.csv','.txt')]
 original_output_hashes={p.name:hashfile(p) for p in output_paths}
 before={p.name:hashfile(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
 run=subprocess.run([sys.executable,str(R/'catalogue_r366_abstention_fixtures.py')],cwd=R,capture_output=True,text=True,timeout=100,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 after={p.name:hashfile(p) for p in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
 data=json.loads((R/(OUT+'.json')).read_text(encoding='utf-8'))
 with (R/(OUT+'.csv')).open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
 source,hashes,_=load_records(R.parent/'app')
 refs={str(x[0]) for x in source}
 recreated={tuple(sorted(x)) for f in data['fixtures'] for x in itertools.combinations(f['source_candidates_DISTINCT_UNVERIFIED'],2)}
 prior=json.loads((R/'CAT_R365_REVIEW_QUEUE.json').read_text(encoding='utf-8'))
 original_pairs={tuple(sorted((f['reference_a_UNVERIFIED'],f['reference_b_UNVERIFIED']))) for f in prior['pairs']}
 checks={
   'CAT_R365_files_preserved':not changed and len(baseline)>=1500,
   'CAT_R365_verified':json.loads((R/'CAT_R365_VERIFICATION.json').read_text())['ok'],
   'deterministic_outputs':run.returncode==0 and all(hashfile(p)==original_output_hashes[p.name] for p in output_paths),
   'generator_12_checks':data['ok'] and len(data['checks'])==12,
   'canonical_source_untouched':len(source)==len(refs)==5103 and before==after==hashes==data['canonical_sha256'],
   '64_unique_synthetic_transcriptions':len(data['fixtures'])==64 and len(csv_rows)==64,
   '68_exact_prior_review_pairs':len(recreated)==68 and recreated==original_pairs,
   '130_distinct_refs':len({x for f in data['fixtures'] for x in f['source_candidates_DISTINCT_UNVERIFIED']})==130,
   'all_csv_fields_match_json':all(row['synthetic_ocr_text_NOT_A_PHYSICAL_KEY']==f['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] and row['expected_test_policy']==f['expected_test_policy'] and int(row['candidate_count'])==f['candidate_count'] for row,f in zip(csv_rows,data['fixtures'])),
   'all_expected_abstain_no_key_cert':all(f['expected_test_policy']=='ABSTAIN_MANUAL_REVIEW' and not f['physical_key_verified'] and not f['automatic_alias_or_identity_permitted'] for f in data['fixtures']),
   'runtime_NOT_claimed':not data['active_classifier_tested'] and not data['physical_key_validation'] and not data['active_OCR_rule_modified'],
 }
 result={'schema':'bres-cat-r366-independent-fixture-verification-v1','milestone':'CAT-R366','checks':checks,'ok':all(checks.values()),'parent_sha_file_count':len(baseline),'modified_parent_files':changed,'generator_stdout':run.stdout,'limitations':['fixtures specify desired abstention; they do not demonstrate active app decision','no physical key nor Samsung test','no OCR runtime executed']}
 (R/'CAT_R366_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (R/'CAT_R366_VERIFICATION.txt').write_text('CAT-R366 '+('PASS' if result['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} independent checks; no catalogue changes.\n',encoding='utf-8')
 print(json.dumps({'ok':result['ok'],'checks':len(checks),'failures':[k for k,v in checks.items() if not v],'preserved_parent':len(baseline)}))
 return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())