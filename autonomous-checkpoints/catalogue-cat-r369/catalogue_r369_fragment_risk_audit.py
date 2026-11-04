#!/usr/bin/env python3
"""CAT-R369 read-only fragment distribution of the 393 theoretical typo/OCR pairs.
No source/reference/maker edits. No photographs or physical equivalences.
"""
from pathlib import Path
from collections import Counter,defaultdict
from catalogue_audit_cat_r349 import load_records
import csv,hashlib,json,subprocess,re
C=Path(__file__).resolve().parent; A=C.parent/'app'
ledger=json.loads((C/'CAT_R363_PAIR_REVIEW_LEDGER.json').read_text(encoding='utf-8'))
records,hashes,_=load_records(A)
assert len(records)==5103
ref_to_chunk={}; ref_to_row={}
for i in range(1,11):
    name=f'catalog-{i:02}.js'
    raw=(A/'catalogue'/'v3'/name).read_text(encoding='utf8')
    m=re.search(r'push\(\.\.\.(\[.*\])\);?\s*$',raw.strip(),re.S)
    assert m
    for row in json.loads(m.group(1)):
        ref=str(row[0]);assert ref not in ref_to_chunk
        ref_to_chunk[ref]=i;ref_to_row[ref]=row
# Node's JSON.stringify number formatting is authoritative for the JS inventory checksum.
node=subprocess.run(['node',str(C/'hash_catalog_r369.js')],capture_output=True,text=True,check=True)
expected=json.loads(node.stdout)
rows=[]
for pair in ledger['pairs']:
    a,b=pair['reference_a'],pair['reference_b'];ra,rb=ref_to_row[a],ref_to_row[b]
    ca,cb=ref_to_chunk[a],ref_to_chunk[b]
    known_ocr=bool(pair['already_known_hypothetical_OCR'])
    try:
        delta_l=abs(float(ra[3])-float(rb[3]))
        delta_w=abs(float(ra[4])-float(rb[4]))
    except (IndexError,ValueError,TypeError):delta_l=delta_w=None
    rows.append({'ref_a':a,'ref_b':b,'risk_type':'glyph_confusion_THEORETICAL' if known_ocr else 'typing_neighbor_THEORETICAL',
                 'chunk_a':ca,'chunk_b':cb,'cross_chunk':ca!=cb,
                 'maker_a_labeled':bool(ra[1]),'maker_b_labeled':bool(rb[1]),
                 'length_delta_mm_REPORT_ONLY':round(delta_l,4) if delta_l is not None else None,
                 'width_delta_mm_REPORT_ONLY':round(delta_w,4) if delta_w is not None else None,
                 'automatically_equivalent':False,'physical_validation':False,
                 'priority':'P1_cross_fragment_ocr_ambiguity' if known_ocr and ca!=cb else ('P2_ocr' if known_ocr else 'P3_typing')})
counts=Counter(x['priority'] for x in rows)
ocr=[r for r in rows if r['risk_type']=='glyph_confusion_THEORETICAL']
typing=[r for r in rows if r['risk_type']=='typing_neighbor_THEORETICAL']
cross=[r for r in rows if r['cross_chunk']]
all_refs={r['ref_a'] for r in rows}|{r['ref_b'] for r in rows}
checks={
 'canonical_10_hashes_match_ledger':len(hashes)==10 and hashes==ledger['canonical_sha256'],
 '5103_unique_refs':len(records)==len(ref_to_chunk)==len(ref_to_row)==5103,
 '393_pairs':len(rows)==393,
 '68_theoretical_ocr_edges':len(ocr)==68,
 '325_typing_edges':len(typing)==325,
 '732_unique_review_refs':len(all_refs)==732,
 'all_review_refs_have_canonical_chunk':all(r['ref_a'] in ref_to_chunk and r['ref_b'] in ref_to_chunk for r in rows),
 'node_catalogue_checksum_equal_R369_guard':expected['length']==5103 and expected['hash1']==2511607957 and expected['hash2']==2549944249,
 'all_pairs_unverified_and_unmerged':all(not r['automatically_equivalent'] and not r['physical_validation'] for r in rows),
 'priority_partition_exact':sum(counts.values())==len(rows),
}
result={'schema':'bres-cat-r369-fragment-risk-audit-v1','milestone':'CAT-R369','date':'2026-11-04',
 'ok':all(checks.values()),'checks':checks,'catalogue_reference_count':len(records),
 'canonical_sha256':hashes,'expected_inventory_short_checksum_NONCRYPTO':expected['expectedHex'],
 'theoretical_ocr_pairs':len(ocr),'typing_pairs':len(typing),'distinct_review_references':len(all_refs),
 'cross_fragment_total':len(cross),'cross_fragment_ocr_pairs':sum(r['cross_chunk'] for r in ocr),
 'cross_fragment_typing_pairs':sum(r['cross_chunk'] for r in typing),
 'priority_counts':dict(sorted(counts.items())),'rows':rows,'catalogue_modified':False,
 'actual_ocr_executed':False,'physical_validation':False,'manufacturer_inferred':False,
 'limitations':['Pairs are theoretical textual risks, not known wrong-key identifications',
  'The fragment number is the file holding a reference, not a manufacturer or equivalence',
  'Geometry numeric differences are report-only and not calibrated tolerances',
  'R369 fingerprint covers columns 0..4 only, not complete original source authenticity']}
(C/'CAT_R369_FRAGMENT_RISK_AUDIT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
with (C/'CAT_R369_FRAGMENT_RISK_AUDIT.csv').open('w',newline='',encoding='utf-8-sig') as f:
    wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
(C/'CAT_R369_FRAGMENT_RISK_AUDIT.txt').write_text(f"CAT-R369 {'PASS' if result['ok'] else 'FAIL'} {sum(checks.values())}/{len(checks)} checks; 393 textual pairs, {len(cross)} across catalogue fragments ({result['cross_fragment_ocr_pairs']} OCR, {result['cross_fragment_typing_pairs']} typing), 732 unique refs. No physical OCR.\n"+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n',encoding='utf8')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'cross_fragment_ocr':result['cross_fragment_ocr_pairs'],'cross_fragment_typing':result['cross_fragment_typing_pairs'],'priority':counts},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
