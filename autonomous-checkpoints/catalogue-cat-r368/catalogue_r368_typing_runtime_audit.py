#!/usr/bin/env python3
"""CAT-R368: full-catalogue actual JS decision audit of the 325 typing-only risk pairs.

Read-only. Pairs are *not* physical key equivalences; actual OCR not run.
"""
import csv,hashlib,json,os,sys,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from catalogue_audit_cat_r349 import load_records
sys.dont_write_bytecode=True
C=Path(__file__).resolve().parent; A=C.parent/'app'
ledger=json.loads((C/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text(encoding='utf-8'))
pairs=[p for p in ledger['pairs'] if not p['already_known_hypothetical_OCR']]
assert len(pairs)==325 and len(ledger['pairs'])==393
texts=sorted({str(p[k]) for p in pairs for k in ('reference_a','reference_b')})
records,hashes,_=load_records(A)
assert len(records)==5103 and hashes==ledger['canonical_sha256']
with zipfile.ZipFile('/mnt/data/bres_r367_release/BRES_Cles_Mobile_V2_28_CHECKPOINT_R367.zip') as z:old=z.read('app/index.html').decode('utf-8')
new=(A/'index.html').read_text(encoding='utf-8')
errors=[]

def run(browser,html):
    ctx=browser.new_context(offline=True,service_workers='block')
    ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
    pg=ctx.new_page();pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.set_content(html,wait_until='domcontentloaded',timeout=45000)
    pg.add_script_tag(content=(A/'v228-catalogue.js').read_text())
    for i in range(1,11):pg.add_script_tag(content=(A/f'catalogue/v3/catalog-{i:02}.js').read_text())
    res=pg.evaluate('''ss=>ss.map(t=>{let i=interpretOCRViews([t,t]);return {text:t,best:i.best?.canon||null,
      eligible:!!(i.best&&i.best.sim>=OCR_PREFILL_THRESHOLD),ambiguous:i.referenceAmbiguity,
      compact:i.compactAmbiguities?.length||0,fold:i.ocrFoldAmbiguitiesR367?.length||0,
      catalogueReady:i.ocrCatalogueReadyR368??null};})''',texts)
    ctx.close();return dict((x['text'],x) for x in res)

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    try:
        before=run(b,old);after=run(b,new)
    finally:b.close()

rows=[]
for p in pairs:
    a,b=p['reference_a'],p['reference_b']
    Arow,Brow=after[a],after[b]
    changes=[x for x in (a,b) if {k:before[x][k] for k in ('best','eligible','ambiguous','compact','fold')}!={k:after[x][k] for k in ('best','eligible','ambiguous','compact','fold')}]
    wrong_a=Arow['eligible'] and Arow['best']==b
    wrong_b=Brow['eligible'] and Brow['best']==a
    rows.append({'pair':a+' / '+b,'reference_a':a,'reference_b':b,'edit_types':p['edit_types'],
        'r367_a_prefill':before[a]['best'],'r367_b_prefill':before[b]['best'],
        'r368_a_prefill':Arow['best'],'r368_b_prefill':Brow['best'],
        'r368_a_ambiguous':Arow['ambiguous'],'r368_b_ambiguous':Brow['ambiguous'],
        'r368_a_eligible':Arow['eligible'],'r368_b_eligible':Brow['eligible'],
        'r368_cross_pair_text_prefill':bool(wrong_a or wrong_b),
        'regression_against_r367':bool(changes),'priority':'P1_cross_pair_text_mismatch' if wrong_a or wrong_b else 'P2_text-only_unverified',
        'reference_physical_equivalence_confirmed':False,'real_OCR_performed':False,'manufacturer_confirmed':False})

changes=[r for r in rows if r['regression_against_r367']]
wrong=[r for r in rows if r['r368_cross_pair_text_prefill']]
checks={
  '325_typing_only_edges':len(pairs)==len(rows)==325,
  '393_total_review_edges':len(ledger['pairs'])==393,
  'distinct_typing_endpoints_all_loaded':len(before)==len(after)==len(texts),
  '5103_references_unchanged':len(records)==5103,
  '10_canonical_hashes_unchanged':len(hashes)==10 and hashes==ledger['canonical_sha256'],
  'every_full_catalogue_call_ready':all(x['catalogueReady'] is True for x in after.values()),
  'R368_vs_R367_no_changed_typing_decisions':not changes,
  'all_pairs_diagnostic_only':all(not x['real_OCR_performed'] and not x['reference_physical_equivalence_confirmed'] and not x['manufacturer_confirmed'] for x in rows),
  'no_js_errors':not errors,
}
result={'schema':'bres-cat-r368-typing-only-js-audit-v1','milestone':'CAT-R368','date':'2026-11-03',
 'ok':all(checks.values()),'checks':checks,'canonical_sha256':hashes,'reference_count':5103,
 'typing_pairs':len(pairs),'distinct_typing_endpoints':len(texts),'r367_to_r368_regression_pair_count':len(changes),
 'text_prefill_to_other_review_reference_pairs':len(wrong),
 'cross_pair_text_prefill_priorities':wrong[:60], 'rows':rows,'js_errors':errors,
 'catalogue_mutated':False,'physical_validation':False,'real_OCR_performed':False,
 'limitations':['Text-only synthetic transcription, not actual OCR/photo','A typing neighbour is not a known misrecognition or equivalent physical key','Pairs with cross-prefill are triage candidates, not verified incorrect key identifications']}
(C/'CAT_R368_TYPING_RUNTIME_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (C/'CAT_R368_TYPING_RUNTIME_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as f:
    keys=['reference_a','reference_b','edit_types','r368_a_prefill','r368_b_prefill','r368_a_eligible','r368_b_eligible','r368_cross_pair_text_prefill','regression_against_r367','priority']
    wr=csv.DictWriter(f,keys);wr.writeheader();
    for x in rows:wr.writerow({k:('|'.join(x[k]) if isinstance(x[k],list) else x[k]) for k in keys})
(C/'CAT_R368_TYPING_RUNTIME_AUDIT.txt').write_text(f"CAT-R368 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)}: {len(pairs)} typing-only edges, {len(texts)} endpoints, {len(changes)} changed R367->R368 decisions, {len(wrong)} text-prefill cross-pair triage cases. No physical key / OCR.\n")
print(json.dumps({'ok':result['ok'],'checks':len(checks),'endpoints':len(texts),'cross_pair_triage':len(wrong),'changed_decisions':len(changes),'errors':errors[:2]},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)