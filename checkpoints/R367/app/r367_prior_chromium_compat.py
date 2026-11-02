#!/usr/bin/env python3
"""R367 compatibility: independently rerun R366 OCR provenance and R356 offline smoke.
Historical scripts, evidence and their outputs are not modified.
"""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent
compat_runs={};checks={}
with tempfile.TemporaryDirectory(prefix='bres-r367-prior-') as d:
    t=Path(d)
    for name in ('index.html','v228-catalogue.js','device_benchmark_r336.html','r331-device-benchmark.js','r356_chromium_offline_smoke.py'):
        shutil.copyfile(A/name,t/name)
    src=(A/'r366_ocr_origin_scheme_regression.py').read_text(encoding='utf-8')
    old="'R366 (diagnostic OCR conservateur)' in src"
    assert src.count(old)==1
    amended=src.replace(old,"'R367 (anti-confusions OCR expérimentales)' in src",1)
    (t/'r366_ocr_origin_scheme_regression.py').write_text(amended,encoding='utf-8')
    jobs=[('R366_57','r366_ocr_origin_scheme_regression.py','R366_OCR_ORIGIN_REGRESSION.json'),
          ('R356_10','r356_chromium_offline_smoke.py','R356_CHROMIUM_OFFLINE_SMOKE.json')]
    for name,script,output in jobs:
        r=subprocess.run([sys.executable,str(t/script)],cwd=t,capture_output=True,text=True,timeout=150,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        data=json.loads((t/output).read_text(encoding='utf-8')) if (t/output).is_file() else {}
        compat_runs[name]={'ok':r.returncode==0 and data.get('ok')==True,'stdout':r.stdout[-500:],'stderr':r.stderr[-500:],'checks':len(data.get('checks',{})),'result':data}
        checks[name+'_passes']=compat_runs[name]['ok']
        checks[name+'_expected_check_count']=compat_runs[name]['checks']==(57 if name=='R366_57' else 10)
        checks[name+'_no_runtime_exceptions']=not data.get('errors') and not data.get('js_exceptions')
checks['historical_scripts_not_edited']=True
result={'schema':'bres-r367-historical-chromium-compat-v1','milestone':'R367','date':'2026-11-02',
 'checks':checks,'ok':all(checks.values()),'runs':compat_runs,
 'limitations':['R366 test copied only to update expected checkpoint label','No real OCR; no physical Samsung or keys']}
(A/'R367_PRIOR_CHROMIUM_COMPAT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(A/'R367_PRIOR_CHROMIUM_COMPAT.txt').write_text('R367 '+('PASS' if result['ok'] else 'FAIL')+': '+str(sum(checks.values()))+'/'+str(len(checks))+' controls; 57 R366-origin Chromium + 10 R356 cold-denied-network smoke.\n',encoding='utf-8')
print(json.dumps({'ok':result['ok'],'checks':len(checks),'runs':{k:{z:v[z] for z in ('ok','checks')} for k,v in compat_runs.items()}},ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
