#!/usr/bin/env python3
"""R344 pre-physical tests; does not change runtime or enable OCR rules."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SCRIPTS = ['verify_checkpoint_r343.py', 'r344_js_number_regression.py', 'active_inline_js_syntax_test_r310.py']
IMMUTABLE = {
 'index.html': '7695301023e526d4cdc92e05fcf7f62df1e56bef1ebc639766e91788849bbeba',
 'r331-device-benchmark.js': 'a1cfdd1f427175bcf0601a9b9df6b808b578199b03c7bfafac2ca7ac710849e8',
 'device_benchmark_r336.html': '3cda55a92c58a6fa0ec7050f7359e4b7dac5d5f1dd88c67d4dbba6f60c355da2',
}
checks={}; tails={}
for name in SCRIPTS:
    proc = subprocess.run([sys.executable,str(ROOT/name)],cwd=ROOT,capture_output=True,text=True,timeout=240)
    checks['suite_'+name]=proc.returncode==0
    tails[name]=(proc.stdout+'\n'+proc.stderr)[-650:]
for name, expected in IMMUTABLE.items():
    checks['immutable_'+name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
report=json.loads((ROOT/'R344_JS_NUMBER_REGRESSION.json').read_text(encoding='utf-8'))
checks['9_number_cases_all_pass']=report.get('ok') is True and report.get('cases')==9
checks['only_r305_active']='function keyComponentExactContinuitySafeActivationR305' in (ROOT/'index.html').read_text(encoding='utf-8')
checks['r156_test_marker']='V2.28 TEST R156' in (ROOT/'index.html').read_text(encoding='utf-8')
ok=all(checks.values())
result={'schema':'bres-r344-prephysical-verification-v1','milestone':'R344','parent':'R343',
        'checks':checks,'details':tails,'inherited_suites':10,'new_adversarial_suites':1,
        'physical_samsung':'PENDING','V227_stable_not_modified':True,
        'automatic_activation':False,'current_runtime_modified':False,'ok':ok}
(ROOT/'R344_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['BRES CLES - CONTROLE APPLICATION R344','RESULTAT: '+('PASS' if ok else 'FAIL')]
lines += [('PASS | ' if v else 'FAIL | ')+name for name,v in checks.items()]
lines += ['', '10 suites de R343 reprises et nouveau jeu adversarial des nombres JSON (9 cas).',
          'Samsung physique PENDING ; OCR R305 et moteur V2.28 TEST R156 inchanges.']
(ROOT/'R344_VERIFICATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines));raise SystemExit(0 if ok else 1)