#!/usr/bin/env python3
"""CAT-R389: compare exact decimal geometry thresholds with R388 float arithmetic."""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
from itertools import combinations
import csv, json, re, hashlib, sys
C=Path(__file__).resolve().parent; A=C.parent/'app'/'catalogue'/'v3'
rows={}; checks={}; contract=json.loads((C/'CAT_R386_FRAGMENT_CONTRACT.json').read_text())
for p in sorted(A.glob('catalog-*.js')):
    raw=p.read_bytes(); checks[p.name]=hashlib.sha256(raw).hexdigest()==contract['chunks'][p.name]['sha256']
    for r in json.loads(re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw,re.S)[1],parse_float=Decimal):
        assert r[0] not in rows and len(r)==12; rows[r[0]]=r
pairs=set(); signatures=defaultdict(list)
for ref in rows:
    for i in range(len(ref)):
        signatures[(len(ref),i,ref[:i],ref[i+1:])].append(ref)
        shorter=ref[:i]+ref[i+1:]
        if shorter in rows:pairs.add(tuple(sorted((ref,shorter))))
        if i+1<len(ref):
            swap=ref[:i]+ref[i+1]+ref[i]+ref[i+2:]
            if swap!=ref and swap in rows:pairs.add(tuple(sorted((ref,swap))))
for refs in signatures.values():pairs.update(tuple(sorted(pair)) for pair in combinations(refs,2))
exact=set(); float_near=set(); changed=[]; missing=set()
for a,b in sorted(pairs):
    x,y=rows[a],rows[b]; ds=[abs(Decimal(x[i])-Decimal(y[i])) for i in (3,4)]
    fs=[abs(float(x[i])-float(y[i])) for i in (3,4)]
    if max(ds)<=1:
        exact.add((a,b))
        if not x[1] or not y[1]:missing.add((a,b))
    if max(fs)<=1:float_near.add((a,b))
    if (max(ds)<=1)!=(max(fs)<=1):changed.append(dict(ref_a=a,ref_b=b,length=str(ds[0]),height=str(ds[1]),float_lengths=fs,missing_maker=not x[1] or not y[1]))
with (C/'CAT_R388_MANUAL_REVIEW_QUEUE.csv').open(encoding='utf-8-sig') as f:old={(r['ref_a'],r['ref_b']) for r in csv.DictReader(f)}
checks.update(rows=len(rows)==5103,pairs=len(pairs)==24576,float_near=len(float_near)==2459,old_queue=old=={(a,b) for a,b in float_near if not rows[a][1] or not rows[b][1]},no_float_false_positive=float_near<=exact,priority_only_real_pairs=missing<=pairs)
with (C/'CAT_R389_EXACT_REVIEW_QUEUE.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['ref_a','ref_b','length_diff_mm','height_diff_mm','maker_a','maker_b','status'])
    for a,b in sorted(missing):
        x,y=rows[a],rows[b];w.writerow([a,b,*[str(abs(Decimal(x[i])-Decimal(y[i]))) for i in (3,4)],x[1],y[1],'OCR risk only; no physical equivalence'])
report=dict(milestone='CAT-R389',checks=checks,ok=all(checks.values()),pairs=len(pairs),exact_near=len(exact),float_near=len(float_near),exact_priority=len(missing),prior_priority=len(old),new_priority=sorted(missing-old),boundary_differences=changed,physical_equivalences=0,manufacturers_imputed=0)
(C/'CAT_R389_DECIMAL_AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report));sys.exit(not report['ok'])
