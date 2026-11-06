#!/usr/bin/env python3
"""CAT-R371 read-only reproduction. python cat_r371_repro_minimal.py APP_V3_DIR CSV_LEDGER
APP_V3_DIR: extracted app/catalogue/v3 from R369/R371 checkpoint.
CSV_LEDGER: CAT_R363_PAIR_REVIEW_LEDGER.csv. No physical-equivalence assertion.
"""
import csv, json, re, hashlib, math, sys
from pathlib import Path

v3,ledger=map(Path,sys.argv[1:3])
rows=[];hashes={}
for i in range(1,11):
 p=v3/f'catalog-{i:02}.js';raw=p.read_bytes();hashes[p.name]=hashlib.sha256(raw).hexdigest()
 m=re.search(r'push\(\.\.\.(\[.*\])\);?\s*$',raw.decode(),re.S)
 if not m:raise ValueError('Unrecognized canonical chunk format')
 rows.extend(json.loads(m.group(1)))
byref={r[0]:r for r in rows}
if len(rows)!=len(byref)!=5103:raise ValueError('Unexpected catalogue size or duplicate')
items=list(csv.DictReader(ledger.open(encoding='utf-8-sig')))
if len(items)!=393:raise ValueError('Unexpected risk count')
res=[]
for x in items:
 a,b=byref[x['reference_a']],byref[x['reference_b']]
 d=[a[k][j]-b[k][j] for k in (6,7,8) for j in range(24)]
 rms=math.sqrt(sum(v*v for v in d)/72)
 res.append({'refs':[a[0],b[0]],'ocr':x['already_known_hypothetical_OCR']=='True',
    'length_mm':round(abs(a[3]-b[3]),5),'width_mm':round(abs(a[4]-b[4]),5),
    'rms72':round(rms,7),'mask_hamming':(int(a[9],16)^int(b[9],16)).bit_count(),
    'same_label_UNVERIFIED':bool(a[1]) and a[1]==b[1],
    'automatic_validation':False,'physical_equivalence':False})
ocr=[x for x in res if x['ocr']];typing=[x for x in res if not x['ocr']]
assert len(ocr)==68 and len(typing)==325
flag=lambda rows:{'both_dim_within_1mm':sum(x['length_mm']<=1 and x['width_mm']<=1 for x in rows),
 'rms72_below_0_05':sum(x['rms72']<0.05 for x in rows),
 'mask_hamming_le_8':sum(x['mask_hamming']<=8 for x in rows),
 'same_label_UNVERIFIED':sum(x['same_label_UNVERIFIED'] for x in rows)}
result={'schema':'bres-cat-r371-repro-minimal-v1','canonical_ref_count':len(rows),'chunks':len(hashes),
  'canonical_sha256':hashes,'pairs':len(res),'ocr_pairs':len(ocr),'typing_pairs':len(typing),
  'ocr_flags_REPORT_ONLY':flag(ocr),'typing_flags_REPORT_ONLY':flag(typing),
  'no_auto_validation':all(not x['automatic_validation'] and not x['physical_equivalence'] for x in res),
  'ocr_review_top12':sorted(ocr,key=lambda x:(not (x['length_mm']<=1 and x['width_mm']<=1),not(x['rms72']<.05),x['rms72'],x['refs']))[:12],
  'limitations':'Synthetic catalogue geometry only. No physical key, source maker inference, or OCR success claim.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
