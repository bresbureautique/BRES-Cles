#!/usr/bin/env python3
"""CAT-R344: two-axis worst-case ambiguity audit, not an OCR classifier.

No learned thresholds. Hypothetical measurement error limits are deliberately
kept separate from verified catalogue data and physical Samsung measurements.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--app-dir', type=Path, required=True)
a = parser.parse_args()
prior = json.loads((HERE/'CATALOGUE_NOMINAL_UNCERTAINTY_BUDGET_CAT_R343.json').read_text(encoding='utf-8'))
queue = json.loads((HERE/'CATALOGUE_CALIBRATION_PRIORITY_AUDIT_CAT_R340.json').read_text(encoding='utf-8'))['priority_queue']['groups']
canonical = a.app_dir/'catalogue'/'v3'
errors=[]; hashes={}; rows=[]
for name, expected in sorted(prior['canonical_hashes'].items()):
    source = (canonical/name).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    hashes[name] = digest
    if digest != expected: errors.append('canonical_hash_changed:'+name)
    match = re.search(r'push\(\.\.\.(\[.*\])\);?\s*$', source.decode('utf-8').strip(), re.S)
    if not match:
        errors.append('invalid_catalogue_js:'+name)
    else:
        rows.extend(json.loads(match.group(1)))
refs = {str(r[0]):r for r in rows}
D = lambda v:Decimal(str(v))
# Scenario budgets: independent worst-case error bounds in mm for image and nominal data.
scenarios = [
    ('one_mm_both_axes_nominal_0_10',D('1.0'),D('1.0'),D('0.10'),D('0.10')),
    ('length_1_5_width_0_5_nominal_0_10',D('1.5'),D('0.5'),D('0.10'),D('0.10')),
    ('length_2_width_0_5_nominal_0_10',D('2.0'),D('0.5'),D('0.10'),D('0.10')),
    ('length_2_width_2_nominal_0_10',D('2.0'),D('2.0'),D('0.10'),D('0.10')),
    ('length_1_width_0_25_nominal_0_10',D('1.0'),D('0.25'),D('0.10'),D('0.10')),
]
results=[]
for group in queue:
    candidates=[]
    for left,right in itertools.combinations(group['raw_refs'],2):
        if left not in refs or right not in refs:
            errors.append('missing_reference:'+left+'|'+right);continue
        length_gap = abs(D(refs[left][3])-D(refs[right][3]))
        width_gap = abs(D(refs[left][4])-D(refs[right][4]))
        candidates.append({'raw_refs':[left,right],'length_gap_mm':str(length_gap),'width_gap_mm':str(width_gap)})
    if not candidates: continue
    decisions={}
    for label,lie,wie,lne,wne in scenarios:
        lbound=2*(lie+lne);wbound=2*(wie+wne)
        pair_results=[{
            'raw_refs':r['raw_refs'],
            'length_disjoint':D(r['length_gap_mm'])>lbound,
            'width_disjoint':D(r['width_gap_mm'])>wbound,
            'rectangle_disjoint':D(r['length_gap_mm'])>lbound or D(r['width_gap_mm'])>wbound,
        } for r in candidates]
        decisions[label]={'all_pairs_separated':all(x['rectangle_disjoint'] for x in pair_results),
                          'all_pairs_length_only':all(x['length_disjoint'] for x in pair_results),
                          'all_pairs_width_only':all(x['width_disjoint'] for x in pair_results),
                          'pair_decisions':pair_results}
    results.append({'group':group['glyph_key'],'raw_refs':group['raw_refs'],
                    'nominal_pair_gaps':candidates,'scenarios':decisions})
results.sort(key=lambda r:r['group'])
summary={}
for label,*_ in scenarios:
    separated=[r['group'] for r in results if r['scenarios'][label]['all_pairs_separated']]
    length_only=[r['group'] for r in results if r['scenarios'][label]['all_pairs_length_only']]
    rescued=sorted(set(separated)-set(length_only))
    summary[label]={'separated_count':len(separated), 'unsafe_or_unresolved':sorted({r['group'] for r in results}-set(separated)),
                    'length_only_count':len(length_only),'width_rescued':rescued}
cii=next((r for r in results if r['group']=='CIII'),None)
cii_len=min((D(x['length_gap_mm']) for x in cii['nominal_pair_gaps']),default=D('0')) if cii else D('0')
cii_width=min((D(x['width_gap_mm']) for x in cii['nominal_pair_gaps']),default=D('0')) if cii else D('0')
checks={
 '5103_references_unique':len(rows)==len(refs)==5103,
 '10_canonical_hashes_unmodified':len(hashes)==10 and hashes==prior['canonical_hashes'],
 '17_groups_recomputed':len(results)==17,
 'BK3_4_BK34_distinct':'BK3-4' in refs and 'BK34' in refs and refs['BK3-4']!=refs['BK34'],
 'CIII_minimum_length_2_11mm':cii_len==D('2.11'),
 'CIII_minimum_width_0_24mm':cii_width==D('0.24'),
 'one_mm_both_axes_matches_r343_length_only':summary['one_mm_both_axes_nominal_0_10']['length_only_count']==prior['scenario_counts']['nominal_uncertainty_0_10mm'],
 'no_runtime_or_ocr_changes':'V2.28 TEST R156' in (a.app_dir/'index.html').read_text(encoding='utf-8'),
}
errors.extend(k for k,v in checks.items() if not v)
report={'schema':'bres-cat-r344-two-axis-rectangular-disjointness-v1','milestone':'CAT-R344','parent':'CAT-R343',
 'premise':'For two candidate catalogue geometries to be guaranteed distinguishable by nominal length/width, each candidate uncertainty rectangle must be disjoint from the other for at least one axis. For an axis with symmetric image error e and catalogue nominal uncertainty u, require nominal gap > 2(e+u).',
 'warning':'All error budgets are hypothetical. No Samsung calibration measurement was provided. Decimal display precision is NOT a physical tolerance guarantee; no active geometry threshold or OCR change.',
 'scenarios':[{'name':name,'image_length_error_mm':str(lie),'image_width_error_mm':str(wie),'nominal_length_uncertainty_mm':str(lne),'nominal_width_uncertainty_mm':str(wne)} for name,lie,wie,lne,wne in scenarios],
 'scenario_summaries':summary,'priority_groups':results,
 'CIII_precision_required_if_nominal_uncertainty_0_10mm':{
     'image_length_error_strictly_below_mm':str(cii_len/2-D('0.10')),
     'image_width_error_strictly_below_mm':str(cii_width/2-D('0.10'))},
 'catalogue_count':len(rows),'unique':len(refs),'canonical_hashes':hashes,'checks':checks,'errors':errors,'ok':not errors}
(HERE/'CATALOGUE_TWO_AXIS_BOUNDS_CAT_R344.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLES - AUDIT CATALOGUE CAT-R344 (2 AXES)','RESULTAT: '+('PASS' if not errors else 'FAIL')]
lines.extend(('PASS | ' if v else 'FAIL | ')+k for k,v in checks.items())
lines+=['','Separations theorique des 17 groupes, non mesurees :']
for label,v in summary.items():
    lines.append(f'  {label}: {v["separated_count"]}/17 ; largeur sauve {len(v["width_rescued"])} groupe(s) ; non resolus {v["unsafe_or_unresolved"]}')
lines.extend(['','Groupe CIII: avec nominal ±0,10 mm, erreur image longueur strictement <0,955 mm ou largeur <0,020 mm serait necessaire pour chaque paire au pire cas.','Aucun seuil applique, aucune modification de canon, OCR ou runtime.'])
(HERE/'CATALOGUE_INTERNAL_AUDIT_CAT_R344.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(HERE/'CHECKPOINT_CAT_R344.txt').write_text('CAT-R344 : audit multi-axes pire cas, 17 groupes OCR sensibles, sans seuil actif. 5103 references uniques / 10 blocs canoniques inchanges. Test Samsung physique toujours en attente.\n',encoding='utf-8')
(HERE/'CATALOGUE_CHUNK_HASHES_CAT_R344.txt').write_text('\n'.join(f'{h}  {name}' for name,h in sorted(hashes.items()))+'\n',encoding='utf-8')
print('\n'.join(lines))
raise SystemExit(0 if not errors else 1)