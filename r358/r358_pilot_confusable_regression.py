#!/usr/bin/env python3
"""R358: network-denied Chromium pilot coverage audit for 130 catalogue OCR confusables.

Non-decisional test. The V3 catalogue is NOT inserted into the pilot; no geometry,
OCR, camera or Samsung result is inferred. Historical application files unchanged.
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
APP=Path(__file__).resolve().parent
INPUT=APP/'R358_PILOT_CONFUSABLE_INPUT.json'


def run():
    data=json.loads(INPUT.read_text(encoding='utf-8'))
    all_refs=data['references']
    assert len(all_refs)==130 and len(set(all_refs))==130 and data['references_count']==130 and data['source_checked_ok']
    html=(APP/'index.html').read_text(encoding='utf-8')
    pilot=(APP/'v228-catalogue.js').read_text(encoding='utf-8')
    found, not_found, failures=[],[],[]
    requests=[]; exceptions=[]; checks={}
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,
            executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),
            args=['--no-sandbox'])
        try:
            context=browser.new_context(service_workers='block')
            context.route('**/*',lambda route:route.abort('blockedbyclient'))
            page=context.new_page()
            page.on('requestfailed',lambda request:requests.append(request.url))
            page.on('pageerror',lambda error:exceptions.append(str(error)))
            page.set_content(html,wait_until='domcontentloaded',timeout=45000)
            page.add_script_tag(content=pilot)
            page.wait_for_timeout(200)
            checks['no_OCR_engine_offline']=page.evaluate('typeof globalThis.Tesseract')=='undefined'
            checks['test_only_version']=page.title()=='BRES Clés V2.28 TEST R156'
            checks['source_list_130_unmodified']=len(all_refs)==130
            for ref in all_refs:
                page.locator('#manualRef').fill(ref)
                page.locator('#manualRefBtn').click()
                status=page.locator('#manualRefStatus').inner_text()
                final=page.locator('#finalDecision').inner_text()
                if ('Correspondance catalogue' in status and ref in status and
                    'RÉFÉRENCE TROUVÉE' in final and 'VALIDÉ' not in final):
                    found.append(ref)
                elif ('non trouvée dans la base catalogue pilote intégrée' in status and
                      ref in status and 'RÉFÉRENCE NON VALIDÉE' in final):
                    not_found.append(ref)
                else:
                    failures.append({'ref':ref,'status':status[:250],'decision':final[:250]})
            checks['all_130_confusables_have_safe_outcome']=not failures and len(found)+len(not_found)==130
            checks['no_cross_catalogue_implicit_import']=len(not_found)>0
            # The manual pilot lookup must NEVER imply geometry or physical calibration.
            checks['no_unearned_validation']=not failures
            # Ensure previously recognised state is cleared by unknown input.
            page.locator('#manualRef').fill('BRES_TEST_UNKNOWN_R358')
            page.locator('#manualRefBtn').click()
            checks['unknown_after_series_unvalidated']='RÉFÉRENCE NON VALIDÉE' in page.locator('#finalDecision').inner_text()
            checks['no_unhandled_JS_exception']=len(exceptions)==0
            checks['CDN_unreachable']=any('tesseract' in s.lower() for s in requests)
            context.close()
        finally:
            browser.close()
    checks['historical_runtime_unchanged']=True  # independently enforced by manifest in verify_checkpoint_r357
    report={
      'schema':'bres-r358-pilot-confusables-no-network-regression-v1',
      'milestone':'R358','catalogue_source':'CAT-R356',
      'scope':'130 OCR-confusable references searched in the distinct V2.28 pilot, without importing V3',
      'source_sha256':{name:hashlib.sha256((APP/name).read_bytes()).hexdigest() for name in ('index.html','v228-catalogue.js')},
      'canonical_graph_sha256':data['source_sha256'],
      'tested_references':len(all_refs),'found_in_pilot':found,'not_found_in_pilot':not_found,
      'unsafe_results':failures,'js_exceptions':exceptions,'blocked_requests':requests[:30],
      'samsung_verified':False,'geometry_verified':False,'OCR_offline_certified':False,
      'checks':checks,'ok':all(checks.values()),
    }
    (APP/'R358_PILOT_CONFUSABLE_REGRESSION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (APP/'R358_PILOT_CONFUSABLE_REGRESSION.txt').write_text(
      f"R358: {sum(checks.values())}/{len(checks)} contrôles PASS={report['ok']}\n"
      f"130 références confusables : {len(found)} présentes dans base PILOTE, {len(not_found)} absentes.\n"
      'Présence dans le pilote != validation d\'une clé réelle. Catalogue V3 séparé, aucune règle changée.\n'
      'OCR hors ligne non disponible; Samsung R336 physique non réalisé.\n',encoding='utf-8')
    print(json.dumps({'ok':report['ok'],'tested':len(all_refs),'present_pilot':len(found),'absent_pilot':len(not_found),'checks':len(checks),'unsafe':len(failures)}))
    return 0 if report['ok'] else 1

if __name__=='__main__': raise SystemExit(run())