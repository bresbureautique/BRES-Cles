#!/usr/bin/env python3
"""CAT-R382: independent, fail-closed re-verification of R381 OCR-pair evidence.
No canonical edits, no manufacturer inference, no physical equivalence claim.
"""
from pathlib import Path
from catalogue_audit_cat_r349 import load_records
import csv, hashlib, json, copy, math, sys
C=Path(__file__).resolve().parent;A=C.parent/'app'
rows, hashes, _=load_records(A)
original=list(csv.DictReader((C/'CAT_R381_OCR_PAIR_EVIDENCE.csv').open(encoding='utf-8-sig',newline='')))
prior=list(csv.DictReader((C/'CAT_R380_OCR_REVIEW_QUEUE.csv').open(encoding='utf-8-sig',newline='')))
report381=json.loads((C/'CAT_R381_OCR_PAIR_EVIDENCE_AUDIT.json').read_text('utf-8'))
byref={r[0]:r for r in rows}
expected={(r['reference_A'],r['reference_B']):r for r in prior}
DIMS=('length_delta_mm_REPORT_ONLY','width_delta_mm_REPORT_ONLY','mean_profile_delta_REPORT_ONLY')

def sha_row(r):return hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=False,separators=(',',':')).encode()).hexdigest()
def diff_num(a,b):
    try:
        a,b=float(a),float(b)
        return round(abs(a-b),4) if math.isfinite(a) and math.isfinite(b) else None
    except (ValueError,TypeError,OverflowError):return None

def expected_dims(a,b):
    prof=[]
    for i in (6,7,8):
        if isinstance(a[i],list) and isinstance(b[i],list) and len(a[i])==len(b[i]) and len(a[i])>0:
            prof.extend(abs(float(x)-float(y)) for x,y in zip(a[i],b[i]))
    return (diff_num(a[3],b[3]),diff_num(a[4],b[4]),round(sum(prof)/len(prof),6) if prof else None)
def numerically_equal(value, expected):
    if expected is None:return value in ('',None)
    try:
        n=float(value)
        return math.isfinite(n) and abs(n-expected)<=0.00000051
    except (TypeError,ValueError,OverflowError):return False

def validate(ledger):
    faults=[];seen=set()
    if len(ledger)!=70:faults.append('wrong_pair_count')
    for i,entry in enumerate(ledger):
        key=(entry.get('reference_A'),entry.get('reference_B'))
        if key in seen:faults.append('duplicate_pair')
        seen.add(key)
        p=expected.get(key)
        if p is None:
            faults.append('unknown_pair');continue
        a,b=byref.get(key[0]),byref.get(key[1])
        if a is None or b is None:faults.append('missing_canonical_row');continue
        fields={'priority':p['review_priority'],'OCR_fold':p['OCR_fold'],'maker_A':a[1], 'maker_B':b[1],
         'manufacturer_status':p['reason'],'catalogue_code_A':str(a[2]),'catalogue_code_B':str(b[2]),
         'full_row_SHA256_A':sha_row(a),'full_row_SHA256_B':sha_row(b),
         'requires_real_physical_check':'YES','requires_documented_reference':'YES','review_status':'PENDING','auto_equivalence':'NO'}
        for k,v in fields.items():
            if entry.get(k)!=str(v):faults.append('row_'+str(i)+'_'+k)
        for k,v in zip(DIMS,expected_dims(a,b)):
            if not numerically_equal(entry.get(k),v):faults.append('row_'+str(i)+'_'+k)
    if seen!=set(expected):faults.append('pair_set_mismatch')
    return sorted(set(faults))

