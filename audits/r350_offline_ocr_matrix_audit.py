#!/usr/bin/env python3
"""R350: cold-offline OCR prerequisites, diagnostically assessed; no runtime edits.

This is an *evidence* audit, not a network connectivity test. A script cached
by a browser must never be mistaken for an installable offline bundle.
"""
from __future__ import annotations
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROTECTED = {
    'index.html': '7695301023e526d4cdc92e05fcf7f62df1e56bef1ebc639766e91788849bbeba',
    'r331-device-benchmark.js': 'a1cfdd1f427175bcf0601a9b9df6b808b578199b03c7bfafac2ca7ac710849e8',
    'device_benchmark_r336.html': '3cda55a92c58a6fa0ec7050f7359e4b7dac5d5f1dd88c67d4dbba6f60c355da2',
    'v228-catalogue.js': '433c98851e99bfa116776e13eac95164b4c9c68d7e487763b31548194235fcd1',
}
ASSET_BASENAMES = {
    'tesseract.min.js', 'tesseract.js', 'worker.min.js',
    'tesseract-core.wasm', 'tesseract-core-simd.wasm', 'tesseract-core-lstm.wasm',
    'eng.traineddata', 'eng.traineddata.gz', 'eng.traineddata.zip',
}

class HTMLResources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resource_links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'script' and attrs.get('src'):
            self.resource_links.append({'tag': 'script', 'uri': attrs['src']})
        if tag.lower() == 'link' and attrs.get('href'):
            self.resource_links.append({'tag': 'link', 'uri': attrs['href']})

def classify_uri(uri):
    p = urlparse(uri)
    if uri.startswith('//') or p.scheme in {'http','https'}:
        return 'network'
    if p.scheme in {'data', 'blob'}:
        return 'embedded'
    if p.scheme or uri.startswith('\\'):
        return 'special'
    return 'relative'

def html_resources(content):
    reader = HTMLResources()
    reader.feed(content)
    return [dict(x, location=classify_uri(x['uri'])) for x in reader.resource_links]

