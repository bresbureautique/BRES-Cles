from pathlib import Path
import json,re,collections,hashlib,sys

ROOT=Path(__file__).resolve().parent
P='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'

def pfx(ref):
    m=re.match(r'([A-Za-z]+)',ref)
    return m.group(1).upper() if m else ''

def load_rows():
    rows=[]
    for i in range(1,11):
        t=(ROOT/f'catalogue/v3/catalog-{i:02d}.js').read_text(encoding='utf-8')
        if not t.startswith(P):
            raise RuntimeError(f'Unexpected wrapper catalog-{i:02d}.js')
        rows += json.loads(t[len(P):].rstrip()[:-2])
    return rows

rows=load_rows()
known=[r for r in rows if str(r[1]).strip()]
blank=[r for r in rows if not str(r[1]).strip()]

gb=collections.defaultdict(collections.Counter)
pb=collections.defaultdict(collections.Counter)
for r in known:
    gb[str(r[2])][r[1]]+=1
    pb[pfx(r[0])][r[1]]+=1

cats=collections.Counter()
strong=[]
for r in blank:
    ref,b,g=r[:3]
    gc=gb[str(g)]
    pc=pb[pfx(ref)]
    if len(gc)>1:
        cats['D_AMBIGUOUS_GROUP']+=1
        continue
    brand=next(iter(gc)) if gc else None
    total=sum(pc.values())
    exact=pc.get(brand,0) if brand else 0
    ratio=exact/total if total else 0
    if brand and len(pc)==1 and next(iter(pc))==brand:
        cat='A_DUAL_EXACT'
    elif brand and ratio>=0.90:
        cat='B_PREFIX_DOMINANT'
    elif brand and exact>0:
        cat='C_MIXED_PREFIX'
    else:
        cat='C_PREFIX_CONFLICT'
    cats[cat]+=1
    if cat in ('A_DUAL_EXACT','B_PREFIX_DOMINANT'):
        strong.append((r,brand))

def geom_key(r):
    return json.dumps(r[3:9],separators=(',',':'),ensure_ascii=False)

known_geom=collections.defaultdict(list)
for r in known:
    known_geom[geom_key(r)].append(r)

triple=0
text_only=0
conflicts=0
for r,brand in strong:
    twins=known_geom.get(geom_key(r),[])
    brands={x[1] for x in twins}
    if twins and brands=={brand}:
        triple+=1
    elif twins:
        conflicts+=1
    else:
        text_only+=1

expected_cats={
    'A_DUAL_EXACT':42,
    'B_PREFIX_DOMINANT':16,
    'C_MIXED_PREFIX':14,
    'C_PREFIX_CONFLICT':1,
    'D_AMBIGUOUS_GROUP':91
}

checks=[
    ('5103_references',len(rows)==5103),
    ('5103_unique',len({r[0] for r in rows})==5103),
    ('164_blank_manufacturers',len(blank)==164),
    ('c2_categories_unchanged',dict(cats)==expected_cats),
    ('58_c2_strong',len(strong)==58),
    ('35_triple_internal_evidence',triple==35),
    ('23_strong_text_only',text_only==23),
    ('0_geometry_conflicts',conflicts==0),
]

# Verify the 10 catalogue chunk hashes against the R158-C3 continuity file.
cont=(ROOT/'CATALOGUE_CHUNK_CONTINUITY_R158_C3.txt').read_text(encoding='utf-8')
hash_ok=True
for i in range(1,11):
    name=f'catalog-{i:02d}.js'
    h=hashlib.sha256((ROOT/'catalogue/v3'/name).read_bytes()).hexdigest()
    if f'{name}  {h}  PASS' not in cont:
        hash_ok=False
checks.append(('10_chunks_hash_verified',hash_ok))

print('BRES CLÉS — CATALOGUE R158-C3 SELFTEST REPRODUCTIBLE')
for name,ok in checks:
    print(f'{name}: {"PASS" if ok else "FAIL"}')
print(f'TOTAL: {sum(ok for _,ok in checks)}/{len(checks)} PASS')
sys.exit(0 if all(ok for _,ok in checks) else 1)
