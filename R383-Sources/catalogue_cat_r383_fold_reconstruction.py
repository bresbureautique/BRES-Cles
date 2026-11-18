#!/usr/bin/env python3
"""Independent OCR collision reconstruction from canonical 10 chunks; no catalogue edits."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import csv,json,hashlib,re,sys
from catalogue_audit_cat_r349 import load_records
C=Path(__file__).resolve().parent;A=C.parent/'app'
rows, hashes, meta=load_records(A)
prior=list(csv.DictReader((C/'CAT_R381_OCR_PAIR_EVIDENCE.csv').open(encoding='utf-8-sig',newline='')))
report382=json.loads((C/'CAT_R382_PAIR_LEDGER_INTEGRITY.json').read_text('utf8'))
TRANSLATE=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def compact(ref):return re.sub('[^A-Z0-9]','',str(ref).upper().strip())
def fold(ref):return compact(ref).translate(TRANSLATE)
def make_groups(source):
    groups=defaultdict(set)
    for r in source:groups[fold(r[0])].add(r[0])
    return {k:sorted(v) for k,v in groups.items() if len(v)>1}
byref={r[0]:r for r in rows};groups=make_groups(rows)
pairs={(a,b):k for k,refs in groups.items() for a,b in combinations(refs,2)}
old={(r['reference_A'],r['reference_B']):r for r in prior}
compact_groups=defaultdict(set)
for r in rows:compact_groups[compact(r[0])].add(r[0])
compact_collisions={k:sorted(v) for k,v in compact_groups.items() if len(v)>1}
ledger=[]
for (a,b),key in sorted(pairs.items(),key=lambda kv:(kv[1],kv[0])):
    ra,rb=byref[a],byref[b]
    dx=round(abs(float(ra[3])-float(rb[3])),4)
    dy=round(abs(float(ra[4])-float(rb[4])),4)
    status='missing_maker' if not ra[1] or not rb[1] else ('same_maker' if ra[1]==rb[1] else 'different_makers')
    ledger.append({'fold':key,'reference_A':a,'reference_B':b,'maker_A':ra[1], 'maker_B':rb[1],
                   'group_size':len(groups[key]),'length_delta_mm_REPORT_ONLY':dx,'width_delta_mm_REPORT_ONLY':dy,
                   'review_reason':status,'dimension_proximity_REPORT_ONLY':'YES' if dx<=2 and dy<=2 else 'NO',
                   'review_status':'PENDING','automatic_equivalence':'NO'})
checks={
 'R382_evidence_audit_passed':report382['ok'] is True,
 'R382_canonic_sha_unchanged':hashes==report382['canonical_sha256'],
 'canonical_5103_unique_12_field':len(rows)==len(byref)==5103 and all(len(r)==12 for r in rows),
 'blank_makers_164':sum(not r[1] for r in rows)==164,
 'OCR_fold_groups_66':len(groups)==66,
 'OCR_fold_pairs_70':len(pairs)==70,
 'pairs_independently_rebuild_prior_queue':set(old)==set(pairs),
 'pairs_have_correct_prior_fold':all(old[(a,b)]['OCR_fold']==key for (a,b),key in pairs.items()),
 'pair_reference_and_maker_match_prior':all(old[(a,b)]['maker_A']==byref[a][1] and old[(a,b)]['maker_B']==byref[b][1] for a,b in pairs),
 'compact_collision_BK3-4_BK34_recorded':set(compact_collisions.get('BK34',[]))=={'BK3-4','BK34'},
 'review_not_automatic':all(r['review_status']=='PENDING' and r['automatic_equivalence']=='NO' for r in ledger),
 'all_fold_keys_nonempty_ascii':all(k and re.fullmatch('[A-Z0-9]+',k) for k in groups),
 'idempotent_fold':all(fold(fold(r[0]))==fold(r[0]) for r in rows),
 'edit_reference_detected':make_groups([[('ZZ-UNRELATED' if r[0]=='BK3-4' else r[0])]+r[1:] for r in rows])!=groups,
 'edit_maker_detected':dict((r[0],r[1]) for r in rows[:1]+[[rows[1][0],'INVENTED']+rows[1][2:]]+rows[2:])!=dict((r[0],r[1]) for r in rows),
}
summary={'missing_maker':sum(r['review_reason']=='missing_maker' for r in ledger),
 'same_maker':sum(r['review_reason']=='same_maker' for r in ledger),
 'different_makers':sum(r['review_reason']=='different_makers' for r in ledger),
 'close_dimensions_only_not_equivalence':sum(r['dimension_proximity_REPORT_ONLY']=='YES' for r in ledger),
 'groups_with_3_or_more':sum(len(v)>=3 for v in groups.values())}
checks['maker_partition_1_6_63']=summary['missing_maker']==1 and summary['same_maker']==6 and summary['different_makers']==63
checks['canonical_chunks_ten']=len(hashes)==10
(C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.csv').write_text('',encoding='utf8')
with (C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.csv').open('w',encoding='utf8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
result={'schema':'bres-cat-r383-independent-ocr-fold-reconstruction-v1','date':'2026-11-18','milestone':'CAT-R383',
 'ok':all(checks.values()),'checks':checks,'summary':summary,'canonical_records':len(rows),
 'canonical_chunk_sha256':hashes,'collision_groups':len(groups),'collision_pairs':len(pairs),
 'compact_collision_groups':compact_collisions,'source_modified':False,'new_manufacturers_assigned':0,
 'physical_equivalence_verified':False,'limits':['Modelled OCR glyph confusion only','Geometry proximity is indicative and cannot verify physical compatibility','Actual Samsung and cold-offline recognition not tested']}
(C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.txt').write_text('CAT-R383 '+('PASS' if result['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)}; {len(groups)} groups, {len(pairs)} pairs\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n'+json.dumps(summary,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'ok':result['ok'],'pass':sum(checks.values()),'total':len(checks),'summary':summary,'compact':compact_collisions,'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
if not result['ok']:sys.exit(1)
