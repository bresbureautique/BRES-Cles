#!/usr/bin/env python3
"""CAT-R390: group the existing priority queue without inferring equivalence."""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
import csv, json, re, hashlib, sys
C=Path(__file__).resolve().parent
contract=json.loads((C/'CAT_R386_FRAGMENT_CONTRACT.json').read_text())
rows={}; checks={}
for name, spec in sorted(contract['chunks'].items()):
    p=C.parent/'app'/'catalogue'/'v3'/name
    raw=p.read_bytes(); checks[name]=hashlib.sha256(raw).hexdigest()==spec['sha256']
    for r in json.loads(re.search(rb'push\(\.\.\.(\[.*\])\);?\s*$',raw,re.S)[1],parse_float=Decimal):
        assert r[0] not in rows; rows[r[0]]=r
with (C/'CAT_R389_EXACT_REVIEW_QUEUE.csv').open(encoding='utf-8-sig') as f:
    queue=list(csv.DictReader(f))
graph=defaultdict(set); edges={}; exact=set(); valid=True
for q in queue:
    a,b=q['ref_a'],q['ref_b']; x,y=rows[a],rows[b]
    delta=tuple(abs(Decimal(x[i])-Decimal(y[i])) for i in (3,4))
    edge=tuple(sorted((a,b)))
    valid &= a!=b and edge not in edges and max(delta)<=1 and (not x[1] or not y[1]) and delta==(Decimal(q['length_diff_mm']),Decimal(q['height_diff_mm'])) and (x[1],y[1])==(q['maker_a'],q['maker_b'])
    graph[a].add(b); graph[b].add(a); edges[edge]=delta
    if not any(delta):exact.add(edge)
remaining=set(graph); groups=[]
while remaining:
    seen=set(); todo=[min(remaining)]
    while todo:
        a=todo.pop()
        if a in seen:continue
        seen.add(a); todo.extend(graph[a]-seen)
    remaining-=seen
    links=sorted(e for e in edges if e[0] in seen and e[1] in seen)
    groups.append(dict(references=sorted(seen),direct_pairs=links,identical_length_height_pairs=[e for e in links if e in exact],missing_maker_refs=sorted(a for a in seen if not rows[a][1])))
groups.sort(key=lambda g:(-len(g['identical_length_height_pairs']),-len(g['direct_pairs']),g['references']))
checks.update(canonical_rows=len(rows)==5103,queue_integrity=valid and len(edges)==len(queue)==170,all_refs_covered=len(graph)==247 and sum(len(g['references']) for g in groups)==len(graph),all_edges_covered=sum(len(g['direct_pairs']) for g in groups)==len(edges),exact_edges_covered=sum(len(g['identical_length_height_pairs']) for g in groups)==len(exact),no_cross_group_edge=all(sum(a in g['references'] and b in g['references'] for g in groups)==1 for a,b in edges))
report=dict(milestone='CAT-R390',ok=all(checks.values()),checks=checks,priority_pairs=len(edges),references=len(graph),review_groups=len(groups),identical_length_height_pairs=len(exact),groups=groups,policy='Worklist grouping only; connected paths are not direct OCR pairs or physical equivalences. Identical two dimensions are not identity.',manufacturers_imputed=0,physical_equivalences=0)
(C/'CAT_R390_REVIEW_GRAPH.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='groups'}));sys.exit(not report['ok'])
