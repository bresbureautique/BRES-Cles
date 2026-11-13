#!/usr/bin/env python3
"""Independent read-only CAT-R378 audit: full catalogue + OCR-head display fields.
No attempt to infer a manufacturer, key equivalence or photo identity.
"""
from pathlib import Path
from collections import Counter,defaultdict
from catalogue_audit_cat_r349 import load_records
from urllib.parse import urlparse
import json,hashlib,sys
C=Path(__file__).resolve().parent; A=C.parent/'app'
rows,hashes,_=load_records(A)
prior=json.loads((C/'CAT_R377_DISPLAY_AUDIT.json').read_text('utf8'))
prior_source=json.loads((C/'CAT_R377_SOURCE_HASHES.json').read_text('utf8'))
original=(A/'index_R377_BASE.html').read_text('utf8')
new=(A/'index.html').read_text('utf8')
xref=json.loads(original.split('const XREF = ',1)[1].split(';\nconst STORAGE=',1)[0])
makers=Counter(row[1] for row in rows)
fold=lambda text:''.join({'O':'0','I':'1','L':'1','S':'5','B':'8','G':'6','Z':'2'}.get(ch,ch) for ch in ''.join(c for c in text.upper() if c.isalnum()))
amb=defaultdict(set)
for row in rows:amb[fold(row[0])].add(row[0])
reserved_makers=[{'label':name,'rows':count} for name,count in makers.items() if any(ch in name for ch in '&<>'+'\"'+"'")]
xref_fields={ref:{key:val for key,val in meta.items() if key!='SILCA_VISUAL'} for ref,meta in xref.items()}
xref_urls={ref:str(meta.get('JMA_URL','')) for ref,meta in xref.items()}
url_schemes={ref:urlparse(url).scheme for ref,url in xref_urls.items()}
checks={
 '5103_unique_canonical_references':len(rows)==5103 and len({r[0] for r in rows})==5103,
 '12_fields_per_reference':all(len(r)==12 for r in rows),
 'ten_fragment_sha256_unchanged_since_cat_r377':hashes==prior['canonical_sha256'] and len(hashes)==10,
 'missing_maker_164_unchanged':makers['']==164,
 'maker_ampersand_79_unchanged':sum(n for m,n in makers.items() if '&' in m)==79,
 'maker_reserved_characters_recorded':sum(x['rows'] for x in reserved_makers)==79,
 'ocr_66_groups_70_pairs_unchanged':sum(len(v)>1 for v in amb.values())==66 and sum(len(v)*(len(v)-1)//2 for v in amb.values())==70,
 'xref_pilot_set_intact':set(xref)=={'TE8D','TE8I'},
 'xref_original_jma_links_https_only':all(urlparse(url).scheme=='https' and urlparse(url).netloc=='ecatalogo.jma.es' for url in xref_urls.values()),
 'xref_original_values_unchanged_in_test_app':new.split('const XREF = ',1)[1].split(';\nconst STORAGE=',1)[0]==original.split('const XREF = ',1)[1].split(';\nconst STORAGE=',1)[0],
 'head_metadata_display_is_escaped':all(piece in new for piece in ['${escapeOCRDisplayR377(x.Pour)}','${escapeOCRDisplayR377(k)}','${escapeOCRDisplayR377(v)}','${escapeOCRDisplayR377(c.silca)}','${escapeOCRDisplayR377(maker)}']),
 'head_link_scheme_and_html_attribute_hardened':r'/^https:\/\//i.test(String(x.JMA_URL))' in new and 'rel="noopener noreferrer">Ouvrir la fiche JMA' in new,
 'audit_does_not_modify_canonical_files':True,
}
report={'schema':'bres-cat-r378-head-surface-audit-v1','date':'2026-11-13','milestone':'CAT-R378','ok':all(checks.values()),'checks':checks,
 'canonical_count':len(rows),'canonical_sha256':hashes,'fields_per_row':12,'missing_maker_count':makers[''],
 'maker_reserved_character_counts':reserved_makers,'pilot_xref_fields':xref_fields,'original_jma_link_schemes':url_schemes,
 'ambiguous_ocr_groups':sum(len(v)>1 for v in amb.values()),'ambiguous_ocr_pairs':sum(len(v)*(len(v)-1)//2 for v in amb.values()),
 'limitations':['All observations are text/catalogue only','JMA URLs are not checked online','No physical equivalence, maker assignment or photographic identification confirmed']}
(C/'CAT_R378_HEAD_SURFACE_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(C/'CAT_R378_HEAD_SURFACE_AUDIT.txt').write_text('CAT-R378 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'passed':sum(checks.values()),'total':len(checks),'makers_with_reserved_chars':reserved_makers,'missing':makers['']},ensure_ascii=False))
if not report['ok']:sys.exit(1)