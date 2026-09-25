from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
idx=(ROOT/'index.html').read_text(encoding='utf-8')
errors=[]

hs=idx.find('function invalidateDecisionContextAndDiagnosticR172(reason){')
he=idx.find('\n}',hs)
helper=idx[hs:he+2] if hs>=0 and he>hs else ''
if not helper:
    errors.append('R172 invalidation helper missing')
else:
    for marker in ['invalidateIdentificationOutputs(reason);','clearOCRDiagnosticExport();']:
        if marker not in helper: errors.append('helper missing '+marker)
    inv=helper.find('invalidateIdentificationOutputs(reason);')
    clr=helper.find('clearOCRDiagnosticExport();')
    if inv<0 or clr<0 or not inv<clr:
        errors.append('R172 helper must close QA2 chain before clearing diagnostic')

manual_start=idx.find('el("manualRef").addEventListener("input"')
manual_end=idx.find('\nrefreshFieldSourceStatus();',manual_start)
manual=idx[manual_start:manual_end] if manual_start>=0 and manual_end>manual_start else ''
for reason in [
    'Référence modifiée : résultat précédent invalidé, revérification nécessaire.',
    'Marque modifiée : résultat précédent invalidé, revérification nécessaire.',
    'Saisie effacée : aucune validation précédente n’est conservée.'
]:
    call=f'invalidateDecisionContextAndDiagnosticR172("{reason}");'
    if call not in manual: errors.append('manual context path missing R172 helper: '+reason)
if manual.count('invalidateDecisionContextAndDiagnosticR172(')!=3:
    errors.append('manual context must have exactly 3 R172 invalidation calls')

ls=idx.find('function invalidateLocalTemplateDependentResults(')
le=idx.find('\nfunction handleExternalTemplateStorageChange',ls)
local=idx[ls:le] if ls>=0 and le>ls else ''
if 'invalidateDecisionContextAndDiagnosticR172(reason);' not in local:
    errors.append('local-template invalidation does not use R172 helper')
if 'bumpIdentificationEpoch();' not in local:
    errors.append('local-template invalidation lost identification epoch bump')

for fn,nextfn,label in [
    ('function invalidatePhotoDerivedIdentification(){','\nfunction invalidateHeadPhotoDerivedIdentification','main-photo'),
    ('function invalidateHeadPhotoDerivedIdentification(){','\nfunction resolvedOCRBrand','head-photo')
]:
    s=idx.find(fn); e=idx.find(nextfn,s)
    block=idx[s:e] if s>=0 and e>s else ''
    if not block: errors.append(label+' invalidation block missing'); continue
    if block.count('clearOCRDiagnosticExport();')!=1: errors.append(label+' clear count changed')
    if 'invalidateDecisionContextAndDiagnosticR172(' in block: errors.append(label+' must keep specialized photo invalidation path')

cs=idx.find('function clearOCRDiagnosticExport(){')
ce=idx.find('\nfunction safeOCRDiagnosticPass',cs)
clear_block=idx[cs:ce] if cs>=0 and ce>cs else ''
if not clear_block: errors.append('clearOCRDiagnosticExport block missing')
elif 'catalogueQa2LastContextReset=null' in clear_block: errors.append('diagnostic clear erases pending R168 reset trace')

report={
  'schema':'bres-manual-context-diagnostic-invalidation-guard-v1',
  'milestone':'R172',
  'helper_present':bool(helper),
  'qa2_closed_before_diagnostic_clear':bool(helper and helper.find('invalidateIdentificationOutputs(reason);')<helper.find('clearOCRDiagnosticExport();')),
  'manual_reference_uses_helper':'Référence modifiée : résultat précédent invalidé, revérification nécessaire.' in manual and manual.count('invalidateDecisionContextAndDiagnosticR172(')==3,
  'manual_brand_uses_helper':'Marque modifiée : résultat précédent invalidé, revérification nécessaire.' in manual and manual.count('invalidateDecisionContextAndDiagnosticR172(')==3,
  'manual_clear_uses_helper':'Saisie effacée : aucune validation précédente n’est conservée.' in manual and manual.count('invalidateDecisionContextAndDiagnosticR172(')==3,
  'local_template_uses_helper':'invalidateDecisionContextAndDiagnosticR172(reason);' in local,
  'photo_paths_preserved':not any('photo' in e for e in errors),
  'pending_r168_reset_preserved':bool(clear_block and 'catalogueQa2LastContextReset=null' not in clear_block),
  'errors':errors,
  'ok':not errors
}
(ROOT/'MANUAL_CONTEXT_DIAGNOSTIC_INVALIDATION_GUARD_TEST_R172.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
keys=['helper_present','qa2_closed_before_diagnostic_clear','manual_reference_uses_helper','manual_brand_uses_helper','manual_clear_uses_helper','local_template_uses_helper','photo_paths_preserved','pending_r168_reset_preserved']
lines=['BRES CLES - GARDE INVALIDATION DIAGNOSTIC CONTEXTE R172',f"RESULTAT: {'PASS' if report['ok'] else 'FAIL'}"]
for k in keys: lines.append(f"{'PASS' if report[k] else 'FAIL'} | {k}")
if errors: lines += ['ERREURS:']+['- '+e for e in errors]
else: lines += ['SELFTEST OK']
(ROOT/'MANUAL_CONTEXT_DIAGNOSTIC_INVALIDATION_GUARD_TEST_R172.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
sys.exit(0 if report['ok'] else 1)
