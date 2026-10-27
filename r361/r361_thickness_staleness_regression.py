#!/usr/bin/env python3
"""R361: fail-closed diagnostic after manual caliper thickness changes.

Only tests V2.28 TEST R156 pilot in Chromium with the network blocked. Neither
physical identification nor OCR offline performance is certified.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent

def run():
    html=(R/'index.html').read_bytes();pilot=(R/'v228-catalogue.js').read_bytes()
    checks={};trace=[];errors=[];dialogs=[];failures=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            ctx=browser.new_context(service_workers='block');ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
            page=ctx.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            page.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
            page.on('requestfailed',lambda req:failures.append(req.url))
            page.set_content(html.decode('utf-8'),wait_until='domcontentloaded',timeout=45000)
            page.add_script_tag(content=pilot.decode('utf-8'))
            ref=page.locator('#manualRef');brand=page.locator('#manualBrand');th=page.locator('#manualThickness')
            status=page.locator('#manualRefStatus');final=page.locator('#finalDecision')
            def snap(stage):
                d={'stage':stage,'reference':ref.input_value(),'brand':brand.input_value(),'thickness':th.input_value(),
                   'status':status.inner_text()[:240],'status_class':status.get_attribute('class'),
                   'final':final.inner_text()[:260],'ocr':page.locator('#ocrStatus').inner_text()[:150]}
                trace.append(d);return d
            ref.fill('TE8D');page.locator('#manualRefBtn').click();first=snap('initial_verified')
            checks['known_reference_is_catalogue_candidate_not_physical_validation']=('Correspondance catalogue : TE8D' in first['status'] and 'RÉFÉRENCE TROUVÉE : TE8D' in first['final'] and 'VALIDÉ :' not in first['final'])
            th.fill('2.40');s=snap('caliper_value_added')
            checks['first_thickness_edit_revokes_manual_candidate']=('TE8D' not in s['status'] and s['status_class']=='status warn')
            checks['first_thickness_edit_revokes_final_decision']=('TE8D' not in s['final'] and 'en attente' in s['final'])
            checks['input_keeps_reference_brand_and_latest_measurement']=(s['reference']=='TE8D' and s['brand']=='' and s['thickness']=='2.40')
            checks['OCR_readout_explicitly_marked_stale']='Épaisseur modifiée' in s['ocr']
            checks['catalogue_image_cleared']=('Aucun visuel catalogue' in page.locator('#catalogVisual').inner_text())
            page.wait_for_timeout(850);s=snap('wait_after_edit')
            checks['delayed_lookup_does_not_reanimate_old_candidate']='TE8D' not in s['status'] and 'TE8D' not in s['final']
            page.locator('#manualRefBtn').click();s=snap('verified_with_new_thickness')
            checks['explicit_reverification_shows_current_thickness']=('2.40 mm' in s['status'] and 'RÉFÉRENCE TROUVÉE : TE8D' in s['final'])
            th.fill('3.10');s=snap('caliper_value_changed')
            checks['second_thickness_edit_revokes_new_decision']=('TE8D' not in s['status'] and 'en attente' in s['final'])
            th.fill('');s=snap('caliper_removed')
            checks['clearing_thickness_does_not_reinstate_old_decision']=('TE8D' not in s['final'] and 'en attente' in s['final'])
            brand.fill('TESA');ref.fill('TE8I');page.locator('#manualRefBtn').click();s=snap('new_reference_after_measurement_edit')
            checks['catalogue_lookup_reusable_after_thickness_revision']=('Correspondance catalogue : TE8I' in s['status'] and 'VALIDÉ :' not in s['final'])
            th.fill('2.55');page.locator('#clearManualBtn').click();s=snap('clear_fields_after_thickness_edit')
            checks['manual_clear_has_no_hidden_old_decision']=('TE8I' not in s['final'] and s['reference']=='' and s['brand']=='')
            checks['engine_remains_test_R156']=page.title()=='BRES Clés V2.28 TEST R156'
            checks['no_page_error_or_dialog']=not errors and not dialogs
            checks['offline_network_was_blocked']=bool(failures) and any('tesseract' in url.lower() for url in failures)
            ctx.close()
        finally:browser.close()
    out={'schema':'bres-r361-thickness-staleness-regression-v1','milestone':'R361','parent':'R360',
      'scope':'manual thickness invalidation after catalogue lookup (offline Chromium)',
      'sha256':{'index.html':hashlib.sha256(html).hexdigest(),'v228-catalogue.js':hashlib.sha256(pilot).hexdigest()},
      'checks':checks,'trace':trace,'page_errors':errors,'dialogs':dialogs,'failed_network_request_count':len(failures),
      'physical_samsung_tested':False,'ocr_offline_certified':False,'catalogue_v3_integrated':False,'ok':all(checks.values())}
    (R/'R361_THICKNESS_STALENESS_REGRESSION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'R361_THICKNESS_STALENESS_REGRESSION.txt').write_text(f"R361 {'PASS' if out['ok'] else 'FAIL'} : {sum(checks.values())}/{len(checks)} contrôles Chromium hors ligne.\nÉpaisseur modifiée : décision manuelle et diagnostic OCR invalidés immédiatement.\n",encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'errors':errors,'failed_network_requests':len(failures)},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(run())