/* BRES Clés V2.26 — garde-fou anti faux positif catalogue */
(function(){
  function sigDistance(a,b){
    const x=(a&&a.sig)||a, y=(b&&b.sig)||b;
    if(!x||!y)return Infinity;
    const rms=(u,v)=>{
      u=u||[];v=v||[];const n=Math.min(u.length,v.length);if(!n)return 1;
      let s=0;for(let i=0;i<n;i++){const d=u[i]-v[i];s+=d*d;}return Math.sqrt(s/n);
    };
    const contour=(rms(x.top,y.top)+rms(x.bot,y.bot))/2;
    const columns=rms(x.colFill,y.colFill);
    const dims=Math.abs((x.width_mm||0)-(y.width_mm||0))/10+Math.abs((x.height_mm||0)-(y.height_mm||0))/10;
    const area=Math.abs((x.area||0)-(y.area||0));
    const blade=Math.abs((x.bladeFill||0)-(y.bladeFill||0));
    const head=Math.abs((x.headFill||0)-(y.headFill||0));
    return dims+area+contour+columns+blade+head;
  }

  function ambiguousPeers(canon){
    let base=null;
    try{base=catalogVisualEntry(canon);}catch(e){return [];}
    if(!base)return [];
    const peers=[];
    for(const other of Object.keys(XREF||{})){
      if(other===canon)continue;
      let c=null;try{c=catalogVisualEntry(other);}catch(e){}
      if(c && sigDistance(base,c)<0.003)peers.push(other);
    }
    return peers;
  }

  // Repère visuel immédiat pour savoir que le correctif est chargé.
  try{
    document.title='BRES Clés V2.26';
    const badge=document.querySelector('.app-version-badge');
    if(badge)badge.textContent='V2.26 • APPLICATION COMPLETE • AUTOFOCUS • ANTI-FAUX-POSITIF';
    const hdr=document.querySelector('header p');
    if(hdr)hdr.textContent=hdr.textContent.replace('V2.25','V2.26');
    const testBox=document.querySelector('main .card .status.ok');
    if(testBox)testBox.innerHTML=testBox.innerHTML.replace('V2.25 — test réel de l’application complète.','V2.26 — contrôle anti-faux positif actif.');
  }catch(e){}

  // On conserve le moteur V2.25 mais on interdit VALIDÉ lorsque deux références
  // partagent pratiquement la même signature catalogue 2D (ex. TE8I/TE8D actuellement).
  const previousVerify=verifyManualReference;
  verifyManualReference=function(auto=false){
    previousVerify(auto);
    try{
      const typed=el('manualRef').value.trim();
      const canon=normalizeKnownRef(typed);
      if(!canon||!currentSig)return;
      const peers=ambiguousPeers(canon);
      if(!peers.length)return;
      const cat=catalogVisualEntry(canon);
      const check=cat?catalogVisualScore(currentSig,cat):null;
      if(!check)return;

      const cv=el('catalogVisual');
      if(cv){
        cv.className='status warn';
        cv.innerHTML+=`<br><b>V2.26 — contrôle non discriminant :</b> l’index actuel partage pratiquement la même signature 2D avec <b>${peers.join(', ')}</b>. Le score de silhouette ne peut donc pas, à lui seul, départager ces références.`;
      }

      if(check.score>=68){
        const fd=el('finalDecision');
        fd.className='status warn';
        fd.innerHTML=`<b>À CONFIRMER : ${canon}</b><br>Silhouette générale cohérente (${check.score} %), mais cette forme 2D est aussi compatible avec ${peers.join(', ')}. <b>Aucune validation automatique n’est autorisée tant qu’un détail discriminant (marquage fiable, profil/rainures ou étalon distinct) n’est pas disponible.</b>`;
      }
    }catch(e){
      console.warn('Correctif V2.26 non appliqué',e);
    }
  };
})();
