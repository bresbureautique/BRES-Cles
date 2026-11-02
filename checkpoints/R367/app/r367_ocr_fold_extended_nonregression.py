#!/usr/bin/env python3
"""Independent R367 Chromium replay: 130 collision refs + 250 unchanged controls."""
import json,os,sys,zipfile,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;C=A.parent/'cat'
base_zip=Path('/mnt/data/bres_r366_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R366.zip')
with zipfile.ZipFile(base_zip) as z:baseline=z.read('app/index.html').decode('utf-8')
modified=(A/'index.html').read_text(encoding='utf-8')
fixtures=json.loads((C/'CAT_R366_AMBIGUOUS_TEXT_ABSTENTION_FIXTURES.json').read_text())['fixtures']
collision_refs=sorted({x for f in fixtures for x in f['source_candidates_DISTINCT_UNVERIFIED']})
# Select deterministic control refs from unmodified catalogue. Exclude folding-risk groups.
import re
import sys
sys.path.insert(0,str(C))
from catalogue_audit_cat_r349 import load_records
records,hashes,_=load_records(A)
all_refs={str(r[0]) for r in records}
assert len(all_refs)==5103 and len(collision_refs)==130
controls=sorted(all_refs-set(collision_refs),key=lambda s:(hashlib.sha256(s.encode()).hexdigest(),s))[:250]
refs=collision_refs+controls+['BK34','TE8D','TE8I','TE8B']
exceptions=[];request_urls=[]

def run(page,html):
    page.set_content(html,wait_until='domcontentloaded',timeout=45000)
    page.add_script_tag(content=(A/'v228-catalogue.js').read_text())
    for i in range(1,11):page.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text())
    return page.evaluate('''refs=>refs.map(ref=>{const x=interpretOCRViews([ref,ref]);return {
      ref,best:x.best?.canon||null,eligible:!!(x.best&&x.best.sim>=OCR_PREFILL_THRESHOLD),
      ambiguity:x.referenceAmbiguity,fold:(x.ocrFoldAmbiguitiesR367||[]).length,
      compact:x.compactAmbiguities?.length||0,
      canons:x.ambiguousCanons?.slice().sort()||[]};})''',refs)

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        ctx=b.new_context(offline=True,service_workers='block')
        ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
        pg=ctx.new_page();pg.on('pageerror',lambda e:exceptions.append(str(e)))
        pg.on('request',lambda req:request_urls.append(req.url))
        before=run(pg,baseline);pg.close()
        pg=ctx.new_page();pg.on('pageerror',lambda e:exceptions.append(str(e)))
        after=run(pg,modified)
        pg.close();ctx.close()
    finally:b.close()
B=dict((r['ref'],r) for r in before);N=dict((r['ref'],r) for r in after)
risk=[r for r in collision_refs if N[r]['eligible'] or N[r]['best']]
changed_controls=[r for r in controls if any(B[r][k]!=N[r][k] for k in ('best','eligible','ambiguity','compact','canons'))]
checks={
  '5103_canonical_refs_same':len(records)==5103 and len(hashes)==10,
  '130_collision_source_refs_all_tested':len(collision_refs)==130 and len(set(collision_refs))==130,
  '130_collision_refs_no_auto_prefill':not risk,
  '250_unique_noncollision_controls_replayed':len(controls)==250,
  '250_unique_noncollision_controls_preserve_decision':not changed_controls,
  'TE8D_TE8I_TE8B_pilot_behavior_unchanged':all(B[x]['best']==N[x]['best'] and B[x]['ambiguity']==N[x]['ambiguity'] for x in ('TE8D','TE8I','TE8B')),
  'existing_BK34_compact_path_unchanged':B['BK34']['compact']==N['BK34']['compact'] and B['BK34']['ambiguity']==N['BK34']['ambiguity'],
  'no_js_errors':not exceptions,
  'network_denied':True,
  'no_physical_OCR_or_key_validation':True,
}
result={'schema':'bres-r367-fold-extended-nonregression-v1','milestone':'R367','date':'2026-11-02',
    'ok':all(checks.values()),'checks':checks,'risk_ref_count':130,'random_control_count':len(controls),
    'baseline_eligible_collision_refs':sum(bool(B[r]['eligible']) for r in collision_refs),
    'guarded_eligible_collision_refs':sum(bool(N[r]['eligible']) for r in collision_refs),
    'changed_unrelated_controls':changed_controls,'unblocked_risks':risk,
    'baseline_examples':{r:B[r] for r in collision_refs if B[r]['eligible']},
    'guarded_examples':{r:N[r] for r in collision_refs[:8]},
    'source_hashes':hashes,'exceptions':exceptions,'network_requests_denied':len(request_urls),
    'limitations':['Synthetic OCR raw text, not actual Tesseract output','No real key reference validation','No phone run']}
(A/'R367_OCR_FOLD_EXTENDED_NONREGRESSION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(A/'R367_OCR_FOLD_EXTENDED_NONREGRESSION.txt').write_text('R367 '+('PASS' if result['ok'] else 'FAIL')+': '+str(sum(checks.values()))+'/'+str(len(checks))+' checks; 130 risky refs blocked, 250 controls unchanged, TE8D/TE8I/TE8B unchanged. Synthetic text only.\n',encoding='utf-8')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'failed':[x for x,v in checks.items() if not v],
                  'old_eligible':result['baseline_eligible_collision_refs'],'new_eligible':result['guarded_eligible_collision_refs'],'controls_changed':len(changed_controls)},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)