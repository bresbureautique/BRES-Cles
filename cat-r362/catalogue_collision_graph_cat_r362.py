#!/usr/bin/env python3
"""CAT-R362: deterministic review groups for purely textual collision hypotheses.

The canonical V3 catalogue, manufacturers, OCR rules and physical validation
remain untouched. Graph edges encode plausible transcription/typing confusions,
NOT interchangeable physical key blanks.
"""
from __future__ import annotations
import csv,hashlib,json,sys
sys.dont_write_bytecode=True
from collections import Counter,defaultdict
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
from catalogue_single_edit_collision_cat_r361 import make_candidates,decide
R=Path(__file__).resolve().parent

def run():
    rows,canonical_hashes,_=load_records(R.parent/'app')
    prior=json.loads((R/'CAT_R361_SINGLE_EDIT_COLLISIONS.json').read_text(encoding='utf-8'))
    prev=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    by_ref={str(rec[0]):str(rec[1] or '').strip() for rec in rows}
    canonical=set(by_ref)
    dsu={ref:ref for ref in canonical}
    def find(ref):
        while dsu[ref]!=ref:
            dsu[ref]=dsu[dsu[ref]];ref=dsu[ref]
        return ref
    def join(a,b):
        a=find(a);b=find(b)
        if a!=b:dsu[max(a,b)]=min(a,b)
    causes=defaultdict(set)
    for ref in sorted(canonical):
        for other,kind in make_candidates(ref):
            if other in canonical and other!=ref:
                causes[tuple(sorted((ref,other)))].add(kind)
    old_edges={tuple(sorted((e['reference_a'],e['reference_b'])))
             for comp in prev['components'] for e in comp['edges']}
    for (a,b) in sorted(causes):join(a,b)
    related=defaultdict(set)
    for a,b in sorted(causes):related[find(a)].update((a,b))
    comps=[];rows_csv=[];seen=set()
    for members in sorted((tuple(sorted(v)) for v in related.values()),key=lambda v:(-len(v),v)):
        if any(x in seen for x in members):raise AssertionError('Component overlap')
        seen.update(members)
        edges=[(a,b) for a,b in sorted(causes) if a in members and b in members]
        kinds=Counter(k for pair in edges for k in causes[pair])
        old_edge_count=sum(e in old_edges for e in edges)
        typing_edge_count=sum('adjacent_transposition' in causes[e] and e not in old_edges for e in edges)
        src_makers=sorted({by_ref[v] for v in members if by_ref[v]})
        unresolved=sum(not by_ref[v] for v in members)
        # Priority is a REVIEW QUEUE grouping, not confidence in a match.
        priority=('P1_multiref_OCR_review' if len(members)>=3 and old_edge_count else
                  'P2_OCR_review' if old_edge_count else
                  'P3_multiref_typing_review' if len(members)>=3 else 'P4_typing_review')
        comp_id=f'C{len(comps)+1:04d}'
        comp={'component':comp_id,'references':list(members),'reference_count':len(members),
              'edge_count':len(edges),'prior_known_OCR_pair_count':old_edge_count,
              'new_typing_pair_count':typing_edge_count,'edit_type_counts':dict(sorted(kinds.items())),
              'source_manufacturers_UNVERIFIED':src_makers,
              'missing_source_maker_count':unresolved,
              'review_priority_NOT_IDENTIFICATION':priority,
              'physical_key_confirmation_needed':True,'auto_validate':False,'merge':False}
        comps.append(comp)
        rows_csv.append({'component':comp_id,'priority':priority,'references':' | '.join(members),
                         'reference_count':len(members),'collision_edges':len(edges),
                         'prior_OCR_pairs':old_edge_count,'new_typing_pairs':typing_edge_count,
                         'source_makers_UNVERIFIED':' | '.join(src_makers),
                         'source_maker_missing_count':unresolved,
                         'physical_key_confirmed':'NO','auto_validate':'NO','catalogue_edit':'NO'})
    # Deterministic coverage without assuming that graph proximity is identity.
    class_count=Counter(comp['review_priority_NOT_IDENTIFICATION'] for comp in comps)
    vertex_degree=Counter(v for edge in causes for v in edge)
    all_ref_covered=set(ref for comp in comps for ref in comp['references'])
    checks={
      'source_same_10_canonical_hashes':canonical_hashes==prior['canonical_sha256'] and len(canonical_hashes)==10,
      'unique_5103_references':len(rows)==len(canonical)==5103,
      'R361_393_edges_reproduced':len(causes)==prior['variant_pair_count']==393,
      'all_68_historic_OCR_edges_covered':len(old_edges)==68 and old_edges.issubset(causes),
      '325_only_new_typing_edges':sum(edge not in old_edges for edge in causes)==325 and all(causes[e]=={'adjacent_transposition'} for e in causes if e not in old_edges),
      'all_edges_in_component_and_bidirectional':all(find(a)==find(b) for a,b in causes),
      'every_graph_vertex_exactly_one_component':all_ref_covered==set(vertex_degree) and sum(len(comp['references']) for comp in comps)==len(all_ref_covered),
      'component_edge_partition_exact':sum(comp['edge_count'] for comp in comps)==len(causes),
      'source_manufacturers_not_assumed_confirmed':all(comp['physical_key_confirmation_needed'] and not comp['auto_validate'] for comp in comps),
      'review_priority_not_automatic_match':all(comp['review_priority_NOT_IDENTIFICATION'].startswith('P') and not comp['merge'] for comp in comps),
      'all_reference_types_fail_closed':not decide([])['auto_validate'] and not decide(['AB1'])['auto_validate'] and not decide(['AB1','BA1'])['auto_validate'],
      'known_pilot_case_VI2_and_VL2_grouped':any({'VI2','VL2'}.issubset(set(comp['references'])) for comp in comps),
      'typing_case_AB1_BA1_grouped':any({'AB1','BA1'}.issubset(set(comp['references'])) for comp in comps),
      'no_software_catalogue_activation':prior['activated_in_app'] is False and prior['manufacturer_attributed'] is False,
    }
    result={'schema':'bres-cat-r362-text-collision-review-graph-v1','milestone':'CAT-R362','parent':'CAT-R361',
            'scope':'Risk review from canonical text only; no OCR image observed and no physical match established',
            'canonical_sha256':canonical_hashes,'unique_references':len(canonical),
            'collision_edges':len(causes),'legacy_OCR_edges':len(old_edges),
            'new_typing_edges':len(causes)-len(old_edges),'graph_vertices':len(all_ref_covered),
            'component_count':len(comps),'largest_component_size':max(len(comp['references']) for comp in comps),
            'review_priority_counts':dict(sorted(class_count.items())),
            'components':comps,'checks':checks,'ok':all(checks.values()),
            'data_modified':False,'OCR_rule_activated':False,'samsung_test_repeated':False,
            'manufacturer_confirmed':False,'physical_key_validated':False}
    (R/'CAT_R362_TEXT_COLLISION_GRAPH.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/'CAT_R362_REVIEW_COMPONENTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows_csv[0]));writer.writeheader();writer.writerows(rows_csv)
    (R/'CAT_R362_TEXT_COLLISION_GRAPH.txt').write_text(
        f'CAT-R362 {"PASS" if result["ok"] else "FAIL"} : {sum(checks.values())}/{len(checks)} contrôles.\n'
        f'{len(causes)} paires hypothétiques ; {len(all_ref_covered)} références dans {len(comps)} groupes de revue.\n'
        f'68 paires OCR textuelles déjà connues et 325 transpositions de frappe ; zéro nouvelle preuve physique.\n'
        f'File de revue : {dict(class_count)} ; aucune référence fusionnée, aucun fabricant confirmé.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'checks':len(checks),'components':len(comps),'vertices':len(all_ref_covered),'max_component':result['largest_component_size'],'priorities':dict(class_count)},ensure_ascii=False))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
