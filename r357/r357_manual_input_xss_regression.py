#!/usr/bin/env python3
"""R357: security regression for untrusted manual reference and maker display.

Cold/network-blocked Chromium; negative test for DOM HTML injection and data integrity.
Does not validate Android, camera, real OCR, or geometry.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent


def main():
    checks={}; detail={}; errors=[]; denied=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('BRES_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        try:
            ctx=browser.new_context(service_workers='block')
            ctx.route('**/*',lambda r:r.abort('blockedbyclient'))
            page=ctx.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('requestfailed',lambda r:denied.append(r.url))
            page.set_content((ROOT/'index.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
            page.add_script_tag(content=(ROOT/'v228-catalogue.js').read_text(encoding='utf-8'))
            page.wait_for_timeout(180)
            def query(ref,brand):
                page.locator('#manualRef').fill(ref)
                page.locator('#manualBrand').fill(brand)
                page.locator('#manualRefBtn').click()
                page.wait_for_timeout(50)
                return page.locator('#manualRefStatus').inner_text(),page.locator('#finalDecision').inner_text()
            # The source contains a string that only executes if placed in innerHTML unsafely.
            payload='<img src=x onerror="window.__bresR357Probe=1">'
            page.evaluate('window.__bresR357Probe=0')
            status,final=query(payload,'')
            checks['unknown_ref_HTML_payload_shown_as_plain_text']=(payload in status and 'RÉFÉRENCE NON VALIDÉE' in final)
            checks['unknown_ref_inert_no_unsafe_dom']=(page.evaluate('window.__bresR357Probe')==0
                                                     and page.locator('#manualRefStatus img').count()==0)
            page.evaluate('window.__bresR357Probe=0')
            status,final=query('REF_INCONNUE_999',payload)
            checks['unknown_maker_HTML_payload_shown_as_plain_text']=(payload in status and 'RÉFÉRENCE NON VALIDÉE' in final)
            checks['unknown_maker_inert_no_unsafe_dom']=(page.evaluate('window.__bresR357Probe')==0
                                                       and page.locator('#manualRefStatus img').count()==0)
            page.evaluate('window.__bresR357Probe=0')
            status,final=query('TE8D',payload)
            checks['valid_ref_with_untrusted_maker_stays_inert']=(page.evaluate('window.__bresR357Probe')==0
                and page.locator('#manualRefStatus img').count()==0 and payload in status
                and 'RÉFÉRENCE TROUVÉE' in final and 'VALIDÉ' not in final)
            status,final=query('te8d','TESA & « atelier »')
            checks['canonical_casefold_still_found']=('Correspondance catalogue' in status and 'TE8D' in status)
            checks['ampersand_and_quotes_displayed_literally']=('TESA & « atelier »' in status)
            status,final=query('TE8I','TESA')
            checks['other_known_ref_still_found_unvalidated']=('Correspondance catalogue' in status and 'TE8I' in status
                 and 'RÉFÉRENCE TROUVÉE' in final and 'VALIDÉ' not in final)
            status,final=query('VI2','')
            checks['outside_pilot_reference_not_falsely_accepted']=('non trouvée dans la base catalogue pilote' in status
                                                                  and 'RÉFÉRENCE NON VALIDÉE' in final)
            checks['no_page_exceptions']=not errors
            checks['tesseract_cdn_blocked']=(any('tesseract' in x for x in denied)
                                             and page.evaluate('typeof window.Tesseract')=='undefined')
            detail['raw_text_sample']=status[:200]
            detail['externals_blocked']=denied
            detail['exception_messages']=errors
            detail['environment']='Linux Chromium, no network, no real OCR/camera/Samsung'
            ctx.close()
        finally:browser.close()
    result={'schema':'bres-r357-manual-input-inert-dom-v1','milestone':'R357','checks':checks,
            'checks_pass':sum(checks.values()),'checks_total':len(checks),'ok':all(checks.values()),
            'evidence':detail,'OCR_offline_certified':False,'Samsung_validated':False,
            'code_sha256':hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()}
    (ROOT/'R357_MANUAL_INPUT_SECURITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'R357_MANUAL_INPUT_SECURITY.txt').write_text(
        'BRES Clés R357 : '+str(sum(checks.values()))+'/'+str(len(checks))+' contrôles '+('PASS' if result['ok'] else 'FAIL')+'\n'+
        '\n'.join(('PASS' if good else 'FAIL')+' '+k for k,good in checks.items())+
        '\nPas de certification Samsung ni OCR hors ligne.\n',encoding='utf-8')
    print(json.dumps({'ok':result['ok'],'pass':result['checks_pass'],'total':result['checks_total']}))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())