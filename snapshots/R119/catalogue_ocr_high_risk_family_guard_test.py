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
eligible=[r for r in rows if 3<=len(str(r[0]))<=10 and re.search('[A-Z]',str(r[0])) and re.search(r'\d',str(r[0]))]
raw_by_norm=collections.defaultdict(set); rows_by_norm=collections.defaultdict(list)
for row in eligible:
 raw=str(row[0]); norm=re.sub('[^A-Z0-9]','',raw.upper()); raw_by_norm[norm].add(raw); rows_by_norm[norm].append(row)
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
triple=sorted(r for r,v in risks.items() if len(v)>=3)
def family_key(norm):
 m=re.match(r'[A-Z]+',norm)
 if m:return m.group(0)
 m=re.search(r'[A-Z]+',norm)
 return '#'+m.group(0) if m else '#'
maker_counts=collections.Counter(); family_counts=collections.Counter(); maker_family_counts=collections.Counter(); triple_rows=[]
for norm in triple:
 makers=sorted({str(row[1]).strip().upper() or '(SANS FABRICANT)' for row in rows_by_norm[norm]}) or ['(SANS FABRICANT)']
 fam=family_key(norm)
 for maker in makers:
  maker_counts[maker]+=1; maker_family_counts[(maker,fam)]+=1
 family_counts[fam]+=1
 triple_rows.append({'norm':norm,'raw_refs':sorted(raw_by_norm[norm]),'makers':makers,'family':fam,'risks':sorted(risks[norm])})
combo_counts=collections.Counter(tuple(sorted(risks[n])) for n in triple)
checks={'catalogue_5103_unique':len(rows)==5103 and len(set(refs))==5103,'chunks_bit_identical':not any(e.startswith('chunk_changed:') for e in errors),'triple_risk_refs_556':len(triple)==556,'classic_three_risk_555':combo_counts.get(('insertion_deletion','substitution','transposition'),0)==555,'separator_three_risk_1':combo_counts.get(('insertion_deletion','separator_collision','substitution'),0)==1,'bk34_special_case':risks.get('BK34')=={'substitution','insertion_deletion','separator_collision'},'abus_top_34':maker_counts.get('ABUS')==34,'blank_maker_26':maker_counts.get('(SANS FABRICANT)')==26,'family_ya_42':family_counts.get('YA')==42,'family_ab_39':family_counts.get('AB')==39,'maker_family_abus_ab_34':maker_family_counts.get(('ABUS','AB'))==34,'maker_family_abloy_ay_16':maker_family_counts.get(('ABLOY','AY'))==16}
for k,v in checks.items():
 if not v: errors.append(k)
report={'schema':'bres-catalogue-ocr-high-risk-family-r119-v1','milestone':'BRES Clés catalogue audit R119','active_test_runtime':'V2.28 TEST R116','policy':'Audit/guard only: catalogue references exposed to at least three OCR collision mechanisms may be proposed as candidates, but final automatic validation requires independent image/geometry/profile evidence; normalized OCR text alone is insufficient.','family_definition':'family = leading alphabetic prefix of punctuation-stripped canonical reference; if reference starts with a digit, use the first alphabetic run prefixed with #.','metrics':{'rows':len(rows),'unique_refs':len(set(refs)),'triple_risk_refs':len(triple),'triple_risk_classic_sub_indel_trans':combo_counts.get(('insertion_deletion','substitution','transposition'),0),'triple_risk_separator_special':combo_counts.get(('insertion_deletion','separator_collision','substitution'),0),'manufacturers_with_triple_risk':len(maker_counts),'families_with_triple_risk':len(family_counts)},'top_manufacturers':[{'maker':k,'refs':v} for k,v in maker_counts.most_common(30)],'top_families':[{'family':k,'refs':v} for k,v in family_counts.most_common(30)],'top_maker_families':[{'maker':k[0],'family':k[1],'refs':v} for k,v in maker_family_counts.most_common(50)],'triple_risk_refs_sha256':hashlib.sha256(('\n'.join(triple)+'\n').encode('utf-8')).hexdigest(),'examples_triple_risk':triple_rows[:80],'chunk_sha256':hashes,'checks':checks,'errors':errors,'ok':not errors}
(ROOT/'catalogue/evidence/catalogue_ocr_high_risk_family_r119.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS — AUDIT CATALOGUE/OCR R119 (runtime V2.28 TEST R116 inchangé)','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['',f'Triple risque: {len(triple)} références. Top fabricants: '+', '.join(f'{k}={v}' for k,v in maker_counts.most_common(5))+'.',f'Top familles: '+', '.join(f'{k}={v}' for k,v in family_counts.most_common(5))+'.','SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'CATALOGUE_OCR_HIGH_RISK_FAMILY_TEST_R119.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines));sys.exit(1 if errors else 0)