baseline_faults=validate(original)
checks={
 'prior_R381_audit_success':report381['ok'] is True,
 'canonical_sha_identical_R381':hashes==report381['canonical_sha256'] and len(hashes)==10,
 'canonical_5103_12_fields':len(rows)==len(byref)==5103 and all(len(r)==12 for r in rows),
 '70_in_prior_queue':len(prior)==len(expected)==70,
 'unaltered_evidence_passes':not baseline_faults,
 'all_pairs_wait_for_physical_and_documented_reference':all(r['review_status']=='PENDING' and r['auto_equivalence']=='NO' and r['requires_real_physical_check']==r['requires_documented_reference']=='YES' for r in original),
 'one_missing_maker_case':sum(r['manufacturer_status']=='manufacturer_missing' for r in original)==1,
 'manufacturer_divergence_counts':sum(r['manufacturer_status']=='different_manufacturers' for r in original)==63 and sum(r['manufacturer_status']=='same_manufacturer' for r in original)==6,
 'all_row_hashes_64_hex':all(len(r['full_row_SHA256_A'])==len(r['full_row_SHA256_B'])==64 and all(c in '0123456789abcdef' for c in r['full_row_SHA256_A']+r['full_row_SHA256_B']) for r in original),
}
negative_cases={
 'changed_reference':(0,'reference_A','NOT-IN-CANON'),
 'changed_ocr_fold':(0,'OCR_fold','ERROR'),
 'changed_manufacturer':(0,'maker_B','INVENTED'),
 'changed_code':(0,'catalogue_code_A','0'),
 'changed_digest':(0,'full_row_SHA256_A','0'*64),
 'changed_length':(0,DIMS[0],'0.5'),
 'changed_width':(0,DIMS[1],'99.1'),
 'changed_profile':(0,DIMS[2],'0.0'),
 'false_automatic_equivalence':(0,'auto_equivalence','YES'),
 'false_review_approval':(0,'review_status','VERIFIED'),
 'remove_documentation_guard':(0,'requires_documented_reference','NO'),
 'alter_priority':(0,'priority','9'),
}
mutations={}
for name,(idx,key,value) in negative_cases.items():
 clone=copy.deepcopy(original);clone[idx][key]=value
 mutations[name]=validate(clone)
 checks['tamper_block_'+name]=len(mutations[name])>0
for name,mut in [('duplicated_pair',original+[copy.deepcopy(original[0])]),('removed_pair',original[:-1])]:
 mutations[name]=validate(mut);checks['tamper_block_'+name]=len(mutations[name])>0
report={'schema':'bres-cat-r382-pair-ledger-integrity-v1','date':'2026-11-17','milestone':'CAT-R382',
 'ok':all(checks.values()),'checks':checks,'baseline_errors':baseline_faults,'negative_mutation_detected':{k:len(v)>0 for k,v in mutations.items()},'negative_error_reasons':mutations,
 'reference_count':len(rows),'pair_count':len(original),'manufacturer_missing_count':164,
 'canonical_sha256':hashes,'evidence_source':'CAT_R381_OCR_PAIR_EVIDENCE.csv','autonomous_manufacturer_assignment':False,'physical_equivalence_verified':False,
 'limits':['Theoretical OCR-fold pairs: no physical-key verification','Reports and geometry do not establish key compatibility','Actual cold-offline OCR remains unverified']}
(C/'CAT_R382_PAIR_LEDGER_INTEGRITY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
(C/'CAT_R382_PAIR_LEDGER_INTEGRITY.txt').write_text('CAT-R382 '+('PASS' if report['ok'] else 'FAIL')+f' {sum(checks.values())}/{len(checks)} checks; 70 pair evidence rows; {len(mutations)} tamper tests\n'+'\n'.join(('PASS ' if v else 'FAIL ')+k for k,v in checks.items())+'\n','utf8')
print(json.dumps({'ok':report['ok'],'checks_passed':sum(checks.values()),'checks_total':len(checks),'mutations_detected':sum(bool(x) for x in mutations.values()),'canonical':len(rows),'pairs':len(original),'failures':[k for k,v in checks.items() if not v]},ensure_ascii=False))
if not report['ok']:sys.exit(1)
