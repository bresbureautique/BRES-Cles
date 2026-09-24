// R157 : protocole physique dédié TE8D / TE8I.
// TE8B reste uniquement un jeton OCR intermédiaire et ne devient jamais un canon.
// Ce protocole numérote les cycles, conserve les preuves et ne modifie aucune décision.
const OCR_TESA_TE8_PHYSICAL_MAX_CYCLES=5;
let ocrTesaTe8PhysicalTestActive=false;
let ocrTesaTe8PhysicalTestId=0;
let ocrTesaTe8PhysicalHistory=[];
let ocrTesaTe8PhysicalRejectedCycles=0;
function deactivateOCRTesaTe8PhysicalTest(){
  ocrTesaTe8PhysicalTestActive=false;
  return buildOCRTesaTe8PhysicalTestSummary(ocrTesaTe8PhysicalHistory,false);
}
function startOCRTesaTe8PhysicalTest(){
  ocrTesaTe8PhysicalTestId+=1;
  ocrTesaTe8PhysicalTestActive=true;
  ocrTesaTe8PhysicalHistory=[];
  ocrTesaTe8PhysicalRejectedCycles=0;
  const series=startOCRCaptureSeries();
  const summary=buildOCRTesaTe8PhysicalTestSummary([],true);
  renderOCRTesaTe8PhysicalTestStatus(summary);
  return {...summary,captureSeriesId:series.seriesId};
}
function buildOCRTesaTe8PhysicalCycle(info,criticalFamily,captureSeries,physicalReadiness){
  const familyCanons=new Set(["TE8D","TE8I"]);
  const close=buildCloseReferenceDiagnostic(info);
  const bridgeTokensSeen=[...new Set((criticalFamily?.bridgeTokensSeen||[]).filter(x=>compactRef(x)==="TE8B").map(()=>"TE8B"))];
  const familyInvolved=criticalFamily?.familyId==="tesa-te8";
  const sessionRejected=!!captureSeries?.rejectedCycle || captureSeries?.status==="session-changed" || captureSeries?.status==="key-mismatch-suspected";
  const accepted=!!ocrTesaTe8PhysicalTestActive && familyInvolved && !sessionRejected;
  const decisiveCanon=close?.decisiveCanon && familyCanons.has(String(close.decisiveCanon)) ? String(close.decisiveCanon) : null;
  const views=(close?.views||[]).slice(0,2).map(v=>({side:String(v?.side||"vue"),topCanon:v?.topCanon&&familyCanons.has(String(v.topCanon))?String(v.topCanon):null,topSimilarity:roundedRepeatabilityNumber(v?.topSimilarity),secondCanon:v?.secondCanon&&familyCanons.has(String(v.secondCanon))?String(v.secondCanon):null,secondSimilarity:roundedRepeatabilityNumber(v?.secondSimilarity),margin:v?.margin===null?null:roundedRepeatabilityNumber(v?.margin),ambiguous:!!v?.ambiguous}));
  const ambiguityStatuses=new Set(["ambiguous","conflict"]);
  const familyAmbiguityStatuses=new Set(["dual-canon-near-tie","bridge-token-ambiguity","cross-view-conflict","multi-cycle-unstable","persistent-ambiguity"]);
  const ambiguous=ambiguityStatuses.has(String(close?.status||"")) || familyAmbiguityStatuses.has(String(criticalFamily?.status||""));
  return {testId:ocrTesaTe8PhysicalTestId,captureSeriesId:captureSeries?.seriesId??null,cycleEpoch:Number(ocrCaptureCycleEpoch)||0,cycleNumber:0,accepted,rejectionReason:sessionRejected?String(captureSeries?.status||"session-rejected"):(familyInvolved?null:"outside-family"),familyInvolved,familyStatus:String(criticalFamily?.status||"not-involved"),decisiveCanon,bridgeTokensSeen,ambiguous,physicalCheckRecommended:!!criticalFamily?.physicalCheckRecommended || physicalReadiness?.recommendation==="physical-check-required",physicalRecommendation:String(physicalReadiness?.recommendation||"collect-more"),views,decisionInfluence:false};
}
function buildOCRTesaTe8PhysicalTestSummary(samples=ocrTesaTe8PhysicalHistory,active=ocrTesaTe8PhysicalTestActive){
  const byCycle=new Map();
  for(const sample of samples||[])byCycle.set(Number(sample?.cycleEpoch)||0,sample);
  const cycles=[...byCycle.values()].slice(-OCR_TESA_TE8_PHYSICAL_MAX_CYCLES).map((x,i)=>({...x,cycleNumber:i+1}));
  const accepted=cycles.filter(x=>x?.accepted),rejected=cycles.filter(x=>!x?.accepted);
  const decisiveSequence=accepted.map(x=>x?.decisiveCanon).filter(x=>x==="TE8D"||x==="TE8I"),distinctDecisive=[...new Set(decisiveSequence)];
  const bridgeTokenCount=accepted.reduce((n,x)=>n+(x?.bridgeTokensSeen||[]).filter(t=>t==="TE8B").length,0);
  const ambiguousCycleCount=accepted.filter(x=>x?.ambiguous).length,physicalFlagCount=accepted.filter(x=>x?.physicalCheckRecommended).length,outsideFamilyCount=rejected.filter(x=>x?.rejectionReason==="outside-family").length;
  let status="inactive",label="TEST TE8D / TE8I INACTIF",recommendation="none",stableCanon=null;
  if(active){status="collect-more";label="POURSUIVRE LES PRISES";recommendation="collect-more";if(outsideFamilyCount&&!accepted.length){status="outside-family";label="REFAIRE UNE PRISE TE8D / TE8I";recommendation="repeat-capture";}else if(accepted.length>=2&&distinctDecisive.length>1){status="unstable";label="LECTURE TE8D / TE8I INSTABLE";recommendation="repeat-capture";}else if(accepted.length>=3&&(physicalFlagCount>=1||ambiguousCycleCount>=2)){status="physical-check-required";label="CONTRÔLE PHYSIQUE TE8D / TE8I NÉCESSAIRE";recommendation="physical-check-required";}else if(accepted.length>=3&&decisiveSequence.length===accepted.length&&distinctDecisive.length===1){status="repeatable";stableCanon=distinctDecisive[0];label=`RÉSULTAT RÉPÉTABLE : ${stableCanon}`;recommendation="repeatable";}else if(accepted.length>=1&&!decisiveSequence.length){status="retake";label="REFAIRE UNE PRISE";recommendation="repeat-capture";}}
  return {schema:"bres-tesa-te8-physical-test-v1",milestone:"V2.28 TEST R157",active:!!active,testId:ocrTesaTe8PhysicalTestId,status,label,recommendation,cycleCount:cycles.length,acceptedCycleCount:accepted.length,rejectedCycleCount:rejected.length,decisiveSequence,distinctDecisiveCanons:distinctDecisive,stableCanon,bridgeTokenCount,ambiguousCycleCount,physicalFlagCount,outsideFamilyCount,canonicalReferences:["TE8D","TE8I"],nonCanonicalBridgeTokens:["TE8B"],cycles,decisionInfluence:false};
}
function recordOCRTesaTe8PhysicalCycle(info,criticalFamily,captureSeries,physicalReadiness){
  if(!ocrTesaTe8PhysicalTestActive)return buildOCRTesaTe8PhysicalTestSummary([],false);
  const sample=buildOCRTesaTe8PhysicalCycle(info,criticalFamily,captureSeries,physicalReadiness);
  if(!sample.accepted)ocrTesaTe8PhysicalRejectedCycles+=1;
  const pos=ocrTesaTe8PhysicalHistory.findIndex(x=>Number(x?.cycleEpoch)===sample.cycleEpoch);
  if(pos>=0)ocrTesaTe8PhysicalHistory[pos]=sample;else ocrTesaTe8PhysicalHistory.push(sample);
  ocrTesaTe8PhysicalHistory=ocrTesaTe8PhysicalHistory.slice(-OCR_TESA_TE8_PHYSICAL_MAX_CYCLES);
  return buildOCRTesaTe8PhysicalTestSummary(ocrTesaTe8PhysicalHistory,true);
}
function renderOCRTesaTe8PhysicalTestStatus(summary){
  const target=el("ocrTesaTe8PhysicalTestStatus");if(!target)return;
  if(!summary?.active){target.className="status";target.textContent="Test physique TE8D / TE8I inactif. Démarrez-le uniquement avec plusieurs prises de la même clé.";return;}
  target.className=summary.status==="repeatable"?"status ok":(summary.status==="physical-check-required"?"status bad":"status warn");
  let html=`<b>Test TE8D / TE8I — ${escapeOCRDiagnosticText(summary.label)}</b><br><small>${summary.acceptedCycleCount} cycle(s) accepté(s), ${summary.rejectedCycleCount} rejeté(s). TE8B reste un jeton OCR non canonique et ne valide jamais une référence.</small>`;
  for(const cycle of summary.cycles||[]){const canon=cycle.decisiveCanon||"—";const bridge=cycle.bridgeTokensSeen?.length?` • jeton ${cycle.bridgeTokensSeen.join("/")}`:"";const verdict=cycle.accepted?`candidat ${canon}${cycle.ambiguous?" • ambigu":""}${bridge}`:`rejeté : ${cycle.rejectionReason||"non exploitable"}`;html+=`<br><small><b>Cycle ${cycle.cycleNumber} :</b> ${escapeOCRDiagnosticText(verdict)}</small>`;}
  target.innerHTML=html;
}
