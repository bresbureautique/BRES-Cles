#!/usr/bin/env python3
"""CAT-R388 independent read-only audit of one OCR transcription error and geometry.
Generates a review queue only; deliberately never produces key equivalence or maker imputation.
"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import hashlib,re,json,csv,io,sys,time
C=Path(__file__).resolve().parent;A=C.parent/'app'/'catalogue'/'v3';beg=time.monotonic()
prior=json.loads((C/'CAT_R386_FRAGMENT_CONTRACT.json').read_text('utf8'))
checks={};chunks={};rows=[]
for i in range(1,11):
 name=f'catalog-{i:02}.js';raw=(A/name).read_bytes();
 parts=re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw.strip(),re.S)
 if not parts:raise ValueError('Malformed fragment '+name)
 batch=json.loads(parts.group(1));rows+=batch
 chunks[name]={'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(batch)}
 checks[f'{name}_sha256_canonical']=chunks[name]['sha256']==prior['chunks'][name]['sha256']
 checks[f'{name}_all_twelve_fields']=all(isinstance(r,list) and len(r)==12 for r in batch)
by_ref={r[0]:r for r in rows}
checks['unique_5103_refs']=len(rows)==len(by_ref)==5103
checks['missing_manufacturer_164']=sum(not r[1] for r in rows)==164
checks['no_candidate_ref_is_invented']=all(isinstance(k,str) and k for k in by_ref)
# Independent one-edit candidate generation: one substitution, one deletion,
# one insertion (the inverse of deletion), or one adjacent transposition.
# These OCR error models are broad and conservative, not confirmed recognition errors.
sub_index=defaultdict(list)
for ref in by_ref:
 for idx in range(len(ref)):sub_index[(len(ref),idx,ref[:idx]+'*'+ref[idx+1:])].append(ref)
classes=defaultdict(set)
def store(a,b,kind):
 if a!=b:classes[tuple(sorted((a,b)))].add(kind)
for cluster in sub_index.values():
 for a,b in combinations(cluster,2):store(a,b,'substitution')
for ref in by_ref:
 for idx in range(len(ref)):
  smaller=ref[:idx]+ref[idx+1:]
  if smaller in by_ref:store(ref,smaller,'insertion-deletion')
 for idx in range(len(ref)-1):
  swapped=ref[:idx]+ref[idx+1]+ref[idx]+ref[idx+2:]
  if swapped in by_ref:store(ref,swapped,'transposition')
# Confirm every emitted pair is one valid elementary OCR transcription edit.
def true_one_edit(a,b):
 if len(a)==len(b):
  n=[i for i in range(len(a)) if a[i]!=b[i]]
  return len(n)==1 or (len(n)==2 and n[1]==n[0]+1 and a[n[0]]==b[n[1]] and a[n[1]]==b[n[0]])
 if abs(len(a)-len(b))!=1:return False
 short,long=sorted((a,b),key=len)
 return any(long[:i]+long[i+1:]==short for i in range(len(long)))
checks['all_edit_pairs_are_real_reference_pairs']=all(a in by_ref and b in by_ref for a,b in classes)
checks['all_edit_pairs_are_exactly_one_edit']=all(true_one_edit(a,b) for a,b in classes)
# New queue: near-geometry pairs with >=1 unknown manufacturer; these are
# evidence-gap priorities, NEVER physical matches. The ambiguity count is
# intentionally computed from the data, not hardcoded.
priority=[];dim_near=[]
for (a,b),kind in sorted(classes.items()):
 left,right=by_ref[a],by_ref[b]
 dw=abs(float(left[3])-float(right[3]));dh=abs(float(left[4])-float(right[4]))
 if dw<=1.0 and dh<=1.0:
  dim_near.append((a,b))
  if not left[1] or not right[1]:
   priority.append({'ref_a':a,'ref_b':b,'edit_types':'+'.join(sorted(kind)),
    'maker_a':left[1],'maker_b':right[1],
    'length_diff_mm':round(dw,4),'height_diff_mm':round(dh,4),
    'note':'Revue humaine si une photographie étalon devient disponible ; PAS une équivalence'})
priority.sort(key=lambda x:(x['length_diff_mm']+x['height_diff_mm'],x['ref_a'],x['ref_b']))
checks['review_queue_is_unique_and_subset']=len(priority)==len({(x['ref_a'],x['ref_b']) for x in priority}) and all((x['ref_a'],x['ref_b']) in classes for x in priority)
checks['review_queue_has_missing_maker_and_close_dimensions']=all((not x['maker_a'] or not x['maker_b']) and x['length_diff_mm']<=1 and x['height_diff_mm']<=1 for x in priority)
# Recompute prior collision fold independently.
fold_map=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def fold(x):return re.sub('[^A-Z0-9]','',x.upper().strip()).translate(fold_map)
fold_groups=defaultdict(set)
for r in by_ref:fold_groups[fold(r)].add(r)
fold_pairs={tuple(sorted((a,b))) for cluster in fold_groups.values() if len(cluster)>1 for a,b in combinations(sorted(cluster),2)}
checks['legacy_66_fold_groups_70_pairs']=sum(len(g)>1 for g in fold_groups.values())==66 and len(fold_pairs)==70
checks['no_canonical_sources_written']=all(hashlib.sha256((A/name).read_bytes()).hexdigest()==v['sha256'] for name,v in chunks.items())
count_kinds=Counter(k for labels in classes.values() for k in labels)
summary={'references':len(rows),'fields':12,'canonical_fragments':10,'manufacturer_missing':sum(not r[1] for r in rows),
 'legacy_fold_groups':sum(len(g)>1 for g in fold_groups.values()),'legacy_fold_pairs':len(fold_pairs),
 'one_edit_candidate_pairs':len(classes),'one_edit_pair_types':dict(count_kinds),
 'one_edit_with_dimensions_within_1mm':len(dim_near),
 'prioritized_missing_manufacturer_and_near_geometry':len(priority),
 'physical_equivalences_asserted':0,'manufacturers_imputed':0}
report={'schema':'bres-cat-r388-one-edit-review-v1','date':'2026-11-23','milestone':'CAT-R388',
 'ok':all(checks.values()),'checks':checks,'summary':summary,'fragments':chunks,
 'first_priority_examples':priority[:12], 'duration_seconds':round(time.monotonic()-beg,3),
 'limits':['One-edit candidates and similar dimensions are OCR transcription RISK ONLY, never reference equality.',
           'Manufacturer blanks remain blanks; no supplier normalization or photo identification inferred.',
           'This is a read-only desktop audit, not a physical Samsung validation.']}
(C/'CAT_R388_ONE_EDIT_AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n','utf8')
output=C/'CAT_R388_MANUAL_REVIEW_QUEUE.csv'
with output.open('w',newline='',encoding='utf-8-sig') as file:
 writer=csv.DictWriter(file,fieldnames=['ref_a','ref_b','edit_types','maker_a','maker_b','length_diff_mm','height_diff_mm','note']);writer.writeheader();writer.writerows(priority)
(C/'CAT_R388_ONE_EDIT_AUDIT.txt').write_text('CAT-R388 '+('PASS' if report['ok'] else 'FAIL')+f" {sum(checks.values())}/{len(checks)}\n"+json.dumps(summary,indent=2,ensure_ascii=False)+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'summary':summary,'failed':[k for k,v in checks.items() if not v]}))
sys.exit(0 if report['ok'] else 1)
