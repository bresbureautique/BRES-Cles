from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parent
P=ROOT/'catalogue/evidence/live_discriminant_collection_packet_r125.json'
packet=json.loads(P.read_text(encoding='utf-8'))
errors=[]
pol=packet.get('policy',{}); slots=packet.get('session_slots',[]); gab=packet.get('gabarit',{})
checks={
 'schema_exact':packet.get('schema')=='bres-live-discriminant-collection-packet-r125-v1',
 'links_r124_protocol':packet.get('protocol')=='bres-live-discriminant-collection-protocol-r124-v1',
 'links_r124_template':packet.get('source_template')=='bres-live-discriminant-collection-template-r124-v1',
 'runtime_r116_declared':packet.get('active_test_runtime')=='V2.28 TEST R116',
 'non_authoritative':pol.get('decision_authority')=='NONE' and pol.get('policy_status')=='A_CONFIRMER',
 'no_auto_validation':pol.get('no_automatic_validation') is True,
 'no_threshold_authorized':pol.get('no_acceptance_threshold_authorized') is True,
 'three_preallocated_slots':[x.get('capture_session_id') for x in slots]==['S1','S2','S3'],
 'all_slots_empty':all(x.get('slot_status')=='EMPTY' for x in slots),
 'recto_verso_separate':all(x.get('captures',{}).get('recto',{}).get('side')=='RECTO' and x.get('captures',{}).get('verso',{}).get('side')=='VERSO' for x in slots),
 'capture_ids_not_prefilled':all(x.get('captures',{}).get('recto',{}).get('capture_id') is None and x.get('captures',{}).get('verso',{}).get('capture_id') is None for x in slots),
 'photo_hashes_not_prefilled':all(x.get('captures',{}).get('recto',{}).get('source_file_sha256') is None and x.get('captures',{}).get('verso',{}).get('source_file_sha256') is None for x in slots),
 'calibration_not_preapproved':gab.get('calibration_documented') is False and gab.get('calibration_ok') is None,
 'scale_slots_50_100':[x.get('target_mm') for x in gab.get('scale_checks',[])]==[50,100],
 'collection_starts_empty':packet.get('collection_sessions')==[],
 'summary_not_ready':packet.get('collection_summary',{}).get('packet_ready_for_review') is False,
}
for k,v in checks.items():
    if not v: errors.append(k)
report={'schema':'bres-live-collection-packet-guard-r125-v1','milestone':'BRES Cles catalogue audit R125','checks':checks,'errors':errors,'ok':not errors}
(ROOT/'CATALOGUE_LIVE_COLLECTION_PACKET_GUARD_R125.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'CATALOGUE_LIVE_COLLECTION_PACKET_GUARD_R125.txt').write_text('\n'.join(['BRES CLES — GARDE PAQUET COLLECTE R125','']+[('OK  '+k if v else 'ECHEC  '+k) for k,v in checks.items()]+['','SELFTEST OK' if not errors else 'SELFTEST ECHEC'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(1 if errors else 0)
