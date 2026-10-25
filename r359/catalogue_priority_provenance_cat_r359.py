#!/usr/bin/env python3
"""CAT-R359: independent, hash-verified 8-group source dossiers for manual OCR review.
Never transfer the V3 catalogue into the V2.28 pilot, infer a maker or change a threshold.
"""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent


def build_packets(groups,by_ref):
    packets=[]
    for group in groups:
        refs=group['members']
        if len(refs)!=len(set(refs)) or len(refs)<2 or any(ref not in by_ref for ref in refs):
            raise ValueError('invalid_ocr_group_or_missing_reference')
        source=[]
        for ref in refs:
            row=by_ref[ref]
            if len(row)<5:raise ValueError('invalid_source_record')
            source.append({'reference':ref,'maker_as_catalogue_source_UNVERIFIED':row[1] or None,
                           'length_mm_as_catalogue':row[3], 'width_mm_as_catalogue':row[4],
                           'manufacturer_proof':False,'physical_dimension_proof':False})
        packets.append({'level':group['level'],'members':refs,'min_extra_uncertainty_mm_REPORT_ONLY':group['closest_extra_uncertainty_mm'],
                        'source_details':source,'known_makers_in_source':sorted({x['maker_as_catalogue_source_UNVERIFIED'] for x in source if x['maker_as_catalogue_source_UNVERIFIED']}),
                        'distinct_references':len(source),'manually_verify_reference_and_dimension':True,
                        'approved_alias':False,'maker_attributed':False,'threshold_changed':False})
    return packets


def main():
    audit=json.loads((R/'CAT_R358_DIMENSION_PRIORITY.json').read_text(encoding='utf-8'))
    component=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    records,hashes,prior=load_records(R.parent/'app')
    unique={row[0]:row for row in records}
    selected=[group for group in audit['queue'] if group['level'].startswith(('P0','P1','P2'))]
    packets=build_packets(selected,unique)
    allrefs=[ref for packet in packets for ref in packet['members']]
    graph_pairs={tuple(sorted(edge[k] for k in ('reference_a','reference_b')))
                 for comp in component['components'] for edge in comp['edges']}
    def reject_fixture(group,rows):
        try:build_packets([group],rows)
        except ValueError:return True
        return False
    fixture={'missing_ref_rejected':reject_fixture({'members':['ABC','MISSING'],'level':'P1','closest_extra_uncertainty_mm':'0.1'}, {'ABC':['ABC','X','1',45,20]}),
             'duplicate_ref_rejected':reject_fixture({'members':['ABC','ABC'],'level':'P1','closest_extra_uncertainty_mm':'0.1'}, {'ABC':['ABC','X','1',45,20]}),
             'truncated_record_rejected':reject_fixture({'members':['ABC','DEF'],'level':'P1','closest_extra_uncertainty_mm':'0.1'}, {'ABC':['ABC'], 'DEF':['DEF','X','2',45,20]})}
    checks={
      'source_10_canonical_hashes_match':len(hashes)==10 and hashes==audit['canonical_sha256']==component['canonical_sha256'],
      'source_has_5103_unique_rows':len(records)==len(unique)==5103,
      'graph_68_edges_original':len(graph_pairs)==68 and component['edges']==68,
      'review_exactly_8_priority_groups':len(packets)==8 and len(selected)==audit['priority_up_to_half_mm'],
      'priority_groups_exact_2_2_4':Counter(p['level'].split(' - ')[0] for p in packets)==Counter({'P0':2,'P1':2,'P2':4}),
      'priority_refs_exist_and_no_overlapping_groups':len(set(allrefs))==len(allrefs) and set(allrefs).issubset(unique),
      'groups_induced_from_audited_edges':all(any(set(edge).issubset(p['members']) for edge in graph_pairs) for p in packets),
      'VI4_VL4_is_priority_0':set(packets[0]['members'])=={'VI4','VL4'},
      'VI4R_VL4R_is_priority_0':set(packets[1]['members'])=={'VI4R','VL4R'},
      'triples_remain_separate_and_unmerged':{tuple(p['members']) for p in packets if len(p['members'])==3}=={('CIL1','CLI1','CLL1'),('KF1','KFI','KFL')},
      'no_inferred_maker_or_threshold':all(p['manually_verify_reference_and_dimension'] and not p['maker_attributed'] and not p['approved_alias'] and not p['threshold_changed'] for p in packets),
      'source_maker_not_claimed_verified':all(not x['manufacturer_proof'] and not x['physical_dimension_proof'] for p in packets for x in p['source_details']),
      'negative_fixtures':all(fixture.values()),
    }
    out={'schema':'bres-cat-r359-priority-source-provenance-v1','milestone':'CAT-R359','parent':'CAT-R358',
         'scope':'catalogue SOURCE data only: measurements and makers unverified physically',
         'canonical_sha256':hashes,'source_priority_sha256':hashlib.sha256((R/'CAT_R358_DIMENSION_PRIORITY.json').read_bytes()).hexdigest(),
         'source_graph_sha256':hashlib.sha256((R/'CAT_R356_OCR_COMPONENTS.json').read_bytes()).hexdigest(),
         'canonical_records':len(records),'distinct_references':len(unique),'groups':len(packets),
         'priority_references':len(allrefs),'manual_packets':packets,'fixtures':fixture,'checks':checks,
         'samsung_calibration':False,'physical_identification_claimed':False,'maker_promoted':False,
         'ok':all(checks.values())}
    (R/'CAT_R359_SOURCE_REVIEW.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (R/'CAT_R359_SOURCE_REVIEW.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['priorite','groupe','reference','fabricant_catalogue_NON_VERIFIE','longueur_catalogue_mm','largeur_catalogue_mm','incertitude_supplementaire_THEORIQUE_mm','etat'])
        for p in packets:
            for row in p['source_details']:
                w.writerow([p['level'],' / '.join(p['members']),row['reference'],row['maker_as_catalogue_source_UNVERIFIED'] or '',row['length_mm_as_catalogue'],row['width_mm_as_catalogue'],p['min_extra_uncertainty_mm_REPORT_ONLY'],'A VERIFIER SUR REFERENCE CERTAINE'])
    (R/'CAT_R359_SOURCE_REVIEW.txt').write_text(
      f"CAT-R359 : {sum(checks.values())}/{len(checks)} contrôles {'PASS' if out['ok'] else 'FAIL'} ; "
      f"{len(packets)} groupes prioritaires ; {len(allrefs)} références dans les groupes.\n"
      'Dimensions et fabricants = valeurs catalogue NON certifiées physiquement. Aucun alias, fabricant ou seuil activé.\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'priority_groups':len(packets),'references':len(allrefs)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())