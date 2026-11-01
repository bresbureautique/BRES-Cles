#!/usr/bin/env python3
"""CAT-R366: reproducible negative QA fixture set for OCR-fold collisions.
Fixture EXPECTATION != proof the production classifier abstains. No source mutation.
"""
import csv,hashlib,itertools,json,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
from catalogue_fold_homograph_audit_cat_r364 import fold
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
OUT='CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES'

def main():
    r364=json.loads((R/'CAT_R364_OCR_FOLD_AUDIT.json').read_text(encoding='utf-8'))
    r365=json.loads((R/'CAT_R365_REVIEW_QUEUE.json').read_text(encoding='utf-8'))
    records,hashes,_=load_records(R.parent/'app')
    refs={str(row[0]) for row in records}
    entries=[]
    for group in r364['groups']:
        folded=group['folded_transcription_NOT_REFERENCE']
        canons=sorted(group['source_references_distinct'])
        entries.append({
           'synthetic_ocr_text_NOT_A_PHYSICAL_KEY':folded,
           'source_candidates_DISTINCT_UNVERIFIED':canons,
           'candidate_count':len(canons),
           'expected_test_policy':'ABSTAIN_MANUAL_REVIEW',
           'test_only':True,
           'current_app_runtime_abstention_tested':False,
           'physical_key_verified':False,
           'maker_verified':False,
           'automatic_alias_or_identity_permitted':False,
           'input_kind':'lossy-OCR-fold-SYNTHETIC',
           'notes':'Do not select a unique reference based on lossy text alone; recto/verso calibrated photos and certain reference required.'
        })
    entries.sort(key=lambda v:(-v['candidate_count'],v['synthetic_ocr_text_NOT_A_PHYSICAL_KEY']))
    generated_pairs={tuple(sorted(p)) for e in entries for p in itertools.combinations(e['source_candidates_DISTINCT_UNVERIFIED'],2)}
    all_refs={r for e in entries for r in e['source_candidates_DISTINCT_UNVERIFIED']}
    parent_pairs={tuple(sorted((x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED']))) for x in r365['pairs']}
    checks={
       'R364_fold_audit_pass':r364['ok'] is True,
       'R365_queue_pass':r365['ok'] is True,
       'source_5103_distinct':len(refs)==len(records)==5103,
       'ten_canonical_hashes_same':len(hashes)==10 and hashes==r364['canonical_sha256']==r365['canonical_sha256'],
       '64_complete_fold_groups':len(entries)==64 and len({e['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] for e in entries})==64,
       '130_unique_source_refs':len(all_refs)==130 and all_refs.issubset(refs),
       '68_parent_review_pairs_exact':len(generated_pairs)==68 and generated_pairs==parent_pairs,
       'pair_endpoints_are_distinct':all(len(x)==2 and x[0]!=x[1] for x in generated_pairs),
       'all_collisions_roundtrip_to_fold':all(all(fold(ref)==e['synthetic_ocr_text_NOT_A_PHYSICAL_KEY'] for ref in e['source_candidates_DISTINCT_UNVERIFIED']) for e in entries),
       'all_test_expectations_abstain':all(e['expected_test_policy']=='ABSTAIN_MANUAL_REVIEW' for e in entries),
       'no_implied_runtime_success':all(e['current_app_runtime_abstention_tested'] is False for e in entries),
       'no_identity_manufacturer_or_alias':all(not e['physical_key_verified'] and not e['maker_verified'] and not e['automatic_alias_or_identity_permitted'] for e in entries),
    }
    result={'schema':'bres-cat-r366-ocr-negative-qa-fixtures-v1','milestone':'CAT-R366','parent':'CAT-R365',
       'scope':'Read-only synthetic OCR text ambiguity fixtures (not live OCR runs)',
       'canonical_ref_count':len(refs),'canonical_sha256':hashes,
       'fold_groups':len(entries),'distinct_source_references':len(all_refs),'theoretical_pairs':len(generated_pairs),
       'fixtures':entries,'checks':checks,'ok':all(checks.values()),
       'active_classifier_tested':False,'physical_key_validation':False,'source_catalogue_modified':False,
       'active_OCR_rule_modified':False,'manufacturer_attribution':False}
    (R/(OUT+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/(OUT+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
       names=['synthetic_ocr_text_NOT_A_PHYSICAL_KEY','source_candidates_DISTINCT_UNVERIFIED','candidate_count','expected_test_policy','current_app_runtime_abstention_tested']
       w=csv.DictWriter(f,fieldnames=names,lineterminator='\r\n');w.writeheader()
       for row in entries:w.writerow({**{n:row[n] for n in names},'source_candidates_DISTINCT_UNVERIFIED':' | '.join(row['source_candidates_DISTINCT_UNVERIFIED'])})
    (R/(OUT+'.txt')).write_text('CAT-R366 '+('PASS' if result['ok'] else 'FAIL')+f': {sum(checks.values())}/{len(checks)} generator controls; 64 synthetic folded strings, 68 theoretical risky pairs, 130 distinct source refs.\nNo real OCR executed; test policy ABSTAIN must be checked against runtime separately; no source/catalogue changes.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'failures':[k for k,v in checks.items() if not v],'groups':len(entries),'pairs':len(generated_pairs)}))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())