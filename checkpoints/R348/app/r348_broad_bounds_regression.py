#!/usr/bin/env python3
"""Demonstrate R346 accepted unrealistic browser measurements that R348 rejects."""
from __future__ import annotations
import copy
import json
import tempfile
from pathlib import Path
from validate_r346_device_result import validate as prior
from validate_r348_device_result import validate as new

ROOT=Path(__file__).resolve().parent
original=json.loads((ROOT/'R337_FIXTURE_CANONICAL.json').read_text(encoding='utf-8'))

def mutate(name):
    d=copy.deepcopy(original)
    e=d['r334Meta']['deviceEvidence'];s=e['screen']
    if name=='giant_screen_width':
        s['width']=1000000;s['availWidth']=1000000
    elif name=='giant_screen_height':
        s['height']=1000000;s['availHeight']=1000000
    elif name=='giant_pixel_ratio':s['pixelRatio']=1e6
    elif name=='minuscule_pixel_ratio':s['pixelRatio']=0.0001
    elif name=='giant_core_count':e['hardwareConcurrency']=1000000
    elif name=='giant_device_memory':e['deviceMemory']=1000000
    elif name=='landscape':s.update({'width':800,'height':360,'availWidth':800,'availHeight':340,'pixelRatio':3.0})
    elif name=='optionals_absent':e.update({'hardwareConcurrency':None,'deviceMemory':None})
    elif name=='upper_bound':
        s.update({'width':16384,'height':16384,'availWidth':16384,'availHeight':16384,'pixelRatio':16})
        e.update({'hardwareConcurrency':1024,'deviceMemory':2048})
    return d

negative=['giant_screen_width','giant_screen_height','giant_pixel_ratio',
          'minuscule_pixel_ratio','giant_core_count','giant_device_memory']
positive=['canonical','landscape','optionals_absent','upper_bound']
checks={};prior_acceptance={};errors={}
with tempfile.TemporaryDirectory() as td:
    for name in positive+negative:
        file=Path(td)/(name+'.json');file.write_text(json.dumps(mutate(name)),encoding='utf-8')
        a=prior(file);b=new(file)
        prior_acceptance[name]=a['ok'];errors[name]=b['errors']
        checks[name+'_r346_prior_accepted']=a['ok'] is True
        checks[name+'_r348_'+('accepted' if name in positive else 'rejected')]=b['ok'] is (name in positive)
        if name in negative:checks[name+'_has_specific_error']=bool(b['errors'])
        checks[name+'_never_activated']=b['automatic_activation'] is False and b['physical_samsung_verified'] is False
ok=all(checks.values())
report={'schema':'bres-r348-broad-bounds-regression-v1','parent':'R347',
        'six_previously_accepted_outliers_rejected':len(negative),
        'positive_cases':positive,'negative_cases':negative,'prior_acceptance':prior_acceptance,
        'checks':checks,'errors':errors,'physical_samsung':'PENDING','ok':ok}
(ROOT/'R348_BROAD_BOUNDS_REGRESSION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(ROOT/'R348_BROAD_BOUNDS_REGRESSION.txt').write_text(
    'BRES CLES — R348 BROWSER BOUNDS\n'+('PASS' if ok else 'FAIL')+f' | {len(negative)} incoherences rejetees, {len(positive)} cas normaux acceptes.\n'
    +'Limite : metadata navigateur declarative, Samsung physique PENDING.\n',encoding='utf-8')
print(json.dumps({'ok':ok,'checks':len(checks),'outliers_rejected':len(negative)},ensure_ascii=False))
raise SystemExit(0 if ok else 1)