#!/usr/bin/env python3
"""CAT-R363: immutable, reproducible pair-by-pair review ledger.

A candidate edge describes a textual transcription/typing hazard, never a
physical match. Catalogue V3 chunks and maker attribution remain untouched.
"""
from __future__ import annotations
import csv,hashlib,json,sys
sys.dont_write_bytecode=True
from pathlib import Path
from collections import Counter,defaultdict
from catalogue_audit_cat_r349 import load_records
from catalogue_single_edit_collision_cat_r361 import make_candidates, decide
R=Path(__file__).resolve().parent

def produce():
    rows,hashes,_=load_records(R.parent/'app')
    by_ref={str(r[0]):str(r[1] or '').strip() for r in rows}
    prior=json.loads((R/'CAT_R362_TEXT_COLLISION_GRAPH.json').read_text(encoding='utf-8'))
    before=json.loads((R/'CAT_R361_SINGLE_EDIT_COLLISIONS.json').read_text(encoding='utf-8'))
    graph_map={ref:c for c in prior['components'] for ref in c['references']}
    known=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    old_pairs={tuple(sorted((e['reference_a'],e['reference_b']))) for group in known['components'] for e in group['edges']}
    edges=defaultdict(set)
    for ref in sorted(by_ref):
        for candidate,kind in make_candidates(ref):
            if candidate in by_ref and ref!=candidate:
                edges[tuple(sorted((ref,candidate)))].add(kind)
    ledger=[]
    for (a,b),kinds in sorted(edges.items()):
        comp=graph_map[a]
        if graph_map[b]['component']!=comp['component']:raise RuntimeError('Edge crosses components')
        same=bool(by_ref[a] and by_ref[b] and by_ref[a]==by_ref[b])
        missing=(not by_ref[a] or not by_ref[b])
        rec={
          'reference_a':a,'reference_b':b,'component':comp['component'],
          'review_priority_NOT_MATCH_CONFIDENCE':comp['review_priority_NOT_IDENTIFICATION'],
          'edit_types':sorted(kinds),'already_known_hypothetical_OCR':(a,b) in old_pairs,
          'manufacturer_a_UNVERIFIED':by_ref[a], 'manufacturer_b_UNVERIFIED':by_ref[b],
          'same_manufacturer_SOURCE_ONLY':same,'manufacturer_missing_SOURCE_ONLY':missing,
          'physical_match_confirmed':False,'maker_confirmed':False,'auto_validate':False,
          'catalogue_merge_allowed':False,'review_state':'UNVERIFIED_TEXT_ONLY'
        }
        ledger.append(rec)
    vertices=sorted({v for e in edges for v in e})
    priority=Counter(x['review_priority_NOT_MATCH_CONFIDENCE'] for x in ledger)
    checks={
        'parent_graph_PASS':prior['ok'] and before['ok'],
        'canonical_10_chunks_identical':len(hashes)==10 and hashes==prior['canonical_sha256'],
        '5103_distinct_source_refs':len(rows)==len(by_ref)==5103,
        'all_393_edges_exact':len(ledger)==prior['collision_edges']==393,
        'known_68_edges_exact':len(old_pairs)==sum(x['already_known_hypothetical_OCR'] for x in ledger)==68,
        '325_unverified_typing_edges':sum(not x['already_known_hypothetical_OCR'] for x in ledger)==325,
        '732_endpoints_and_345_review_groups':len(vertices)==prior['graph_vertices']==732 and len({x['component'] for x in ledger})==prior['component_count']==345,
        'components_match_reference_membership':all(x['reference_a'] in graph_map[x['reference_b']]['references'] for x in ledger),
        'priority_is_review_not_auto_validation':all(x['review_state']=='UNVERIFIED_TEXT_ONLY' and not x['auto_validate'] and not x['physical_match_confirmed'] and not x['maker_confirmed'] for x in ledger),
        'none_of_the_393_pairs_are_merged':all(not x['catalogue_merge_allowed'] for x in ledger),
        'synthetic_single_candidate_still_abstains':not decide(['TE8D'])['auto_validate'],
        'canonical_keys_are_contained':set(vertices).issubset(by_ref),
    }
    data={'schema':'bres-cat-r363-pair-review-ledger-v1','milestone':'CAT-R363','parent':'CAT-R362',
          'method':'canonical text single-edit OCR glyph/adjacent typing or separator only',
          'note':'Pairs are review hints, not physical equivalence, verified OCR errors, manufacturer identity or machine-match evidence.',
          'canonical_sha256':hashes,'reference_count':len(by_ref),'edge_count':len(ledger),
          'distinct_endpoints':len(vertices),'review_groups':prior['component_count'],
          'old_OCR_theoretical_edges':len(old_pairs),'new_typing_theoretical_edges':len(ledger)-len(old_pairs),
          'priority_counts_EDGES':dict(sorted(priority.items())),'all_test_reference_strings':vertices,
          'pairs':ledger,'checks':checks,'ok':all(checks.values()),
          'physical_validation':False,'app_rule_activation':False,'catalogue_modified':False}
    (R/'CAT_R363_PAIR_REVIEW_LEDGER.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (R/'CAT_R363_PAIR_REVIEW_LEDGER.csv').open('w',encoding='utf-8-sig',newline='') as out:
        cols=['component','review_priority_NOT_MATCH_CONFIDENCE','reference_a','reference_b','edit_types','already_known_hypothetical_OCR','manufacturer_a_UNVERIFIED','manufacturer_b_UNVERIFIED','same_manufacturer_SOURCE_ONLY','manufacturer_missing_SOURCE_ONLY','review_state','auto_validate']
        w=csv.DictWriter(out,fieldnames=cols,lineterminator='\r\n');w.writeheader()
        for r in ledger:w.writerow({**{k:r[k] for k in cols},'edit_types':' | '.join(r['edit_types'])})
    (R/'CAT_R363_PAIR_REVIEW_LEDGER.txt').write_text(
        f'CAT-R363 {"PASS" if data["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)} checks; 393 theoretical pairs, 732 endpoints, 345 groups.\n'
        'NO physical key verification, manufacturer confirmation, catalogue merge, OCR activation or automatic acceptance.\n',encoding='utf-8')
    print(json.dumps({'ok':data['ok'],'checks':len(checks),'pairs':len(ledger),'refs':len(vertices),'failed':[k for k,v in checks.items() if not v]}))
    return 0 if data['ok'] else 1
if __name__=='__main__':raise SystemExit(produce())
