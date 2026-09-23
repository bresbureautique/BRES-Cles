// BRES Clés V2.28 TEST R153 CANDIDATE
// Diagnostic multi-cycle only: does not influence identification decisions.
function buildOCRCaptureProtocolSummary(samples){
  const byCycle=new Map();
  for(const sample of samples||[])byCycle.set(Number(sample?.captureCycleEpoch)||0,sample);
  const cycles=[...byCycle.values()].slice(-OCR_CAPTURE_SERIES_MAX_CYCLES);
  const decisiveSequence=cycles.map(x=>x?.decisiveCanon?String(x.decisiveCanon):null);
  const statusSequence=cycles.map(x=>String(x?.status||"insufficient"));
  let candidateChangeCount=0,statusChangeCount=0;
  for(let i=1;i<cycles.length;i++){
    if((decisiveSequence[i]||"")!==(decisiveSequence[i-1]||""))candidateChangeCount+=1;
    if(statusSequence[i]!==statusSequence[i-1])statusChangeCount+=1;
  }
  const candidateCounts={};
  const sideCandidateCounts={};
  for(const cycle of cycles){
    if(cycle?.decisiveCanon){const c=String(cycle.decisiveCanon);candidateCounts[c]=(candidateCounts[c]||0)+1;}
    for(const view of cycle?.views||[]){
      if(!view?.topCanon)continue;
      const side=String(view.side||"vue"),canon=String(view.topCanon);
      sideCandidateCounts[side]=sideCandidateCounts[side]||{};
      sideCandidateCounts[side][canon]=(sideCandidateCounts[side][canon]||0)+1;
    }
  }
  const recurrentCandidates=Object.entries(candidateCounts)
    .map(([canon,count])=>({canon,count,ratio:cycles.length?roundedRepeatabilityNumber(count/cycles.length):0}))
    .sort((a,b)=>b.count-a.count||a.canon.localeCompare(b.canon));
  const ambiguousFlags=cycles.map(x=>x?.status==="ambiguous"||x?.status==="conflict");
  let ambiguityStreak=0,maxAmbiguityStreak=0;
  for(const flag of ambiguousFlags){ambiguityStreak=flag?ambiguityStreak+1:0;maxAmbiguityStreak=Math.max(maxAmbiguityStreak,ambiguityStreak);}
  const seriesSummary=buildOCRCaptureSeriesSummary(cycles);
  let recommendation="collect-more";
  if(cycles.length>=3 && seriesSummary.physicalAmbiguitySuspected && maxAmbiguityStreak>=2)recommendation="physical-check-required";
  else if(cycles.length>=3 && seriesSummary.stable && candidateChangeCount===0)recommendation="repeatable";
  else if(cycles.length>=2 && candidateChangeCount>0)recommendation="ocr-instability-review";
  return {active:ocrCaptureSeriesActive,seriesId:ocrCaptureSeriesId,cycleCount:cycles.length,recurrentCandidates,sideCandidateCounts,candidateChangeCount,statusChangeCount,maxAmbiguityStreak,decisiveSequence,statusSequence,recommendation,decisionInfluence:false};
}
