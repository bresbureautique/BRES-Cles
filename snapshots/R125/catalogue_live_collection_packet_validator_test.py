from pathlib import Path
import json, copy, sys, importlib.util
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('validator',ROOT/'collection_packet_validator_r125.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base=json.loads((ROOT/'catalogue/evidence/live_discriminant_collection_packet_r125.json').read_text(encoding='utf-8'))

def valid_fixture():
    p=copy.deepcopy(base)
    p['physical_key_id']='KEY-001'; p['candidate_pair']={'a':'REF-A','b':'REF-B'}
    p['gabarit'].update({'id':'BRES-A4','version':'R124','calibration_source':'manual-scale-check','calibration_documented':True})
    p['gabarit']['scale_checks'][0]['measured_mm']=50.0; p['gabarit']['scale_checks'][1]['measured_mm']=100.0
    p['collection_sessions']=[]
    for i,slot in enumerate(p['session_slots'],1):
        s=copy.deepcopy(slot); s['slot_status']='FILLED'; s['captured_at']=f'2026-09-22T1{i}:00:00+02:00'; s['device_model']='SAMSUNG-TEST'
        s['captures']['recto']['capture_id']=f'S{i}-R'; s['captures']['verso']['capture_id']=f'S{i}-V'
        s['captures']['recto']['source_file_sha256']=(f'{i:02x}'*32)[:64]
        s['captures']['verso']['source_file_sha256']=(f'{i+10:02x}'*32)[:64]
        s['stop_or_shoulder']['position_mm']=12.0+i/10; s['stop_or_shoulder']['uncertainty_mm']=0.2; s['stop_or_shoulder']['measurement_method']='manual-gabarit'
        p['collection_sessions'].append(s)
    return p
checks={}
v=valid_fixture(); checks['valid_complete_fixture_passes']=mod.validate_packet(v)['ok'] is True
p=valid_fixture(); p['collection_sessions']=p['collection_sessions'][:2]; r=mod.validate_packet(p); checks['incomplete_packet_rejected']=not r['ok'] and 'requires_exactly_three_collection_sessions' in r['errors']
p=valid_fixture(); p['collection_sessions'][1]['captures']['verso']['capture_id']=p['collection_sessions'][0]['captures']['recto']['capture_id']; r=mod.validate_packet(p); checks['reused_capture_id_rejected']=not r['ok'] and 'capture_id_reused_across_packet' in r['errors']
p=valid_fixture(); p['collection_sessions'][2]['captures']['recto']['source_file_sha256']=p['collection_sessions'][0]['captures']['verso']['source_file_sha256']; r=mod.validate_packet(p); checks['reused_photo_hash_rejected']=not r['ok'] and 'photo_file_reused_across_packet' in r['errors']
p=valid_fixture(); p['gabarit']['calibration_documented']=False; r=mod.validate_packet(p); checks['undocumented_calibration_rejected']=not r['ok'] and 'calibration_not_documented' in r['errors']
p=valid_fixture(); p['collection_sessions'][0]['stop_or_shoulder']['uncertainty_mm']=None; r=mod.validate_packet(p); checks['measured_stop_without_uncertainty_rejected']=not r['ok'] and 'session_1_stop_uncertainty_missing' in r['errors']
p=valid_fixture(); p['collection_sessions'][0]['decision_authority']='FINAL'; r=mod.validate_packet(p); checks['session_decision_authority_escalation_rejected']=not r['ok'] and 'session_1_decision_authority' in r['errors']
p=valid_fixture(); p['policy']['decision_authority']='FINAL'; r=mod.validate_packet(p); checks['packet_decision_authority_escalation_rejected']=not r['ok'] and 'decision_authority' in r['errors']
errors=[k for k,v in checks.items() if not v]
report={'schema':'bres-live-collection-packet-validator-test-r125-v1','milestone':'BRES Cles catalogue audit R125','checks':checks,'errors':errors,'ok':not errors}
(ROOT/'CATALOGUE_LIVE_COLLECTION_PACKET_VALIDATOR_R125.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'CATALOGUE_LIVE_COLLECTION_PACKET_VALIDATOR_R125.txt').write_text('\n'.join(['BRES CLES — TEST VALIDATEUR PAQUET R125','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['','SELFTEST OK' if not errors else 'SELFTEST ECHEC'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
