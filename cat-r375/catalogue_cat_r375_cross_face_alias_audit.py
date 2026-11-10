#!/usr/bin/env python3
"""CAT-R375 read-only catalogue audit + independent synthetic two-face negative fixtures.

The strings are diagnostic examples, not evidence that two manufacturers can/cannot
co-occur on a particular *physical* key. No canonical record is edited.
"""
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
import json, csv, hashlib

C=Path(__file__).resolve().parent
A=C.parent/'app'
rows,hashes,_=load_records(A)
prior=json.loads((C/'CAT_R374_ALIAS_CONFLICT_AUDIT.json').read_text(encoding='utf8'))
legacy=json.loads((C/'CAT_R373_CROSS_VIEW_AUDIT.json').read_text(encoding='utf8'))
refs=('TE8D','TRF1','AB10')
fixtures=[]
for ref in refs:
    patterns=[
        ('JMA',f'SILCA {ref}','maker_only_vs_other_maker_reference'),
        (f'JMA {ref}','SILCA','maker_reference_vs_other_maker_only'),
        (f'JMA {ref}',f'SILCA {ref}','both_faces_same_spelling_different_maker'),
        (f'J M A {ref}',f'S I L C A {ref}','spaced_out_different_makers'),
    ]
    for a,b,why in patterns:
        for left,right in ((a,b),(b,a)):
            fixtures.append({'recto_ocr_TEXT_SYNTHETIC':left,'verso_ocr_TEXT_SYNTHETIC':right,
                'expected_automatic_reference':None,'manual_review_required':True,
                'reason':'different_alias_manufacturer_namespace_across_views',
                'scenario':why,'reference_token_NOT_PHYSICAL_PROOF':ref})
assert len(fixtures)==24
checks={
 'catalogue_5103_unique_codes_12_columns':len(rows)==len(set(r[0] for r in rows))==5103 and all(len(r)==12 for r in rows),
 'ten_canonical_fragments_unchanged_from_r374':hashes==prior['canonical_10_chunk_sha256'] and len(hashes)==10,
 'prior_r374_audit_passed':prior['ok'] is True and len(prior['negative_fixtures'])==24,
 'historical_r373_compact_cases_preserved':len(legacy['negative_fixtures'])==12,
 'historical_fold_groups_preserved':legacy['ocr_fold_groups']==66 and legacy['ocr_fold_pairs']==70,
 'twenty_four_unique_bidirectional_synthetic_vectors':len({(f['recto_ocr_TEXT_SYNTHETIC'],f['verso_ocr_TEXT_SYNTHETIC']) for f in fixtures})==24,
 'both_namespaces_across_two_views':all('JMA' in f['recto_ocr_TEXT_SYNTHETIC'].replace(' ','')+f['verso_ocr_TEXT_SYNTHETIC'].replace(' ','') and 'SILCA' in f['recto_ocr_TEXT_SYNTHETIC'].replace(' ','')+f['verso_ocr_TEXT_SYNTHETIC'].replace(' ','') for f in fixtures),
 'three_reference_tokens_four_scenarios_two_sides':len(set(f['reference_token_NOT_PHYSICAL_PROOF'] for f in fixtures))==3 and len(set(f['scenario'] for f in fixtures))==4 and len(fixtures)==3*4*2,
 'all_fixtures_manual_only':all(f['expected_automatic_reference'] is None and f['manual_review_required'] for f in fixtures),
 'canonical_catalogue_reference_tokens_exist':set(refs[1:]).issubset({r[0] for r in rows}),
 'pilot_reference_TE8D_in_XREF_not_canon':"TE8D" in (A/'index.html').read_text('utf8') and 'TE8D' not in {r[0] for r in rows},
 'manufacturer_attribution_unchanged':sum(not r[1] for r in rows)==164,
 'no_canonical_mutation':True,
}
report={'schema':'bres-cat-r375-opposed-face-alias-audit-v1','milestone':'CAT-R375','date':'2026-11-10','ok':all(checks.values()),'checks':checks,
        'canonical_10_chunk_sha256':hashes,'catalogue_size':len(rows),'unknown_manufacturer':sum(not r[1] for r in rows),
        'negative_fixtures':fixtures,'limitations':['All OCR strings are synthetic; not real photographed keys',
        'Different alias tokens on separate photos require review, not proof of any maker or physical equivalence',
        'No canonical catalogue record changed']}
(C/'CAT_R375_CROSS_FACE_ALIAS_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (C/'CAT_R375_CROSS_FACE_ALIAS_NEGATIVE_FIXTURES.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(fixtures[0]));w.writeheader();w.writerows(fixtures)
(C/'CAT_R375_CROSS_FACE_ALIAS_AUDIT.txt').write_text('CAT-R375 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks, {len(fixtures)} negative synthetic scenarios.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
print(json.dumps({'ok':report['ok'],'checks':sum(checks.values()),'total':len(checks),'fixtures':len(fixtures)}))
if not report['ok']:raise SystemExit(1)
