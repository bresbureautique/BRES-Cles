// R161 : conserver séparément la preuve qui a levé la garde QA2.
function buildCatalogueQa2ResolutionTrace(ref,signal,details={}){
  const canon=norm(ref), partners=catalogueQa2Partners(canon);
  if(!canon||!partners.length)return {active:false,source:"R158-QA2",status:"not-applicable",ref:canon||null,partners:[],signal:null,independentSignalSatisfied:false,automaticValidationBlocked:true};
  const critical=partners.some(p=>p.severity==="critical");
  const labels={manual:"référence certaine saisie manuellement","ocr-main":"marquage OCR recto/verso principal","ocr-head":"marquage OCR sur photos rapprochées de tête"};
  return {
    active:true,source:"R158-QA2",status:"resolved-by-independent-signal",
    ref:canon,partners:[...new Set(partners.map(p=>norm(p.ref)).filter(Boolean))],
    severity:critical?"critical":"near",severityLabel:critical?"collision critique":"collision proche",
    signal:String(signal||"independent"),signalLabel:labels[signal]||"signal indépendant",
    geometryScore:Number.isFinite(Number(details.geometryScore))?Number(details.geometryScore):null,
    visualScore:Number.isFinite(Number(details.visualScore))?Number(details.visualScore):null,
    ocrSimilarity:Number.isFinite(Number(details.ocrSimilarity))?Number(details.ocrSimilarity):null,
    independentSignalSatisfied:true,automaticValidationBlocked:false
  };
}
function syncCatalogueQa2ResolutionTraceToDiagnostic(){
  if(!lastOCRDiagnosticExport)return;
  lastOCRDiagnosticExport.catalogueQa2ResolutionTrace=catalogueQa2ResolutionTrace;
  if(lastOCRDiagnosticExport.humanSummary)lastOCRDiagnosticExport.humanSummary.catalogueQa2ResolutionTrace=catalogueQa2ResolutionTrace;
}
function setCatalogueQa2ResolutionTrace(ref,signal,details={}){
  catalogueQa2ResolutionTrace=buildCatalogueQa2ResolutionTrace(ref,signal,details);
  syncCatalogueQa2ResolutionTraceToDiagnostic();
  return catalogueQa2ResolutionTrace;
}
function clearCatalogueQa2ResolutionTrace(){
  catalogueQa2ResolutionTrace=null;
  syncCatalogueQa2ResolutionTraceToDiagnostic();
}
function renderCatalogueQa2ResolutionTrace(trace){
  if(!trace?.active)return "";
  const scores=[];
  if(trace.geometryScore!==null)scores.push(`géométrie ${Math.round(trace.geometryScore)} %`);
  if(trace.visualScore!==null)scores.push(`visuel ${Math.round(trace.visualScore)} %`);
  if(trace.ocrSimilarity!==null)scores.push(`OCR ${Math.round(trace.ocrSimilarity*100)} %`);
  const partner=trace.partners.length?` face à ${trace.partners.join(" / ")}`:"";
  return `<small><b>Traçabilité QA2 :</b> ${trace.ref}${partner} départagée par ${trace.signalLabel}${scores.length?` • ${scores.join(" • ")}`:""}. Le blocage automatique est levé uniquement grâce à ce signal indépendant.</small>`;
}
