from pathlib import Path
import json,hashlib,sys
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
P='window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];\nwindow.BRES_CATALOG_V3.push(...'
TARGETS={'YA85R','YA18R','YA86R','YA17','YA4R','YA34','YA20','YA109','YA64R','YA32','YA69R','YA68R','YA16L','YA90'}
EXPECTED_FINAL={
    'catalog-01.js':'9fd12564aa987387a06e2d8e28d13ce1021ec5bb694ebae4f41ce827dcfe8ef0',
    'catalog-02.js':'3dbef93fd9bba1697ca16b8149277284e5eafa77bfc0a73a778d13ab000ef244',
    'catalog-03.js':'22d0afe722f46b706b7b6ce3d1b572434323dccd36e6d70442ee4d6c2d8e7a07',
    'catalog-04.js':'c6b3b3a333692dcf279583b9fd362b6e7ca41b615e34b402bf52d9c63a98c9f2',
    'catalog-05.js':'f2ce81a5a58f7556fd03f753b5ba223da3bcbe61e1aa57e8a7813bac73551d74',
    'catalog-06.js':'cdfe8dbb821f95dd29c0356d220cb1ab7f91ccc691f2d2061cc62021a9b0bbf5',
    'catalog-07.js':'3b0b223197514ba0b4eac50d130d7010c5dc47b60c0f32c19fdeb2661987142a',
    'catalog-08.js':'9fd24fecfd9ca0733a6fc54dc3c26e80a9db95477d8518ae9ed7c0f4f24f08d8',
    'catalog-09.js':'cb8cf3599dcc6fadd032a2e5b2e62b7922e5a46f4f0d7de8f7b90e755a41e7dd',
    'catalog-10.js':'f92b2c802862e385643c2b7c3bf0e797105a9652625da704a3fd72993020e9e4',
}

def load(p):
    t=p.read_text(encoding='utf-8')
    if not t.startswith(P): raise RuntimeError(f'Unexpected wrapper: {p}')
    return json.loads(t[len(P):].rstrip()[:-2])
def save(p,rows):
    p.write_text(P+json.dumps(rows,ensure_ascii=False,separators=(',',':'))+');\n',encoding='utf-8')
seen=set()
for i in range(1,11):
    p=ROOT/f'catalogue/v3/catalog-{i:02d}.js'
    rows=load(p); touched=False
    for r in rows:
        if r[0] in TARGETS:
            if str(r[1]).strip() not in ('','YALE'):
                raise RuntimeError(f'Precondition failed {r[0]} manufacturer={r[1]!r}')
            r[1]='YALE'; seen.add(r[0]); touched=True
    if touched: save(p,rows)
if seen!=TARGETS: raise RuntimeError(f'Missing targets: {sorted(TARGETS-seen)}')
for i in range(1,11):
    n=f'catalog-{i:02d}.js'; h=hashlib.sha256((ROOT/'catalogue/v3'/n).read_bytes()).hexdigest()
    if h!=EXPECTED_FINAL[n]: raise RuntimeError(f'Final hash mismatch {n}: {h}')
print('R158-C7 PATCH APPLY: PASS')
print('14 YALE manufacturer fields applied; final chunk hashes verified 10/10.')
