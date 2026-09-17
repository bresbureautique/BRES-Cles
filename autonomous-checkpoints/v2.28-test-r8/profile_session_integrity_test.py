from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parent
js=(ROOT/'v228-catalogue.js').read_text(encoding='utf-8')
checks={
    'schema calibration R8 v2': "schema:'bres-profile-calibration-v2'" in js,
    'diagnostic R8 v3': "schema:'bres-profile-diagnostic-v3'" in js,
    'référence session verrouillée': 'sessionKnownRef' in js and 'Référence certaine modifiée pendant la session' in js,
    'reset efface la référence': "const kr=el2('profileKnownRef');if(kr)kr.value=''" in js,
    'contrôle existence catalogue': 'knownReferenceExistsInCatalogue' in js,
    'contrôle présence groupe top': 'knownReferenceInTopGroup' in js,
    'bloc intégrité exporté': 'referenceStable' in js and 'referenceExistsInCatalogue' in js and 'validForReplay' in js,
    'minimum deux captures': 'sufficientCaptures' in js and 'profileSession.length>=2' in js,
    'aucune photo brute exportée': all(x not in js for x in ['rawImage:','imageData:','dataUrl:','base64Image:']),
}
cp=subprocess.run([sys.executable,str(ROOT/'profile_calibration_replay.py'),'--selftest'],capture_output=True,text=True,timeout=30)
checks['replay R8 selftest']=(cp.returncode==0 and 'SELFTEST OK' in cp.stdout and '"skipped": 1' in cp.stdout and '"PROVISIONAL"' in cp.stdout)
lines=['BRES CLÉS V2.28 TEST R8 — TEST INTÉGRITÉ SESSION CALIBRATION','']
for name,ok in checks.items(): lines.append(('OK  ' if ok else 'ECHEC  ')+name)
lines += ['', 'R8 empêche le mélange de deux références dans une même session, marque les exports non exploitables quand nécessaire, et refuse de transformer un très petit échantillon en réglage global.', '', 'SELFTEST REPLAY:', cp.stdout.strip()]
(ROOT/'PROFILE_SESSION_INTEGRITY_TEST_R8.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
raise SystemExit(0 if all(checks.values()) else 1)
