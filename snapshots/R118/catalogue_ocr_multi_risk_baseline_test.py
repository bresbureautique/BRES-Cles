from pathlib import Path
import json,re,hashlib,sys,itertools,collections
ROOT=Path(__file__).resolve().parent
prefix='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'
expected={'catalog-01.js':'e105dc58c5a5466861f7c77e6259ce19aed2a9c47916feb61ada5509244d3a1b','catalog-02.js':'955843144211e70ca729aedc9cde82a93fd4ae6fafa81529d8470101116f4f75','catalog-03.js':'9f1940683f9a52c7a0c7c4a886811107e7a832b1f7daf218969cc0b40c7f6210','catalog-04.js':'14652e82b2c34c5ba8fabf8c4434556545ed1c642cbfe5d225cfa11030235942','catalog-05.js':'5867e331e50e932ff3cc8dc57beffc16e501f922eae0c7419cd400ad8341801b','catalog-06.js':'b32995f4f0713933804e73d8464b5e05a8cbc79249d7c1b5abac832958f285ac','catalog-07.js':'b7bbf9e751298c948029a746f8c6000310ee89958f70d829842db5b4194231b1','catalog-08.js':'3fc124a98ee082aa63516daa64b7ffd5d9d83290255632accb654db8b229a814','catalog-09.js':'4c7fcc349a620e354ca1224f68099c9c3fb4bedc90e4d9451cfc452314890d1f','catalog-10.js':'f92b2c802862e385643c2b7c3bf0e797105a9652625da704a3fd72993020e9e4'}
rows=[]; hashes={}; errors=[]
for i in range(1,11):
 p=ROOT/f'catalogue/v3/catalog-{i:02d}.js'; b=p.read_bytes(); hashes[p.name]=hashlib.sha256(b).hexdigest()
 if hashes[p.name]!=expected[p.name]: errors.append('chunk_changed:'+p.name)
 t=b.decode('utf-8'); rows+=json.loads(t[len(prefix):].rstrip()[:-2])
refs=[str(r[0]) for r in rows]
eligible_raw=[r for r in refs if 3<=len(r)<=10 and re.search('[A-Z]',r) and re.search(r'\d',r)]
raw_by_norm=collections.defaultdict(set)
for r in eligible_raw: raw_by_norm[re.sub('[^A-Z0-9]','',r.upper())].add(r)
refset=set(raw_by_norm)
buckets=collections.defaultdict(list)
for r in refset:
 for i in range(len(r)): buckets[(len(r),i,r[:i]+'*'+r[i+1:])].append(r)
sub_pairs=set()
for vals in buckets.values():
 if len(vals)>1:
  for a,b in itertools.combinations(sorted(set(vals)),2):
   if sum(x!=y for x,y in zip(a,b))==1: sub_pairs.add((a,b))
sub_refs={x for p in sub_pairs for x in p}
indel_pairs=set()
for longer in sorted(refset):
 for i in range(len(longer)):
  shorter=longer[:i]+longer[i+1:]
  if shorter in refset and shorter!=longer: indel_pairs.add(tuple(sorted((shorter,longer))))
indel_refs={x for p in indel_pairs for x in p}
trans_pairs=set()
for r in refset:
 for i in range(len(r)-1):
  if r[i]==r[i+1]: continue
  swapped=r[:i]+r[i+1]+r[i]+r[i+2:]
  if swapped in refset and swapped!=r: trans_pairs.add(tuple(sorted((r,swapped))))
trans_refs={x for p in trans_pairs for x in p}
separator_refs={n for n,raws in raw_by_norm.items() if len(raws)>1}
risks={r:set() for r in refset}
for r in sub_refs: risks[r].add('substitution')
for r in indel_refs: risks[r].add('insertion_deletion')
for r in trans_refs: risks[r].add('transposition')
for r in separator_refs: risks[r].add('separator_collision')
risk_count_distribution=collections.Counter(len(v) for v in risks.values())
at_least_1=sum(1 for v in risks.values() if len(v)>=1); at_least_2=sum(1 for v in risks.values() if len(v)>=2); at_least_3=sum(1 for v in risks.values() if len(v)>=3); at_least_4=sum(1 for v in risks.values() if len(v)>=4)
checks={'catalogue_5103_unique':len(rows)==5103 and len(set(refs))==5103,'chunks_bit_identical':not any(e.startswith('chunk_changed:') for e in errors),'eligible_raw_5059':len(eligible_raw)==5059,'normalized_unique_5058':len(refset)==5058,'substitution_refs_4794':len(sub_refs)==4794,'indel_refs_3883':len(indel_refs)==3883,'transposition_refs_643':len(trans_refs)==643,'separator_collision_normalized_refs_1':len(separator_refs)==1,'multi_risk_at_least_1_4946':at_least_1==4946,'multi_risk_at_least_2_3819':at_least_2==3819,'multi_risk_at_least_3_556':at_least_3==556,'multi_risk_at_least_4_0':at_least_4==0,'zero_risk_refs_112':risk_count_distribution.get(0,0)==112,'exactly_one_risk_1127':risk_count_distribution.get(1,0)==1127,'exactly_two_risks_3263':risk_count_distribution.get(2,0)==3263,'exactly_three_risks_556':risk_count_distribution.get(3,0)==556,'bk34_three_risks':risks.get('BK34')=={'substitution','insertion_deletion','separator_collision'}}
for k,v in checks.items():
 if not v: errors.append(k)
report={'schema':'bres-catalogue-ocr-multi-risk-baseline-v1','milestone':'BRES Clés catalogue audit R118','active_test_runtime':'V2.28 TEST R116','metrics':{'rows':len(rows),'unique_refs':len(set(refs)),'eligible_raw':len(eligible_raw),'normalized_unique':len(refset),'substitution_pairs':len(sub_pairs),'substitution_refs':len(sub_refs),'indel_pairs':len(indel_pairs),'indel_refs':len(indel_refs),'transposition_pairs':len(trans_pairs),'transposition_refs':len(trans_refs),'separator_collision_normalized_refs':len(separator_refs),'refs_at_least_one_risk':at_least_1,'refs_at_least_two_risks':at_least_2,'refs_at_least_three_risks':at_least_3,'refs_at_least_four_risks':at_least_4},'checks':checks,'errors':errors,'ok':not errors}
(ROOT/'catalogue/evidence/catalogue_ocr_multi_risk_r118.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SELFTEST OK' if not errors else 'SELFTEST ECHEC');sys.exit(1 if errors else 0)
