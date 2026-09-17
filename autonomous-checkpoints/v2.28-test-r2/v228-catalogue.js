/* BRES Clés V2.28 TEST R2 — recherche catalogue Silca massif (V3) */
(function(){
  const CHUNKS=Array.from({length:10},(_,i)=>`catalogue/v3/catalog-${String(i+1).padStart(2,'0')}.js?v=228`);
  let loadingPromise=null;
  function el2(id){return document.getElementById(id)}
  function loadScript(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=()=>reject(new Error('Chargement impossible : '+src));document.head.appendChild(s);});}

  function catalogueSigDistance(a,b){
    const x=(a&&a.sig)||a,y=(b&&b.sig)||b;if(!x||!y)return Infinity;
    const rr=(u,v)=>{u=u||[];v=v||[];const n=Math.min(u.length,v.length);if(!n)return 1;let z=0;for(let i=0;i<n;i++){const d=u[i]-v[i];z+=d*d}return Math.sqrt(z/n)};
    return Math.abs((x.width_mm||0)-(y.width_mm||0))/10+Math.abs((x.height_mm||0)-(y.height_mm||0))/10+Math.abs((x.area||0)-(y.area||0))+((rr(x.top,y.top)+rr(x.bot,y.bot))/2)+rr(x.colFill,y.colFill)+Math.abs((x.bladeFill||0)-(y.bladeFill||0))+Math.abs((x.headFill||0)-(y.headFill||0));
  }
  function ambiguousPilotPeers(canon){
    let base=null;try{base=catalogVisualEntry(canon)}catch(e){} if(!base)return [];
    const peers=[];for(const other of Object.keys(XREF||{})){if(other===canon)continue;let c=null;try{c=catalogVisualEntry(other)}catch(e){}if(c&&catalogueSigDistance(base,c)<.003)peers.push(other)}return peers;
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
        const canon=normalizeKnownRef(el('manualRef').value.trim());if(!canon||!currentSig)return;
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
  async function ensureCatalogue(status){
    if(window.BRES_CATALOG_V3 && window.BRES_CATALOG_V3.length>5000)return window.BRES_CATALOG_V3;
    if(loadingPromise)return loadingPromise;
    window.BRES_CATALOG_V3=window.BRES_CATALOG_V3||[];
    loadingPromise=(async()=>{
      for(let i=0;i<CHUNKS.length;i++){
        if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
        await loadScript(CHUNKS[i]);
      }
      return window.BRES_CATALOG_V3;
    })();
    return loadingPromise;
  }
  function rms(a,b){const n=Math.min((a||[]).length,(b||[]).length);if(!n)return 1;let s=0;for(let i=0;i<n;i++){const d=a[i]-b[i];s+=d*d}return Math.sqrt(s/n)}
  function sample2(a){return (a||[]).filter((_,i)=>i%2===0)}
  function reverseSig(r){return {t:[...r[6]].reverse(),o:[...r[7]].reverse(),c:[...r[8]].reverse()}}
  function mirrorVertical(r){return {t:r[7].map(x=>1-x),o:r[6].map(x=>1-x),c:r[8]}}
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
  function bestScore(sig,r){
    let best=null;for(const v of ['normal','h','v','hv']){const x=scoreOne(sig,r,v);if(!best||x.score>best.score)best=x;}return best;
  }
  function searchCatalogue(sig,db){
    const w=sig.width_mm||0,h=sig.height_mm||0;
    let arr=[];
    for(const r of db){
      if(r[11]<.45)continue;
      if(Math.abs(w-r[3])>10 || Math.abs(h-r[4])>12)continue;
      const m=bestScore(sig,r);
      arr.push({r,m});
    }
    arr.sort((a,b)=>b.m.score-a.m.score || b.r[11]-a.r[11]);
    return arr.slice(0,12);
  }
  function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function render(results,box){
    if(!results.length){box.className='status warn';box.innerHTML='<b>Aucun candidat catalogue suffisamment proche.</b>';return;}
    const top=results[0], second=results[1];
    const margin=second?top.m.score-second.m.score:99;
    const tied=results.filter(x=>(top.m.score-x.m.score)<=1);
    const extractionQuality=Number(top.r[11]||0);
    const strongSilhouette=top.m.score>=88 && margin>=8 && extractionQuality>=.70;
    let h=`<b>Catalogue Silca massif : ${window.BRES_CATALOG_V3.length} silhouettes chargées.</b><br>`;
    h+=`<b>Meilleur candidat catalogue : ${escapeHtml(top.r[0])} — ${top.m.score}%</b><br>`;
    if(top.r[1])h+=`Famille/marque : ${escapeHtml(top.r[1])}<br>`;
    h+=`Page Silca : ${escapeHtml(top.r[2])}<br>`;
    h+=`Qualité extraction catalogue : ${Math.round(extractionQuality*100)} %<br>`;
    if(tied.length>1){
      h+=`<b>Silhouette non discriminante :</b> ${tied.length} références sont à 1 point ou moins du meilleur score (${tied.slice(0,6).map(x=>escapeHtml(x.r[0])).join(', ')}${tied.length>6?'…':''}).<br>`;
    } else if(strongSilhouette) {
      h+=`<b>Silhouette nettement isolée</b>, mais elle ne valide jamais seule la référence : contrôle du marquage/profil requis.<br>`;
    } else {
      h+=`<b>Résultat à confirmer.</b> Écart entre les meilleurs candidats : ${margin} point(s).<br>`;
    }
    if(extractionQuality<.70)h+=`<b>Attention :</b> le dessin catalogue de ce candidat a une qualité d’extraction limitée ; il ne peut pas servir de preuve de validation.<br>`;
    h+='<br><b>Top candidats :</b>';
    results.slice(0,8).forEach((x,i)=>{h+=`<br>${i+1}. <b>${escapeHtml(x.r[0])}</b> — ${x.m.score}%${x.r[1]?` — ${escapeHtml(x.r[1])}`:''} — p.${escapeHtml(x.r[2])}`;});
    h+=`<br><br><small>La silhouette sert à présélectionner. Le profil catalogue reste un critère séparé et une forme ambiguë ne produit jamais de validation automatique.</small>`;
    box.className='status '+(strongSilhouette?'ok':'warn');box.innerHTML=h;
  }
  function addCard(){
    const cards=document.querySelectorAll('main .card'); if(!cards.length)return;
    const card=document.createElement('section');card.className='card';card.id='catalogueMassifCard';
    card.innerHTML=`<h2>2. Catalogue Silca massif — V2.28 TEST</h2><p class="small">Recherche automatique dans plus de 5 000 silhouettes extraites du Catalogue Silca 110. Cette recherche présélectionne des candidats mais ne remplace pas le contrôle du profil et du marquage.</p><button id="catalogueMassifBtn">🔎 Rechercher automatiquement dans le catalogue Silca</button><div id="catalogueMassifStatus" class="status">Analysez d’abord recto + verso, puis lancez la recherche catalogue.</div>`;
    cards[0].insertAdjacentElement('afterend',card);
    const btn=el2('catalogueMassifBtn'),status=el2('catalogueMassifStatus');
    btn.onclick=async()=>{
      if(!window.currentSig && typeof currentSig!=='undefined' && !currentSig){status.className='status bad';status.textContent='Analysez d’abord les deux photos recto + verso.';return;}
      const sig=(typeof currentSig!=='undefined')?currentSig:window.currentSig;
      if(!sig){status.className='status bad';status.textContent='Analysez d’abord les deux photos recto + verso.';return;}
      try{status.className='status warn';const db=await ensureCatalogue(status);status.textContent='Comparaison des silhouettes…';const res=searchCatalogue(sig,db);render(res,status);}catch(e){status.className='status bad';status.textContent='Catalogue massif indisponible : '+(e.message||e);}
    };
  }
  try{
    document.title='BRES Clés V2.28 TEST R2';
    const badge=document.querySelector('.app-version-badge');if(badge)badge.textContent='V2.28 TEST R2 • CATALOGUE SILCA MASSIF • STABLE CONSERVÉE';
    const hdr=document.querySelector('header p');if(hdr)hdr.textContent=hdr.textContent.replace(/V2\.2[5-7]/,'V2.28 TEST');
    installSafetyWrappers();
    addCard();
  }catch(e){console.warn('V2.28 test non initialisée',e)}
})();
