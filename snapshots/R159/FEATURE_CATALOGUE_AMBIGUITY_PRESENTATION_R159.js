// R159 : présentation explicite des collisions QA2 sans modifier la logique catalogue.
function catalogueQa2AmbiguityView(cand,guard){
  if(!guard||guard.ok||!["critical","near-uncompared","near-gap"].includes(guard.severity)||!cand?.length)return null;
  const first=cand[0], partnerRefs=[...new Set((guard.partners||[]).map(norm).filter(Boolean))];
  const refs=[norm(first.ref),...partnerRefs.filter(r=>r!==norm(first.ref))];
  const rows=refs.map((ref,index)=>{
    const candidate=(cand||[]).find(c=>norm(c?.ref)===ref)||null;
    return {ref,score:candidate&&Number.isFinite(Number(candidate.score))?Number(candidate.score):null,rank:candidate?(cand.indexOf(candidate)+1):null,role:index===0?"candidat principal":"référence à départager"};
  });
  const severityLabel=guard.severity==="critical"?"collision critique":"collision proche";
  return {severity:guard.severity,severityLabel,refs,rows,title:`À DÉPARTAGER : ${refs.join(" / ")}`};
}
function renderCatalogueQa2Ambiguity(cand,guard){
  const view=catalogueQa2AmbiguityView(cand,guard); if(!view)return "";
  const rows=view.rows.map(r=>`<div class="candidate"><b>${r.ref}</b>${r.score===null?" — non comparé dans les étalons locaux":` — ${Math.round(r.score)} %`}</div>`).join("");
  const why=view.severity==="critical" ? "La forme seule ne peut pas choisir entre ces références, même avec un score élevé." : view.severity==="near-uncompared" ? "La référence concurrente doit être comparée avant qu'un candidat unique puisse être retenu." : "Les scores sont trop proches pour retenir une seule référence.";
  return `<div class="status warn"><b>${view.title}</b><br>${why}${rows}<small><b>Pour trancher :</b> lire le marquage de la tête recto/verso, saisir la référence si elle est certaine, ou faire un contrôle physique discriminant.</small></div>`;
}
