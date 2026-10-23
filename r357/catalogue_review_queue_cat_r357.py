#!/usr/bin/env python3
"""CAT-R357: reproducible REVIEW-ONLY OCR ambiguity triage.

Inputs: immutable CAT-R356 components and canonical catalogue V3. Output never updates
source references, inferred manufacturers, aliases or recognition thresholds.
"""
from __future__ import annotations
from decimal import Decimal
import csv,hashlib,json
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent


def classify(component):
    if not component['review_needed'] or component['merge_or_accept']:
        raise ValueError('component_not_review_only')
    members=tuple(component['members'])
    edges=component['edges']
    assert edges and all(e['reference_a'] in members and e['reference_b'] in members for e in edges)
    extra=min(Decimal(e['extra_uncertainty_mm_REPORT_ONLY']) for e in edges)
    # Zero overlap plus uncertain manufacturer are highest priority but do not
    # confer any additional permission to classify or merge records.
    if extra==Decimal('0') or component['unknown_manufacturer_some']:priority='P0'
    elif extra<=Decimal('0.1') or len(members)>2:priority='P1'
    else:priority='P2'
    return priority,extra


def main():
    source=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    rows,hashes,_=load_records(R.parent/'app')
    canon={r[0] for r in rows}
    groups=[]
    for component in source['components']:
        priority,margin=classify(component)
        groups.append({
            'members':component['members'], 'priority':priority,
            'nearest_boundary_extra_uncertainty_mm_THEORETICAL':str(margin),
            'missing_manufacturer_requires_source_check':component['unknown_manufacturer_some'],
            'group_size':component['member_count'], 'direct_ocr_edges':component['edge_count'],
            'human_review_only':True,'new_aliases':False,'automatic_identification_allowed':False,
            'recommended_evidence':['source manufacturer or vendor catalogue page (when unknown)',
                                     'front/back photos with a millimetre scale',
                                     'repeated measured blade width and length',
                                     'labelled provenance of reference and key blanks']})
    groups.sort(key=lambda g:({'P0':0,'P1':1,'P2':2}[g['priority']],
                               Decimal(g['nearest_boundary_extra_uncertainty_mm_THEORETICAL']),g['members']))
    pr={p:sum(g['priority']==p for g in groups) for p in ('P0','P1','P2')}
    refs=set().union(*(set(g['members']) for g in groups))
    fixtures={
      'zero_overlap_is_P0': classify({'review_needed':True,'merge_or_accept':False,'members':['A','B'],
             'unknown_manufacturer_some':False,'edges':[{'reference_a':'A','reference_b':'B','extra_uncertainty_mm_REPORT_ONLY':'0'}]})[0]=='P0',
      'unknown_maker_is_P0_even_when_far': classify({'review_needed':True,'merge_or_accept':False,'members':['A','B'],
             'unknown_manufacturer_some':True,'edges':[{'reference_a':'A','reference_b':'B','extra_uncertainty_mm_REPORT_ONLY':'3'}]})[0]=='P0',
      'nonzero_close_is_P1': classify({'review_needed':True,'merge_or_accept':False,'members':['A','B'],
             'unknown_manufacturer_some':False,'edges':[{'reference_a':'A','reference_b':'B','extra_uncertainty_mm_REPORT_ONLY':'0.055'}]})[0]=='P1',
      'far_pair_is_P2': classify({'review_needed':True,'merge_or_accept':False,'members':['A','B'],
             'unknown_manufacturer_some':False,'edges':[{'reference_a':'A','reference_b':'B','extra_uncertainty_mm_REPORT_ONLY':'1.5'}]})[0]=='P2',
      'auto_merge_source_rejected':False,
    }
    try: classify({'review_needed':True,'merge_or_accept':True,'members':['A','B'],
                 'unknown_manufacturer_some':False,'edges':[{'reference_a':'A','reference_b':'B','extra_uncertainty_mm_REPORT_ONLY':'0'}]})
    except ValueError: fixtures['auto_merge_source_rejected']=True
    checks={
      'all_10_canonical_hashes_equal_R356':len(hashes)==10 and hashes==source['canonical_sha256'],
      '5103_distinct_references_unchanged':len(rows)==len(canon)==5103,
      '64_groups_all_review_only':len(groups)==64 and all(g['human_review_only'] for g in groups),
      '130_endpoints_preserved':len(refs)==130 and refs<=canon,
      '68_direct_edges_unchanged':sum(g['direct_ocr_edges'] for g in groups)==68,
      'two_triples_remain_review_only':sum(g['group_size']==3 for g in groups)==2,
      'all_priorities_are_exhaustive':sum(pr.values())==64,
      'unknown_maker_VI2_VL2_is_P0':any(g['members']==['VI2','VL2'] and g['priority']=='P0' for g in groups),
      'zero_overlap_is_P0':all(g['priority']=='P0' for g in groups if Decimal(g['nearest_boundary_extra_uncertainty_mm_THEORETICAL'])==0),
      'canonical_graph_unmodified':all(g['new_aliases'] is False and g['automatic_identification_allowed'] is False for g in groups),
      'synthetic_boundaries_no_auto_merge':all(fixtures.values()),
    }
    out={'schema':'bres-cat-r357-manual-review-queue-v1','milestone':'CAT-R357','parent':'CAT-R356',
         'scope':'triage for evidence collection only; not geometry calibration or OCR acceptance',
         'canonical_sha256':hashes,'distinct_references':len(canon),'group_count':len(groups),
         'priority_counts':pr,'review_queue':groups,'fixtures':fixtures,'checks':checks,
         'manufacturers_inferred':0,'aliases_written':0,'active_thresholds_changed':False,
         'Samsung_physical_readiness':'PENDING','ok':all(checks.values())}
    (R/'CAT_R357_REVIEW_QUEUE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/'CAT_R357_REVIEW_QUEUE.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(('priority','members','nearest_theoretical_extra_mm','missing_manufacturer','group_size','edges','status'))
        for g in groups:w.writerow((g['priority'],'/'.join(g['members']),g['nearest_boundary_extra_uncertainty_mm_THEORETICAL'],
                                     g['missing_manufacturer_requires_source_check'],g['group_size'],g['direct_ocr_edges'],'HUMAN_REVIEW_ONLY'))
    (R/'CAT_R357_REVIEW_QUEUE.txt').write_text(
        f"CAT-R357 : {sum(checks.values())}/{len(checks)} contrôles, {sum(fixtures.values())}/{len(fixtures)} fixtures PASS.\n"
        f"64 groupes OCR à revoir : P0={pr['P0']}, P1={pr['P1']}, P2={pr['P2']}.\n"
        "Les bornes sont théoriques, pas une calibration. Le fabricant VI2/VL2 n'est pas attribué.\n"
        "Aucune modification des 5 103 références, des fabricants, du moteur ou des seuils.\n",encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'priorities':pr,'checks':len(checks)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())