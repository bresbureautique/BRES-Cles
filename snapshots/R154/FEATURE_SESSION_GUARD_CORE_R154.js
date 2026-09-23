// BRES Cles V2.28 TEST R154 — garde de session multi-prises OCR
// Extrait exact du runtime; diagnostic uniquement.

function beginOCRRequest(){ocrRequestEpoch+=1;return {requestEpoch:ocrRequestEpoch,identificationEpoch,captureSeriesId:ocrCaptureSeriesActive?ocrCaptureSeriesId:null};}

const OCR_CAPTURE_SERIES_MAX_CYCLES=5;
// R154 : garde de session. Une série est liée à son identifiant de requête OCR et,
// lorsqu'une géométrie principale est disponible, à une ancre grossière de la clé.
// Le contrôle est volontairement conservateur : il ne valide jamais une référence,
// il empêche seulement qu'une requête d'une ancienne série ou une clé manifestement
// différente soit ajoutée au protocole multi-prises.
const OCR_CAPTURE_SERIES_GEOMETRY_WIDTH_DRIFT_LIMIT=0.35;
const OCR_CAPTURE_SERIES_GEOMETRY_HEIGHT_DRIFT_LIMIT=0.35;
const OCR_CAPTURE_SERIES_GEOMETRY_AREA_DRIFT_LIMIT=0.28;
const OCR_CAPTURE_SERIES_GEOMETRY_FILL_DRIFT_LIMIT=0.35;
let ocrCaptureSeriesActive=false;
let ocrCaptureSeriesId=0;
let ocrCaptureSeriesHistory=[];
let ocrCaptureSeriesAnchor=null;
let ocrCaptureSeriesRejectedCycles=0;
function buildOCRCaptureSeriesGeometryAnchor(sig=currentSig){
  if(!sig)return null;
  const num=x=>roundedRepeatabilityNumber(Number(x));
  return {width_mm:num(sig.width_mm),height_mm:num(sig.height_mm),area:num(sig.area),bladeFill:num(sig.bladeFill),headFill:num(sig.headFill)};
}
function buildOCRCaptureSeriesSessionGuard(expectedSeriesId,sig=currentSig){
  const expected=expectedSeriesId===null||expectedSeriesId===undefined?null:Number(expectedSeriesId);
  const sameSeries=!!ocrCaptureSeriesActive && expected===ocrCaptureSeriesId;
  const anchor=ocrCaptureSeriesAnchor;
  const current=buildOCRCaptureSeriesGeometryAnchor(sig);
  let geometryComparable=!!(anchor&&current),geometryMismatch=false;
  let widthDrift=null,heightDrift=null,areaDrift=null,bladeFillDrift=null,headFillDrift=null;
  if(geometryComparable){
    widthDrift=Math.abs(current.width_mm-anchor.width_mm)/Math.max(10,Math.abs(anchor.width_mm)||10);
    heightDrift=Math.abs(current.height_mm-anchor.height_mm)/Math.max(5,Math.abs(anchor.height_mm)||5);
    areaDrift=Math.abs(current.area-anchor.area);
    bladeFillDrift=Math.abs(current.bladeFill-anchor.bladeFill);
    headFillDrift=Math.abs(current.headFill-anchor.headFill);
    geometryMismatch=widthDrift>OCR_CAPTURE_SERIES_GEOMETRY_WIDTH_DRIFT_LIMIT || heightDrift>OCR_CAPTURE_SERIES_GEOMETRY_HEIGHT_DRIFT_LIMIT || areaDrift>OCR_CAPTURE_SERIES_GEOMETRY_AREA_DRIFT_LIMIT || bladeFillDrift>OCR_CAPTURE_SERIES_GEOMETRY_FILL_DRIFT_LIMIT || headFillDrift>OCR_CAPTURE_SERIES_GEOMETRY_FILL_DRIFT_LIMIT;
  }
  return {
    active:ocrCaptureSeriesActive,expectedSeriesId:expected,currentSeriesId:ocrCaptureSeriesId,sameSeries,
    geometryComparable,geometryMismatch,
    widthDrift:widthDrift===null?null:roundedRepeatabilityNumber(widthDrift),
    heightDrift:heightDrift===null?null:roundedRepeatabilityNumber(heightDrift),
    areaDrift:areaDrift===null?null:roundedRepeatabilityNumber(areaDrift),
    bladeFillDrift:bladeFillDrift===null?null:roundedRepeatabilityNumber(bladeFillDrift),
    headFillDrift:headFillDrift===null?null:roundedRepeatabilityNumber(headFillDrift),
    accepted:sameSeries&&!geometryMismatch,decisionInfluence:false
  };
}

