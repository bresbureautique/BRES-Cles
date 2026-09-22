from __future__ import annotations
from typing import Any, Dict, List

def _nonnull(x):
    return x is not None and x != ''

def validate_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    policy=packet.get('policy',{})
    if packet.get('schema')!='bres-live-discriminant-collection-packet-r125-v1': errors.append('schema')
    if packet.get('active_test_runtime')!='V2.28 TEST R116': errors.append('runtime')
    if policy.get('decision_authority')!='NONE': errors.append('decision_authority')
    if policy.get('policy_status')!='A_CONFIRMER': errors.append('policy_status')
    if policy.get('no_automatic_validation') is not True: errors.append('automatic_validation_policy')
    if policy.get('no_acceptance_threshold_authorized') is not True: errors.append('threshold_policy')
    if not _nonnull(packet.get('physical_key_id')): errors.append('physical_key_id_missing')
    pair=packet.get('candidate_pair',{})
    if not _nonnull(pair.get('a')) or not _nonnull(pair.get('b')): warnings.append('candidate_pair_incomplete')
    gab=packet.get('gabarit',{})
    for k in ('id','version','calibration_source'):
        if not _nonnull(gab.get(k)): errors.append(f'gabarit_{k}_missing')
    if gab.get('calibration_documented') is not True: errors.append('calibration_not_documented')
    checks=gab.get('scale_checks',[])
    if [x.get('target_mm') for x in checks] != [50,100]: errors.append('scale_check_targets')
    if any(not _nonnull(x.get('measured_mm')) for x in checks): errors.append('scale_check_measurements_missing')
    sessions=packet.get('collection_sessions',[])
    if len(sessions)!=3: errors.append('requires_exactly_three_collection_sessions')
    session_ids=[]; capture_ids=[]; capture_hashes=[]
    for i,s in enumerate(sessions,1):
        prefix=f'session_{i}'
        sid=s.get('capture_session_id')
        if not _nonnull(sid): errors.append(prefix+'_id_missing')
        else: session_ids.append(sid)
        for field in ('captured_at','device_model'):
            if not _nonnull(s.get(field)): errors.append(prefix+'_'+field+'_missing')
        caps=s.get('captures',{})
        local_ids=[]
        for face,expected in (('recto','RECTO'),('verso','VERSO')):
            c=caps.get(face,{})
            if c.get('side')!=expected: errors.append(prefix+'_'+face+'_side')
            cid=c.get('capture_id'); sha=c.get('source_file_sha256')
            if not _nonnull(cid): errors.append(prefix+'_'+face+'_capture_id_missing')
            else: capture_ids.append(cid); local_ids.append(cid)
            if not isinstance(sha,str) or len(sha)!=64 or any(ch not in '0123456789abcdefABCDEF' for ch in sha):
                errors.append(prefix+'_'+face+'_sha256_invalid')
            else: capture_hashes.append(sha.lower())
        if len(local_ids)==2 and local_ids[0]==local_ids[1]: errors.append(prefix+'_face_capture_id_reused')
        stop=s.get('stop_or_shoulder',{})
        if stop.get('status')!='MEASURED_UNVALIDATED': errors.append(prefix+'_stop_status')
        if stop.get('position_mm') is not None and stop.get('uncertainty_mm') is None: errors.append(prefix+'_stop_uncertainty_missing')
        if stop.get('position_mm') is not None and not _nonnull(stop.get('measurement_method')): errors.append(prefix+'_stop_method_missing')
        dual=s.get('dual_face',{})
        if dual.get('status')!='MEASURED_UNVALIDATED': errors.append(prefix+'_dual_status')
        if dual.get('independent_capture_ids') is not True: errors.append(prefix+'_dual_independence_flag')
        if s.get('decision_authority')!='NONE': errors.append(prefix+'_decision_authority')
        if s.get('policy_status')!='A_CONFIRMER': errors.append(prefix+'_policy_status')
    if len(session_ids)!=len(set(session_ids)): errors.append('session_id_reused')
    if len(capture_ids)!=len(set(capture_ids)): errors.append('capture_id_reused_across_packet')
    if len(capture_hashes)!=len(set(capture_hashes)): errors.append('photo_file_reused_across_packet')
    return {
        'schema':'bres-live-discriminant-collection-packet-validation-r125-v1',
        'ok':not errors,
        'errors':errors,
        'warnings':warnings,
        'decision_authority':'NONE',
        'policy_status':'A_CONFIRMER',
        'complete_sessions':len(sessions) if len(sessions)==3 else 0
    }
