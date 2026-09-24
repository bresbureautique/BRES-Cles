// R160 : trace diagnostique structurée de la garde QA2 sans modifier la décision.
// Dépend de catalogueQa2AmbiguityView() (R159).
function buildCatalogueQa2DiagnosticTrace(cand,guard){
  const view=catalogueQa2AmbiguityView(cand,guard);
  if(!view)return {active:false,source:"R158-QA2",severity:null,refs:[],rows:[],gapPoints:null,partnerCompared:false,automaticValidationBlocked:false,independentSignalRequired:false,nextAction:null};
  const rows=view.rows.map(r=>({ref:r.ref,score:r.score,rank:r.rank,role:r.role,compared:r.score!==null}));
  const first=rows[0]||null, partner=rows.slice(1).find(r=>r.compared)||rows[1]||null;
  let gapPoints=Number.isFinite(Number(guard?.gap))?Number(guard.gap):null;
  if(gapPoints===null&&first?.score!==null&&partner?.score!==null)gapPoints=Math.abs(Number(first.score)-Number(partner.score));
  const trigger=view.severity==="critical"?"collision critique de géométrie":view.severity==="near-uncompared"?"concurrent catalogue non comparé":"écart de scores inférieur à la marge QA2";
  const nextAction=view.severity==="near-uncompared"?"comparer la référence concurrente puis rechercher un marquage indépendant":"rechercher un marquage recto/verso ou effectuer un contrôle physique discriminant";
  return {active:true,source:"R158-QA2",severity:view.severity,severityLabel:view.severityLabel,refs:[...view.refs],rows,gapPoints,partnerCompared:rows.slice(1).some(r=>r.compared),trigger,automaticValidationBlocked:true,independentSignalRequired:true,nextAction};
}
function renderCatalogueQa2DiagnosticTrace(trace){
  if(!trace?.active)return "";
  const gap=trace.gapPoints===null?(trace.partnerCompared?"écart non calculable":"concurrent non comparé"):`écart ${Math.round(trace.gapPoints)} point(s)`;
  return `<small><b>Diagnostic QA2 :</b> ${trace.severityLabel} • ${gap} • source ${trace.source}. <b>Suite :</b> ${trace.nextAction}.</small>`;
}