function startOCRCaptureSeries(){
  ocrCaptureSeriesId+=1;
  ocrCaptureSeriesActive=true;
  ocrCaptureSeriesHistory=[];
  ocrCaptureSeriesAnchor=buildOCRCaptureSeriesGeometryAnchor(currentSig);
  ocrCaptureSeriesRejectedCycles=0;
  const summary=buildOCRCaptureSeriesSummary([]);
  renderOCRCaptureSeriesStatus(summary);
  renderOCRCaptureProtocolStatus(buildOCRCaptureProtocolSummary([]));
  return summary;
}

function recordOCRCaptureSeries(info,expectedSeriesId=ocrCaptureSeriesActive?ocrCaptureSeriesId:null){
  if(!ocrCaptureSeriesActive)return {active:false,seriesId:ocrCaptureSeriesId,cycleCount:0,status:"inactive",decisionInfluence:false};
  if(!ocrCaptureSeriesAnchor && currentSig)ocrCaptureSeriesAnchor=buildOCRCaptureSeriesGeometryAnchor(currentSig);
  const sessionGuard=buildOCRCaptureSeriesSessionGuard(expectedSeriesId,currentSig);
  if(!sessionGuard.accepted){
    ocrCaptureSeriesRejectedCycles+=1;
    const base=buildOCRCaptureSeriesSummary(ocrCaptureSeriesHistory);
    return {...base,status:sessionGuard.sameSeries?"key-mismatch-suspected":"session-changed",rejectedCycle:true,rejectedCycleCount:ocrCaptureSeriesRejectedCycles,sessionGuard,decisionInfluence:false};
  }
  const sample=buildOCRCaptureCycleSample(info,ocrCaptureCycleEpoch);
  sample.captureSeriesId=ocrCaptureSeriesId;
  const pos=ocrCaptureSeriesHistory.findIndex(x=>x.captureCycleEpoch===sample.captureCycleEpoch);
  if(pos>=0)ocrCaptureSeriesHistory[pos]=sample;else ocrCaptureSeriesHistory.push(sample);
  ocrCaptureSeriesHistory=ocrCaptureSeriesHistory.slice(-OCR_CAPTURE_SERIES_MAX_CYCLES);
  return {...buildOCRCaptureSeriesSummary(ocrCaptureSeriesHistory),rejectedCycle:false,rejectedCycleCount:ocrCaptureSeriesRejectedCycles,sessionGuard,decisionInfluence:false};
}

function enableOCRDiagnosticExport(reads,info,seriesContext=null){
  const repeatability=recordOCRRepeatability(info);
  const expectedSeriesId=seriesContext&&Object.prototype.hasOwnProperty.call(seriesContext,"captureSeriesId")?seriesContext.captureSeriesId:(ocrCaptureSeriesActive?ocrCaptureSeriesId:null);
  const captureSeries=recordOCRCaptureSeries(info,expectedSeriesId);
  const captureProtocol=buildOCRCaptureProtocolSummary(ocrCaptureSeriesHistory);
  const human=renderOCRHumanDiagnostic(reads,info,repeatability);
  renderOCRCaptureSeriesStatus(captureSeries);
  renderOCRCaptureProtocolStatus(captureProtocol);
  lastOCRDiagnosticExport=buildOCRDiagnosticExport(reads,info);
  lastOCRDiagnosticExport.humanSummary=human.exportSummary;
  lastOCRDiagnosticExport.repeatability=repeatability;
  lastOCRDiagnosticExport.captureSeries=captureSeries;
  lastOCRDiagnosticExport.captureProtocol=captureProtocol;
  lastOCRDiagnosticExport.captureSeriesGuard=captureSeries.sessionGuard||null;
  const btn=el("ocrDiagnosticExportBtn");
  if(btn)btn.disabled=false;
}
