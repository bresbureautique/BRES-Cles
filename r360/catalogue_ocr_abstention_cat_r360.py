#!/usr/bin/env python3
"""CAT-R360 audit: 64 OCR-confusable groups, manufacturers and safe abstention.

Does NOT integrate V3 into V2.28, assign a manufacturer, merge references,
set a confidence threshold or claim that an OCR result is physically correct.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from decimal import Decimal
import csv,hashlib,json
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent

def catalogue_only_decision(references, by_ref):
    """A non-activation demonstration; never returns a 'validated' status."""
    unique=list(dict.fromkeys(references))
    present=[r for r in unique if r in by_ref]
    if not present:return {'status':'unknown_catalogue','automatically_validated':False}
    if len(unique)!=1 or len(present)!=1:return {'status':'ambiguous_manual_review','automatically_validated':False}
    return {'status':'candidate_requires_physical_confirmation','automatically_validated':False}

def run():
    component=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    priority=json.loads((R/'CAT_R358_DIMENSION_PRIORITY.json').read_text(encoding='utf-8'))
    provenance=json.loads((R/'CAT_R359_SOURCE_REVIEW.json').read_text(encoding='utf-8'))
    rows,source_hashes,_=load_records(R.parent/'app');by_ref={r[0]:r for r in rows}
    groups=[];graph_pairs=set();allrefs=[];testcases=[];invalid_dimensions=[]
    priorities={tuple(sorted(g['members'])):g for g in priority['queue']}
    for group in component['components']:
        refs=group['members'];allrefs.extend(refs)
        makers=sorted({by_ref[x][1] for x in refs if by_ref[x][1]})
        missing=[x for x in refs if not by_ref[x][1]]
        dims=[]
        for x in refs:
            a,b=Decimal(str(by_ref[x][3])),Decimal(str(by_ref[x][4]))
            if not (a>0 and b>0):invalid_dimensions.append(x)
            dims.append((str(a),str(b)))
        pairs=[]
        for e in group['edges']:
            pair=tuple(sorted((e['reference_a'],e['reference_b'])))
            graph_pairs.add(pair);pairs.append(pair)
            testcases.append(catalogue_only_decision(pair,by_ref))
        pr=priorities[tuple(sorted(refs))]
        grade=pr['level'].split(' - ')[0]
        typ='fabricant_manquant' if missing else 'fabricants_distincts' if len(makers)>1 else 'meme_fabricant_catalogue'
        groups.append({'references':refs,'count':len(refs),'source_manufacturers_NOT_PHYSICALLY_VERIFIED':makers,
                       'missing_manufacturer_references':missing,'kind':typ,'dimension_values_SOURCE_ONLY':dims,
                       'priority':grade,'min_extra_uncertainty_mm_THEORETICAL_ONLY':pr['closest_extra_uncertainty_mm'],
                       'ocr_edge_count':len(pairs),'action':'EXIGER_CONFIRMATION_HUMAINE_SUR_CLE_REELLE',
                       'auto_accept':False,'maker_inferred':False,'merged':False,'threshold_changed':False})
    sample={
      'empty':catalogue_only_decision([],by_ref),
      'unknown':catalogue_only_decision(['REF_R360_IMPOSSIBLE'],by_ref),
      'single_known':catalogue_only_decision(['VI4'],by_ref),
      'confusable_pair':catalogue_only_decision(['VI4','VL4'],by_ref),
      'duplicate_single':catalogue_only_decision(['VI4','VI4'],by_ref),
      'mixed_unknown':catalogue_only_decision(['VI4','REF_R360_IMPOSSIBLE'],by_ref),
      'missing_maker_pair':catalogue_only_decision(['VI2','VL2'],by_ref),
    }
    dist=Counter(g['kind'] for g in groups);grades=Counter(g['priority'] for g in groups)
    priority8=[g for g in groups if g['priority'] in ('P0','P1','P2')]
    checks={
      'source_hashes_match_10_canonical':len(source_hashes)==10 and source_hashes==component['canonical_sha256']==priority['canonical_sha256']==provenance['canonical_sha256'],
      'source_exact_5103_unique':len(rows)==len(by_ref)==5103,
      '64_disjoint_ocr_groups':len(groups)==64 and len(allrefs)==len(set(allrefs))==130,
      '68_distinct_edges':len(graph_pairs)==68 and len(testcases)==68,
      'all_graph_edges_have_distinct_known_references':all(a!=b and a in by_ref and b in by_ref for a,b in graph_pairs),
      'priority_matches_2_2_4_56':grades=={'P0':2,'P1':2,'P2':4,'P3':56},
      '64_groups_have_source_dimensions':not invalid_dimensions,
      '59_groups_cross_maker_and_no_maker_claim':dist['fabricants_distincts']==59,
      '4_groups_same_maker_but_not_equated':dist['meme_fabricant_catalogue']==4,
      'one_group_missing_maker_VI2_VL2':dist['fabricant_manquant']==1 and any(g['references']==['VI2','VL2'] and g['kind']=='fabricant_manquant' for g in groups),
      '8_priority_7_multi_maker':len(priority8)==8 and sum(g['kind']=='fabricants_distincts' for g in priority8)==7,
      'all_68_edge_cases_reject_automatic_validation':all(o['status']=='ambiguous_manual_review' and not o['automatically_validated'] for o in testcases),
      'single_reference_not_a_real_world_proof':sample['single_known']['status']=='candidate_requires_physical_confirmation' and not sample['single_known']['automatically_validated'],
      'unknown_and_mixed_input_fail_closed':sample['unknown']['status']=='unknown_catalogue' and sample['mixed_unknown']['status']=='ambiguous_manual_review',
      'known_duplicate_does_not_create_second_candidate':sample['duplicate_single']['status']=='candidate_requires_physical_confirmation',
      'no_alias_threshold_maker_or_approval_added':all(not g[k] for g in groups for k in ('auto_accept','maker_inferred','merged','threshold_changed')),
      'provenance_CAT_R359_unchanged':provenance['ok'] and provenance['groups']==8 and provenance['priority_references']==18,
    }
    result={'schema':'bres-cat-r360-ocr-abstention-audit-v1','milestone':'CAT-R360','parent':'CAT-R359',
      'purpose':'Catalogue V3 / OCR groups: prevent unearned identification in future integration',
      'source_canonical_sha256':source_hashes,'source_graph_sha256':hashlib.sha256((R/'CAT_R356_OCR_COMPONENTS.json').read_bytes()).hexdigest(),
      'source_priority_sha256':hashlib.sha256((R/'CAT_R358_DIMENSION_PRIORITY.json').read_bytes()).hexdigest(),
      'references':len(rows),'distinct_references':len(by_ref),'ocr_groups':len(groups),'ocr_edges':len(graph_pairs),
      'groups_across_source_makers':dist['fabricants_distincts'],'groups_same_source_maker':dist['meme_fabricant_catalogue'],
      'groups_with_missing_source_maker':dist['fabricant_manquant'],'priority8_multimaker':sum(g['kind']=='fabricants_distincts' for g in priority8),
      'distribution':dict(sorted(dist.items())),'groups':groups,'decision_fixtures':sample,'checks':checks,
      'samsung_physical_validated':False,'maker_proven':False,'ocr_offline_validated':False,
      'activated_in_application':False,'ok':all(checks.values())}
    (R/'CAT_R360_ABSTENTION_AUDIT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (R/'CAT_R360_ABSTENTION_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['priorite','references','type_risque','fabricants_source_NON_CERTIFIES','fabricant_manquant','minimum_incertitude_THEORIQUE_mm','action'])
        for g in sorted(groups,key=lambda x:({'P0':0,'P1':1,'P2':2,'P3':3}[x['priority']],x['references'])):
            w.writerow([g['priority'],' / '.join(g['references']),g['kind'],' | '.join(g['source_manufacturers_NOT_PHYSICALLY_VERIFIED']),
                        ' / '.join(g['missing_manufacturer_references']),g['min_extra_uncertainty_mm_THEORETICAL_ONLY'],g['action']])
    (R/'CAT_R360_ABSTENTION_AUDIT.txt').write_text(
      f"CAT-R360 {'PASS' if result['ok'] else 'FAIL'} : {sum(checks.values())}/{len(checks)} contrôles.\n"
      f"64 groupes OCR / 68 paires : {dist['fabricants_distincts']} multi-fabricants, {dist['meme_fabricant_catalogue']} mono-fabricant, "
      f"{dist['fabricant_manquant']} avec fabricant absent.\n"
      'Aucune correction automatique; il faut des clés physiques certaines avant activation de règles.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'cross_maker':dist['fabricants_distincts'],'priority8_multi_maker':result['priority8_multimaker']}))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())