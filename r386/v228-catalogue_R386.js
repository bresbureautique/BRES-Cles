/* BRES Clés V2.28 TEST R156 — preuves manuelles résiduelles séparées + garde-fous anti-validation */
(function(){
  const CHUNKS=Array.from({length:10},(_,i)=>`catalogue/v3/catalog-${String(i+1).padStart(2,'0')}.js?v=228r156`);
  const PROFILE_GUIDE={x:.18,y:.32,w:.64,h:.36};
  const PROFILE_THRESHOLDS={quality:60,score:.58,margin:.10,cross:.55};
  let loadingPromise=null, catalogueStats=null, lastCatalogueResults=null, lastCatalogueDb=null, capturedProfileBlob=null, profileStream=null, profileCameraEpoch=0, profileAnalysisEpoch=0;
  let previousProfileResult=null,lastProfileDiagnostic=null,profileCaptureMeta=null,profileSession=[],sessionKnownRef=null,lastManualAmbiguityEvidence=null,profileSessionMainEpoch=null,profileCaptureMainEpoch=null;
  function el2(id){return document.getElementById(id)}
  // R385 TEST: reject a catalogue script that never fires load/error, then let
  // R384 clear the partial inventory and retry. Removing the timed-out script
  // cancels its network fetch in supported browsers; late event callbacks are
  // ignored. The canonical catalogue and stable V2.27 are never modified.
  const CATALOGUE_CHUNK_TIMEOUT_R385_MS=4000;
  function loadScript(src){
    return new Promise((resolve,reject)=>{
      const s=document.createElement('script');
      let settled=false;
      const complete=(error)=>{
        if(settled)return;
        settled=true;
        clearTimeout(timer);
        s.onload=s.onerror=null;
        s.remove();
        if(error)reject(error);else resolve();
      };
      s.src=src;
      s.onload=()=>complete(null);
      s.onerror=()=>complete(new Error('Chargement impossible : '+src));
      const timer=setTimeout(()=>complete(new Error('Délai de chargement dépassé : '+src)),CATALOGUE_CHUNK_TIMEOUT_R385_MS);
      try{document.head.appendChild(s);}catch(e){complete(e);}
    });
  }
  function normText(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[^A-Z0-9]+/g,' ').trim();}
  function brandCompatible(rowBrand,wanted){
    const a=normText(rowBrand),b=normText(wanted); if(!a||!b)return false;
    return a===b || a.includes(b) || b.includes(a);
  }
  function silhouetteKey(r){return JSON.stringify(r.slice(3,9));}
  function unique(a){return [...new Set(a)];}
  function catalogueStatsFor(db){
    if(catalogueStats)return catalogueStats;
    const groups=new Map();
    for(const r of db){const k=silhouetteKey(r);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}
    let collisionGroups=0,refsInCollision=0,fullyProfileResolved=0,partialProfileResolved=0,notProfileResolved=0,residualProfileClusters=0,residualProfileRefs=0;
    for(const g of groups.values()){
      if(g.length<2)continue; collisionGroups++;refsInCollision+=g.length;
      const good=g.filter(r=>Number(r[10]||0)>=.8 && r[9]),p=unique(good.map(r=>r[9]));
      if(p.length===g.length)fullyProfileResolved++;
      else if(p.length>1)partialProfileResolved++;
      else notProfileResolved++;
      const byProfile=new Map();for(const r of good){if(!byProfile.has(r[9]))byProfile.set(r[9],[]);byProfile.get(r[9]).push(r);}
      for(const rr of byProfile.values())if(rr.length>1){residualProfileClusters++;residualProfileRefs+=rr.length;}
    }
    catalogueStats={groups:groups.size,collisionGroups,refsInCollision,fullyProfileResolved,partialProfileResolved,notProfileResolved,residualProfileClusters,residualProfileRefs};
    return catalogueStats;
  }

  function catalogueSigDistance(a,b){
    const x=(a&&a.sig)||a,y=(b&&b.sig)||b;if(!x||!y)return Infinity;
    const rr=(u,v)=>{u=u||[];v=v||[];const n=Math.min(u.length,v.length);if(!n)return 1;let z=0;for(let i=0;i<n;i++){const d=u[i]-v[i];z+=d*d}return Math.sqrt(z/n)};
    return Math.abs((x.width_mm||0)-(y.width_mm||0))/10+Math.abs((x.height_mm||0)-(y.height_mm||0))/10+Math.abs((x.area||0)-(y.area||0))+((rr(x.top,y.top)+rr(x.bot,y.bot))/2)+rr(x.colFill,y.colFill)+Math.abs((x.bladeFill||0)-(y.bladeFill||0))+Math.abs((x.headFill||0)-(y.headFill||0));
  }
  function ambiguousPilotPeers(canon){
    let base=null;try{base=catalogVisualEntry(canon)}catch(e){} if(!base)return [];
    const peers=[];for(const other of Object.keys(XREF||{})){if(other===canon)continue;let c=null;try{c=catalogVisualEntry(other)}catch(e){}if(c&&catalogueSigDistance(base,c)<.003)peers.push(other)}return peers;
  }
  // R233 : le wrapper catalogue installé après verifyManualReference() ne doit jamais
  // réintroduire un VALIDÉ / CONFLIT à partir d'une géométrie de secours. Il réutilise
  // la preuve publiée R227 et échoue fermé si cette preuve n'est pas disponible.
  function wrapperCalibrationGuardR233(){
    try{
      const fn=globalThis.currentAutoIdentificationCalibrationR227;
      const guard=(typeof fn==='function')?fn():null;
      return guard&&guard.ok===true?guard:{ok:false,reason:(guard&&guard.reason)||'strong-4/4-proof-unavailable',faces:(guard&&Array.isArray(guard.faces))?guard.faces:[]};
    }catch(e){return {ok:false,reason:'strong-4/4-proof-error',faces:[]};}
  }
  function localTemplateDecision(canon){
    let cand=[];try{cand=(currentSig&&typeof match==='function')?(match(currentSig)||[]):[]}catch(e){}
    if(!cand.length)return {state:'none'};const first=cand[0],second=cand[1]||null;
    if((first.score||0)<88)return {state:'weak',first,second};
    if(second&&((first.score||0)-(second.score||0))<8)return {state:'ambiguous',first,second};
    return {state:first.ref===canon?'same':'conflict',first,second};
  }
  function installSafetyWrappers(){
    if(typeof verifyManualReference!=='function'||typeof normalizeKnownRef!=='function')return;
    const previousVerify=verifyManualReference;
    verifyManualReference=function(auto=false){
      previousVerify(auto);
      try{
        const canon=normalizeKnownRef(el('manualRef').value.trim(),el('manualBrand').value.trim());if(!canon||!currentSig)return;
        const calibrationGuardR233=wrapperCalibrationGuardR233();
        // Le cœur R228 a déjà rendu les résultats faibles indicatifs. Ne jamais les
        // réécrire ici : seul strong-4/4 autorise ce wrapper à renforcer la décision.
        if(!calibrationGuardR233.ok)return;
        const local=localTemplateDecision(canon),fd=el('finalDecision'),cv=el('catalogVisual');
        if(local.state==='same'){
          fd.className='status ok';fd.innerHTML=`<b>VALIDÉ PAR ÉTALON LOCAL : ${canon}</b><br>Correspondance forte avec votre étalon enregistré (${local.first.score} %).`;
          if(cv)cv.innerHTML+=`<br><b>V2.28 — étalon local :</b> correspondance ${local.first.ref} ${local.first.score} %.`;return;
        }
        if(local.state==='conflict'){
          fd.className='status bad';fd.innerHTML=`<b>CONFLIT ÉTALON LOCAL</b><br>Référence saisie : <b>${canon}</b>.<br>La clé photographiée correspond fortement à l’étalon <b>${local.first.ref}</b> (${local.first.score} %). <b>${canon} n’est pas validée.</b>`;
          if(cv)cv.innerHTML+=`<br><b>V2.28 — conflit étalon :</b> préférence forte pour ${local.first.ref} (${local.first.score} %).`;return;
        }
        const peers=ambiguousPilotPeers(canon);
        let cat=null,check=null;try{cat=catalogVisualEntry(canon);check=cat?catalogVisualScore(currentSig,cat):null}catch(e){}
        if(peers.length&&check&&check.score>=68){
          fd.className='status warn';fd.innerHTML=`<b>À CONFIRMER : ${canon}</b><br>Silhouette cohérente (${check.score} %), mais le visuel pilote est également compatible avec ${peers.join(', ')}. Aucun faux VALIDÉ n’est autorisé sans critère discriminant.`;
          if(cv)cv.innerHTML+=`<br><b>V2.28 — contrôle anti-faux-positif :</b> visuel pilote non discriminant avec ${peers.join(', ')}.`;
        }
      }catch(e){console.warn('Sécurité V2.28',e)}
    };
  }
  // R384 TEST: a transient chunk failure must never poison the loader forever.
  // A retry starts from a fresh array (no duplicate partial rows), preserves
  // the single-flight promise, and accepts only the COMPLETE canonical inventory.
  // This guard does not infer compatibility, manufacturers or OCR identity.
  function catalogueIsCompleteR384(db){
    if(!Array.isArray(db)||db.length!==5103)return false;
    // When the app's all-field inventory verifier is present, use its fixed
    // expected hashes rather than trusting an arbitrary 5103-row array.
    const verify=globalThis.ocrCatalogueAllFieldsR371;
    if(typeof verify!=="function")return false;
    try{return verify().ok===true;}catch(_){return false;}
  }
  async function ensureCatalogue(status){
    // An in-flight loader takes precedence over a partially populated array.
    if(loadingPromise)return loadingPromise;
    if(catalogueIsCompleteR384(window.BRES_CATALOG_V3))return window.BRES_CATALOG_V3;
    // Do not reuse rows left by a failed attempt or a mutated complete array.
    window.BRES_CATALOG_V3=[];
    catalogueStats=null;lastCatalogueDb=null;
    let pending=null;
    pending=(async()=>{
      try{
        // R386 TEST: fail immediately if a script reports "load" without the
        // expected canonical fragment (empty, repeated, swapped, malformed or
        // a replacement array). This is a transport guard, NOT key recognition.
        // The R371 all-fields digest remains the final integrity authority.
        const fragmentShapeR386=[
          [511,'TRF1','ZOL1'],[511,'TRF2','ZO1'],[511,'TRF1R','MTK2P'],
          [510,'TRF3','CA12'],[510,'TRF3R','CA7'],[510,'TRF4','CA10'],
          [510,'TRF6R','CA11'],[510,'TRF5R','CA11R'],
          [510,'TRM1R','CA10R'],[510,'TRM2','ZH1R']
        ];
        for(let i=0;i<CHUNKS.length;i++){
          if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
          const before=window.BRES_CATALOG_V3, start=before.length;
          await loadScript(CHUNKS[i]);
          const db=window.BRES_CATALOG_V3;
          const [count,first,last]=fragmentShapeR386[i];
          if(db!==before || !Array.isArray(db) || db.length!==start+count ||
             db[start]?.[0]!==first || db[db.length-1]?.[0]!==last ||
             !db.slice(start).every(row=>Array.isArray(row)&&row.length===12))
            throw new Error(`Fragment catalogue non conforme : ${CHUNKS[i]}`);
        }
        if(!catalogueIsCompleteR384(window.BRES_CATALOG_V3))
          throw new Error("Catalogue incomplet ou altéré : inventaire R371 non conforme");
        catalogueStatsFor(window.BRES_CATALOG_V3);
        return window.BRES_CATALOG_V3;
      }catch(error){
        // A rejected script has completed; there is no outstanding chunk
        // belonging to this sequential loader. The next call may retry safely.
        if(loadingPromise===pending){
          window.BRES_CATALOG_V3=[];
          catalogueStats=null;lastCatalogueDb=null;
        }
        throw error;
      }finally{
        if(loadingPromise===pending)loadingPromise=null;
      }
    })();
    loadingPromise=pending;
    return pending;
  }
  window.ensureBresCatalogueR208=ensureCatalogue;
  function rms(a,b){const n=Math.min((a||[]).length,(b||[]).length);if(!n)return 1;let s=0;for(let i=0;i<n;i++){const d=a[i]-b[i];s+=d*d}return Math.sqrt(s/n)}
  function sample2(a){return (a||[]).filter((_,i)=>i%2===0)}
  function scoreOne(sig,r,variant='normal'){
    const st=sample2(sig.top), so=sample2(sig.bot), sc=sample2(sig.colFill);
    let rt=r[6],ro=r[7],rc=r[8];
    if(variant==='h'){rt=[...rt].reverse();ro=[...ro].reverse();rc=[...rc].reverse();}
    if(variant==='v'){const nt=ro.map(x=>1-x),no=rt.map(x=>1-x);rt=nt;ro=no;}
    if(variant==='hv'){rt=[...ro].reverse().map(x=>1-x);ro=[...r[6]].reverse().map(x=>1-x);rc=[...rc].reverse();}
    const dw=Math.abs((sig.width_mm||0)-r[3]), dh=Math.abs((sig.height_mm||0)-r[4]), da=Math.abs((sig.area||0)-r[5]);
    const contour=(rms(st,rt)+rms(so,ro))/2, col=rms(sc,rc);
    const d=.29*(dw/7.5)+.17*(dh/7.5)+.13*(da/.22)+.28*(contour/.20)+.13*(col/.22);
    return {score:Math.max(0,Math.min(99,Math.round(100*Math.exp(-1.45*d)))),dw,dh,contour,col,variant};
  }
  function bestScore(sig,r){let best=null;for(const v of ['normal','h','v','hv']){const x=scoreOne(sig,r,v);if(!best||x.score>best.score)best=x;}return best;}
  function catalogueAmbiguousGeometryDecisionR209(canonRefs,sig){
    const db=lastCatalogueDb||window.BRES_CATALOG_V3||[];
    const refs=unique((canonRefs||[]).map(strictRefKey).filter(Boolean));
    if(!sig)return {status:'no-geometry',ref:null,topScore:0,margin:0,candidates:[]};
    if(refs.length<2)return {status:'not-ambiguous',ref:null,topScore:0,margin:0,candidates:[]};
    const scored=[];
    for(const ref of refs){
      const rows=db.filter(r=>strictRefKey(r&&r[0])===ref);
      if(!rows.length)continue;
      let best=null,bestRow=null;
      for(const row of rows){const m=bestScore(sig,row);if(!best||m.score>best.score){best=m;bestRow=row;}}
      if(best&&bestRow)scored.push({ref:bestRow[0],maker:bestRow[1]||null,system:bestRow[2]||null,score:best.score,quality:Number(bestRow[11]||0),details:best});
    }
    scored.sort((a,b)=>b.score-a.score||a.ref.localeCompare(b.ref));
    const top=scored[0]||null,second=scored[1]||null,margin=top&&second?top.score-second.score:0;
    if(scored.length!==refs.length)return {status:'catalogue-incomplete',ref:null,topScore:top?.score||0,margin,candidates:scored};
    if(scored.some(x=>x.quality<.45))return {status:'catalogue-quality-insufficient',ref:null,topScore:top?.score||0,margin,candidates:scored};
    if(!top||top.score<78)return {status:'geometry-weak',ref:null,topScore:top?.score||0,margin,candidates:scored};
    if(!second||margin<10)return {status:'geometry-ambiguous',ref:null,topScore:top.score,margin,candidates:scored};
    return {status:'resolved',ref:top.ref,maker:top.maker,system:top.system,topScore:top.score,margin,candidates:scored};
  }
  window.bresCatalogueAmbiguityGeometryR209=catalogueAmbiguousGeometryDecisionR209;
  // R210 : une moyenne recto/verso ne suffit plus à résoudre une collision compacte.
  // Chaque face doit, séparément, atteindre les mêmes seuils forts que la moyenne et
  // désigner le même canon. Un désaccord ou une face faible conserve l'ambiguïté.
  function catalogueAmbiguousGeometryDecisionR210(canonRefs,sig,viewSigs){
    const average=catalogueAmbiguousGeometryDecisionR209(canonRefs,sig);
    const faces=(Array.isArray(viewSigs)?viewSigs:[]).filter(Boolean).slice(0,2).map((faceSig,index)=>{
      const d=catalogueAmbiguousGeometryDecisionR209(canonRefs,faceSig);
      return {index,status:d.status,ref:d.ref||null,topScore:d.topScore||0,margin:d.margin||0,candidates:d.candidates||[]};
    });
    if(average.status!=="resolved")return {...average,faceAgreement:false,faces};
    if(faces.length!==2)return {...average,status:"face-evidence-missing",ref:null,faceAgreement:false,faces};
    const decisive=faces.filter(x=>x.status==="resolved"&&x.ref).map(x=>String(x.ref));
    if(decisive.length!==2)return {...average,status:"face-geometry-weak",ref:null,faceAgreement:false,faces};
    if(decisive[0]!==decisive[1])return {...average,status:"face-disagreement",ref:null,faceAgreement:false,faces};
    if(decisive[0]!==String(average.ref))return {...average,status:"face-average-conflict",ref:null,faceAgreement:false,faces};
    return {...average,faceAgreement:true,faces};
  }
  window.bresCatalogueAmbiguityGeometryR210=catalogueAmbiguousGeometryDecisionR210;
  // R211 : une collision compacte ne peut être auto-résolue qu'avec deux faces
  // suffisamment bien calibrées. Le mode 3/4 (repère inféré), le mode de silhouette
  // tolérant, une qualité de repères trop faible ou un mode de détection différent
  // entre recto et verso conservent volontairement l'ambiguïté.
  const R211_MIN_MARKER_QUALITY=.18;
  function faceCalibrationEvidenceR211(faceSig,index){
    if(!faceSig)return {index,ok:false,reason:'face-missing',markerQuality:null,markerMode:null,missingMarker:null,detectionMode:null};
    const markerQuality=Number(faceSig.markerQuality),markerMode=String(faceSig.markerMode||''),missingMarker=faceSig.missingMarker||null,detectionMode=String(faceSig.detectionMode||'');
    if(!Number.isFinite(markerQuality)||markerQuality<R211_MIN_MARKER_QUALITY)return {index,ok:false,reason:'marker-quality-low',markerQuality:Number.isFinite(markerQuality)?markerQuality:null,markerMode,missingMarker,detectionMode};
    if(markerMode!=='4/4'||missingMarker)return {index,ok:false,reason:'marker-inferred',markerQuality,markerMode,missingMarker,detectionMode};
    if(!detectionMode||detectionMode==='tolérant')return {index,ok:false,reason:'detection-mode-weak',markerQuality,markerMode,missingMarker,detectionMode};
    return {index,ok:true,reason:'strong-calibration',markerQuality,markerMode,missingMarker:null,detectionMode};
  }
  function catalogueAmbiguousGeometryDecisionR211(canonRefs,sig,viewSigs){
    const base=catalogueAmbiguousGeometryDecisionR210(canonRefs,sig,viewSigs);
    const rawFaces=(Array.isArray(viewSigs)?viewSigs:[]).filter(Boolean).slice(0,2);
    const faceCalibrations=rawFaces.map((faceSig,index)=>faceCalibrationEvidenceR211(faceSig,index));
    if(base.status!=="resolved")return {...base,faceCalibrations,calibrationAgreement:false};
    if(faceCalibrations.length!==2||faceCalibrations.some(x=>!x.ok))return {...base,status:'face-calibration-insufficient',ref:null,faceCalibrations,calibrationAgreement:false};
    if(faceCalibrations[0].detectionMode!==faceCalibrations[1].detectionMode)return {...base,status:'face-detection-mode-disagreement',ref:null,faceCalibrations,calibrationAgreement:false};
    return {...base,faceCalibrations,calibrationAgreement:true};
  }
  window.bresCatalogueAmbiguityGeometryR211=catalogueAmbiguousGeometryDecisionR211;
  // R226 : séparer explicitement la calibration utile à la mesure de celle autorisée
  // à trancher automatiquement une ambiguïté catalogue. Le moteur d'analyse accepte
  // toujours 3/4 repères à partir du seuil de mesure (0,12), mais l'identification
  // automatique exige 4/4 repères, aucun coin inféré, qualité >= 0,18 et silhouette forte.
  const R226_MIN_MEASUREMENT_MARKER_QUALITY=.12;
  function faceCalibrationEvidenceR226(faceSig,index){
    if(!faceSig)return {index,ok:false,calibrationLevel:'insufficient',measurementUsable:false,autoIdentificationAllowed:false,reason:'face-missing',markerQuality:null,markerMode:null,missingMarker:null,detectionMode:null};
    const markerQuality=Number(faceSig.markerQuality),markerMode=String(faceSig.markerMode||''),missingMarker=faceSig.missingMarker||null,detectionMode=String(faceSig.detectionMode||'');
    if(!Number.isFinite(markerQuality)||markerQuality<R226_MIN_MEASUREMENT_MARKER_QUALITY)
      return {index,ok:false,calibrationLevel:'insufficient',measurementUsable:false,autoIdentificationAllowed:false,reason:'marker-quality-low',markerQuality:Number.isFinite(markerQuality)?markerQuality:null,markerMode,missingMarker,detectionMode};
    const measurementUsable=true;
    if(markerMode!=='4/4'||missingMarker)
      return {index,ok:false,calibrationLevel:'fallback-3/4',measurementUsable,autoIdentificationAllowed:false,reason:'marker-inferred',markerQuality,markerMode,missingMarker,detectionMode};
    if(markerQuality<R211_MIN_MARKER_QUALITY)
      return {index,ok:false,calibrationLevel:'measurement-only',measurementUsable,autoIdentificationAllowed:false,reason:'marker-quality-low',markerQuality,markerMode,missingMarker:null,detectionMode};
    if(!detectionMode||detectionMode==='tolérant')
      return {index,ok:false,calibrationLevel:'measurement-only',measurementUsable,autoIdentificationAllowed:false,reason:'detection-mode-weak',markerQuality,markerMode,missingMarker:null,detectionMode};
    return {index,ok:true,calibrationLevel:'strong-4/4',measurementUsable,autoIdentificationAllowed:true,reason:'strong-calibration',markerQuality,markerMode,missingMarker:null,detectionMode};
  }
  function catalogueAmbiguousGeometryDecisionR226(canonRefs,sig,viewSigs){
    const base=catalogueAmbiguousGeometryDecisionR210(canonRefs,sig,viewSigs);
    const rawFaces=(Array.isArray(viewSigs)?viewSigs:[]).filter(Boolean).slice(0,2);
    const faceCalibrations=rawFaces.map((faceSig,index)=>faceCalibrationEvidenceR226(faceSig,index));
    if(base.status!=="resolved")return {...base,faceCalibrations,calibrationAgreement:false,calibrationPolicy:'R226'};
    if(faceCalibrations.length!==2||faceCalibrations.some(x=>!x.autoIdentificationAllowed))
      return {...base,status:'face-calibration-insufficient',ref:null,faceCalibrations,calibrationAgreement:false,calibrationPolicy:'R226'};
    if(faceCalibrations[0].detectionMode!==faceCalibrations[1].detectionMode)
      return {...base,status:'face-detection-mode-disagreement',ref:null,faceCalibrations,calibrationAgreement:false,calibrationPolicy:'R226'};
    return {...base,faceCalibrations,calibrationAgreement:true,calibrationPolicy:'R226'};
  }
  window.bresCatalogueFaceCalibrationEvidenceR226=faceCalibrationEvidenceR226;
  window.bresCatalogueAmbiguityGeometryR226=catalogueAmbiguousGeometryDecisionR226;
  // R227 : le niveau de calibration est désormais publié et scellé avec chaque face.
  // Le départage automatique exige cette preuve publiée ET sa concordance avec la
  // signature de face courante ; recalculer seulement depuis la signature ne suffit plus.
  function sameFaceCalibrationEvidenceR227(published,recomputed){
    if(!published||!recomputed)return false;
    const keys=['index','calibrationLevel','measurementUsable','autoIdentificationAllowed','reason','markerQuality','markerMode','missingMarker','detectionMode'];
    return keys.every(k=>{
      const a=published[k],b=recomputed[k];
      if(k==='markerQuality')return (a===null&&b===null)||(Number.isFinite(Number(a))&&Number.isFinite(Number(b))&&Math.abs(Number(a)-Number(b))<1e-9);
      return a===b;
    });
  }
  function catalogueAmbiguousGeometryDecisionR227(canonRefs,sig,viewSigs,publishedFaceCalibrations){
    const base=catalogueAmbiguousGeometryDecisionR210(canonRefs,sig,viewSigs);
    const rawFaces=(Array.isArray(viewSigs)?viewSigs:[]).filter(Boolean).slice(0,2);
    const recomputed=rawFaces.map((faceSig,index)=>faceCalibrationEvidenceR226(faceSig,index));
    const published=(Array.isArray(publishedFaceCalibrations)?publishedFaceCalibrations:[]).slice(0,2);
    const proofAgreement=published.length===2&&recomputed.length===2&&published.every((p,index)=>sameFaceCalibrationEvidenceR227(p,recomputed[index]));
    const faceCalibrations=proofAgreement?published:recomputed;
    if(base.status!=="resolved")return {...base,faceCalibrations,calibrationAgreement:false,calibrationProofAgreement:proofAgreement,calibrationPolicy:'R227'};
    if(!proofAgreement)return {...base,status:'face-calibration-proof-invalid',ref:null,faceCalibrations,calibrationAgreement:false,calibrationProofAgreement:false,calibrationPolicy:'R227'};
    if(faceCalibrations.some(x=>x.calibrationLevel!=='strong-4/4'||x.autoIdentificationAllowed!==true||x.measurementUsable!==true))
      return {...base,status:'face-calibration-insufficient',ref:null,faceCalibrations,calibrationAgreement:false,calibrationProofAgreement:true,calibrationPolicy:'R227'};
    if(faceCalibrations[0].detectionMode!==faceCalibrations[1].detectionMode)
      return {...base,status:'face-detection-mode-disagreement',ref:null,faceCalibrations,calibrationAgreement:false,calibrationProofAgreement:true,calibrationPolicy:'R227'};
    return {...base,faceCalibrations,calibrationAgreement:true,calibrationProofAgreement:true,calibrationPolicy:'R227'};
  }
  window.bresCatalogueAmbiguityGeometryR227=catalogueAmbiguousGeometryDecisionR227;
  // R234 : la recherche catalogue massive ne peut utiliser la géométrie comme
  // préclassement fort que si deux preuves publiées strong-4/4 sont disponibles.
  // Une calibration de secours laisse les groupes et scores consultables, mais dans
  // un ordre non décisionnel et sans autoriser ce groupe à alimenter le profil axial.
  function catalogueMassiveSearchPolicyR234(){
    const guard=wrapperCalibrationGuardR233();
    const strong=guard&&guard.ok===true;
    return {
      strongCalibration:strong,
      geometryRankingAllowed:strong,
      profileCandidateRestrictionAllowed:strong,
      status:strong?'strong-4/4-catalogue-search':'calibration-indicative-only',
      reason:strong?'strong-4/4-published':((guard&&guard.reason)||'strong-4/4-proof-unavailable'),
      faces:(guard&&Array.isArray(guard.faces))?guard.faces:[]
    };
  }
  window.bresCatalogueMassiveSearchPolicyR234=catalogueMassiveSearchPolicyR234;
  // R235 : une calibration de secours ne doit pas seulement perdre son pouvoir de
  // classement ; elle ne doit plus pouvoir exclure silencieusement une référence
  // avant le classement via les fenêtres de largeur/hauteur.
  function catalogueMassiveSearchCandidatePolicyR235(){
    const base=catalogueMassiveSearchPolicyR234();
    const strong=base&&base.strongCalibration===true;
    return {
      ...base,
      geometryCandidateExclusionAllowed:strong,
      candidateEligibilityStatus:strong?'strong-4/4-geometry-window-active':'weak-calibration-geometry-window-disabled'
    };
  }
  window.bresCatalogueMassiveSearchCandidatePolicyR235=catalogueMassiveSearchCandidatePolicyR235;
  function groupSearchCatalogue(sig,db){
    const policy=catalogueMassiveSearchCandidatePolicyR235();
    const w=sig.width_mm||0,h=sig.height_mm||0,wantedBrand=el2('manualBrand')?el2('manualBrand').value.trim():'';
    const groups=new Map();
    for(const r of db){
      if(r[11]<.45)continue;
      if(policy.geometryCandidateExclusionAllowed && (Math.abs(w-r[3])>10 || Math.abs(h-r[4])>12))continue;
      const m=bestScore(sig,r),k=silhouetteKey(r);
      let g=groups.get(k);
      if(!g){g={rows:[],m,brandHit:false};groups.set(k,g);}
      g.rows.push(r); if(m.score>g.m.score)g.m=m;
      if(brandCompatible(r[1],wantedBrand))g.brandHit=true;
    }
    let arr=[...groups.values()];
    if(policy.geometryRankingAllowed){
      arr.sort((a,b)=>{
        const band=Math.abs(a.m.score-b.m.score)<=3;
        if(wantedBrand && band && a.brandHit!==b.brandHit)return a.brandHit?-1:1;
        return b.m.score-a.m.score || Math.max(...b.rows.map(r=>r[11]))-Math.max(...a.rows.map(r=>r[11]));
      });
    }else{
      // Fail-closed : conserver un aperçu consultable sans transformer le score faible
      // en classement. L'ordre lexical rend explicite qu'aucun « meilleur groupe »
      // géométrique n'est choisi à partir d'une calibration de secours.
      arr.sort((a,b)=>String((a.rows[0]||[])[0]||'').localeCompare(String((b.rows[0]||[])[0]||'')));
    }
    const out=arr.slice(0,12);
    out._r234Policy=policy; // alias historique conservé pour les consommateurs R234
    out._r235Policy=policy;
    out._r234CandidateGroupCount=arr.length;
    out._r235CandidateGroupCount=arr.length;
    return out;
  }
  function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function profileStatus(rows){
    const good=rows.filter(r=>Number(r[10]||0)>=.8 && r[9]);
    const sigs=unique(good.map(r=>r[9]));
    if(rows.length<2)return {text:'non nécessaire pour départager cette silhouette',kind:'single',distinct:sigs.length};
    if(good.length!==rows.length)return {text:'profil incomplet pour ce groupe',kind:'partial',distinct:sigs.length};
    if(sigs.length===rows.length)return {text:`OUI — ${sigs.length} profils catalogue distincts`,kind:'full',distinct:sigs.length};
    if(sigs.length>1)return {text:`PARTIEL — ${sigs.length} profils distincts pour ${rows.length} références`,kind:'partial',distinct:sigs.length};
    return {text:'NON — même profil extrait',kind:'none',distinct:sigs.length};
  }
  function profileBits(hex){
    const s=String(hex||'').trim(); if(!/^[0-9a-f]{32}$/i.test(s))return null;
    const bin=BigInt('0x'+s).toString(2).padStart(128,'0');
    const rows=[];for(let y=0;y<8;y++)rows.push([...bin.slice(y*16,(y+1)*16)].map(x=>x==='1'?1:0));
    return rows;
  }
  function profileSvg(hex,label){
    const b=profileBits(hex);if(!b)return '';
    let cells='';for(let y=0;y<8;y++)for(let x=0;x<16;x++)if(b[y][x])cells+=`<rect x="${x}" y="${y}" width="1" height="1"/>`;
    return `<svg viewBox="0 0 16 8" role="img" aria-label="Profil catalogue ${escapeHtml(label||'')}" style="width:128px;max-width:100%;height:auto;background:#fff;border:1px solid #ccd3da;border-radius:6px;padding:4px"><g fill="#111">${cells}</g></svg>`;
  }
  function popcnt(n){let c=0;while(n){n&=n-1;c++;}return c;}
  function bitsToMasks(bits){
    const rows=[];for(let y=0;y<8;y++){let m=0;for(let x=0;x<16;x++)if(bits[y]&&bits[y][x])m|=(1<<(15-x));rows.push(m>>>0);}return rows;
  }
  function rotateProfileBits(bits,deg){
    if(!deg)return bits;const th=deg*Math.PI/180,ct=Math.cos(th),st=Math.sin(th),cx=7.5,cy=3.5;
    const out=Array.from({length:8},()=>Array(16).fill(0));
    for(let y=0;y<8;y++)for(let x=0;x<16;x++){
      const dx=x-cx,dy=y-cy,sx=ct*dx+st*dy+cx,sy=-st*dx+ct*dy+cy,ix=Math.round(sx),iy=Math.round(sy);
      if(ix>=0&&ix<16&&iy>=0&&iy<8)out[y][x]=bits[iy][ix]?1:0;
    }
    return out;
  }
  function transformProfile(bits,flipH,flipV,dx,dy){
    const out=Array.from({length:8},()=>Array(16).fill(0));
    for(let y=0;y<8;y++)for(let x=0;x<16;x++)if(bits[y][x]){
      const xx=(flipH?15-x:x)+dx, yy=(flipV?7-y:y)+dy;
      if(xx>=0&&xx<16&&yy>=0&&yy<8)out[yy][xx]=1;
    }
    return out;
  }
  function profileSimilarity(a,b){
    if(!a||!b)return 0;const A=bitsToMasks(a),B=bitsToMasks(b);let inter=0,uni=0;
    for(let y=0;y<8;y++){inter+=popcnt((A[y]&B[y])>>>0);uni+=popcnt((A[y]|B[y])>>>0);}return uni?inter/uni:0;
  }
  function bestProfileSimilarityDetails(photoBits,hex){
    const cat=profileBits(hex);if(!photoBits||!cat)return {score:0,angle:0,flipH:false,flipV:false,dx:0,dy:0};let best={score:0,angle:0,flipH:false,flipV:false,dx:0,dy:0};
    for(const angle of [-15,-10,-5,0,5,10,15]){
      const rotated=rotateProfileBits(photoBits,angle);
      for(const fh of [false,true])for(const fv of [false,true])for(let dx=-3;dx<=3;dx++)for(let dy=-2;dy<=2;dy++){
        const score=profileSimilarity(transformProfile(rotated,fh,fv,dx,dy),cat);
        if(score>best.score)best={score,angle,flipH:fh,flipV:fv,dx,dy};
      }
    }
    return best;
  }
  function bestProfileSimilarity(photoBits,hex){return bestProfileSimilarityDetails(photoBits,hex).score;}
  function otsuThreshold(gray){
    const h=new Uint32Array(256);for(const v of gray)h[v]++;const n=gray.length;let sum=0;for(let i=0;i<256;i++)sum+=i*h[i];let wb=0,sb=0,best=-1,t=127;
    for(let i=0;i<256;i++){wb+=h[i];if(!wb)continue;const wf=n-wb;if(!wf)break;sb+=i*h[i];const mb=sb/wb,mf=(sum-sb)/wf,v=wb*wf*(mb-mf)*(mb-mf);if(v>best){best=v;t=i;}}
    return t;
  }
  function largestComponent(mask,w,h){
    const seen=new Uint8Array(w*h);let best=null;const qx=new Int32Array(w*h),qy=new Int32Array(w*h);
    for(let sy=0;sy<h;sy++)for(let sx=0;sx<w;sx++){const si=sy*w+sx;if(!mask[si]||seen[si])continue;let q0=0,q1=0,n=0,minx=sx,maxx=sx,miny=sy,maxy=sy;qx[q1]=sx;qy[q1++]=sy;seen[si]=1;
      while(q0<q1){const x=qx[q0],y=qy[q0++];n++;if(x<minx)minx=x;if(x>maxx)maxx=x;if(y<miny)miny=y;if(y>maxy)maxy=y;for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const ii=yy*w+xx;if(mask[ii]&&!seen[ii]){seen[ii]=1;qx[q1]=xx;qy[q1++]=yy;}}}
      const bw=maxx-minx+1,bh=maxy-miny+1,area=bw*bh,fill=n/Math.max(1,area);if(n>80&&bw>8&&bh>8&&fill>.08&&fill<.92){const touches=(minx<=1)+(miny<=1)+(maxx>=w-2)+(maxy>=h-2),borderPenalty=touches>=3?.18:touches===2?.45:touches===1?.78:1;const score=n*(1-Math.abs(.38-fill))*borderPenalty;if(!best||score>best.score)best={minx,maxx,miny,maxy,n,fill,score};}
    }return best;
  }
  async function loadProfileImage(file){
    if(typeof createImageBitmap==='function')return await createImageBitmap(file);
    return await new Promise((resolve,reject)=>{const u=URL.createObjectURL(file),im=new Image();im.onload=()=>{URL.revokeObjectURL(u);resolve(im)};im.onerror=()=>{URL.revokeObjectURL(u);reject(new Error('Photo illisible.'))};im.src=u;});
  }
  function bumpProfileAnalysisEpoch(){profileAnalysisEpoch+=1;return profileAnalysisEpoch;}
  function profileAnalysisIsCurrent(epoch){return epoch===profileAnalysisEpoch;}
  function currentMainPhotoEpoch(){try{return typeof mainPhotoEpoch==='number'?mainPhotoEpoch:(typeof identificationEpoch==='number'?identificationEpoch:null)}catch(e){return null}}
  async function fileToProfileBits(file,preview,expectedAnalysisEpoch=null){
    if(!file)throw new Error('Ajoutez une photo du profil.');
    const bmp=await loadProfileImage(file);
    if(expectedAnalysisEpoch!==null&&!profileAnalysisIsCurrent(expectedAnalysisEpoch)){if(bmp&&bmp.close)bmp.close();return null;}
    const iw=bmp.width||bmp.naturalWidth,ih=bmp.height||bmp.naturalHeight;const scale=Math.min(1,640/Math.max(iw,ih)),w=Math.max(48,Math.round(iw*scale)),h=Math.max(48,Math.round(ih*scale));
    const c=document.createElement('canvas');c.width=w;c.height=h;const cx=c.getContext('2d',{willReadFrequently:true});cx.drawImage(bmp,0,0,w,h);if(bmp.close)bmp.close();
    const im=cx.getImageData(0,0,w,h),gray=new Uint8Array(w*h);for(let i=0,j=0;i<im.data.length;i+=4,j++)gray[j]=Math.round(.299*im.data[i]+.587*im.data[i+1]+.114*im.data[i+2]);const t=otsuThreshold(gray);
    let lowSum=0,lowN=0,highSum=0,highN=0;for(const v of gray){if(v<t){lowSum+=v;lowN++;}else{highSum+=v;highN++;}}
    const contrast=Math.abs((highN?highSum/highN:255)-(lowN?lowSum/lowN:0));
    let best=null;for(const dark of [true,false]){const mask=new Uint8Array(w*h);for(let i=0;i<gray.length;i++)mask[i]=dark?(gray[i]<t?1:0):(gray[i]>t?1:0);const cc=largestComponent(mask,w,h);if(cc&&(!best||cc.score>best.cc.score))best={mask,cc,dark};}
    if(!best)throw new Error('Profil non isolé. Posez le bout de la clé devant un fond uni et rapprochez-vous.');
    const b=best.cc,bboxW=b.maxx-b.minx+1,bboxH=b.maxy-b.miny+1,margin=Math.min(b.minx/w,b.miny/h,(w-1-b.maxx)/w,(h-1-b.maxy)/h);
    const sizeFrac=Math.min(bboxW/w,bboxH/h),touches=(b.minx<=1)+(b.miny<=1)+(b.maxx>=w-2)+(b.maxy>=h-2);
    let qualityScore=0;qualityScore+=contrast>=55?40:contrast>=35?30:contrast>=22?18:5;qualityScore+=margin>=.025?25:margin>=.01?15:5;qualityScore+=sizeFrac>=.12?20:sizeFrac>=.07?12:4;qualityScore+=(touches===0?15:touches===1?8:2);qualityScore=Math.max(0,Math.min(100,qualityScore));
    const qualityLabel=qualityScore>=80?'bonne':qualityScore>=60?'moyenne':'faible';
    const pad=Math.round(Math.max(bboxW,bboxH)*.08),x0=Math.max(0,b.minx-pad),y0=Math.max(0,b.miny-pad),x1=Math.min(w-1,b.maxx+pad),y1=Math.min(h-1,b.maxy+pad),bw=x1-x0+1,bh=y1-y0+1;
    const bits=Array.from({length:8},()=>Array(16).fill(0));
    for(let gy=0;gy<8;gy++)for(let gx=0;gx<16;gx++){let on=0,n=0;const xa=Math.floor(x0+gx*bw/16),xb=Math.max(xa+1,Math.floor(x0+(gx+1)*bw/16)),ya=Math.floor(y0+gy*bh/8),yb=Math.max(ya+1,Math.floor(y0+(gy+1)*bh/8));for(let y=ya;y<yb&&y<h;y++)for(let x=xa;x<xb&&x<w;x++){on+=best.mask[y*w+x];n++;}bits[gy][gx]=(on/Math.max(1,n))>.28?1:0;}
    bits._quality={score:qualityScore,label:qualityLabel,contrast:Math.round(contrast),margin,touches,sizeFrac,darkObject:best.dark};
    if(preview){preview.width=320;preview.height=160;preview.style.display='block';const pc=preview.getContext('2d');pc.fillStyle='#fff';pc.fillRect(0,0,320,160);pc.fillStyle='#111';for(let y=0;y<8;y++)for(let x=0;x<16;x++)if(bits[y][x])pc.fillRect(x*20,y*20,20,20);pc.strokeStyle='#ddd';for(let x=0;x<=16;x++){pc.beginPath();pc.moveTo(x*20,0);pc.lineTo(x*20,160);pc.stroke();}for(let y=0;y<=8;y++){pc.beginPath();pc.moveTo(0,y*20);pc.lineTo(320,y*20);pc.stroke();}}
    return bits;
  }
  function bumpProfileCameraEpoch(){profileCameraEpoch+=1;return profileCameraEpoch;}
  function profileCameraIsCurrent(epoch){return epoch===profileCameraEpoch;}
  function stopProfileStream(stream){if(stream){for(const tr of stream.getTracks())tr.stop();}}
  function stopProfileCamera(){
    // R66: stopping/resetting invalidates getUserMedia, play() and capture promises still in flight.
    bumpProfileCameraEpoch();
    const stream=profileStream;profileStream=null;stopProfileStream(stream);
    const v=el2('profileCameraVideo'),stage=el2('profileCameraStage');if(v)v.srcObject=null;if(stage)stage.style.display='none';
  }
  async function startProfileCamera(){
    const st=el2('profilePhotoStatus'),v=el2('profileCameraVideo'),stage=el2('profileCameraStage');
    // R116 : en ouverture locale Android, déclencher le picker natif immédiatement pendant le toucher utilisateur.
    if(typeof nativeCaptureRequired==='function'&&nativeCaptureRequired()){if(typeof openNativeCapture==='function')openNativeCapture('profilePhoto');return;}
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){st.className='status warn';st.innerHTML='<b>Caméra guidée indisponible ici.</b> Utilisez le bouton « Photo du profil » ci-dessus.';return;}
    if(location.protocol!=='https:'&&location.hostname!=='localhost'){if(typeof openNativeCapture==='function')openNativeCapture('profilePhoto');return;}
    stopProfileCamera();
    const session=bumpProfileCameraEpoch();
    let stream=null;
    try{
      stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
      if(!profileCameraIsCurrent(session)){stopProfileStream(stream);return;}
      profileStream=stream;v.srcObject=stream;stage.style.display='block';
      await v.play();
      if(!profileCameraIsCurrent(session)||profileStream!==stream){stopProfileStream(stream);return;}
      st.className='status warn';st.innerHTML='<b>Caméra guidée ouverte.</b> Placez uniquement le bout de la clé dans le cadre, sur fond uni, sans le couper.';
    }catch(e){
      if(stream&&stream!==profileStream)stopProfileStream(stream);
      if(!profileCameraIsCurrent(session))return;
      stopProfileCamera();st.className='status warn';st.innerHTML='<b>Ouverture caméra impossible.</b> Utilisez « Photo du profil ». '+escapeHtml(e.message||'');
    }
  }
  async function captureProfileCamera(){
    const st=el2('profilePhotoStatus'),v=el2('profileCameraVideo'),session=profileCameraEpoch,stream=profileStream;if(!v||!stream||!profileCameraIsCurrent(session)||!v.videoWidth){st.className='status bad';st.textContent='La caméra n’est pas prête.';return;}
    // R6 : on enregistre réellement la zone du cadre, pas toute l'image caméra.
    const videoWidth=v.videoWidth,videoHeight=v.videoHeight;
    const sx=Math.round(videoWidth*PROFILE_GUIDE.x),sy=Math.round(videoHeight*PROFILE_GUIDE.y),sw=Math.max(32,Math.round(videoWidth*PROFILE_GUIDE.w)),sh=Math.max(32,Math.round(videoHeight*PROFILE_GUIDE.h));
    const c=document.createElement('canvas');c.width=sw;c.height=sh;c.getContext('2d').drawImage(v,sx,sy,sw,sh,0,0,sw,sh);
    const blob=await new Promise(resolve=>c.toBlob(resolve,'image/jpeg',.94));
    if(!blob||!profileCameraIsCurrent(session)||profileStream!==stream)return;
    bumpProfileAnalysisEpoch();
    capturedProfileBlob=blob;
    profileCaptureMainEpoch=currentMainPhotoEpoch();
    profileCaptureMeta={source:'camera-guided-roi',videoWidth,videoHeight,crop:{sx,sy,sw,sh},capturedAt:new Date().toISOString()};
    stopProfileCamera();
    st.className='status warn';st.innerHTML='<b>Photo guidée recadrée capturée.</b> R92 analyse uniquement la zone blanche. Lancez « Comparer le profil ».';
  }
  function candidateProfileRows(rows){return rows.filter(r=>Number(r[10]||0)>=.8&&r[9]);}
  function candidateProfileClusters(rows){
    const m=new Map();for(const r of candidateProfileRows(rows)){if(!m.has(r[9]))m.set(r[9],{profileKey:r[9],rows:[]});m.get(r[9]).rows.push(r);}return [...m.values()];
  }
  function ambiguityGuidance(rows){
    const refs=new Set((rows||[]).map(r=>refKey(r&&r[0]))),has=(x)=>refs.has(refKey(x));
    if(rows&&rows.length===2&&has('VAC151')&&has('VAC151SM'))return {kind:'shoulder-milling',title:'VAC151 / VAC151SM : profil identique',text:'Le catalogue Silca 2024 présente VAC151SM avec un usinage spécifique de l’épaulement (shoulder milling). La silhouette et le profil axial seuls ne suffisent donc pas : contrôlez l’épaulement ou le marquage avant toute décision.'};
    if(rows&&rows.length===4&&has('RO4')&&has('RO45')&&has('RO4R')&&has('RO48R'))return {kind:'ronis-series',title:'RONIS : groupe de série',text:'RO4 et RO45 partagent la même signature de profil dans la base ; RO4R et RO48R ont des profils distincts. R24 reconnaît uniquement certains indices positifs documentés de RO4 et ajoute un garde-fou d’espace de noms : JMA RO-45 / Errebi R39 / Silca RO85 désignent un autre blanc et ne constituent jamais une preuve de Silca RO45. Aucun RO45 n’est déduit par absence ou exclusion.'};
    return null;
  }
  function residualAmbiguityCase(rows){
    const refs=new Set((rows||[]).map(r=>refKey(r&&r[0]))),has=(x)=>refs.has(refKey(x));
    if(has('VAC151')&&has('VAC151SM'))return 'vac151';
    if(has('RO4')&&has('RO45'))return 'ronis-ro4-ro45';
    return null;
  }
  const CATALOGUE_NAMESPACE_REGISTRY_R91=[
    {id:'JMA_RO7D_TO_SILCA_RO4',maker:'JMA',tokens:['RO-7D','RO7D'],label:'JMA RO-7D / RO7D',targetRef:'RO4',targetSystem:'Silca',action:'positive_preference_inside_cluster',confidence:'multi-source'},
    {id:'KEYLINE_RI10_TO_SILCA_RO4',maker:'KEYLINE',tokens:['RI10'],label:'Keyline RI10',targetRef:'RO4',targetSystem:'Silca',action:'positive_preference_inside_cluster',confidence:'multi-source'},
    {id:'ERREBI_R23R_TO_SILCA_RO4',maker:'ERREBI',tokens:['R23R'],label:'Errebi R23R',targetRef:'RO4',targetSystem:'Silca',action:'positive_preference_inside_cluster',confidence:'multi-source'},
    {id:'ORION_RN13_TO_SILCA_RO4',maker:'ORION',tokens:['RN13'],label:'Orion RN13',targetRef:'RO4',targetSystem:'Silca',action:'positive_preference_inside_cluster',confidence:'multi-source'},
    {id:'SILCA_RO4_DIRECT',maker:'SILCA',tokens:['RO4'],label:'Silca RO4',targetRef:'RO4',targetSystem:'Silca',action:'positive_preference_inside_cluster',confidence:'catalogue-direct'},
    {id:'JMA_RO45_TO_SILCA_RO85',maker:'JMA',tokens:['RO-45','RO45'],label:'JMA RO-45 / RO45',targetRef:'RO85',targetSystem:'Silca',action:'redirect_outside_cluster_only',confidence:'multi-source'},
    {id:'ERREBI_R39_TO_SILCA_RO85',maker:'ERREBI',tokens:['R39'],label:'Errebi R39',targetRef:'RO85',targetSystem:'Silca',action:'redirect_outside_cluster_only',confidence:'multi-source'},
    {id:'SILCA_RO85_OUTSIDE_CLUSTER',maker:'SILCA',tokens:['RO85'],label:'Silca RO85',targetRef:'RO85',targetSystem:'Silca',action:'direct_outside_cluster_check',confidence:'catalogue-direct'}
  ];
  function namespaceCompactToken(x){return String(x||'').toUpperCase().replace(/[^A-Z0-9]/g,'');}
  function namespaceEscRe(x){return String(x||'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}
  const NAMESPACE_TOKEN_MAX_WEAK_GAP=3;
  const NAMESPACE_TOKEN_MAX_TOTAL_WEAK_GAP=3;
  const NAMESPACE_TOKEN_WEAK_GAP='[ .\t\u00A0\u202F\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0D-]{0,3}';
  const NAMESPACE_UNICODE_ALNUM='\\p{L}\\p{N}\\p{M}\\p{Cf}';
  function namespaceTokenPattern(token){
    const chars=namespaceCompactToken(token).split('').map(namespaceEscRe);return new RegExp(`(^|[^${NAMESPACE_UNICODE_ALNUM}])${chars.join(NAMESPACE_TOKEN_WEAK_GAP)}([^${NAMESPACE_UNICODE_ALNUM}]|$)`,'iu');
  }
  const NAMESPACE_PAIR_MAX_GAP=12;
  const NAMESPACE_PAIR_SAFE_GAP_RE=/^[ \t\u00A0\u202F.:#()\-\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0D\u2026=]*$/u;
  const NAMESPACE_PAIR_MAX_PUNCT=2;
  const NAMESPACE_STRONG_DELIMITER_RE=/[\/\\;,|+\r\n\u2044\u2215\uFF0F\uFF3C\uFF1B\uFF0C\uFF5C\uFF0B]/g;
  function namespaceSegmentAt(text,index){
    const head=String(text||'').slice(0,Math.max(0,index));
    const hits=head.match(NAMESPACE_STRONG_DELIMITER_RE);return hits?hits.length:0;
  }
  function namespaceMakerOccurrences(text){
    const upper=String(text||'').toUpperCase(),out=[];
    for(const maker of [...new Set(CATALOGUE_NAMESPACE_REGISTRY_R91.map(r=>r.maker))]){
      // R38: marks and Unicode format controls are word extenders, not usable boundaries.
      // This prevents ΩJMA, JMÁSTER, X\u200dJMA, etc. from manufacturing an ASCII-only maker boundary.
      const re=new RegExp(`(^|[^${NAMESPACE_UNICODE_ALNUM}])(${namespaceEscRe(maker)})(?=[^${NAMESPACE_UNICODE_ALNUM}]|$)`,'igu');let m;
      while((m=re.exec(upper))){const start=m.index+(m[1]||'').length;out.push({maker,start,end:start+m[2].length,segment:namespaceSegmentAt(upper,start)});if(!m[0].length)re.lastIndex++;}
    }
    return out.sort((a,b)=>a.start-b.start||a.maker.localeCompare(b.maker));
  }
  function namespaceTokenOccurrences(text,token){
    const upper=String(text||'').toUpperCase(),chars=namespaceCompactToken(token).split('').map(namespaceEscRe),out=[];
    if(!chars.length)return out;
    // R34: do not treat an adjacent non-ASCII letter/number as a token boundary.
    const re=new RegExp(`(^|[^${NAMESPACE_UNICODE_ALNUM}])(${chars.join(NAMESPACE_TOKEN_WEAK_GAP)})(?=[^${NAMESPACE_UNICODE_ALNUM}]|$)`,'igu');let m;
    while((m=re.exec(upper))){
      const start=m.index+(m[1]||'').length,end=start+m[2].length,segment=namespaceSegmentAt(upper,start);
      // R24: token reconstruction is allowlisted, not permissive. Inside a reference, only horizontal
      // spaces, dots and common hyphen/minus variants may be ignored. Brackets, quotes, underscores,
      // colons, ellipses, mathematical separators, zero-width characters and non-ASCII letters/numerals
      // cannot bridge token characters. The strong-delimiter segment guard remains as a second barrier.
      if(namespaceSegmentAt(upper,Math.max(start,end-1))!==segment){if(!m[0].length)re.lastIndex++;continue;}
      // R34: the per-gap limit alone was still too permissive: a short token could accumulate several
      // tolerated gaps (for example "R . O . 7 . D") and be reconstructed from noisy OCR. Keep the
      // existing 3-character per-gap limit, but also cap the total ignored characters across the token.
      const totalWeakGap=[...m[2]].length-chars.length;
      if(totalWeakGap>NAMESPACE_TOKEN_MAX_TOTAL_WEAK_GAP){if(!m[0].length)re.lastIndex++;continue;}
      out.push({token,start,end,segment,totalWeakGap});if(!m[0].length)re.lastIndex++;
    }
    return out;
  }
  function nearestNamespaceMaker(makers,start,end,segment){
    const local=makers.filter(m=>m.segment===segment);
    if(!local.length)return null;const ranked=local.map(m=>{const gap=end<=m.start?m.start-end:start>=m.end?start-m.end:0;return {...m,gap};}).sort((a,b)=>a.gap-b.gap||a.start-b.start);
    if(ranked[0].gap>NAMESPACE_PAIR_MAX_GAP)return null;
    if(ranked[1]&&ranked[1].gap===ranked[0].gap&&ranked[1].maker!==ranked[0].maker)return null;
    return ranked[0];
  }
  function namespacePairGapIsSafe(text,maker,occ){
    const upper=String(text||'');
    const gap=maker.end<=occ.start?upper.slice(maker.end,occ.start):occ.end<=maker.start?upper.slice(occ.end,maker.start):'';
    // R34: maker↔reference pairing is deliberately narrower than token reconstruction. Only the
    // reviewed local separators below are accepted, and no more than two non-space punctuation
    // characters may occur in the gap. This blocks OCR decoration/runs such as ___, !!!, ???,
    // brackets/braces/quotes, and ### from being treated as manufacturer-qualified evidence.
    if(!NAMESPACE_PAIR_SAFE_GAP_RE.test(gap))return false;
    const punct=[...gap].filter(ch=>!/[ \t\u00A0\u202F]/u.test(ch)).length;
    return punct<=NAMESPACE_PAIR_MAX_PUNCT;
  }
  function qualifiedNamespaceEvidence(marking){
    const raw=String(marking||'').trim(),upper=raw.toUpperCase();if(!raw)return null;
    const makers=namespaceMakerOccurrences(upper),qualified=[],seen=new Set();
    for(const rule of CATALOGUE_NAMESPACE_REGISTRY_R91){
      for(const token of rule.tokens){
        for(const occ of namespaceTokenOccurrences(upper,token)){
          const nearest=nearestNamespaceMaker(makers,occ.start,occ.end,occ.segment);if(!nearest||nearest.maker!==rule.maker||!namespacePairGapIsSafe(upper,nearest,occ))continue;
          const key=`${rule.id}:${occ.start}:${occ.end}`;if(seen.has(key))continue;seen.add(key);
          qualified.push({kind:'manufacturer-qualified-cross-reference',id:rule.id,label:rule.label,maker:rule.maker,token,targetRef:rule.targetRef,targetSystem:rule.targetSystem,action:rule.action,confidence:rule.confidence,strength:rule.confidence==='catalogue-direct'?'catalogue-direct-qualified':'catalogue-positive-multisource-qualified',pairGap:nearest.gap});
        }
      }
    }
    if(qualified.length){
      const targets=[...new Set(qualified.map(x=>`${x.targetSystem||''}:${x.targetRef||''}`))];
      if(targets.length>1)return {kind:'namespace-qualified-conflict',id:'QUALIFIED_CONFLICT',label:'Marquages fabricant-qualifiés contradictoires',maker:null,token:null,targetRef:null,targetSystem:null,action:'block-conflicting-qualified-evidence',strength:'catalogue-namespace-conflict',candidateMakers:[...new Set(qualified.map(x=>x.maker))],possibleTargets:[...new Set(qualified.map(x=>x.targetRef))],matches:qualified};
      const direct=qualified.find(x=>x.confidence==='catalogue-direct'),chosen=direct||qualified[0];
      return {...chosen,qualifiedMatchCount:qualified.length,matches:qualified};
    }
    const compact=namespaceCompactToken(raw),bare=[];
    for(const rule of CATALOGUE_NAMESPACE_REGISTRY_R91)for(const token of rule.tokens)if(namespaceCompactToken(token)===compact)bare.push(rule);
    if(bare.length)return {kind:'namespace-ambiguous-token',id:'BARE_'+compact,label:`${raw} sans fabricant`,maker:null,token:raw,targetRef:null,targetSystem:null,action:'block-unqualified-token',strength:'catalogue-namespace-ambiguous',candidateMakers:[...new Set(bare.map(x=>x.maker))],possibleTargets:[...new Set(bare.map(x=>x.targetRef))]};
    return null;
  }
  const RONIS_CODE_MAX_WEAK_GAP=3;
  const RONIS_CODE_WEAK_GAP_RE=/[ .\t\u00A0\u202F\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0D-]/g;
  const RONIS_CODE_WEAK_GAP_RUN_RE=/[ .\t\u00A0\u202F\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0D-]{4,}/;
  const RONIS_CODE_ALLOWED_RE=/^[A-Z0-9 .\t\u00A0\u202F\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0D-]+$/;
  function ronisRo4CodeSeries(code){
    const raw=String(code||'').trim().toUpperCase();
    if(!raw||!RONIS_CODE_ALLOWED_RE.test(raw)||RONIS_CODE_WEAK_GAP_RUN_RE.test(raw))return null;
    const x=raw.replace(RONIS_CODE_WEAK_GAP_RE,'');
    let m,n;
    if((m=x.match(/^D(\d{4})$/))&&(n=+m[1])>=1&&n<=1000)return 'D0001-D1000';
    if((m=x.match(/^F(\d{3})$/))&&(n=+m[1])>=1&&n<=200)return 'F001-F200';
    if((m=x.match(/^GV(\d{3})$/))&&(n=+m[1])>=1&&n<=300)return 'GV001-GV300';
    if((m=x.match(/^PS(\d{2})$/))&&(n=+m[1])>=1&&n<=30)return 'PS01-PS30';
    if((m=x.match(/^S(\d{3})$/))&&(n=+m[1])>=1&&n<=106)return 'S001-S106';
    if((m=x.match(/^T(\d{3})$/))&&(n=+m[1])>=1&&(n<=106||(n>=313&&n<=380)))return n<=106?'T001-T106':'T313-T380';
    if((m=x.match(/^TA(\d{3})$/))&&(n=+m[1])>=1&&n<=224)return 'TA001-TA224';
    if((m=x.match(/^A(\d{3})A$/))&&(n=+m[1])>=1&&(n<=200||(n>=501&&n<=700)))return n<=200?'A001A-A200A':'A501A-A700A';
    if((m=x.match(/^C(\d{3})$/))&&(n=+m[1])>=101&&n<=600)return 'C101-C600';
    if((m=x.match(/^(\d{3})C$/))&&(n=+m[1])>=101&&n<=600)return '101C-600C';
    if((m=x.match(/^(\d{3})F$/))&&(n=+m[1])>=1&&n<=500)return '001F-500F';
    if((m=x.match(/^1F(\d{2})$/))&&(n=+m[1])>=1&&n<=21)return '1F01-1F21';
    return null;
  }
  function ronisRo4PositiveEvidence(marking){
    const series=ronisRo4CodeSeries(marking);if(series)return {kind:'key-code-series',id:series,label:series,strength:'catalogue-positive-single-source'};
    return null;
  }
  function manualEvidenceFor(caseId,data){
    const at=new Date().toISOString();
    if(caseId==='vac151'){
      const observation=String((data&&data.shoulderMilling)||'unknown');
      if(observation==='visible')return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,observation:'shoulder-milling-visible',preferredRefs:['VAC151SM'],strength:'physical-positive',canValidate:false,note:'Usinage d’épaulement observé : préférence manuelle pour VAC151SM. Cette preuve ne produit jamais VALIDÉ à elle seule.'};
      if(observation==='not-visible')return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,observation:'shoulder-milling-not-visible',preferredRefs:[],strength:'non-discriminating-negative',canValidate:false,note:'Usinage non observé : l’absence visible n’est pas traitée comme une preuve suffisante de VAC151.'};
      return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,observation:'unknown',preferredRefs:[],strength:'none',canValidate:false,note:'Aucune observation discriminante enregistrée.'};
    }
    if(caseId==='ronis-ro4-ro45'){
      const marking=String((data&&data.marking)||'').trim(),application=String((data&&data.application)||'').trim(),namespaceEvidence=qualifiedNamespaceEvidence(marking);
      if(namespaceEvidence){
        if(namespaceEvidence.kind==='namespace-qualified-conflict')return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:namespaceEvidence,preferredRefs:[],suggestedCatalogueRef:null,suggestedCatalogueSystem:null,strength:namespaceEvidence.strength,canValidate:false,note:`Plusieurs marquages fabricant-qualifiés pointent vers des références différentes (${namespaceEvidence.possibleTargets.join(' / ')}). R24 bloque toute préférence et demande un contrôle séparé de la clé réelle.`};
        if(namespaceEvidence.kind==='namespace-ambiguous-token')return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:namespaceEvidence,preferredRefs:[],suggestedCatalogueRef:null,suggestedCatalogueSystem:null,strength:namespaceEvidence.strength,canValidate:false,note:`${namespaceEvidence.label} reste ambigu sans fabricant. R24 n'utilise aucun alias externe non qualifié et ne crée aucune préférence.`};
        const inside=namespaceEvidence.action==='positive_preference_inside_cluster'&&namespaceEvidence.targetRef==='RO4';
        const outside=namespaceEvidence.action==='redirect_outside_cluster_only'||namespaceEvidence.action==='direct_outside_cluster_check';
        if(inside)return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:namespaceEvidence,preferredRefs:['RO4'],suggestedCatalogueRef:null,suggestedCatalogueSystem:null,strength:namespaceEvidence.strength,canValidate:false,note:`Équivalence fabricant-qualifiée ${namespaceEvidence.label} -> Silca RO4. Préférence documentaire RO4 uniquement ; R27 ne transforme jamais cet indice en VALIDÉ.`};
        if(outside)return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:namespaceEvidence,preferredRefs:[],suggestedCatalogueRef:namespaceEvidence.targetRef,suggestedCatalogueSystem:namespaceEvidence.targetSystem,strength:namespaceEvidence.strength,canValidate:false,note:`${namespaceEvidence.label} est documenté comme équivalent de ${namespaceEvidence.targetSystem} ${namespaceEvidence.targetRef}, hors du couple RO4/RO45. R27 bloque toute préférence interne et propose seulement ce contrôle séparé.`};
      }
      const match=ronisRo4PositiveEvidence(marking);
      if(match)return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:match,preferredRefs:['RO4'],strength:match.strength,canValidate:false,note:`Série de code RO4 documentée ${match.label} : préférence RO4 uniquement. R27 ne transforme jamais cet indice en VALIDÉ et ne déduit jamais RO45 par exclusion.`};
      return {schema:'bres-manual-ambiguity-evidence-v5',caseId,createdAt:at,marking,application,matchedEvidence:null,preferredRefs:[],strength:'record-only',canValidate:false,note:'Aucun indice fabricant-qualifié ni série de code RO4 documentée reconnue. L’information reste mémorisée ; R24 ne déduit jamais RO45 par exclusion.'};
    }
    return null;
  }
  function currentResidualRows(){
    if(!lastCatalogueResults||!lastCatalogueResults.length)return [];
    const policy=lastCatalogueResults._r234Policy;
    if(!policy||policy.profileCandidateRestrictionAllowed!==true)return [];
    return lastCatalogueResults[0].rows;
  }
  function renderManualAmbiguityPanel(rows){
    const host=el2('manualAmbiguityPanel');if(!host)return;
    const caseId=residualAmbiguityCase(rows||[]);
    if(!caseId){host.style.display='none';host.innerHTML='';return;}
    host.style.display='block';
    if(caseId==='vac151'){
      const selected=(lastManualAmbiguityEvidence&&lastManualAmbiguityEvidence.caseId===caseId)?lastManualAmbiguityEvidence.observation:'';
      const value=selected==='shoulder-milling-visible'?'visible':selected==='shoulder-milling-not-visible'?'not-visible':'unknown';
      host.innerHTML=`<b>Contrôle manuel résiduel — VAC151 / VAC151SM</b><br><span class="small">Le bulletin Silca 2024 montre un usinage d’épaulement spécifique pour VAC151SM. Une observation positive peut renforcer VAC151SM ; une absence visible ne force jamais VAC151.</span><label>Usinage d’épaulement observé<select id="manualShoulderMilling"><option value="unknown"${value==='unknown'?' selected':''}>Non contrôlé / incertain</option><option value="visible"${value==='visible'?' selected':''}>Oui, visible</option><option value="not-visible"${value==='not-visible'?' selected':''}>Non visible</option></select></label><button id="manualEvidenceSaveBtn" class="alt" type="button">Enregistrer l’observation</button><div id="manualEvidenceStatus" class="status">Cette observation reste séparée de la décision automatique.</div>`;
    }else{
      const m=(lastManualAmbiguityEvidence&&lastManualAmbiguityEvidence.caseId===caseId)?lastManualAmbiguityEvidence:{};
      host.innerHTML=`<b>Contrôle manuel résiduel — RONIS RO4 / RO45</b><br><span class="small">Le catalogue les conserve dans le même sous-groupe de profil. R24 sait reconnaître des équivalences RO4 fabricant-qualifiées (JMA RO-7D, Keyline RI10, Errebi R23R, Orion RN13, Silca RO4), certaines séries de codes RO4 documentées, et bloque les marquages composites contradictoires au lieu de retenir la première correspondance. Garde-fou important : JMA RO-45 / Errebi R39 correspondent à Silca RO85, hors du couple RO4/RO45 : R24 peut proposer RO85 comme contrôle séparé, jamais comme validation. Silca RO85 explicite est traité de la même façon ; un simple « RO45 » sans fabricant reste ambigu. Aucun indice absent ne devient une preuve de RO45.</span><label>Marquage / code visible<input id="manualRonisMarking" value="${escapeHtml(m.marking||'')}" placeholder="Ex. code frappé sur la clé"></label><label>Application / serrure connue<input id="manualRonisApplication" value="${escapeHtml(m.application||'')}" placeholder="Ex. meuble, serrure ou fabricant connu"></label><button id="manualEvidenceSaveBtn" class="alt" type="button">Enregistrer l’observation</button><div id="manualEvidenceStatus" class="status">Une équivalence fabricant-qualifiée ou une série de code RO4 reconnue peut produire une préférence documentaire, jamais un VALIDÉ. Les collisions d’espace de noms et les marquages fabricant-qualifiés contradictoires sont bloqués dans RO4/RO45 ; quand une équivalence fabricant-qualifiée pointe vers une autre référence Silca connue, R24 l’indique uniquement comme référence séparée à contrôler.</div>`;
    }
    const b=el2('manualEvidenceSaveBtn');if(b)b.onclick=saveManualAmbiguityEvidence;
  }
  function saveManualAmbiguityEvidence(){
    const rows=currentResidualRows(),caseId=residualAmbiguityCase(rows),st=el2('manualEvidenceStatus');if(!caseId)return;
    let data={};
    if(caseId==='vac151')data.shoulderMilling=(el2('manualShoulderMilling')||{}).value||'unknown';
    else data={marking:(el2('manualRonisMarking')||{}).value||'',application:(el2('manualRonisApplication')||{}).value||''};
    lastManualAmbiguityEvidence=manualEvidenceFor(caseId,data);
    if(lastProfileDiagnostic)lastProfileDiagnostic.manualAmbiguityEvidence=JSON.parse(JSON.stringify(lastManualAmbiguityEvidence));
    if(st){
      st.className='status warn';
      if(lastManualAmbiguityEvidence.preferredRefs&&lastManualAmbiguityEvidence.preferredRefs.length){
        st.innerHTML=`<b>Préférence manuelle : ${lastManualAmbiguityEvidence.preferredRefs.map(escapeHtml).join(', ')}</b><br>${escapeHtml(lastManualAmbiguityEvidence.note)}<br><b>Aucun VALIDÉ automatique.</b>`;
      }else if(lastManualAmbiguityEvidence.suggestedCatalogueRef){
        const rr=catalogueRefResolution(lastManualAmbiguityEvidence.suggestedCatalogueRef),found=rr&&rr.ref;
        st.innerHTML=`<b>Référence à contrôler hors du groupe : ${escapeHtml(lastManualAmbiguityEvidence.suggestedCatalogueSystem||'Silca')} ${escapeHtml(lastManualAmbiguityEvidence.suggestedCatalogueRef)}</b><br>${escapeHtml(lastManualAmbiguityEvidence.note)}<br>${found?'<b>Cette référence existe dans le catalogue local ; elle doit être contrôlée séparément avant toute validation.</b>':'<b>Référence non résolue dans le catalogue local : aucune action automatique.</b>'}`;
      }else{
        st.innerHTML=`<b>Observation enregistrée sans choix automatique.</b><br>${escapeHtml(lastManualAmbiguityEvidence.note)}`;
      }
    }
  }
  function cloneProfileBits(bits){return bits?bits.map(r=>r.slice()):null;}
  function profileBitsHex(bits){
    if(!bits)return null;let bin='';for(let y=0;y<8;y++)for(let x=0;x<16;x++)bin+=bits[y]&&bits[y][x]?'1':'0';
    if(bin.length!==128)return null;return BigInt('0b'+bin).toString(16).padStart(32,'0');
  }
  function strictRefKey(x){
    return String(x||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[‐‑‒–—−]/g,'-').trim().replace(/\s+/g,' ');
  }
  function looseRefKey(x){return strictRefKey(x).replace(/[^A-Z0-9]/g,'');}
  function catalogueRefResolution(raw){
    const entered=strictRefKey(raw),db=lastCatalogueDb||window.BRES_CATALOG_V3||[];
    if(!entered)return {status:'empty',ref:null,matches:[],entered};
    if(!db.length)return {status:'catalogue-not-loaded',ref:null,matches:[],entered};
    const exact=unique(db.filter(r=>strictRefKey(r&&r[0])===entered).map(r=>r[0]));
    if(exact.length===1)return {status:'exact',ref:exact[0],matches:exact,entered};
    const loose=looseRefKey(entered),matches=unique(db.filter(r=>looseRefKey(r&&r[0])===loose).map(r=>r[0]));
    if(matches.length===1)return {status:'loose-unique',ref:matches[0],matches,entered};
    if(matches.length>1)return {status:'ambiguous-normalization',ref:null,matches,entered};
    return {status:'not-found',ref:null,matches:[],entered};
  }
  function knownCalibrationResolution(){
    const e=el2('profileKnownRef');if(!e)return {status:'empty',ref:null,matches:[],entered:''};
    return catalogueRefResolution(e.value);
  }
  function knownCalibrationRef(){const r=knownCalibrationResolution();return r.ref||'';}
  function refKey(x){return strictRefKey(x);}
  function knownReferenceExistsInCatalogue(ref){
    if(!ref)return null;const db=lastCatalogueDb||window.BRES_CATALOG_V3||[];if(!db.length)return null;const k=refKey(ref);return db.some(r=>refKey(r&&r[0])===k);
  }
  function knownReferenceInTopGroup(ref){
    if(!ref||!lastCatalogueResults||!lastCatalogueResults.length)return null;
    const policy=lastCatalogueResults._r234Policy;if(!policy||policy.profileCandidateRestrictionAllowed!==true)return null;
    const k=refKey(ref);return lastCatalogueResults[0].rows.some(r=>refKey(r&&r[0])===k);
  }
  function sessionConsensusSummary(){
    const strong=profileSession.filter(x=>x&&x.strong&&x.topRef&&x.photoProfileHex);
    const support={};let qualifyingPairs=0;
    for(let i=0;i<strong.length;i++)for(let j=i+1;j<strong.length;j++){
      const a=strong[i],b=strong[j],ra=refKey(a.topRef),rb=refKey(b.topRef);
      if(!ra||ra!==rb)continue;
      const ab=profileBits(a.photoProfileHex),bb=profileBits(b.photoProfileHex);
      if(!ab||!bb)continue;
      const cross=crossCaptureSimilarity(ab,bb);
      if(cross<PROFILE_THRESHOLDS.cross)continue;
      qualifyingPairs++;
      if(!support[ra])support[ra]={ref:a.topRef,pairs:0,bestCross:0,captures:new Set()};
      support[ra].pairs++;support[ra].bestCross=Math.max(support[ra].bestCross,cross);support[ra].captures.add(i);support[ra].captures.add(j);
    }
    const requiredSupportRatio=strong.length<=2?1:(2/3);
    const groups=Object.values(support).map(x=>({ref:x.ref,pairs:x.pairs,bestCross:x.bestCross,captureSupport:x.captures.size,supportRatio:strong.length?x.captures.size/strong.length:0})).sort((a,b)=>b.captureSupport-a.captureSupport||b.pairs-a.pairs||b.bestCross-a.bestCross);
    const qualified=groups.filter(x=>x.captureSupport>=2&&x.supportRatio+1e-9>=requiredSupportRatio);
    const pairConflict=qualified.length>1;
    const consensusRef=qualified.length===1?qualified[0].ref:null;
    const splitSupport=!consensusRef&&!pairConflict&&groups.length>0&&strong.length>=3;
    const q=profileSession.map(x=>Number((x.quality||{}).score||0)).filter(Number.isFinite).sort((a,b)=>a-b);
    const medianQuality=q.length?(q.length%2?q[(q.length-1)/2]:(q[q.length/2-1]+q[q.length/2])/2):0;
    const strongRefs=unique(strong.map(x=>refKey(x.topRef)).filter(Boolean));
    return {strongCount:strong.length,strongRefs,pairConsensusRefs:groups,qualifiedConsensusRefs:qualified,qualifyingPairs,pairConflict,splitSupport,consensusRef,requiredSupportRatio,medianQuality:Math.round(medianQuality*10)/10};
  }
  function sessionIntegrity(){
    const captureRefs=unique(profileSession.map(x=>refKey(x.knownReference)).filter(Boolean));
    const known=sessionKnownRef||knownCalibrationRef(),resolution=known?catalogueRefResolution(known):knownCalibrationResolution();
    const stable=captureRefs.length<=1&&(!captureRefs.length||!known||captureRefs[0]===refKey(known));
    const exists=knownReferenceExistsInCatalogue(known),inTop=knownReferenceInTopGroup(known);
    const enough=profileSession.length>=2,consensus=sessionConsensusSummary();
    const resolutionSafe=!known?false:['exact','loose-unique'].includes(resolution.status);
    const valid=!!known&&stable&&exists===true&&enough&&resolutionSafe;
    return {knownReference:known||null,referenceKeyPolicy:'punctuation-preserving-v1',referenceResolution:resolution,referenceStable:stable,referenceExistsInCatalogue:exists,referenceInTopGroup:inTop,captureKnownReferences:captureRefs,sufficientCaptures:enough,consensus,validForReplay:valid};
  }
  function resetProfileSession(){
    bumpProfileAnalysisEpoch();
    stopProfileCamera();previousProfileResult=null;lastProfileDiagnostic=null;profileCaptureMeta=null;capturedProfileBlob=null;profileSession=[];sessionKnownRef=null;lastManualAmbiguityEvidence=null;profileSessionMainEpoch=currentMainPhotoEpoch();profileCaptureMainEpoch=null;
    const inp=el2('profilePhoto');if(inp)inp.value='';const kr=el2('profileKnownRef');if(kr)kr.value='';const prev=el2('profilePhotoPreview');if(prev){const pc=prev.getContext&&prev.getContext('2d');if(pc)pc.clearRect(0,0,prev.width||1,prev.height||1);prev.style.display='none';}
    const st=el2('profilePhotoStatus');if(st){st.className='status';st.innerHTML='<b>Nouvelle session profil prête.</b> Saisissez la référence certaine puis prenez au moins deux captures du même bout de clé.';}
  }
  function crossCaptureSimilarity(a,b){
    if(!a||!b)return 0;let best=0;
    for(const angle of [-15,-10,-5,0,5,10,15]){
      const rotated=rotateProfileBits(a,angle);
      for(const fh of [false,true])for(const fv of [false,true])for(let dx=-2;dx<=2;dx++)for(let dy=-1;dy<=1;dy++)best=Math.max(best,profileSimilarity(transformProfile(rotated,fh,fv,dx,dy),b));
    }
    return best;
  }
  function downloadJson(payload,name){
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
  }
  function exportProfileDiagnostic(){
    const st=el2('profilePhotoStatus');
    if(!lastProfileDiagnostic){if(st){st.className='status warn';st.innerHTML='<b>Aucun diagnostic à exporter.</b> Comparez d’abord une photo du profil.';}return;}
    const payload=JSON.parse(JSON.stringify(lastProfileDiagnostic));payload.manualAmbiguityEvidence=lastManualAmbiguityEvidence?JSON.parse(JSON.stringify(lastManualAmbiguityEvidence)):null;payload.packageCheckpoint='R319';downloadJson(payload,`BRES_profil_CHECKPOINT_R319_${new Date().toISOString().replace(/[:.]/g,'-')}.json`);
  }
  function exportCalibrationSession(){
    const st=el2('profilePhotoStatus');if(!profileSession.length){if(st){st.className='status warn';st.innerHTML='<b>Aucune capture analysée dans cette session.</b>';}return;}
    const integrity=sessionIntegrity(),known=integrity.knownReference,strong=profileSession.filter(x=>x.strong),sameKnown=known?strong.filter(x=>refKey(x.topRef)===refKey(known)).length:null,cons=integrity.consensus||{};
    const payload={schema:'bres-profile-calibration-v5',version:'V2.28 TEST R156',packageCheckpoint:'R319',createdAt:new Date().toISOString(),knownReference:known||null,thresholds:{...PROFILE_THRESHOLDS},captureCount:profileSession.length,integrity,summary:{strongCount:strong.length,strongTopRefs:strong.map(x=>x.topRef),strongKnownMatches:sameKnown,allStrongAgree:strong.length>0&&new Set(strong.map(x=>refKey(x.topRef))).size===1,consensusRef:cons.consensusRef||null,qualifyingPairs:cons.qualifyingPairs||0,pairConflict:!!cons.pairConflict,splitSupport:!!cons.splitSupport,requiredSupportRatio:cons.requiredSupportRatio||1,consensusSupportRatio:(cons.qualifiedConsensusRefs&&cons.qualifiedConsensusRefs.length===1)?cons.qualifiedConsensusRefs[0].supportRatio:0,medianQuality:cons.medianQuality||0},captures:profileSession,manualAmbiguityEvidence:lastManualAmbiguityEvidence?JSON.parse(JSON.stringify(lastManualAmbiguityEvidence)):null};
    downloadJson(payload,`BRES_calibration_CHECKPOINT_R319_${known||'REFERENCE'}_${new Date().toISOString().replace(/[:.]/g,'-')}.json`);
    if(st){let msg=integrity.validForReplay?'session exploitable par le replay':'session conservée mais marquée NON exploitable (référence absente/instable ou moins de deux captures)';if(cons.pairConflict)msg+=' ; conflit entre plusieurs consensus majoritaires, aucune préférence de session';else if(cons.splitSupport)msg+=' ; soutien partagé ou insuffisant, aucune préférence de session';else if(cons.consensusRef)msg+=` ; consensus majoritaire : ${escapeHtml(cons.consensusRef)}`;st.className=(integrity.validForReplay&&!cons.pairConflict)?'status warn':'status bad';st.innerHTML+=`<br><b>Session de calibration exportée :</b> ${profileSession.length} capture(s), sans photo brute — ${msg}.`;}
  }
  function renderProfileCandidates(rows,host){
    const clusters=candidateProfileClusters(rows);if(!clusters.length){host.innerHTML='<b>Aucun profil catalogue exploitable pour ce groupe.</b>';return;}
    let h='<b>Profils catalogue des candidats (regroupés par signature identique) :</b><div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px">';
    for(const c of clusters){const refs=c.rows.map(r=>r[0]);const label=refs.join(' / ');h+=`<div style="min-width:132px;text-align:center"><b>${escapeHtml(label)}</b>${refs.length>1?'<br><small>même profil catalogue</small>':''}<br>${profileSvg(c.profileKey,label)}</div>`;}host.innerHTML=h+'</div>';
  }
  async function compareProfilePhoto(){
    const st=el2('profilePhotoStatus'),inp=el2('profilePhoto'),prev=el2('profilePhotoPreview'),cand=el2('profileCandidateVisuals');if(!st||!inp)return;
    const mainEpoch=currentMainPhotoEpoch();
    if(profileSessionMainEpoch!==null&&mainEpoch!==null&&profileSessionMainEpoch!==mainEpoch){
      bumpProfileAnalysisEpoch();previousProfileResult=null;lastProfileDiagnostic=null;profileSession=[];sessionKnownRef=null;lastManualAmbiguityEvidence=null;profileSessionMainEpoch=mainEpoch;
      if(profileCaptureMainEpoch!==mainEpoch){capturedProfileBlob=null;profileCaptureMeta=null;profileCaptureMainEpoch=null;inp.value='';st.className='status warn';st.innerHTML='<b>Nouvelle clé détectée.</b> La session précédente a été écartée pour éviter de mélanger deux clés. Prenez une nouvelle photo du profil.';return;}
    }
    if(profileSessionMainEpoch===null)profileSessionMainEpoch=mainEpoch;
    if(!lastCatalogueResults||!lastCatalogueResults.length){st.className='status bad';st.textContent='Lancez d’abord la recherche catalogue sur les photos recto/verso.';return;}
    const searchPolicyR234=lastCatalogueResults._r234Policy;
    if(!searchPolicyR234||searchPolicyR234.profileCandidateRestrictionAllowed!==true){
      st.className='status warn';st.innerHTML='<b>Profil axial non lancé :</b> la recherche de forme précédente repose sur une calibration indicative. Deux faces strong-4/4 publiées sont requises avant de restreindre le profil à un groupe géométrique.';
      return;
    }
    const rows=lastCatalogueResults[0].rows,clusters=candidateProfileClusters(rows),guide=ambiguityGuidance(rows);renderProfileCandidates(rows,cand);
    if(clusters.length<2){let msg='<b>Le profil axial ne peut pas départager ce meilleur groupe.</b>';if(guide)msg+=`<br><b>${escapeHtml(guide.title)}</b><br>${escapeHtml(guide.text)}`;st.className='status warn';st.innerHTML=msg;return;}
    const knownResolution=knownCalibrationResolution(),knownRaw=(el2('profileKnownRef')||{}).value||'',knownNow=knownResolution.ref||'';
    if(knownRaw.trim()&&knownResolution.status==='ambiguous-normalization'){st.className='status bad';st.innerHTML=`<b>Référence ambiguë après normalisation.</b> La saisie « ${escapeHtml(knownRaw)} » peut désigner plusieurs références distinctes : <b>${knownResolution.matches.map(escapeHtml).join(' / ')}</b>. Saisissez exactement la référence avec sa ponctuation.`;return;}
    if(knownRaw.trim()&&!knownNow){st.className='status bad';st.innerHTML=`<b>Référence certaine introuvable dans le catalogue.</b> « ${escapeHtml(knownRaw)} » ne sera pas utilisée pour une calibration.`;return;}
    if(profileSession.length&&refKey(knownNow)!==refKey(sessionKnownRef)){st.className='status bad';st.innerHTML='<b>Référence certaine modifiée pendant la session.</b> Pour éviter de mélanger deux clés, utilisez « Nouvelle clé / remettre à zéro » avant de continuer.';return;}
    if(!profileSession.length)sessionKnownRef=knownNow||null;
    const analysisEpoch=bumpProfileAnalysisEpoch();
    try{
      st.className='status warn';st.textContent='Analyse expérimentale du profil…';
      const source=capturedProfileBlob||(inp.files&&inp.files[0]),bits=await fileToProfileBits(source,prev,analysisEpoch);
      if(!bits||!profileAnalysisIsCurrent(analysisEpoch)||currentMainPhotoEpoch()!==mainEpoch)return;
      const quality=bits._quality||{score:0,label:'inconnue'};
      let scores=clusters.map(c=>{const d=bestProfileSimilarityDetails(bits,c.profileKey);return {refs:c.rows.map(r=>r[0]),profileKey:c.profileKey,score:d.score,angle:d.angle};}).sort((a,b)=>b.score-a.score);
      const top=scores[0],second=scores[1],margin=(top.score-(second?second.score:0)),pct=x=>Math.round(x*100),topLabel=top.refs.join(' / ');
      const strongCluster=quality.score>=PROFILE_THRESHOLDS.quality&&top.score>=PROFILE_THRESHOLDS.score&&margin>=PROFILE_THRESHOLDS.margin;
      const singleReference=top.refs.length===1,topRef=singleReference?top.refs[0]:null,strong=strongCluster&&singleReference;
      const cross=previousProfileResult?crossCaptureSimilarity(bits,previousProfileResult.bits):null;
      const sameCluster=!!(previousProfileResult&&previousProfileResult.strongCluster&&strongCluster&&previousProfileResult.topProfileKey===top.profileKey);
      const sameWinner=!!(sameCluster&&singleReference&&previousProfileResult.topRef===topRef);
      let h=`<b>Qualité photo du profil : ${escapeHtml(quality.label)} — ${Math.round(quality.score)} / 100</b><br>`;
      h+=`Contraste estimé : ${quality.contrast||0}. Tolérance de rotation : ±15°.<br>`;
      if(profileCaptureMeta&&profileCaptureMeta.source==='camera-guided-roi')h+=`Capture guidée : zone utile recadrée automatiquement (${profileCaptureMeta.crop.sw}×${profileCaptureMeta.crop.sh}px).<br>`;
      if(cross!==null)h+=`Cohérence avec la capture précédente : <b>${pct(cross)} %</b>${sameCluster?' — même groupe de profil en tête':''}.<br>`;
      h+=`<br><b>Comparaison du profil — EXPÉRIMENTAL :</b><br>${scores.map((x,i)=>`${i+1}. <b>${escapeHtml(x.refs.join(' / '))}</b> — ${pct(x.score)} %${x.refs.length>1?' — profil identique entre ces références':''}${x.angle?` (correction ${x.angle>0?'+':''}${x.angle}°)`:''}`).join('<br>')}<br>`;
      if(quality.score<PROFILE_THRESHOLDS.quality){h+=`<br><b>Profil non concluant : qualité de photo insuffisante.</b> Reprenez la photo plus près, sur fond uni, sans couper le bout de la clé.`;st.className='status warn';}
      else if(strongCluster&&previousProfileResult&&previousProfileResult.strongCluster&&!sameCluster){h+=`<br><b>Deux captures ne sont pas d’accord sur le groupe de profil.</b> R24 bloque toute préférence : reprenez le profil.`;st.className='status bad';}
      else if(strongCluster&&!singleReference&&sameCluster&&cross>=PROFILE_THRESHOLDS.cross){h+=`<br><b>Double capture cohérente : le profil réduit le résultat à ${escapeHtml(topLabel)}</b> (marge ${pct(margin)} points), mais ces références ont la même signature de profil. R24 refuse de choisir l’une d’elles.`;st.className='status warn';}
      else if(strongCluster&&!singleReference){h+=`<br><b>Le profil réduit le résultat à ${escapeHtml(topLabel)}</b> (marge ${pct(margin)} points), sans pouvoir départager ces références. Faites une seconde capture pour contrôler la répétabilité ; aucun choix individuel n’est autorisé.`;st.className='status warn';}
      else if(strong&&sameWinner&&cross>=PROFILE_THRESHOLDS.cross){h+=`<br><b>Double capture cohérente : ${escapeHtml(topRef)} reste en tête</b> (marge ${pct(margin)} points). Résultat renforcé, mais toujours À CONFIRMER tant qu’un essai réel de référence connue n’a pas validé le procédé.`;st.className='status warn';}
      else if(strong){h+=`<br><b>Le profil photographié préfère ${escapeHtml(topRef)}</b> (marge ${pct(margin)} points). Faites une seconde capture pour contrôler la répétabilité ; aucun VALIDÉ automatique.`;st.className='status warn';}
      else h+=`<br><b>Profil non concluant.</b> Aucun choix automatique n’est autorisé.`;
      if(guide)h+=`<br><b>Critère complémentaire :</b> ${escapeHtml(guide.text)}`;
      const known=sessionKnownRef||knownNow||'';
      const knownExists=knownReferenceExistsInCatalogue(known),knownInTop=knownReferenceInTopGroup(known);
      if(known&&knownExists===false)h+=`<br><b>Attention :</b> la référence certaine « ${escapeHtml(known)} » n’existe pas dans les 5 103 références chargées. Vérifiez la saisie avant d’utiliser cette session pour calibrer.`;
      else if(known&&knownInTop===false)h+=`<br><b>Signal utile de calibration :</b> la référence certaine ${escapeHtml(known)} n’est pas dans le meilleur groupe de forme actuel.`;
      lastProfileDiagnostic={schema:'bres-profile-diagnostic-v10',version:'V2.28 TEST R156',createdAt:new Date().toISOString(),capture:profileCaptureMeta||{source:'file-picker'},quality,scores:scores.slice(0,8),topRefs:top.refs,topRef,topProfileKey:top.profileKey,topScore:top.score,margin,strongCluster,strong,crossCaptureSimilarity:cross,sameCluster,sameWinner,candidateRefs:candidateProfileRows(rows).map(r=>r[0]),photoProfileHex:profileBitsHex(bits),knownReference:known||null,knownReferenceResolution:known?catalogueRefResolution(known):knownResolution,knownReferenceMatch:known?top.refs.some(r=>refKey(r)===refKey(known)):null,knownReferenceExistsInCatalogue:knownExists,knownReferenceInTopGroup:knownInTop,manualAmbiguityEvidence:lastManualAmbiguityEvidence?JSON.parse(JSON.stringify(lastManualAmbiguityEvidence)):null,thresholds:{...PROFILE_THRESHOLDS}};
      profileSession.push(JSON.parse(JSON.stringify(lastProfileDiagnostic)));if(profileSession.length>12)profileSession.shift();
      const cons=sessionConsensusSummary();
      if(cons.pairConflict){h+=`<br><b>Conflit de session :</b> plusieurs références atteignent le seuil majoritaire. R24 bloque toute préférence.`;st.className='status bad';}
      else if(cons.splitSupport){h+=`<br><b>Session partagée :</b> des paires cohérentes existent, mais aucune référence n'est soutenue par au moins ${Math.round(cons.requiredSupportRatio*100)} % des captures fortes. R24 ne choisit rien.`;st.className='status warn';}
      else if(cons.consensusRef){const cg=cons.qualifiedConsensusRefs[0];h+=`<br><b>Consensus majoritaire de session :</b> ${escapeHtml(cons.consensusRef)} soutenue par ${cg.captureSupport}/${cons.strongCount} captures fortes (${Math.round(cg.supportRatio*100)} %) et ${cg.pairs} paire(s) cohérente(s). Ce consensus reste À CONFIRMER.`;}
      else if(profileSession.length>=2){h+=`<br><b>Session :</b> aucun consensus majoritaire suffisamment cohérent ; aucune préférence automatique.`;}
      if(!profileAnalysisIsCurrent(analysisEpoch)||currentMainPhotoEpoch()!==mainEpoch)return;
      previousProfileResult={bits:cloneProfileBits(bits),topProfileKey:top.profileKey,topRefs:[...top.refs],topRef,topScore:top.score,margin,strongCluster,strong,qualityScore:quality.score,knownReference:known||null};
      st.innerHTML=h;
    }catch(e){if(!profileAnalysisIsCurrent(analysisEpoch)||currentMainPhotoEpoch()!==mainEpoch)return;st.className='status bad';st.textContent=e.message||String(e);}
  }
  function render(results,box,db){
    bumpProfileAnalysisEpoch();
    lastCatalogueResults=results;lastCatalogueDb=db;
    if(!results.length){box.className='status warn';box.innerHTML='<b>Aucun candidat catalogue suffisamment proche.</b>';return;}
    const policy=(results&&results._r234Policy)||{strongCalibration:false,geometryRankingAllowed:false,profileCandidateRestrictionAllowed:false,status:'calibration-indicative-only',reason:'strong-4/4-proof-unavailable'};
    const strong=policy.geometryRankingAllowed===true&&policy.profileCandidateRestrictionAllowed===true;
    const top=results[0],second=results[1],margin=strong&&second?top.m.score-second.m.score:null,ps=profileStatus(top.rows),stats=catalogueStatsFor(db);
    const pcv=el2('profileCandidateVisuals');
    if(strong){if(pcv)renderProfileCandidates(top.rows,pcv);renderManualAmbiguityPanel(top.rows);}
    else{
      if(pcv)pcv.innerHTML='<b>Profils non restreints :</b> calibration géométrique indicative. Deux faces strong-4/4 publiées sont requises avant de sélectionner un groupe pour le profil axial.';
      renderManualAmbiguityPanel([]);
    }
    const refs=top.rows.map(r=>r[0]),brands=unique(top.rows.map(r=>r[1]).filter(Boolean)),pages=unique(top.rows.map(r=>r[2]));
    const q=Math.max(...top.rows.map(r=>Number(r[11]||0)));
    let h=`<b>Catalogue Silca massif : ${db.length} silhouettes chargées.</b><br>`;
    if(strong)h+=`<b>Meilleur groupe de forme : ${refs.map(escapeHtml).join(', ')} — ${top.m.score}%</b><br>`;
    else{
      h+=`<b>Recherche géométrique indicative :</b> ${results._r234CandidateGroupCount||results.length} groupe(s) compatible(s) avec les mesures de secours.<br>`;
      h+=`<b>Aucun meilleur groupe n'est désigné :</b> l'ordre ci-dessous est non décisionnel et les pourcentages de forme sont seulement indicatifs tant que deux faces strong-4/4 publiées ne sont pas disponibles.<br>`;
    }
    if(brands.length)h+=`Famille/marque du premier groupe affiché : ${brands.map(escapeHtml).join(', ')}<br>`;
    h+=`Page(s) Silca : ${pages.map(escapeHtml).join(', ')}<br>`;
    h+=`Qualité extraction catalogue : ${Math.round(q*100)} %<br>`;
    if(strong){
      if(top.rows.length>1){
        h+=`<b>Silhouette strictement identique dans le catalogue :</b> ${top.rows.length} références. Aucune d’elles n’est choisie arbitrairement.<br>`;
        h+=`<b>Profil catalogue discriminant :</b> ${escapeHtml(ps.text)}.<br>`;
        if(ps.kind==='full')h+=`Le profil est donc le prochain critère utile pour départager ce groupe ; la silhouette seule reste <b>À CONFIRMER</b>.<br>`;
        const guide=ambiguityGuidance(top.rows);if(guide)h+=`<b>${escapeHtml(guide.title)} :</b> ${escapeHtml(guide.text)}<br>`;
      } else {
        h+=`<b>Silhouette isolée dans la base compacte</b>, mais elle ne valide jamais seule la référence : marquage, profil ou étalon requis.<br>`;
      }
    }else h+=`<b>Profil axial suspendu :</b> la calibration actuelle ne peut pas fournir le groupe de candidats au profil.<br>`;
    const wantedBrand=el2('manualBrand')?el2('manualBrand').value.trim():'';
    if(wantedBrand){
      if(strong)h+=`Marque lue/saisie : <b>${escapeHtml(wantedBrand)}</b>. ${top.brandHit?'Le meilleur groupe est compatible avec cette marque.':'Le meilleur groupe géométrique ne confirme pas cette marque.'}<br>`;
      else h+=`Marque lue/saisie : <b>${escapeHtml(wantedBrand)}</b>. Compatibilité affichée à titre informatif ; elle ne réordonne pas les groupes tant que la calibration reste indicative.<br>`;
    }
    if(strong)h+=`Écart avec le groupe de forme suivant : ${margin} point(s).<br>`;
    h+=`<br><b>${strong?'Top groupes':'Aperçu de groupes — ordre non décisionnel'} :</b>`;
    results.slice(0,8).forEach((g,i)=>{
      const rr=g.rows.map(r=>escapeHtml(r[0]));
      const gp=profileStatus(g.rows);
      h+=`<br>${i+1}. <b>${rr.slice(0,6).join(', ')}${rr.length>6?'…':''}</b> — ${g.m.score}%${strong?'':' — indicatif'}${g.brandHit?' — marque compatible':''}${g.rows.length>1?` — ${g.rows.length} mêmes silhouettes / profil: ${escapeHtml(gp.kind)}`:''}`;
    });
    h+=`<br><br><small>Contrôle R24 : ${stats.collisionGroups} groupes de silhouettes identiques (${stats.refsInCollision} références). Le profil catalogue sépare entièrement ${stats.fullyProfileResolved} de ces groupes ; ${stats.partialProfileResolved} partiellement ; ${stats.notProfileResolved} restent non séparés par le profil extrait. Après regroupement par signature profil, il ne subsiste que ${stats.residualProfileClusters} sous-groupes structurellement ambigus (${stats.residualProfileRefs} références). Aucune validation automatique n’est produite par la forme ou par un profil partagé.</small>`;
    box.className='status warn';box.innerHTML=h;
  }
  function installAutoCatalogueSearch(){
    const analyse=el2('analyseBtn');if(!analyse||analyse.dataset.v228auto==='1')return;analyse.dataset.v228auto='1';const original=analyse.onclick;
    analyse.onclick=async function(ev){
      if(original)await original.call(this,ev);
      const status=el2('catalogueMassifStatus');if(!status||!currentSig)return;
      try{status.className='status warn';status.textContent='V2.28 R52 : recherche catalogue automatique après analyse…';const db=await ensureCatalogue(status);render(groupSearchCatalogue(currentSig,db),status,db);}catch(e){status.className='status bad';status.textContent='Recherche catalogue automatique indisponible : '+(e.message||e);}
    };
  }
  function addCard(){
    const cards=document.querySelectorAll('main .card'); if(!cards.length)return;
    const card=document.createElement('section');card.className='card';card.id='catalogueMassifCard';
    card.innerHTML=`<h2>2. Catalogue Silca massif — V2.28 TEST R156</h2><p class="small">Recherche automatique par <b>groupes de formes</b> dans plus de 5 000 silhouettes. R156 conserve le consensus majoritaire, généralise le registre d’espaces de noms JMA/Silca/Errebi/Keyline/Orion autour de RO4/RO45 et conserve les preuves RO4 strictement non-validantes ; elle compare les profils par signatures distinctes : deux références ayant exactement le même profil catalogue restent groupées au lieu de provoquer un faux gagnant ou un faux échec. Les ambiguïtés résiduelles connues sont signalées avec le critère physique à contrôler. R156 mémorise ces observations manuelles séparément et interdit qu’elles produisent à elles seules un VALIDÉ.</p><button id="catalogueMassifBtn">🔎 Rechercher automatiquement dans le catalogue Silca</button><div id="catalogueMassifStatus" class="status">Analysez d’abord recto + verso, puis lancez la recherche catalogue.</div><div id="profileCandidateVisuals" class="status">Les profils des candidats apparaîtront ici après la recherche.</div><div id="manualAmbiguityPanel" class="status warn" style="display:none"></div><h3>Profil / section de la clé — expérimental</h3><p class="small">Visez <b>le bout de la clé dans l’axe</b>, sur fond uni, sans couper le contour. Pour le test de calibration, saisissez une référence dont vous êtes certaine puis faites au moins deux captures du même bout de clé. R156 compare toutes les paires fortes, exige une majorité de captures cohérentes dès qu’au moins 3 captures fortes sont disponibles et ne crée un consensus de référence que si le profil de tête correspond à une seule référence. Un profil partagé peut réduire le groupe, jamais choisir arbitrairement. Ne changez pas la référence au milieu d’une session.</p><label>Référence certaine pour le test (facultatif hors calibration)<input id="profileKnownRef" placeholder="Ex. TE8D" autocomplete="off"></label><div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0"><button id="profileResetBtn" class="alt" type="button">↺ Nouvelle clé / remettre à zéro</button></div><button id="profilePhotoBtn" class="btn alt" type="button">📷 Photo du profil</button><input id="profilePhoto" type="file" accept="image/*" capture="environment"><div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0"><button id="profileCameraStartBtn" class="alt" type="button">🎯 Ouvrir caméra guidée</button><button id="profileCameraCaptureBtn" class="alt" type="button">📸 Capturer dans le cadre</button><button id="profileCameraStopBtn" class="alt" type="button">Fermer caméra</button></div><div id="profileCameraStage" style="display:none;position:relative;max-width:460px;margin:8px 0"><video id="profileCameraVideo" playsinline muted style="display:block;width:100%;border-radius:8px;background:#111"></video><div aria-hidden="true" style="position:absolute;left:18%;top:32%;width:64%;height:36%;border:3px solid #fff;border-radius:12px;box-shadow:0 0 0 999px rgba(0,0,0,.28);pointer-events:none"></div></div><canvas id="profilePhotoPreview"></canvas><button id="profileCompareBtn" class="alt" type="button">Comparer le profil aux candidats</button><button id="profileDiagnosticBtn" class="alt" type="button">Exporter dernier diagnostic</button><button id="profileCalibrationExportBtn" class="alt" type="button">Exporter session calibration</button><div id="profilePhotoStatus" class="status">Aucune photo de profil analysée.</div>`;
    cards[0].insertAdjacentElement('afterend',card);
    const btn=el2('catalogueMassifBtn'),status=el2('catalogueMassifStatus'),pbtn=el2('profileCompareBtn'),diagBtn=el2('profileDiagnosticBtn'),sessionBtn=el2('profileCalibrationExportBtn'),resetBtn=el2('profileResetBtn'),startCam=el2('profileCameraStartBtn'),captureCam=el2('profileCameraCaptureBtn'),stopCam=el2('profileCameraStopBtn'),photoBtn=el2('profilePhotoBtn'),inp=el2('profilePhoto');
    if(pbtn)pbtn.onclick=compareProfilePhoto;if(diagBtn)diagBtn.onclick=exportProfileDiagnostic;if(sessionBtn)sessionBtn.onclick=exportCalibrationSession;if(resetBtn)resetBtn.onclick=resetProfileSession;if(startCam)startCam.onclick=startProfileCamera;if(captureCam)captureCam.onclick=captureProfileCamera;if(stopCam)stopCam.onclick=stopProfileCamera;if(photoBtn)photoBtn.onclick=()=>{if(typeof openNativeCapture==='function')openNativeCapture('profilePhoto');};
    if(inp)inp.addEventListener('change',()=>{bumpProfileAnalysisEpoch();capturedProfileBlob=null;profileCaptureMainEpoch=currentMainPhotoEpoch();profileCaptureMeta={source:'file-picker',selectedAt:new Date().toISOString()};stopProfileCamera();});
    const knownRefInput=el2('profileKnownRef');if(knownRefInput)knownRefInput.addEventListener('input',()=>bumpProfileAnalysisEpoch());
    btn.onclick=async()=>{
      const sig=(typeof currentSig!=='undefined')?currentSig:window.currentSig;
      if(!sig){status.className='status bad';status.textContent='Analysez d’abord les deux photos recto + verso.';return;}
      try{status.className='status warn';const db=await ensureCatalogue(status);status.textContent='Comparaison des groupes de silhouettes…';const res=groupSearchCatalogue(sig,db);render(res,status,db);}catch(e){status.className='status bad';status.textContent='Catalogue massif indisponible : '+(e.message||e);}
    };
  }
  try{
    document.title='BRES Clés V2.28 TEST R156';
    const badge=document.querySelector('.app-version-badge');if(badge)badge.textContent='V2.28 TEST R156 • CONSENSUS MAJORITAIRE • STABLE CONSERVÉE';
    const hdr=document.querySelector('header p');if(hdr)hdr.textContent=hdr.textContent.replace(/V2\.2[5-8](?: TEST)?/,'V2.28 TEST');
    installSafetyWrappers();
    addCard();
    installAutoCatalogueSearch();
  }catch(e){console.warn('V2.28 TEST R156 non initialisée',e)}
})();
