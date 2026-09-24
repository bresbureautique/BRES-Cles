// R158 : garde de collision catalogue issue de l'audit R158-QA2.
const CATALOGUE_QA2_CRITICAL_PAIRS=[
  {a:"AB2R",b:"CS6R",makers:"ABUS / CISA"},
  {a:"AAA1",b:"UL050",makers:"aaa / UNIVERSAL SERIE DISTINZIONE"},
  {a:"LF6R",b:"LF4",makers:"EURO LOCKS / LOWE & FLETCHER"},
  {a:"CS204",b:"CC3",makers:"CISA / CORNI"},
  {a:"STA9R",b:"DAL2R",makers:"STAR / DALWA"},
  {a:"MEG1R",b:"HOK1R",makers:"MEGA / HOK"}
];
const CATALOGUE_QA2_NEAR_ONLY_PAIRS=[
  {a:"FM2",b:"PC20",makers:"FASEM / P.C. (CORTELLEZZI)"},
  {a:"SOP10",b:"AB46",makers:"SOPRANO / ABUS"},
  {a:"YT15",b:"FI6",makers:"LOB / FIAM"},
  {a:"WA6R",b:"KLE5RX",makers:"WALLY / KALE"},
  {a:"DAL2R",b:"STA4R",makers:"DALWA / STAR"}
];
const CATALOGUE_QA2_NEAR_MARGIN_POINTS=8;
function catalogueQa2Partners(ref,kind="all"){
  const r=norm(ref), out=[];
  const add=(pairs,severity)=>pairs.forEach(pair=>{
    const a=norm(pair.a),b=norm(pair.b);
    if(r===a)out.push({ref:b,severity,pair});
    else if(r===b)out.push({ref:a,severity,pair});
  });
  if(kind!=="near")add(CATALOGUE_QA2_CRITICAL_PAIRS,"critical");
  if(kind!=="critical")add(CATALOGUE_QA2_NEAR_ONLY_PAIRS,"near");
  return out;
}
function catalogueQa2GeometryGuard(cand){
  if(!cand||!cand.length)return {ok:false,severity:"empty",reason:"Aucun étalon disponible."};
  const first=cand[0], critical=catalogueQa2Partners(first.ref,"critical");
  if(critical.length){
    const partners=critical.map(x=>x.ref);
    return {ok:false,severity:"critical",partners,reason:"Collision catalogue critique : preuve indépendante obligatoire."};
  }
  const near=catalogueQa2Partners(first.ref,"near");
  if(near.length){
    const nearRefs=new Set(near.map(x=>x.ref));
    const compared=cand.filter((c,i)=>i>0&&nearRefs.has(norm(c.ref))).sort((a,b)=>b.score-a.score);
    if(!compared.length)return {ok:false,severity:"near-uncompared",partners:[...nearRefs],reason:"Partenaire catalogue proche non comparé."};
    const partner=compared[0],gap=Number(first.score)-Number(partner.score);
    if(!Number.isFinite(gap)||gap<CATALOGUE_QA2_NEAR_MARGIN_POINTS)return {ok:false,severity:"near-gap",partners:[partner.ref],gap,reason:"Marge insuffisante entre candidats proches."};
    return {ok:true,severity:"near-separated",partners:[partner.ref],gap};
  }
  return {ok:true,severity:"none",partners:[]};
}
function catalogueQa2ManualNote(ref){
  const critical=catalogueQa2Partners(ref,"critical"),near=catalogueQa2Partners(ref,"near");
  const all=[...critical,...near];
  if(!all.length)return "";
  const partners=[...new Set(all.map(x=>x.ref))];
  const severity=critical.length?"critique":"proche";
  return "Collision catalogue "+severity+" QA2 avec "+partners.join(" / ")+" : la forme seule ne suffit pas. La référence saisie/lue constitue ici le signal indépendant qui tranche.";
}
