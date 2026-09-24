from pathlib import Path
import json,re,collections,hashlib,sys
ROOT=Path(__file__).resolve().parent
P='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'
rows=[]
for i in range(1,11):
    t=(ROOT/f'catalogue/v3/catalog-{i:02d}.js').read_text(encoding='utf-8')
    rows += json.loads(t[len(P):].rstrip()[:-2])
def pfx(ref):
    m=re.match(r'([A-Za-z]+)',ref); return m.group(1).upper() if m else ''
gb=collections.defaultdict(collections.Counter); pb=collections.defaultdict(collections.Counter)
for r in rows:
    ref,b,g=r[:3]
    if b.strip(): gb[g][b]+=1; pb[pfx(ref)][b]+=1
cats=collections.Counter(); blank=0
for r in rows:
    ref,b,g=r[:3]
    if b.strip(): continue
    blank+=1; gc=gb[g]; pc=pb[pfx(ref)]
    if len(gc)>1: cats['D_AMBIGUOUS_GROUP']+=1; continue
    brand=next(iter(gc)); total=sum(pc.values()); exact=pc.get(brand,0); ratio=exact/total if total else 0
    if len(pc)==1 and next(iter(pc))==brand: cats['A_DUAL_EXACT']+=1
    elif ratio>=0.90: cats['B_PREFIX_DOMINANT']+=1
    elif exact>0: cats['C_MIXED_PREFIX']+=1
    else: cats['C_PREFIX_CONFLICT']+=1
expected={'A_DUAL_EXACT':42,'B_PREFIX_DOMINANT':16,'C_MIXED_PREFIX':14,'C_PREFIX_CONFLICT':1,'D_AMBIGUOUS_GROUP':91}
checks=[len(rows)==5103,len({r[0] for r in rows})==5103,blank==164,dict(cats)==expected]
print('BRES CLÉS — CATALOGUE R158-C2 SELFTEST')
print('5103 références:', 'PASS' if checks[0] else 'FAIL')
print('5103 uniques:', 'PASS' if checks[1] else 'FAIL')
print('164 fabricants vides:', 'PASS' if checks[2] else 'FAIL')
print('classification 42/16/14/1/91:', 'PASS' if checks[3] else 'FAIL')
print('SELFTEST OK' if all(checks) else 'SELFTEST ECHEC')
sys.exit(0 if all(checks) else 1)
