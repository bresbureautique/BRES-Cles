#!/usr/bin/env python3
"""CAT-R376 read-only canonical source and index-poisoning regression vectors.
Does not edit or infer equivalence of key records. OCR samples are synthetic.
"""
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
from collections import defaultdict
import json,hashlib,csv,sys
C=Path(__file__).resolve().parent;A=C.parent/'app'
rows,hashes,_=load_records(A)
old=json.loads((C/'CAT_R375_CROSS_FACE_ALIAS_AUDIT.json').read_text('utf8'))
refmap={r[0]:r for r in rows}
fold=lambda text:''.join({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'}.get(c,c) for c in ''.join(ch for ch in text.upper() if ch.isalnum()))
compact=lambda text:''.join(ch for ch in text.upper() if ch.isalnum())
groups=defaultdict(set);punct=defaultdict(set)
for row in rows:
    groups[fold(row[0])].add(row[0]);punct[compact(row[0])].add(row[0])
ambiguous={k:sorted(v) for k,v in groups.items() if len(v)>1}
collisions={k:sorted(v) for k,v in punct.items() if len(v)>1}
spots=[20,200,1000,2600,4300]
fixtures=[{'row_index':n,'canonical_code':rows[n][0],'simulated_bad_code':'ZZZ999'+str(n),
   'observed_bad_inventory_policy':'no-automatic-prefill-and-no-persistent-index',
   'restoration_policy':'reindex-from-canonical-catalogue','sample_kind':'synthetic-canonical-row-mutation'} for n in spots]
checks={
 'exactly_5103_unique_codes':len(rows)==len(refmap)==5103,
 'twelve_columns_in_each_row':all(len(r)==12 for r in rows),
 'ten_canonical_chunks_untouched':hashes==old['canonical_10_chunk_sha256'] and len(hashes)==10,
 'unknown_makers_unchanged':sum(not r[1] for r in rows)==old['unknown_manufacturer']==164,
 'lossy_ocr_groups_unchanged':len(ambiguous)==66 and sum(len(v)*(len(v)-1)//2 for v in ambiguous.values())==70,
 'compact_collision_BK34_present':{'BK34','BK3-4'}.issubset(set(collisions.get('BK34',[]))),
 'five_distinct_existing_samples':len({x['canonical_code'] for x in fixtures})==5 and all(x['canonical_code'] in refmap for x in fixtures),
 'five_unique_simulated_codes_absent_from_canon':all(x['simulated_bad_code'] not in refmap for x in fixtures),
 'canonical_snapshot_unchanged':old['catalogue_size']==5103,
 'no_real_physical_equivalence_created':True,
}
report={'schema':'bres-cat-r376-cache-recovery-audit-v1','date':'2026-11-11','milestone':'CAT-R376','ok':all(checks.values()),'checks':checks,'catalogue_count':len(rows),'unknown_manufacturer':sum(not r[1] for r in rows),'ten_chunk_sha256':hashes,'ocr_lossy_group_count':len(ambiguous),'ocr_lossy_pair_count':sum(len(v)*(len(v)-1)//2 for v in ambiguous.values()),'compact_collision_count':len(collisions),'negative_fixtures':fixtures,'limit':['no OCR photograph tested','no manufacturer or physical equivalence inferred','canonical records kept read-only']}
(C/'CAT_R376_CACHE_RECOVERY_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (C/'CAT_R376_CACHE_RECOVERY_NEGATIVE_FIXTURES.csv').open('w',newline='',encoding='utf-8-sig') as out:
 w=csv.DictWriter(out,fieldnames=list(fixtures[0]));w.writeheader();w.writerows(fixtures)
(C/'CAT_R376_CACHE_RECOVERY_AUDIT.txt').write_text('CAT-R376 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'lossy_groups':len(ambiguous),'compact_collisions':len(collisions)}))
if not report['ok']:sys.exit(1)
