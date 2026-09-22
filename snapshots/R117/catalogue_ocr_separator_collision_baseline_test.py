from pathlib import Path
import json,re,hashlib,sys,collections
ROOT=Path(__file__).resolve().parent
prefix='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'
expected={'catalog-01.js':'e105dc58c5a5466861f7c77e6259ce19aed2a9c47916feb61ada5509244d3a1b','catalog-02.js':'955843144211e70ca729aedc9cde82a93fd4ae6fafa81529d8470101116f4f75','catalog-03.js':'9f1940683f9a52c7a0c7c4a886811107e7a832b1f7daf218969cc0b40c7f6210','catalog-04.js':'14652e82b2c34c5ba8fabf8c4434556545ed1c642cbfe5d225cfa11030235942','catalog-05.js':'5867e331e50e932ff3cc8dc57beffc16e501f922eae0c7419cd400ad8341801b','catalog-06.js':'b32995f4f0713933804e73d8464b5e05a8cbc79249d7c1b5abac832958f285ac','catalog-07.js':'b7bbf9e751298c948029a746f8c6000310ee89958f70d829842db5b4194231b1','catalog-08.js':'3fc124a98ee082aa63516daa64b7ffd5d9d83290255632accb654db8b229a814','catalog-09.js':'4c7fcc349a620e354ca1224f68099c9c3fb4bedc90e4d9451cfc452314890d1f','catalog-10.js':'f92b2c802862e385643c2b7c3bf0e797105a9652625da704a3fd72993020e9e4'}
rows=[]; hashes={}; errors=[]
for i in range(1,11):
 p=ROOT/f'catalogue/v3/catalog-{i:02d}.js'; b=p.read_bytes(); hashes[p.name]=hashlib.sha256(b).hexdigest()
 if hashes[p.name]!=expected[p.name]: errors.append('chunk_changed:'+p.name)
 t=b.decode('utf-8'); rows+=json.loads(t[len(prefix):].rstrip()[:-2])
refs=[str(r[0]) for r in rows]
by_norm=collections.defaultdict(list)
for row in rows:
 raw=str(row[0]); maker=str(row[1] or '').upper(); norm=re.sub('[^A-Z0-9]','',raw.upper())
 by_norm[norm].append((raw,maker))
collisions={k:v for k,v in by_norm.items() if len(v)>1}
collision_rows=sum(len(v) for v in collisions.values())
same_maker=0
for vals in collisions.values():
 makers={m for _,m in vals if m}
 if len(makers)==1 and makers: same_maker+=1
punctuated_refs=[r for r in refs if re.search('[^A-Za-z0-9]',r)]
checks={
 'catalogue_5103_unique':len(rows)==5103 and len(set(refs))==5103,
 'chunks_bit_identical':not any(e.startswith('chunk_changed:') for e in errors),
 'normalized_unique_5102':len(by_norm)==5102,
 'separator_collision_groups_1':len(collisions)==1,
 'separator_collision_rows_2':collision_rows==2,
 'same_maker_collision_groups_1':same_maker==1,
 'known_collision_bk34':collisions.get('BK34')==[('BK3-4','BKS'),('BK34','BKS')],
 'punctuated_refs_present':len(punctuated_refs)>0,
}
for k,v in checks.items():
 if not v: errors.append(k)
report={
 'schema':'bres-catalogue-ocr-separator-collision-baseline-v1',
 'milestone':'BRES Clés catalogue audit R117',
 'active_test_runtime':'V2.28 TEST R116',
 'policy':'Audit only: separator-stripping normalization must never auto-validate a reference when two distinct canonical references collapse to the same normalized token; exact raw match or independent evidence is required.',
 'metrics':{
   'rows':len(rows),'unique_refs':len(set(refs)),'normalized_unique':len(by_norm),
   'separator_collision_groups':len(collisions),'separator_collision_rows':collision_rows,
   'same_maker_collision_groups':same_maker,'punctuated_refs':len(punctuated_refs)
 },
 'collisions':{k:[{'reference':r,'maker':m} for r,m in v] for k,v in sorted(collisions.items())},
 'chunk_sha256':hashes,'checks':checks,'errors':errors,'ok':not errors
}
(ROOT/'catalogue/evidence/catalogue_ocr_separator_collision_r117.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLÉS — AUDIT CATALOGUE/OCR R117 (runtime V2.28 TEST R116 inchangé)','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['',f"Mesures: {len(collisions)} collision après suppression séparateurs; {collision_rows} références concernées; collision connue BK3-4 / BK34 (BKS).",'SELFTEST OK' if not errors else 'SELFTEST ECHEC']
(ROOT/'CATALOGUE_OCR_SEPARATOR_COLLISION_TEST_R117.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines));sys.exit(1 if errors else 0)
