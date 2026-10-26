#!/usr/bin/env python3
"""R360: browser-level regression for stale green lookup status after manual edits.

Tests the actual R156 pilot on V2.28 TEST, with outbound networking blocked.
Never asserts physical identification, Samsung performance or offline OCR.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent

def run():
    src=(R/'index.html').read_bytes(); pilot=(R/'v228-catalogue.js').read_bytes()
    checks={}; trace=[];errors=[];dialogs=[];failed_requests=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            ctx=browser.new_context(service_workers='block');ctx.route('**/*',lambda route:route.abort('blockedbyclient'))
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
            page.on('requestfailed',lambda q:failed_requests.append(q.url))
            page.set_content(src.decode('utf-8'),wait_until='domcontentloaded',timeout=45000)
            page.add_script_tag(content=pilot.decode('utf-8'))
            ref=page.locator('#manualRef');brand=page.locator('#manualBrand');status=page.locator('#manualRefStatus');decision=page.locator('#finalDecision')
            def snapshot(label):
                o={'phase':label,'reference':ref.input_value(),'brand':brand.input_value(),'status':status.inner_text()[:180],
                   'status_class':status.get_attribute('class'),'decision':decision.inner_text()[:160]}
                trace.append(o);return o
            def lookup(value):ref.fill(value);page.locator('#manualRefBtn').click();return snapshot('lookup_'+value[:15])
            initial=lookup('TE8D')
            checks['TE8D_first_match_without_earned_validation']=('Correspondance catalogue : TE8D' in initial['status'] and
                    'RÉFÉRENCE TROUVÉE : TE8D' in initial['decision'] and 'VALIDÉ :' not in initial['decision'])
            ref.fill('VI2');edit=snapshot('edit_ref_without_click')
            checks['immediate_reference_edit_clears_previous_green_status']=('TE8D' not in edit['status'] and edit['status_class']=='status warn')
            checks['immediate_reference_edit_invalidates_decision']=('TE8D' not in edit['decision'] and 'en attente' in edit['decision'])
            page.wait_for_timeout(820);later=snapshot('reference_wait_820ms')
            checks['debounce_without_geometry_cannot_resurrect_old_match']='TE8D' not in later['status']
            page.locator('#manualRefBtn').click();unknown=snapshot('unknown_verified')
            checks['unknown_ref_requires_correction']=('non trouvée' in unknown['status'] and 'NON VALIDÉE' in unknown['decision'])
            known=lookup('TE8I');checks['TE8I_relookup_works_after_negative']=('Correspondance catalogue : TE8I' in known['status'] and 'VALIDÉ :' not in known['decision'])
            brand.fill('AUTRE MARQUE');brand_edit=snapshot('brand_change_without_click')
            checks['immediate_brand_edit_clears_previous_green_status']=('TE8I' not in brand_edit['status'] and brand_edit['status_class']=='status warn')
            checks['brand_change_invalidates_prior_decision']=('TE8I' not in brand_edit['decision'] and 'en attente' in brand_edit['decision'])
            brand.fill('');brand_clear=snapshot('brand_clear_without_click')
            checks['brand_clear_does_not_restore_old_match']=('TE8I' not in brand_clear['status'] and brand_clear['status_class']=='status warn')
            page.locator('#manualRefBtn').click();reverified=snapshot('manually_reverify_same_ref')
            checks['manual_verification_restores_only_fresh_lookup']=('Correspondance catalogue : TE8I' in reverified['status'] and 'VALIDÉ :' not in reverified['decision'])
            injection='<img src=x onerror="globalThis.__bresR360Attack=1">'
            brand.fill(injection);att=snapshot('html_brand_edit')
            checks['hostile_brand_does_not_retain_old_green_status']=('TE8I' not in att['status'] and att['status_class']=='status warn')
            ref.fill(injection);page.locator('#manualRefBtn').click();att2=snapshot('html_ref_lookup')
            checks['hostile_input_never_executes_or_validates']=(page.evaluate('globalThis.__bresR360Attack') is None and 'NON VALIDÉE' in att2['decision'])
            brand.fill('');ref.fill('TE8D');ref.fill('TE8I');page.locator('#clearManualBtn').click();page.wait_for_timeout(850)
            clear=snapshot('rapid_edit_then_clear_and_wait')
            checks['rapid_edit_clear_blocks_stale_autovalidation']=('TE8D' not in clear['status'] and 'TE8I' not in clear['status'] and
                    'en attente' in clear['decision'] and clear['reference']=='' and clear['brand']=='')
            checks['all_automated_requests_network_denied']=('undefined'==page.evaluate('typeof globalThis.Tesseract') and
                    any('tesseract' in u.lower() for u in failed_requests))
            checks['no_page_error_no_dialog']=not errors and not dialogs
            checks['remains_V2_28_TEST_R156']=page.title()=='BRES Clés V2.28 TEST R156'
            ctx.close()
        finally:browser.close()
    out={'schema':'bres-r360-stale-feedback-regression-v1','milestone':'R360','parent':'R359',
         'test_scope':'manual status refresh on V2.28 TEST pilot in offline Chromium',
         'source_sha256':{'index.html':hashlib.sha256(src).hexdigest(),'v228-catalogue.js':hashlib.sha256(pilot).hexdigest()},
         'checks':checks,'trace':trace,'page_errors':errors,'dialogs':dialogs,
         'samsung_real_tested':False,'ocr_offline_certified':False,'catalogue_v3_integrated':False,'ok':all(checks.values())}
    (R/'R360_STALE_FEEDBACK_REGRESSION.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (R/'R360_STALE_FEEDBACK_REGRESSION.txt').write_text(
        f"R360: {sum(checks.values())}/{len(checks)} tests {'PASS' if out['ok'] else 'FAIL'}\n"
        'Ancienne correspondance verte supprimée immédiatement lors de toute modification référence/marque.\n'
        'Le moteur R156, les règles OCR R305 et le catalogue pilote restent distincts et inchangés.\n',encoding='utf-8')
    print(json.dumps({'ok':out['ok'],'checks':len(checks),'js_errors':len(errors)},ensure_ascii=False))
    return 0 if out['ok'] else 1
if __name__=='__main__':raise SystemExit(run())