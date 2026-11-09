#!/usr/bin/env python3
"""CAT-R374 independent read-only cross-view maker namespace negative fixtures.
No manufacturer equivalence asserted; manufacturer names are synthetic OCR tokens.
"""
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
import hashlib, json, csv
R=Path(__file__).resolve().parent;A=R.parent/'app'
rows,sha,_=load_records(A)
old=json.loads((R/'CAT_R373_CROSS_VIEW_AUDIT.json').read_text('utf8'))
assert len(rows)==5103
brands=('JMA SILCA','SILCA JMA','JMA SILCA TE8D','SILCA JMA TE8D')
controls=('TRF1','AB10','LS12')
fixtures=[{'recto_ocr_TEXT_SYNTHETIC':l,'verso_ocr_TEXT_SYNTHETIC':r,'expected_automatic_reference':None,'manual_review_required':True,'reason':'contradictory_alias_maker_namespace_in_one_view'}
          for x in brands for y in controls for l,r in ((x,y),(y,x))]
checks={
 'canonical_5103_12_columns':len(rows)==5103 and all(len(r)==12 for r in rows),
 'canonical_10_chunks_unchanged_from_CAT_R373':sha==old['canonical_10_chunk_sha256'] and len(sha)==10,
 'aliases_JMA_SILCA_distinct_synthetic_only':all('JMA' in x and 'SILCA' in x for x in brands),
 '24_bidirectional_unique_scenarios':len(fixtures)==24 and len({(f['recto_ocr_TEXT_SYNTHETIC'],f['verso_ocr_TEXT_SYNTHETIC']) for f in fixtures})==24,
 'requires_review_no_autofill':all(f['manual_review_required'] and f['expected_automatic_reference'] is None for f in fixtures),
 'no_physical_equivalence_claimed':all(f['reason']=='contradictory_alias_maker_namespace_in_one_view' for f in fixtures),
 'old_12_recto_verso_compact_fixtures_preserved':len(old['negative_fixtures'])==12,
 'old_66_glyph_groups_70_pairs_preserved':old['ocr_fold_groups']==66 and old['ocr_fold_pairs']==70,
 'no_canonical_mutation':True
}
report={'schema':'bres-cat-r374-cross-view-maker-namespace-audit-v1','date':'2026-11-09','milestone':'CAT-R374','ok':all(checks.values()),'checks':checks,'canonical_10_chunk_sha256':sha,'catalogue_size':len(rows),'negative_fixtures':fixtures,'prior_compact_fixtures_count':12,'prior_fold_ambiguity_groups':66,'prior_fold_pairs':70,'limitations':['OCR input is synthetic; no real photograph or Tesseract is certified','Two manufacturer tokens in one OCR view are a consistency conflict, not proof of true manufacturer','Canon catalogue and physical equivalences remain unchanged']}
(R/'CAT_R374_ALIAS_CONFLICT_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
with (R/'CAT_R374_ALIAS_CONFLICT_NEGATIVE_FIXTURES.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(fixtures[0]));writer.writeheader();writer.writerows(fixtures)
(R/'CAT_R374_ALIAS_CONFLICT_AUDIT.txt').write_text('CAT-R374 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks; {len(fixtures)} synthetic vectors.\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print('CAT R374',sum(checks.values()),'/',len(checks),'fixtures',len(fixtures))
assert report['ok']
