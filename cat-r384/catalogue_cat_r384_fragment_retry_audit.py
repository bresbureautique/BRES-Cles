#!/usr/bin/env python3
"""CAT-R384 independent read-only fragment integrity audit for V2.28 loader recovery.
Intentional negative mutations to copies only: never write canonical fragments.
"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import json,csv,re,hashlib,copy,sys
C=Path(__file__).resolve().parent;A=C.parent/'app'
prior=json.loads((C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.json').read_text('utf8'))
prior_rows=list(csv.DictReader((C/'CAT_R383_OCR_FOLD_RECONSTRUCTION.csv').open(encoding='utf8',newline='')))
checks={};metrics={};records=[];chunks=[];hashes={}
for i in range(1,11):
    name=f'catalog-{i:02}.js';raw=(A/'catalogue'/'v3'/name).read_bytes()
    match=re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw.strip(),re.S)
    if not match:raise ValueError(f'Invalid canonical JS {name}')
    rr=json.loads(match.group(1)); chunks.append(rr);records.extend(rr)
    digest=hashlib.sha256(raw).hexdigest();hashes[name]=digest
    checks[f'{name}_sha256_matches_R383']=digest==prior['canonical_chunk_sha256'][name]
    checks[f'{name}_12_columns_immutable']=all(isinstance(r,list) and len(r)==12 for r in rr)
    metrics[name]={'records':len(rr),'sha256':digest,'first_ref':rr[0][0],'last_ref':rr[-1][0]}
ref_set={r[0] for r in records}
checks['global_5103_distinct_refs']=len(records)==len(ref_set)==5103
checks['164_blank_makers']=sum(not r[1] for r in records)==164
checks['ten_chunks_complete']=len(chunks)==10 and all(chunks)
# Canonical concatenation digest: order and *all columns* matter. This checks
# local recoverability against deletion, duplication, reordering and changes.
def digest(rows):return hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
baseline=digest(records)
for i in range(10):
    removed=[r for j,block in enumerate(chunks) if j!=i for r in block]
    duplicated=[r for j,block in enumerate(chunks) for r in (block*2 if i==j else block)]
    mutated=list(records)
    offset=sum(len(block) for block in chunks[:i]);mutated[offset]=copy.deepcopy(mutated[offset]);mutated[offset][6][0]+=0.0001
    checks[f'chunk_{i+1:02}_omission_detected']=len(removed)!=5103 and digest(removed)!=baseline
    checks[f'chunk_{i+1:02}_duplicate_detected']=len(duplicated)!=5103 and digest(duplicated)!=baseline
    checks[f'chunk_{i+1:02}_geometry_mutation_detected']=digest(mutated)!=baseline
# Reorder a complete chunk pair: length still 5103, but rows/hash must change.
for i in range(9):
    reordered=chunks.copy();reordered[i],reordered[i+1]=reordered[i+1],reordered[i]
    checks[f'chunk_pair_{i+1:02}_{i+2:02}_swap_detected']=digest([r for block in reordered for r in block])!=baseline
FOLD=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def fold(ref):return re.sub('[^A-Z0-9]','',str(ref).upper().strip()).translate(FOLD)
groups=defaultdict(set)
for row in records:groups[fold(row[0])].add(row[0])
groups={k:sorted(v) for k,v in groups.items() if len(v)>1}
pairs={(a,b):k for k,v in groups.items() for a,b in combinations(v,2)}
prev={(r['reference_A'],r['reference_B']):r['fold'] for r in prior_rows}
checks['unchanged_66_ocr_groups']=len(groups)==66
checks['unchanged_70_ocr_pairs']=len(pairs)==70
checks['pair_identity_matches_R383']=pairs==prev
checks['no_auto_maker_or_equivalence_edits']=len(records)==5103 and len([r for r in records if not r[1]])==164
checks['previous_CAT_R383_pass']=prior['ok'] is True
checks['source_unchanged_read_only']=all(hashlib.sha256((A/'catalogue'/'v3'/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
output={'schema':'bres-cat-r384-fragment-retry-audit-v1','date':'2026-11-19','milestone':'CAT-R384',
'checks':checks,'ok':all(checks.values()),'record_count':len(records),'field_count':12,
'canonical_digest_SHA256_report_only':baseline,'canonical_sha256':hashes,
'fragments':metrics,'ocr_fold_groups':len(groups),'ocr_fold_pairs':len(pairs),
'negative_fragment_scenarios':39,'canonical_edited':False,'maker_assigned':0,'physical_equivalence_created':0,
'limitations':['Read-only digital fragment checks; not manufacturer documentation or physical equivalence evidence',
              'No actual Samsung image or cold-offline Tesseract processed']}
(C/'CAT_R384_FRAGMENT_RETRY_AUDIT.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf8')
with (C/'CAT_R384_FRAGMENT_RETRY_AUDIT.csv').open('w',encoding='utf8',newline='') as f:
 w=csv.writer(f);w.writerow(['canonical_chunk','rows','sha256','first_reference','last_reference'])
 for n,m in metrics.items():w.writerow([n,m['records'],m['sha256'],m['first_ref'],m['last_ref']])
(C/'CAT_R384_FRAGMENT_RETRY_AUDIT.txt').write_text(f"CAT-R384 {'PASS' if output['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+
 '\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':output['ok'],'total':len(checks),'pass':sum(checks.values()),'negative':output['negative_fragment_scenarios'],'failures':[k for k,v in checks.items() if not v]}))
if not output['ok']:sys.exit(1)
