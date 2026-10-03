#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from validate_r336_device_result import validate as validate_r336

CANONICAL_UTC_MS = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')

def canonical_utc_ms(value):
    return isinstance(value, str) and CANONICAL_UTC_MS.fullmatch(value) is not None

def validate(path: Path):
    base = validate_r336(path)
    errors=[]; warnings=[]
    try:
        d=json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return {
            'schema':'bres-r337-device-result-validation-v1','milestone':'R337','source':path.name,
            'ok':False,'engineering_review_candidate':False,'activation_candidate':False,'automatic_activation':False,
            'errors':['json_parse:'+str(e)],'warnings':[],'base_r336':base
        }
    r334=d.get('r334Meta') if isinstance(d.get('r334Meta'),dict) else {}
    r336=d.get('r336Meta') if isinstance(d.get('r336Meta'),dict) else {}
    fields={
        'createdAt': d.get('createdAt'),
        'r334_startedAt': r334.get('startedAt'),
        'r334_finishedAt': r334.get('finishedAt'),
        'r336_startedAt': r336.get('startedAt'),
        'r336_benchmarkCreatedAt': r336.get('benchmarkCreatedAt'),
        'r336_finishedAt': r336.get('finishedAt'),
    }
    noncanonical=[k for k,v in fields.items() if not canonical_utc_ms(v)]
    for k in noncanonical:
        errors.append('timestamp_noncanonical:'+k)
    # Browser Date.toISOString() emits millisecond UTC timestamps; requiring exactly that form
    # prevents equivalent-but-ambiguous timezone/precision rewrites from passing as a native receipt.
    canonical_ok=not noncanonical
    b_ok=bool(base.get('ok'))
    engineering=bool(b_ok and canonical_ok and base.get('engineering_review_candidate'))
    return {
        'schema':'bres-r337-device-result-validation-v1','milestone':'R337','source':path.name,
        'sha256':base.get('sha256'),'r336_ok':b_ok,'timestamp_canonical_ok':canonical_ok,
        'canonical_format':'YYYY-MM-DDTHH:MM:SS.sssZ','checked_fields':fields,
        'engineering_review_candidate':engineering,'activation_candidate':False,'automatic_activation':False,
        'errors':errors,'warnings':warnings,'base_r336':base,'ok':bool(b_ok and not errors)
    }

def main():
    ap=argparse.ArgumentParser(description='R337: valide R336 et exige les horodatages UTC milliseconde natifs de Date.toISOString(). Aucune activation automatique.')
    ap.add_argument('result_json',type=Path); ap.add_argument('--out',type=Path); a=ap.parse_args()
    r=validate(a.result_json); txt=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.out: a.out.write_text(txt,encoding='utf-8')
    print(txt,end=''); return 0 if r['ok'] else 2
if __name__=='__main__': raise SystemExit(main())
