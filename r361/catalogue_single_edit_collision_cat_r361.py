#!/usr/bin/env python3
"""CAT-R361 exploratory OCR/typing collision audit over immutable V3 canons.

The source catalogue is NOT changed. A pair is a textual risk indicator,
never proof of interchangeability or a basis for autovalidation.
"""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent
# Hypothetical OCR confusions only; do not interpret as a calibrated confidence model.
OCR={'0':'O','O':'0','1':'IL','I':'1L','L':'1I','5':'S','S':'5','8':'B','B':'8'}

def make_candidates(ref):
    """Generate at most one glyph change, one swap or separator + glyph.

    This enumerates potential *text collisions*, not OCR recognition output.
    """
    for i,c in enumerate(ref):
        for replacement in OCR.get(c,''):
            yield ref[:i]+replacement+ref[i+1:],'glyph_confusable'
        if c=='-':
            minus=ref[:i]+ref[i+1:]
            yield minus,'separator_omission'
            for j,m in enumerate(minus):
                for replacement in OCR.get(m,''):
                    yield minus[:j]+replacement+minus[j+1:],'separator_omission_plus_glyph'
        if i+1<len(ref) and c!=ref[i+1]:
            yield ref[:i]+ref[i+1]+c+ref[i+2:],'adjacent_transposition'

def decide(candidate_pairs):
    """Fail closed, including the seemingly unambiguous synthetic case."""
    if not candidate_pairs:return {'status':'unknown','auto_validate':False}
    if len(candidate_pairs)>1:return {'status':'ambiguous_review','auto_validate':False}
    return {'status':'single_candidate_NOT_PHYSICALLY_CONFIRMED','auto_validate':False}

def run():
    rows,canonical_hashes,_=load_records(R.parent/'app')
    by_ref={row[0]:row for row in rows}
    full=set(by_ref)
    known_json=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    previous=json.loads((R/'CAT_R360_ABSTENTION_AUDIT.json').read_text(encoding='utf-8'))
    known={tuple(sorted((edge['reference_a'],edge['reference_b']))) for comp in known_json['components'] for edge in comp['edges']}
    causes=defaultdict(set)
    for ref in full:
        for other,kind in make_candidates(ref):
            if other in full and other!=ref:causes[tuple(sorted((ref,other)))].add(kind)
    pairs=set(causes)
    new=sorted(pairs-known)
    missing=sorted(known-pairs)
    kinds=Counter(k for vals in causes.values() for k in vals)
    review=[]
    for a,b in new:
        ma=str(by_ref[a][1] or '');mb=str(by_ref[b][1] or '')
        review.append({'reference_a':a,'reference_b':b,'edit_types':sorted(causes[(a,b)]),
          'manufacturer_a_SOURCE_UNVERIFIED':ma,'manufacturer_b_SOURCE_UNVERIFIED':mb,
          'same_manufacturer_SOURCE_ONLY':bool(ma and mb and ma==mb),
          'manufacturer_gap_SOURCE_ONLY':not bool(ma and mb),
          'physical_confirmation_required':True,'automatically_validated':False})
    checks={
      'canonical_10_hashes_still_match':canonical_hashes==previous['source_canonical_sha256'] and len(canonical_hashes)==10,
      'exactly_5103_canonical_unique':len(rows)==len(full)==5103,
      'prior_64_groups_68_edges_unchanged':previous['ocr_groups']==64 and previous['ocr_edges']==len(known)==68,
      'all_68_prior_edges_reproduced_as_textual_variants':len(missing)==0 and len(pairs&known)==68,
      'five_prior_non_glyph_edges_explained':len(known-{pair for pair,ca in causes.items() if 'glyph_confusable' in ca})==5,
      'unlisted_variants_all_adjacent_swap_only':bool(new) and all(causes[pair]=={'adjacent_transposition'} for pair in new),
      'no_unlisted_glyph_alone_or_separator_variants':not any(causes[pair]&{'glyph_confusable','separator_omission','separator_omission_plus_glyph'} for pair in new),
      'known_specific_cases_reconstructed':all(pair in causes for pair in [('AB1','BA1'),('VI2','VL2'),('VI4','VL4'),('CIL1','CLI1'),('CB3-OR','CB30R')]),
      'unknown_and_ambiguous_fail_closed':not decide([])['auto_validate'] and decide(['VI4','VL4'])['status']=='ambiguous_review',
      'single_synthetic_candidate_is_not_real_key_proof':decide(['TE8D'])['auto_validate'] is False,
      'all_new_pairs_require_manual_confirmation':all(x['physical_confirmation_required'] and not x['automatically_validated'] for x in review),
      'no_parent_audit_or_canon_modified':previous['ok'] and not previous['activated_in_application'] and not previous['maker_proven'],
    }
    obj={'schema':'bres-cat-r361-single-edit-collision-ledger-v1','milestone':'CAT-R361','parent':'CAT-R360',
      'source':'canonical V3 textual reference strings only; no photo or physical key measurements',
      'catalogue_unique_references':len(full),'canonical_sha256':canonical_hashes,
      'parent_known_ocr_groups':64,'parent_known_ocr_pairs':len(known),
      'variant_pair_count':len(pairs),'parent_pairs_matched':len(known&pairs),
      'parent_pairs_missing':missing,'new_adjacent_typing_transposition_pairs':len(new),
      'distinct_mutation_types':dict(sorted(kinds.items())),
      'novel_pairs':review,
      'fixtures':{'VI2_VL2':sorted(causes[('VI2','VL2')]),
                  'CB3_OR_CB30R':sorted(causes[('CB3-OR','CB30R')]),
                  'AB1_BA1':sorted(causes[('AB1','BA1')]),
                  'decision_on_a_single_synthetic_candidate':decide(['TE8D'])},
      'checks':checks,'activated_in_app':False,'reference_merged':False,'threshold_changed':False,
      'manufacturer_attributed':False,'samsung_physical_validated':False,'ocr_offline_certified':False,
      'ok':all(checks.values())}
    (R/'CAT_R361_SINGLE_EDIT_COLLISIONS.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (R/'CAT_R361_NEW_TYPING_COLLISIONS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(review[0]))
        writer.writeheader();writer.writerows(review)
    (R/'CAT_R361_SINGLE_EDIT_COLLISIONS.txt').write_text(
      f"CAT-R361 {'PASS' if obj['ok'] else 'FAIL'} : {sum(checks.values())}/{len(checks)} contrôles.\n"
      f"{len(pairs)} paires produites par mutations textuelles contrôlées ; les 68 paires OCR précédentes sont retrouvées.\n"
      f"{len(new)} paires nouvelles proviennent exclusivement de transpositions de frappe adjacentes, PAS d'une preuve OCR.\n"
      'Liste de revue isolée (aucune activation, aucune fusion de références).\n',encoding='utf-8')
    print(json.dumps({'ok':obj['ok'],'checks':len(checks),'pairs':len(pairs),'new_typing_pairs':len(new),'kinds':dict(kinds)},ensure_ascii=False))
    return 0 if obj['ok'] else 1
if __name__=='__main__':raise SystemExit(run())