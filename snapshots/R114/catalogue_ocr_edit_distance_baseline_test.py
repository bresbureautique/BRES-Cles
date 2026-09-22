from pathlib import Path
import json,re,hashlib,sys
ROOT=Path(__file__).resolve().parent
prefix='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'
expected={'catalog-01.js':'e105dc58c5a5466861f7c77e6259ce19aed2a9c47916feb61ada5509244d3a1b','catalog-02.js':'955843144211e70ca729aedc9cde82a93fd4ae6fafa81529d8470101116f4f75','catalog-03.js':'9f1940683f9a52c7a0c7c4a886811107e7a832b1f7daf218969cc0b40c7f6210','catalog-04.js':'14652e82b2c34c5ba8fabf8c4434556545ed1c642cbfe5d225cfa11030235942','catalog-05.js':'5867e331e50e932ff3cc8dc57beffc16e501f922eae0c7419cd400ad8341801b','catalog-06.js':'b32995f4f0713933804e73d8464b5e05a8cbc79249d7c1b5abac832958f285ac','catalog-07.js':'b7bbf9e751298c948029a746f8c6000310ee89958f70d829842db5b4194231b1','catalog-08.js':'3fc124a98ee082aa63516daa64b7ffd5d9d83290255632accb654db8b229a814','catalog-09.js':'4c7fcc349a620e354ca1224f68099c9c3fb4bedc90e4d9451cfc452314890d1f','catalog-10.js':'f92b2c802862e385643c2b7c3bf0e797105a9652625da704a3fd72993020e9e4'}
rows=[]; hashes={}; errors=[]
for i in range(1,11):
 p=ROOT/f'catalogue/v3/catalog-{i:02d}.js'; b=p.read_bytes(); hashes[p.name]=hashlib.sha256(b).hexdigest()
 if hashes[p.name]!=expected[p.name]: errors.append('chunk_changed:'+p.name)
 t=b.decode('utf-8'); rows+=json.loads(t[len(prefix):].rstrip()[:-2])
refs=[r[0] for r in rows]
eligible_raw=[r for r in refs if 3<=len(r)<=10 and re.search('[A-Z]',r) and re.search(r'\d',r)]
normalized=[re.sub('[^A-Z0-9]','',r) for r in eligible_raw]
refset=set(normalized)
maker={}
for row in rows:
 c=re.sub('[^A-Z0-9]','',row[0]); maker.setdefault(c,set()).add(str(row[1] or '').upper())
indel=set()
for longer in sorted(refset):
 for i in range(len(longer)):
  shorter=longer[:i]+longer[i+1:]
  if shorter in refset and shorter!=longer: indel.add(tuple(sorted((shorter,longer))))
def same_maker(a,b):
 ma={x for x in maker.get(a,set()) if x}; mb={x for x in maker.get(b,set()) if x}
 return bool(ma & mb)
same=sum(1 for a,b in indel if same_maker(a,b)); other=len(indel)-same
prefix_pairs=sum(1 for a,b in indel if a.startswith(b) or b.startswith(a))
suffix_pairs=sum(1 for a,b in indel if a.endswith(b) or b.endswith(a))
involved=set(x for p in indel for x in p)
checks={'catalogue_5103_unique':len(rows)==5103 and len(set(refs))==5103,'chunks_bit_identical':not any(e.startswith('chunk_changed:') for e in errors),'eligible_raw_5059':len(eligible_raw)==5059,'normalized_unique_5058':len(refset)==5058,'indel_distance1_pairs_4302':len(indel)==4302,'same_maker_indel_pairs_2522':same==2522,'other_or_blank_indel_pairs_1780':other==1780,'prefix_relation_pairs_1871':prefix_pairs==1871,'suffix_relation_pairs_365':suffix_pairs==365,'indel_involved_refs_3883':len(involved)==3883,'stable_examples_present':all(tuple(sorted(x)) in indel for x in [('AA1','AA1R'),('AB10','AB100'),('AB1R','AB1RX')])}
for k,v in checks.items():
 if not v: errors.append(k)
report={'schema':'bres-catalogue-ocr-edit-distance-baseline-v1','milestone':'BRES Clés catalogue audit R114','active_test_runtime':'V2.28 TEST R113','policy':'Audit only: a one-character insertion/deletion neighbour must never become an automatic OCR validation without independent evidence.','metrics':{'rows':len(rows),'unique_refs':len(set(refs)),'eligible_raw':len(eligible_raw),'normalized_unique':len(refset),'indel_distance1_pairs':len(indel),'same_maker_indel_pairs':same,'other_or_blank_indel_pairs':other,'prefix_relation_pairs':prefix_pairs,'suffix_relation_pairs':suffix_pairs,'indel_involved_refs':len(involved)},'examples_same_maker':[list(p) for p in sorted(indel) if same_maker(*p)][:20],'chunk_sha256':hashes,'checks':checks,'errors':errors,'ok':not errors}
(ROOT/'catalogue/evidence/catalogue_ocr_edit_distance_r114.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS — AUDIT CATALOGUE/OCR R114 (runtime V2.28 TEST R113 inchangé)','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['',f"Mesures: {len(indel)} paires insertion/suppression; {same} même fabricant; {len(involved)} références concernées.",'SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'CATALOGUE_OCR_EDIT_DISTANCE_TEST_R114.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines));sys.exit(1 if errors else 0)
