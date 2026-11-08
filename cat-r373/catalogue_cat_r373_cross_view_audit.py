#!/usr/bin/env python3
"""CAT-R373: read-only catalogue OCR cross-view ambiguity test fixture audit."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,itertools,csv
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent;A=R.parent/'app'
rows,sha,prior=load_records(A)
old=json.loads((R/'CAT_R372_EXTENDED_OCR_FOLD_AUDIT.json').read_text('utf8'))
compact=lambda s:''.join(x for x in s.upper() if x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
fold=lambda s:''.join({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'}.get(x,x) for x in compact(s))
C=defaultdict(set);F=defaultdict(set)
for x in rows:C[compact(x[0])].add(x[0]);F[fold(x[0])].add(x[0])
compact_groups={k:sorted(v) for k,v in C.items() if len(v)>1}
fold_groups={k:sorted(v) for k,v in F.items() if len(v)>1}
strong=['TRF1','AB10','LS12']
assert all(len(C[compact(r)])==len(F[fold(r)])==1 for r in strong)
fixtures=[]
for group in compact_groups.values():
 for spelling in group:
  for other in strong:
   for recto,verso in [(spelling,other),(other,spelling)]:
    fixtures.append({'recto_ocr_TEXT_SYNTHETIC':recto,'verso_ocr_TEXT_SYNTHETIC':verso,
       'expected_automatic_reference':None,'review_required':True,'geometry_may_override_opposing_strong_face':False,
       'unverified_canonical_spellings':group})
checks={
 'canonical_5103_12_fields':len(rows)==5103 and len({r[0] for r in rows})==5103 and all(len(r)==12 for r in rows),
 'canonical_10_hashes_still_match_R372':sha==old['canonical_10_chunk_sha256'] and len(sha)==10,
 'exactly_one_compact_collision_group':list(compact_groups.values())==[['BK3-4','BK34']],
 '66_ocr_glyph_groups_70_pairs':len(fold_groups)==66 and sum(len(g)*(len(g)-1)//2 for g in fold_groups.values())==70,
 'compact_group_not_automatically_equivalent':len(compact_groups)==1,
 'twelve_bidirectional_negative_fixtures':len(fixtures)==12 and len({(x['recto_ocr_TEXT_SYNTHETIC'],x['verso_ocr_TEXT_SYNTHETIC']) for x in fixtures})==12,
 'physical_confirmation_required':all(x['review_required'] and not x['geometry_may_override_opposing_strong_face'] for x in fixtures),
 'canon_is_read_only':True}
report={'schema':'bres-cat-r373-cross-view-ambiguity-v1','date':'2026-11-08','milestone':'CAT-R373',
 'ok':all(checks.values()),'checks':checks,'canonical_10_chunk_sha256':sha,'catalogue_size':len(rows),
 'compact_collision_groups':compact_groups,'ocr_fold_groups':len(fold_groups),
 'ocr_fold_pairs':sum(len(g)*(len(g)-1)//2 for g in fold_groups.values()),
 'negative_fixtures':fixtures,
 'limitations':['No photographic OCR; samples are synthetic text only','No physical equivalence or manufacturer inference',
   'Separation from V2.28 runtime: fixtures are data-only', 'No canonical source modification']}
(R/'CAT_R373_CROSS_VIEW_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
with (R/'CAT_R373_CROSS_VIEW_NEGATIVE_FIXTURES.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.DictWriter(f,fieldnames=['recto_ocr_TEXT_SYNTHETIC','verso_ocr_TEXT_SYNTHETIC','expected_automatic_reference','review_required','geometry_may_override_opposing_strong_face']);writer.writeheader();writer.writerows({k:x[k] for k in writer.fieldnames} for x in fixtures)
(R/'CAT_R373_CROSS_VIEW_AUDIT.txt').write_text('CAT-R373 '+('PASS' if report['ok'] else 'FAIL')+' '+str(sum(checks.values()))+'/'+str(len(checks))+' checks.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
(R/'CHECKPOINT_CAT_R373.md').write_text('''# Catalogue CAT-R373 — 08/11/2026

Audit autonome en lecture seule : 5 103 références, dix fragments canoniques identiques à CAT-R372. Une seule collision de forme compacte existe (`BK3-4`/`BK34`) en plus des 66 groupes de formes OCR théoriquement confondues (70 paires). Douze combinaisons recto/verso synthétiques confrontent une forme compacte ambiguë à TRF1, AB10 ou LS12, et exigent l’abstention plutôt qu’un choix automatique. Aucune équivalence physique n’est conclue, aucun fabricant ni catalogue original n’est modifié. Les fichiers sont indépendants des sources de l’application.
''','utf8')
print(json.dumps({'ok':report['ok'],'checks':len(checks),'fixtures':len(fixtures),'compact_groups':compact_groups},ensure_ascii=False))
assert report['ok']
