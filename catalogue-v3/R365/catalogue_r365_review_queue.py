#!/usr/bin/env python3
"""CAT-R365 review-only evidence queue: triage 68 OCR-fold pairs using old
catalogue geometry and maker labels. Scores are NOT classifier probabilities.
"""
import csv,hashlib,json,sys
from collections import Counter
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    fold=json.loads((R/'CAT_R364_OCR_FOLD_AUDIT.json').read_text(encoding='utf-8'))
    geometry=json.loads((R/'CAT_R351_OCR_GEOMETRY_OVERLAP.json').read_text(encoding='utf-8'))
    ledger=json.loads((R/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text(encoding='utf-8'))
    canonical,hashes,_=load_records(R.parent/'app')
    parent_pairs={tuple(sorted(x)) for x in fold['folded_pair_sources']}
    geo={tuple(sorted([p['reference_a'],p['reference_b']])):p for p in geometry['pairs']}
    review={tuple(sorted([p['reference_a'],p['reference_b']])):p for p in ledger['pairs']}
    queue=[]
    for pair in sorted(parent_pairs):
        p=geo.get(pair);lp=review.get(pair)
        if p is None or lp is None:raise RuntimeError('Missing prior evidence for '+str(pair))
        overlap=bool(p['overlap_both_axes_if_each_error_at_most_1mm_THEORETICAL'])
        unknown=bool(p['maker_missing_either'])
        # This is only a prioritisation heuristic; no assignment or confidence.
        bucket='P1_theoretical_geometry_overlap' if overlap else 'P2_maker_missing' if unknown else 'P3_source_labels_present'
        queue.append({
         'reference_a_UNVERIFIED':pair[0],'reference_b_UNVERIFIED':pair[1],
         'review_priority_NOT_RECOGNITION_CONFIDENCE':bucket,
         'catalogue_length_gap_mm_DIAGNOSTIC':p['length_gap_mm_catalogue'],
         'catalogue_width_gap_mm_DIAGNOSTIC':p['width_gap_mm_catalogue'],
         'geometry_theoretical_1mm_each_axis_overlap_NOT_KEY_EQUIVALENCE':overlap,
         'maker_label_missing_SOURCE_ONLY':unknown,
         'maker_a_SOURCE_UNVERIFIED':p['maker_a_display_only'],
         'maker_b_SOURCE_UNVERIFIED':p['maker_b_display_only'],
         'review_actions':['obtain certain physical reference evidence','compare recto/verso on calibrated guide','verify manufacturer engraving and catalogue independently'],
         'verification_state':'TEXT_ONLY_NOT_PHYSICALLY_VERIFIED',
         'automated_alias_allowed':False,'reference_certified':False,
         'notes':'A dimensional gap or overlap in a catalogue is not a physical key match.'})
    priority={'P1_theoretical_geometry_overlap':0,'P2_maker_missing':1,'P3_source_labels_present':2}
    queue.sort(key=lambda x:(priority[x['review_priority_NOT_RECOGNITION_CONFIDENCE']],x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED']))
    counts=Counter(x['review_priority_NOT_RECOGNITION_CONFIDENCE'] for x in queue)
    checks={
      'parent_fold_audit_OK':fold['ok'] and fold['fold_collision_groups']==64,
      'parent_review_ledger_OK':ledger['ok'] and len(ledger['pairs'])==393,
      'parent_geometry_audit_OK':geometry['ok'] and len(geometry['pairs'])==68,
      'all_68_pairs_exact_coverage':len(queue)==len(parent_pairs)==68 and {tuple(sorted((x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED']))) for x in queue}==parent_pairs,
      '130_distinct_references':len(set(y for x in queue for y in (x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED'])))==130,
      '10_canonical_hashes_unchanged':hashes==fold['canonical_sha256'] and len(hashes)==10,
      '5103_unique_source_references':len(canonical)==len(set(r[0] for r in canonical))==5103,
      '3_theoretical_overlap_pairs':counts['P1_theoretical_geometry_overlap']==3 and counts['P1_theoretical_geometry_overlap']==geometry['pairs_with_theoretical_2axis_overlap'],
      'no_alias_or_autocertification':all(not x['automated_alias_allowed'] and not x['reference_certified'] and x['verification_state'].startswith('TEXT_ONLY') for x in queue),
      'all_pairs_r363_reviewed':parent_pairs.issubset(set(review)),
      'source_manufacturer_not_reclassified':all(x['maker_a_SOURCE_UNVERIFIED']==geo[tuple(sorted((x['reference_a_UNVERIFIED'],x['reference_b_UNVERIFIED'])))]['maker_a_display_only'] for x in queue),
    }
    out={'schema':'bres-cat-r365-manual-review-queue-v1','milestone':'CAT-R365','parent':'CAT-R364','status':'TRIAGE_ONLY_NO_PHYSICAL_EVIDENCE',
      'canonical_count':len(canonical),'canonical_sha256':hashes,'scope':'68 theoretical OCR folding pairs; 325 typing-only pairs separately preserved in CAT-R363',
      'geometry_assumption':'each of two measured dimensions may deviate by at most ±1mm (theoretical, not instrument-calibrated)',
      'priority_counts':dict(sorted(counts.items())), 'pairs':queue,'checks':checks,'ok':all(checks.values()),
      'physical_validation':False,'catalogue_modified':False,'OCR_rule_modified':False,'manufacturer_attribution':False}
    (R/'CAT_R365_REVIEW_QUEUE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    keys=['reference_a_UNVERIFIED','reference_b_UNVERIFIED','review_priority_NOT_RECOGNITION_CONFIDENCE','catalogue_length_gap_mm_DIAGNOSTIC','catalogue_width_gap_mm_DIAGNOSTIC','geometry_theoretical_1mm_each_axis_overlap_NOT_KEY_EQUIVALENCE','maker_label_missing_SOURCE_ONLY','maker_a_SOURCE_UNVERIFIED','maker_b_SOURCE_UNVERIFIED','verification_state']
    with (R/'CAT_R365_REVIEW_QUEUE.csv').open('w',encoding='utf-8-sig',newline='') as fp:
      w=csv.DictWriter(fp,fieldnames=keys,lineterminator='\r\n');w.writeheader();w.writerows({k:r[k] for k in keys} for r in queue)
    (R/'CAT_R365_REVIEW_QUEUE.txt').write_text(f'CAT-R365 {"PASS" if out["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)}; {len(queue)} OCR text-risk pairs (3 theoretical geometry overlaps). No physical verification, no alias or OCR activation.\n'+'\n'.join(f'{k}: {v}' for k,v in sorted(counts.items()))+'\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'priority_counts':counts}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(build())