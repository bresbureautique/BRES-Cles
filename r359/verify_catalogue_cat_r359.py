#!/usr/bin/env python3
"""CAT-R359 additive provenance gate, preserving every CAT-R358 file verbatim."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    entries=(R/'SNAPSHOT_MANIFEST_CAT_R358.sha256').read_text(encoding='utf-8').splitlines()
    bad=[name for dig,name in (l.split('  ',1) for l in entries) if not (R/name).is_file() or sha(R/name)!=dig]
    p=subprocess.run([sys.executable,str(R/'catalogue_priority_provenance_cat_r359.py')],
      cwd=R,capture_output=True,text=True,timeout=100,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    out=json.loads((R/'CAT_R359_SOURCE_REVIEW.json').read_text(encoding='utf-8'))
    prev=json.loads((R/'CAT_R358_VERIFICATION.json').read_text(encoding='utf-8'))
    checks={
      'all_1444_prior_cat_files_byte_identical':len(entries)==1444 and not bad,
      'CAT_R358_10_checks_preserved':prev['ok'] and len(prev['checks'])==10,
      'source_provenance_script_pass':p.returncode==0 and out['ok'],
      '13_new_checks_pass':len(out['checks'])==13 and all(out['checks'].values()),
      'exact_5103_no_mutation':out['canonical_records']==out['distinct_references']==5103,
      '8_priority_groups_contain_18_distinct_refs':out['groups']==8 and out['priority_references']==18,
      'source_sha_matches_current_canonical_files':all(sha(R.parent/'app/catalogue/v3'/n)==v for n,v in out['canonical_sha256'].items()),
      'uncertainty_and_makers_not_certified':not out['samsung_calibration'] and not out['physical_identification_claimed'] and not out['maker_promoted'],
      'all_packets_manual_only':all(not pkt['approved_alias'] and not pkt['threshold_changed'] and not pkt['maker_attributed'] for pkt in out['manual_packets']),
    }
    report={'schema':'bres-cat-r359-verification-v1','milestone':'CAT-R359','parent':'CAT-R358',
      'checks':checks,'parent_entries':len(entries),'parent_mismatches':bad,
      'job':{'exit_code':p.returncode,'stdout':p.stdout[-700:],'stderr':p.stderr[-700:]},'ok':all(checks.values())}
    (R/'CAT_R359_VERIFICATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'CAT_R359_VERIFICATION.txt').write_text('CAT-R359 '+('PASS' if report['ok'] else 'FAIL')+'\n'+
      '\n'.join(('PASS' if v else 'FAIL')+' '+k for k,v in checks.items())+'\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'checks':len(checks),'parent_mismatch':len(bad)}))
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())