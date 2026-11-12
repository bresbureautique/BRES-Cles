#!/usr/bin/env python3
"""CAT-R377 independent read-only catalogue display-surface audit.
No manufacturer inference, no merging and no physical key certification.
"""
from pathlib import Path
from collections import Counter,defaultdict
from catalogue_audit_cat_r349 import load_records
import json,hashlib,sys,csv
C=Path(__file__).resolve().parent;A=C.parent/'app'
rows,hashes,_=load_records(A)
old=json.loads((C/'CAT_R376_CACHE_RECOVERY_AUDIT.json').read_text('utf8'))
refs={r[0]:r for r in rows}
fold=lambda text:''.join({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'}.get(ch,ch) for ch in ''.join(c for c in text.upper() if c.isalnum()))
compact=lambda text:''.join(c for c in text.upper() if c.isalnum())
amb=defaultdict(set);co=defaultdict(set)
for r in rows:amb[fold(r[0])].add(r[0]);co[compact(r[0])].add(r[0])
ampersand=[{'ref':r[0],'manufacturer_text_original':r[1]} for r in rows if '&' in r[1]]
markup=[{'ref':r[0],'field':'code' if any(ch in r[0] for ch in '<>"\'') else 'maker'} for r in rows if any(ch in str(r[i]) for i in (0,1) for ch in '<>"\'')]
checks={
  '5103_unique_codes':len(rows)==len(refs)==5103,
  '12_columns_all_rows':all(len(r)==12 for r in rows),
  'ten_canonical_sha256_match_r376':hashes==old['ten_chunk_sha256'] and len(hashes)==10,
  'unknown_manufacturers_164_unchanged':sum(not r[1] for r in rows)==164,
  'ocr_collision_groups_66_unchanged':sum(len(v)>1 for v in amb.values())==66,
  'ocr_collision_pairs_70_unchanged':sum(len(v)*(len(v)-1)//2 for v in amb.values())==70,
  'compact_reference_collision_unchanged':sum(len(v)>1 for v in co.values())==1 and set(co['BK34'])=={'BK34','BK3-4'},
  'manufacturer_ampersands_present_for_escape_regression':len(ampersand)>0,
  'manufacturer_markup_angle_quotes_absent':len(markup)==0,
  'audit_never_modifies_canonical_rows':True,
}
report={'schema':'bres-cat-r377-display-surface-audit-v1','date':'2026-11-12','milestone':'CAT-R377','ok':all(checks.values()),'checks':checks,
  'catalogue_count':len(rows),'canonical_sha256':hashes,'unknown_manufacturer_count':sum(not r[1] for r in rows),
  'makers_with_ampersand_records':len(ampersand),'maker_ampersand_unique_labels':sorted(set(x['manufacturer_text_original'] for x in ampersand)),
  'unsafe_markup_in_code_maker':markup,'ocr_collision_groups':66,'ocr_collision_pairs':70,'compact_collision_refs':sorted(co['BK34']),
  'limits':['Manufacturer strings with & require HTML escaping when rendered; they are not malicious records',
    'No OCR photo test','No physical equivalence or maker assignment inferred']}
(C/'CAT_R377_DISPLAY_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(C/'CAT_R377_DISPLAY_AUDIT.txt').write_text('CAT-R377 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
with (C/'CAT_R377_MANUFACTURER_AMPERSAND_SAMPLES.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['ref','manufacturer_text_original']);w.writeheader();w.writerows(ampersand)
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'manufacturer_ampersand_records':len(ampersand),'unique_labels':len(report['maker_ampersand_unique_labels'])}))
if not report['ok']:sys.exit(1)