def compute():
    index = (ROOT/'index.html').read_text(encoding='utf-8')
    bench = (ROOT/'device_benchmark_r336.html').read_text(encoding='utf-8')
    html_res = html_resources(index)
    bench_res = html_resources(bench)
    hashes = {k: hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in PROTECTED}
    relevant_local = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
                            if p.is_file() and p.name.lower() in ASSET_BASENAMES)
    remote_ocr = [x['uri'] for x in html_res if x['location']=='network' and 'tesseract' in x['uri'].lower()]
    worker_no_paths = bool(re.search(r'Tesseract\.createWorker\(\s*[\'"]eng[\'"]\s*,\s*1\s*,\s*\{\s*logger\s*:', index))
    explicit_local_config = any(re.search(r'\b'+p+r'\s*:', index) for p in ['workerPath','corePath','langPath'])
    # A Tesseract CDNs script tag can load while OCR still needs network for workers,
    # WebAssembly, and traineddata. Don't assume these artifacts exist because JS does.
    prerequisites = [
        {'name':'application_html','state':'PRESENT_LOCAL','proof':'index.html'},
        {'name':'catalogue_runtime_js','state':'PRESENT_LOCAL','proof':'v228-catalogue.js'},
        {'name':'tesseract_browser_script','state':'NETWORK_ONLY','proof':remote_ocr},
        {'name':'tesseract_worker_js','state':'NOT_BUNDLED','proof':relevant_local},
        {'name':'tesseract_wasm_core','state':'NOT_BUNDLED','proof':relevant_local},
        {'name':'english_language_data','state':'NOT_BUNDLED','proof':relevant_local},
        {'name':'samsung_physical_benchmark','state':'PENDING','proof':'BRES_Cles_R336_Samsung_Benchmark_Result.json not supplied'},
    ]
    fixtures = {
        'https_remote': classify_uri('https://example.invalid/tesseract.min.js') == 'network',
        'protocol_relative_remote': classify_uri('//example.invalid/tesseract.min.js') == 'network',
        'relative_vendor_is_local_class': classify_uri('./vendor/tesseract.min.js') == 'relative',
        'data_url_not_network': classify_uri('data:text/javascript;base64,AAAA') == 'embedded',
        'link_tag_included': len(html_resources('<link rel="stylesheet" href="https://x.invalid/a.css">'))==1,
        'inline_src_ignored': not html_resources('<script>fetch("https://x.invalid")</script>'),
    }
    checks = {
        'protected_hashes_bit_exact': hashes==PROTECTED,
        'R349_parent_valid': json.loads((ROOT/'R349_VERIFICATION.json').read_text())['ok'] is True,
        'R349_observation_agrees': json.loads((ROOT/'R349_OFFLINE_READINESS.json').read_text())['html_dependencies']['remote_scripts']==remote_ocr,
        'tesseract_script_network_only': len(remote_ocr)==1,
        'no_local_ocr_assets': relevant_local==[],
        'worker_eng_without_offline_paths': worker_no_paths and not explicit_local_config,
        'benchmark_no_external_HTML_resources': all(x['location']!='network' for x in bench_res),
        'relative_catalogue_script_exists': any(x['uri'].split('?')[0]=='v228-catalogue.js' and x['location']=='relative' for x in html_res),
        'fixtures_all_pass': all(fixtures.values()),
        'not_presented_as_offline_ready': all(p['state']!='VERIFIED_OFFLINE' for p in prerequisites),
    }
    data = {
      'schema':'bres-r350-ocr-cold-offline-prerequisite-audit-v1', 'milestone':'R350','parent':'R349',
      'status':'NOT_READY_FOR_COLD_OFFLINE_OCR','scope':'diagnostic static audit only',
      'html_resources':html_res,'benchmark_html_resources':bench_res,
      'external_tesseract_js':remote_ocr,
      'Tesseract_createWorker_eng_without_explicit_local_paths':worker_no_paths and not explicit_local_config,
      'local_ocr_assets':relevant_local,'prerequisites':prerequisites,'protected_sha256':hashes,
      'what_a_future_offline_release_must_prove':[
        'Exact local JS worker, WASM core and eng.traineddata bundled with hashes and explicit paths.',
        'Fresh installation on an uncached Samsung (flight mode) loads OCR without any network requests.',
        'Both recto and verso OCR plus manual override still work; compare to fixed non-regression fixtures.',
        'Running R336 benchmark alone does not prove OCR works offline.',
      ],
      'limitations':['Static HTML audit cannot prove all dynamic network accesses.',
                     'Tesseract package may request extra worker/language assets on first OCR.',
                     'A cached CDN response is not evidence of reproducible cold offline readiness.',
                     'No physical Android/Samsung benchmark result received.'],
      'fixtures': fixtures,'checks':checks,'errors':[k for k,v in checks.items() if not v],
      'runtime_changed':False,'ocr_threshold_changed':False,'new_rule_activated':False,
      'physical_samsung':'PENDING','ok':all(checks.values())}
    (ROOT/'R350_OFFLINE_OCR_MATRIX.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ROOT/'R350_OFFLINE_OCR_MATRIX.txt').write_text(
      'BRES Clés R350 — audit statique des prérequis OCR hors connexion\n'
      +('PASS\n' if data['ok'] else 'FAIL\n')
      +'Application et catalogue JS présents localement ; Tesseract.js distant et moteur/langue non empaquetés.\n'
      +'Le mode OCR hors ligne à froid n’est donc pas validé. Aucune activation ni retouche du moteur.\n'
      +'Le benchmark R336 physique sur Samsung reste en attente.\n',encoding='utf-8')
    print(json.dumps({'ok':data['ok'],'checks':len(checks),'fixture_tests':len(fixtures),'status':data['status']}))
    return data

if __name__=='__main__':
    raise SystemExit(0 if compute()['ok'] else 1)