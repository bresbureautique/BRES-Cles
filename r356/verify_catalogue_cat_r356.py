#!/usr/bin/env python3
"""CAT-R356 complete legacy replay, original hash gate and graph tests."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def main():
    jobs={}
    for name in ('verify_catalogue_cat_r355.py','catalogue_confusion_components_cat_r356.py'):
        p=subprocess.run([sys.executable,str(R/name)],cwd=R,text=True,capture_output=True,timeout=240)
        jobs[name]={'exit_code':p.returncode,'stdout':p.stdout[-1100:],'stderr':p.stderr[-1100:]}
    manifest=(R/'SNAPSHOT_MANIFEST_CAT_R355.sha256').read_text(encoding='utf-8').splitlines()
    bad=[]
    for ln in manifest:
        digest,name=ln.split('  ',1)
        if not (R/name).is_file() or hashlib.sha256((R/name).read_bytes()).hexdigest()!=digest:bad.append(name)
    graph=json.loads((R/'CAT_R356_OCR_COMPONENTS.json').read_text(encoding='utf-8'))
    parent=json.loads((R/'CAT_R355_VERIFICATION.json').read_text(encoding='utf-8'))
    canon={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (R.parent/'app/catalogue/v3').glob('catalog-*.js')}
    checks={
      'historic_CAT_R355_replay':parent['ok'] and jobs['verify_catalogue_cat_r355.py']['exit_code']==0,
      'CAT_R356_confusable_graph_replay':jobs['catalogue_confusion_components_cat_r356.py']['exit_code']==0 and graph['ok'],
      'parent_1416_files_unchanged':len(manifest)==1416 and not bad,
      '10_canonical_fragments_unchanged':len(canon)==10 and canon==graph['canonical_sha256'],
      'exactly_5103_unchanged_unique_keys':graph['references']==graph['unique']==5103,
      '68_links_64_components_130_nodes':(graph['edges'],graph['component_count'],graph['graph_references'])==(68,64,130),
      'all_12_graph_invariants_pass':len(graph['checks'])==12 and all(graph['checks'].values()),
      '4_synthetic_graph_fixtures_pass':len(graph['synthetic_tests'])==4 and all(graph['synthetic_tests'].values()),
      'two_triples_report_only':len(graph['triple_groups'])==2 and graph['thresholds_changed'] is False,
      'no_maker_or_alias_automation':graph['manufacturer_inferred'] is False and graph['new_aliases_created'] is False,
    }
    report={'milestone':'CAT-R356','parent':'CAT-R355','jobs':jobs,'parent_files':len(manifest),
            'parent_hash_mismatches':bad,'checks':checks,'ok':all(checks.values())}
    (R/'CAT_R356_VERIFICATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'CAT_R356_VERIFICATION.txt').write_text('CAT-R356 '+('PASS' if report['ok'] else 'FAIL')+'\n'+
      '\n'.join(('PASS ' if good else 'FAIL ')+name for name,good in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'checks':len(checks),'parent_files':len(manifest)}))
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
