#!/usr/bin/env python3
"""Independent CAT-R386 transport-contract audit; never edits canonical fragments."""
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import hashlib,re,json,ast,copy,sys,time
C=Path(__file__).resolve().parent;A=C.parent/'app';start=time.monotonic()
prev=json.loads((C/'CAT_R385_RUNTIME_FOLD_PARITY.json').read_text('utf8'))
js=(A/'v228-catalogue.js').read_text('utf8')
match=re.search(r'const fragmentShapeR386=(\[.*?\]);',js,re.S)
assert match,'Missing R386 fragment contract'
contract=ast.literal_eval(match.group(1))
checks={};metrics={};rows=[];chunks=[]
for i in range(1,11):
 name=f'catalog-{i:02}.js'
 raw=(A/'catalogue'/'v3'/name).read_bytes()
 found=re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw.strip(),re.S)
 assert found,name
 block=json.loads(found.group(1));chunks.append(block);rows+=block
 baseline=prev['summary']['canonical_digests'][name]
 sha=hashlib.sha256(raw).hexdigest();checks[f'fragment_{i:02}_sha256_unchanged']=sha==baseline
 checks[f'fragment_{i:02}_contract_matches_canonical']=[len(block),block[0][0],block[-1][0]]==contract[i-1]
 checks[f'fragment_{i:02}_12_fields']=all(len(r)==12 for r in block)
 metrics[name]={'count':len(block),'first':block[0][0],'last':block[-1][0],'sha256':sha}
 # An independent analogue of the cheap runtime guard. It is only an early
 # error detector, deliberately not a substitute for final all-fields digest.
 def guard(r,original=block,expected=contract[i-1]):
  return isinstance(r,list) and len(r)==expected[0] and r[0][0]==expected[1] and r[-1][0]==expected[2] and all(isinstance(x,list) and len(x)==12 for x in r)
 good=copy.deepcopy(block)
 negatives={
  'omitted':good[:-1],
  'duplicated':good+copy.deepcopy(good),
  'wrong_first':copy.deepcopy(good),
  'wrong_last':copy.deepcopy(good),
  'bad_columns':copy.deepcopy(good),
  'replaced_fragment':copy.deepcopy(chunks[0]),
 }
 negatives['wrong_first'][0][0]='R386_UNKNOWN_REF'
 negatives['wrong_last'][-1][0]='R386_UNKNOWN_END'
 negatives['bad_columns'][1].pop()
 for kind,v in negatives.items():
  # If a replacement fragment is exactly equal to the original, it would
  # not represent wrong content; replace a distinctive field instead.
  if kind=='replaced_fragment' and v==block:v[0][0]='R386_UNEXPECTED'
  # If it has same count + identical first/last then its interior change is
  # intentionally accepted early and must fail the final digest instead.
  expectation = kind!='replaced_fragment' or len(v)!=len(block) or v[0][0]!=block[0][0] or v[-1][0]!=block[-1][0]
  if expectation: checks[f'fragment_{i:02}_{kind}_detected_early']=not guard(v)
  else: checks[f'fragment_{i:02}_{kind}_full_digest_only']=v!=block
 # Mutate interior while preserving boundaries and row count: early guard
 # deliberately passes, final R371 must reject it (verified by Chromium).
 internal=copy.deepcopy(block);internal[1][1]='R386_TAMPERED_MAKER'
 checks[f'fragment_{i:02}_interior_tamper_needs_full_hash']=guard(internal) and internal!=block
checks['ten_complete_chunks']=len(chunks)==len(contract)==10
checks['5103_12_field_unique_refs']=len(rows)==5103 and len({r[0] for r in rows})==5103 and all(len(r)==12 for r in rows)
checks['164_empty_manufacturers_untouched']=sum(not r[1] for r in rows)==164
fold_map=str.maketrans({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'})
def fold(s):return re.sub('[^A-Z0-9]','',s.upper().strip()).translate(fold_map)
by=defaultdict(set)
for r in rows:by[fold(r[0])].add(r[0])
collisions={k:sorted(refs) for k,refs in by.items() if len(refs)>1}
checks['ocr_collision_66_groups_70_pairs']=len(collisions)==66 and sum(len(v)*(len(v)-1)//2 for v in collisions.values())==70
checks['final_12_field_verifier_is_still_invoked']='catalogueIsCompleteR384(window.BRES_CATALOG_V3)' in js and 'ocrCatalogueAllFieldsR371' in js
checks['unmodified_sources_after_audit']=all(hashlib.sha256((A/'catalogue'/'v3'/n).read_bytes()).hexdigest()==m['sha256'] for n,m in metrics.items())
report={'schema':'bres-cat-r386-fragment-early-contract-v1','date':'2026-11-21','milestone':'CAT-R386','ok':all(checks.values()),'checks':checks,'chunks':metrics,
 'canonical_refs':len(rows),'fields':12,'empty_makers':sum(not r[1] for r in rows),'ocr_ambiguities':{'groups':len(collisions),'pairs':sum(len(v)*(len(v)-1)//2 for v in collisions.values())},
 'app_fragment_guard_contract':contract,'elapsed_seconds':round(time.monotonic()-start,3),
 'limitations':['The small per-fragment sentinel check only rejects obvious transport errors; interior edits require R371 all-fields integrity',
              'No physical equivalence or manufacturer inferred; no Samsung/Tesseract offline certification']}
(C/'CAT_R386_FRAGMENT_CONTRACT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(C/'CAT_R386_FRAGMENT_CONTRACT.txt').write_text(f"CAT-R386 {'PASS' if report['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v],'seconds':report['elapsed_seconds']}))
if not report['ok']:sys.exit(1)
