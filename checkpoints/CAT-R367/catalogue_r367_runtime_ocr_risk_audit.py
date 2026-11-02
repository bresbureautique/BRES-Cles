#!/usr/bin/env python3
"""CAT-R367 read-only, provenance-checked ledger of R366 JavaScript OCR risks.
Uses unmodified 5103 canonical references and actual Chromium decision traces.
"""
import csv,hashlib,json,sys
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent;A=C.parent/'app'

def main():
    fixtures=json.loads((C/'CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES.json').read_text())
    proof=json.loads((A/'R367_OCR_FOLD_RUNTIME_REGRESSION.json').read_text())
    extended=json.loads((A/'R367_OCR_FOLD_EXTENDED_NONREGRESSION.json').read_text())
    records,hashes,_=load_records(A)
    baseline=json.loads((C/'CAT_R364_OCR_FOLD_AUDIT.json').read_text())
    b=proof['cases']['baseline_r366'];n=proof['cases']['guarded_r367']
    rows=[]
    for fixture,prior,after in zip(fixtures['fixtures'],b,n):
        raw=fixture['synthetic_ocr_text_NOT_A_PHYSICAL_KEY']
        assert prior['synthetic_text']==after['synthetic_text']==raw
        rows.append({
           'synthetic_ocr_fold_NOT_REFERENCE':raw,
           'source_references_DISTINCT_UNVERIFIED':fixture['source_candidates_DISTINCT_UNVERIFIED'],
           'R366_possible_automatic_reference_prefill':prior['both']['best'],
           'R367_possible_automatic_reference_prefill':after['both']['best'],
           'R367_manual_review_required':not after['both']['best'],
           'R367_detected_fold_ambiguity':after['both']['ambiguous'],
           'priority':'P1_baseline_auto_prefill' if prior['both']['best'] else 'P2_text_confusion',
           'manufacturer_equivalence_asserted':False,
           'physical_key_verified':False,
           'real_OCR_performed':False,
           'input_type':'SYNTHETIC-LOSSY-OCR-FOLD',
        })
    hot=[r for r in rows if r['R366_possible_automatic_reference_prefill']]
    checks={
       'full_corpus_5103_unique_refs':len(records)==5103 and len({str(r[0]) for r in records})==5103,
       'ten_unmodified_canonical_sha256':len(hashes)==10 and hashes==fixtures['canonical_sha256']==baseline['canonical_sha256']==extended['source_hashes'],
       '64_audited_fold_groups_exact':len(rows)==len(set(r['synthetic_ocr_fold_NOT_REFERENCE'] for r in rows))==64,
       '130_source_refs_unchanged':len({ref for r in rows for ref in r['source_references_DISTINCT_UNVERIFIED']})==130,
       'R366_11_synthetic_auto_prefill_risks':len(hot)==proof['prior_unsafe_auto_prefills']==11,
       'R367_0_remaining_synthetic_auto_prefills':all(r['R367_possible_automatic_reference_prefill'] is None for r in rows),
       'R367_126_potential_exact_refs_blocked':extended['baseline_eligible_collision_refs']==126 and extended['guarded_eligible_collision_refs']==0,
       '250_unrelated_controls_unchanged':not extended['changed_unrelated_controls'] and extended['random_control_count']==250,
       'no_implicit_physical_equivalence':all(not r['physical_key_verified'] and not r['manufacturer_equivalence_asserted'] and not r['real_OCR_performed'] for r in rows),
       'QA_proof_success':proof['ok'] and extended['ok'],
       'fixtures_sources_unchanged':fixtures['ok'] and baseline['ok'] and not baseline['catalogue_mutation'],
       'no_fabricated_success_on_no_candidates':sum(r['R367_detected_fold_ambiguity'] for r in rows)==60 and sum(not r['R367_detected_fold_ambiguity'] for r in rows)==4,
    }
    out={'schema':'bres-cat-r367-real-js-ocr-ambiguity-audit-v1','milestone':'CAT-R367','date':'2026-11-02',
      'description':'SYNTHETIC OCR text passed through ACTUAL TEST JavaScript; not Tesseract or physical key identification',
      'canonical_reference_count':len(records),'canonical_sha256':hashes,
      'folded_group_count':len(rows),'risky_baseline_folded_groups':len(hot),
      'baseline_risky_reference_count':extended['baseline_eligible_collision_refs'],
      'post_guard_risky_reference_count':extended['guarded_eligible_collision_refs'],
      'distinct_source_refs':130,'post_guard_tested_text_prefills':0,
      'rows':rows,'checks':checks,'ok':all(checks.values()),
      'physical_key_validation':False,'actual_Tesseract_OCR_performed':False,
      'canonical_catalogue_modified':False,'manufacturer_attribution':False}
    (C/'CAT_R367_RUNTIME_OCR_RISK_AUDIT.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (C/'CAT_R367_RUNTIME_OCR_RISK_AUDIT.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['synthetic_ocr_fold_NOT_REFERENCE','source_references_DISTINCT_UNVERIFIED','priority','R366_possible_automatic_reference_prefill','R367_possible_automatic_reference_prefill','R367_manual_review_required','physical_key_verified']
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\r\n');w.writeheader()
        for r in rows:w.writerow({**{k:r[k] for k in fields},'source_references_DISTINCT_UNVERIFIED':' | '.join(r['source_references_DISTINCT_UNVERIFIED'])})
    (C/'CAT_R367_RUNTIME_OCR_RISK_AUDIT.txt').write_text(
        f"CAT-R367 {'PASS' if out['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} controls. 64 glyph-fold groups, 11 real JS parser auto-prefill risks in R366, 0 in R367. 126/130 canonical ref samples could prefill in R366, 0 in R367. Synthetic text only.\n",encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'risky_baseline_groups':len(hot),'post_risks':0},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
