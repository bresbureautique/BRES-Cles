#!/usr/bin/env python3
"""CAT-R364: deterministic, non-decision audit of lossy OCR transcription folds.

Folding combines glyph confusions O/0, I/L/1, S/5, B/8 and removal of '-'.
These are theoretical risk sets ONLY. No source key, maker, OCR rule or
physical equivalence is ever changed/confirmed. Output can be rebuilt offline.
"""
from __future__ import annotations
import csv,hashlib,itertools,json,sys
from pathlib import Path
from collections import defaultdict,Counter
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
REPLACE=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8'})
def fold(s):return s.upper().translate(REPLACE).replace('-','')
def filehash(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def generate():
    rows,hashes,_=load_records(R.parent/'app')
    references={str(r[0]):str(r[1] or '') for r in rows}
    prior=json.loads((R/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text(encoding='utf-8'))
    old={(x['reference_a'],x['reference_b']) for x in prior['pairs'] if x['already_known_hypothetical_OCR']}
    allold={(x['reference_a'],x['reference_b']) for x in prior['pairs']}
    groups=defaultdict(list)
    for ref in sorted(references):groups[fold(ref)].append(ref)
    collision=[];edges=set()
    for fold_key,refs in sorted(groups.items()):
        if len(refs)<2:continue
        refs=sorted(refs)
        edges.update(tuple(sorted(pair)) for pair in itertools.combinations(refs,2))
        names=[references[r] for r in refs]
        collision.append({
          'folded_transcription_NOT_REFERENCE':fold_key,
          'source_references_distinct':refs,
          'reference_count':len(refs),
          'source_makers_UNVERIFIED':dict(zip(refs,names)),
          'unknown_maker_in_group':any(not n for n in names),
          'different_maker_labels_SOURCE_ONLY':len(set(n for n in names if n))>1,
          'risk_class':'TEXT_OCR_FOLD_ONLY',
          'physical_equivalence_verified':False,
          'automatic_recognition_allowed':False,
          'manual_confirmation_required':True,
        })
    pairs=[list(pair) for pair in sorted(edges)]
    exact_checks={
       'parent_ledger_passes':prior['ok'] is True,
       '5103_canonically_distinct':len(rows)==len(references)==5103,
       'canonical_fragments_unchanged':hashes==prior['canonical_sha256'] and len(hashes)==10,
       '64_theoretical_OCR_fold_groups':len(collision)==64,
       '130_endpoints_in_groups':sum(x['reference_count'] for x in collision)==130,
       '68_fold_pairs_match_prior_OCR_edges_exactly':len(edges)==len(old)==68 and edges==old,
       '325_typing_pairs_NOT_OCR_fold_equivalence':len(allold-edges)==325,
       '393_prior_review_pairs_exhaustively_partitioned':edges.issubset(allold) and len(allold)==393,
       'important_VI2_VL2_still_distinct_source_refs':('VI2','VL2') in edges and references['VI2']!=references['VL2'],
       'important_BK3_4_BK34_distinct_source_refs':('BK3-4','BK34') in edges,
       'no_assignment_or_validation':all(not x['automatic_recognition_allowed'] and not x['physical_equivalence_verified'] and x['manual_confirmation_required'] for x in collision),
       'no_input_canonical_changes':all(x['reference_count']==len(set(x['source_references_distinct'])) for x in collision),
    }
    result={'schema':'bres-cat-r364-lossy-ocr-fold-audit-v1','milestone':'CAT-R364','parent':'CAT-R363',
       'fold_method':'uppercase, O/I/L/S/B glyph-to-digit, remove hyphen (analysis only)',
       'meaning':'Lossy transcription is never a key identity or proof of common manufacturer.',
       'canonical_sha256':hashes,'canonical_reference_count':len(rows),
       'fold_collision_groups':len(collision),'distinct_endpoints':len({r for x in collision for r in x['source_references_distinct']}),
       'folded_pairs':len(edges),'distinct_typing_pairs_unrelated_to_fold':len(allold-edges),
       'folded_pair_sources':pairs,'groups':collision,'checks':exact_checks,'ok':all(exact_checks.values()),
       'physical_key_review':False,'manufacturer_attribution':False,'catalogue_mutation':False,'active_OCR_change':False}
    (R/'CAT_R364_OCR_FOLD_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/'CAT_R364_OCR_FOLD_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as f:
        keys=['folded_transcription_NOT_REFERENCE','source_references_distinct','reference_count','unknown_maker_in_group','different_maker_labels_SOURCE_ONLY','risk_class','manual_confirmation_required','automatic_recognition_allowed']
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\r\n');w.writeheader()
        for row in collision:
            w.writerow({**{k:row[k] for k in keys},'source_references_distinct':' | '.join(row['source_references_distinct'])})
    (R/'CAT_R364_OCR_FOLD_AUDIT.txt').write_text(
      f'CAT-R364 {"PASS" if result["ok"] else "FAIL"}: {sum(exact_checks.values())}/{len(exact_checks)} controls, 64 fold groups, 130 references, 68 hypothetical OCR pairs.\n'
      'The 325 other pairs remain typing-only; no key/maker equivalence or OCR rule established.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(exact_checks),'failed':[k for k,v in exact_checks.items() if not v],'groups':len(collision),'pairs':len(edges),'unknown_maker_groups':sum(x['unknown_maker_in_group'] for x in collision)},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(generate())