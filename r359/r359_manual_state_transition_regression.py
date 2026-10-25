#!/usr/bin/env python3
"""R359 additive browser regression: positive/negative manual lookup transitions.

No catalogue V3 import, network access, or physical Samsung validation.
This deliberately operates on the unchanged R156 pilot runtime.
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
A=Path(__file__).resolve().parent


def main():
    src=(A/'index.html').read_bytes();pilot=(A/'v228-catalogue.js').read_bytes()
    checks={};log=[];errors=[];requests=[];alerts=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True, executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            ctx=b.new_context(service_workers='block')
            ctx.route('**/*', lambda r: r.abort('blockedbyclient'))
            page=ctx.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('requestfailed',lambda req:requests.append(req.url))
            page.on('dialog',lambda dialog:(alerts.append(dialog.message),dialog.dismiss()))
            page.set_content(src.decode('utf-8'),wait_until='domcontentloaded',timeout=45000)
            page.add_script_tag(content=pilot.decode('utf-8'))
            page.wait_for_timeout(150)
            def lookup(ref,brand=''):
                page.locator('#manualRef').fill(ref)
                page.locator('#manualBrand').fill(brand)
                page.locator('#manualRefBtn').click()
                result={ 'input':ref,'brand':brand, 'status':page.locator('#manualRefStatus').inner_text(),
                        'decision':page.locator('#finalDecision').inner_text() }
                log.append({k:(v[:260] if isinstance(v,str) else v) for k,v in result.items()})
                return result
            def found(result,ref):
                return ('Correspondance catalogue : '+ref in result['status'] and
                        'RÉFÉRENCE TROUVÉE : '+ref in result['decision'] and 'VALIDÉ :' not in result['decision'])
            def absent(result):return 'RÉFÉRENCE NON VALIDÉE' in result['decision']
            a=lookup('TE8D'); checks['known_TE8D_is_found_not_physically_validated']=found(a,'TE8D')
            x=lookup('VI2'); checks['unknown_VI2_clears_prior_qualified_state']=absent(x) and 'TE8D' not in x['decision']
            y=lookup('TE8I');checks['known_TE8I_is_found_not_physically_validated']=found(y,'TE8I')
            z=lookup('VL2');checks['unknown_VL2_clears_second_qualified_state']=absent(z) and 'TE8I' not in z['decision']
            aa=lookup('TE-8D');checks['known_separator_variant_resolves_TE8D_without_validation']=found(aa,'TE8D')
            bb=lookup('');checks['blank_clears_known_state']=absent(bb) and 'TE8D' not in bb['decision']
            cc=lookup('CLI1');checks['catalogue_V3_confusable_not_silently_imported']=absent(cc)
            dd=lookup('TE8B');checks['unverified_TE8B_not_promoted']=absent(dd)
            malicious='<img src=x onerror="globalThis.__bresR359Injected=1">'
            ee=lookup(malicious,malicious)
            checks['HTML_payload_never_activates_or_validates']=absent(ee) and page.evaluate('globalThis.__bresR359Injected') is None
            checks['manual_input_persists_as_text_not_as_markup']=malicious in ee['status']
            ff=lookup('TE8I');checks['post_attack_known_pilot_still_operational']=found(ff,'TE8I')
            checks['no_unhandled_JS_error_or_dialog']=not errors and not alerts
            checks['network_denied_and_Tesseract_unavailable']=page.evaluate('typeof globalThis.Tesseract')=='undefined' and any('tesseract' in s.lower() for s in requests)
            checks['R156_test_title_preserved']=page.title()=='BRES Clés V2.28 TEST R156'
            ctx.close()
        finally:b.close()
    out={'schema':'bres-r359-manual-pilot-transition-regression-v1','milestone':'R359','scope':'pilot only, browser network denied',
         'source_sha256':{'index.html':hashlib.sha256(src).hexdigest(),'v228-catalogue.js':hashlib.sha256(pilot).hexdigest()},
         'checks':checks,'transitions':log,'page_errors':errors,'unexpected_dialogs':alerts,
         'offline_OCR_certified':False,'samsung_real_pass':False,'catalogue_V3_imported':False,
         'ok':all(checks.values())}
    (A/'R359_MANUAL_STATE_REGRESSION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (A/'R359_MANUAL_STATE_REGRESSION.txt').write_text(
      f"R359 : {sum(checks.values())}/{len(checks)} contrôles {'PASS' if out['ok'] else 'FAIL'} ;\n"
      'TE8D et TE8I retrouvées dans PILOTE seulement.  Aucune validation physique.\n'
      'VI2 / VL2 / CLI1 / TE8B demeurent non validées ; état de décision réinitialisé.\n'
      'Entrées HTML hostiles neutralisées ; aucun import V3 ; OCR offline non certifié.\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'errors':len(errors),'dialogs':len(alerts)}))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(main())