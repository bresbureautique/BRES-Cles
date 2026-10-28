#!/usr/bin/env python3
"""Verify CAT-R362 risk graph without modifying canonical catalogues."""
from __future__ import annotations
import hashlib,json,subprocess,sys,os
sys.dont_write_bytecode=True
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    old={n:h for h,n in (line.split('  ',1) for line in (R/'SNAPSHOT_MANIFEST_CAT_R361.sha256').read_text().splitlines())}
    changed=[n for n,h in old.items() if not (R/n).is_file() or sha(R/n)!=h]
    before={p.name:sha(p) for p in (R.parent/'app'/'catalogue'/'v3').glob('catalog-*.js')}
    result_script=subprocess.run([sys.executable,str(R/'catalogue_collision_graph_cat_r362.py')],cwd=R,capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    new=json.loads((R/'CAT_R362_TEXT_COLLISION_GRAPH.json').read_text())
    prior=json.loads((R/'CAT_R361_SINGLE_EDIT_COLLISIONS.json').read_text())
    # Regression on the prior R361 code: outputs must remain byte-for-byte identical.
    oldfiles=['CAT_R361_SINGLE_EDIT_COLLISIONS.json','CAT_R361_NEW_TYPING_COLLISIONS.csv','CAT_R361_SINGLE_EDIT_COLLISIONS.txt']
    oldsha={f:sha(R/f) for f in oldfiles}
    oldscript=subprocess.run([sys.executable,str(R/'catalogue_single_edit_collision_cat_r361.py')],cwd=R,capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    rows,hashes,_=load_records(R.parent/'app')
    after={p.name:sha(p) for p in (R.parent/'app'/'catalogue'/'v3').glob('catalog-*.js')}
    checks={
      'parent_1471_files_unchanged':len(old)==1471 and not changed,
      'prior_R361_risk_outputs_still_identical':oldscript.returncode==0 and all(sha(R/f)==oldsha[f] for f in oldfiles),
      'R362_graph_script_succeeded':result_script.returncode==0 and new['ok'] and len(new['checks'])==14,
      'catalogue_5103_immutable_references':len(rows)==5103 and len(set(rec[0] for rec in rows))==5103,
      '10_canonical_sha256_same_as_parent':hashes==prior['canonical_sha256'] and len(hashes)==10,
      'catalogue_JS_chunks_not_modified':before==after and len(before)==10,
      'prior_393_hypothetical_edges_preserved':new['collision_edges']==393 and new['legacy_OCR_edges']==68 and new['new_typing_edges']==325,
      'graph_vertices_and_components_consistent':new['graph_vertices']==732 and new['component_count']==345 and max(c['reference_count'] for c in new['components'])==4,
      'priority_queue_separated_no_mutation':sum(new['review_priority_counts'].values())==345 and not new['data_modified'] and not new['OCR_rule_activated'],
      'all_group_members_fail_closed':all(not c['auto_validate'] and not c['merge'] and c['physical_key_confirmation_needed'] for c in new['components']),
      'maker_physical_claims_disabled':not new['manufacturer_confirmed'] and not new['physical_key_validated'],
    }
    outcome={'schema':'bres-cat-r362-checkpoint-verification-v1','milestone':'CAT-R362','parent':'CAT-R361',
             'old_parent_paths':len(old),'modified_parent_files':changed,'canonical_sha256':hashes,
             'checks':checks,'ok':all(checks.values()),'parent_test_stdout':oldscript.stdout.strip(),'new_test_stdout':result_script.stdout.strip()}
    (R/'CAT_R362_VERIFICATION.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'CAT_R362_VERIFICATION.txt').write_text(f'CAT-R362 {"PASS" if outcome["ok"] else "FAIL"}: {sum(checks.values())}/{len(checks)}\n'+'\n'.join(('PASS ' if ok else 'FAIL ')+k for k,ok in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':outcome['ok'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    return 0 if outcome['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
