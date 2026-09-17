/* BRES Clés V2.27 — validation par étalon local et détection des conflits */
(function(){
  const LOCAL_STRONG_MIN=88;
  const LOCAL_MARGIN_MIN=8;

  function localTemplateDecision(canon){
    let cand=[];
    try{cand=(currentSig&&typeof match==='function')?(match(currentSig)||[]):[];}catch(e){cand=[];}
    if(!cand.length)return {state:'none'};
    const first=cand[0], second=cand[1]||null;
    if((first.score||0)<LOCAL_STRONG_MIN)return {state:'weak',first,second};
    if(second && ((first.score||0)-(second.score||0))<LOCAL_MARGIN_MIN)
      return {state:'ambiguous',first,second};
    return {state:first.ref===canon?'same':'conflict',first,second};
  }

  function appendLocalInfo(decision){
    const cv=el('catalogVisual');
    if(!cv||!decision||!decision.first)return;
    if(decision.state==='same'){
      cv.innerHTML+=`<br><b>V2.27 — étalon local :</b> la clé photographiée correspond fortement à l’étalon <b>${decision.first.ref}</b> (${decision.first.score} %).`;
    }else if(decision.state==='conflict'){
      cv.innerHTML+=`<br><b>V2.27 — conflit étalon :</b> la clé photographiée ressemble fortement à l’étalon <b>${decision.first.ref}</b> (${decision.first.score} %), différent de la référence saisie.`;
    }
  }

  try{
    document.title='BRES Clés V2.27';
    const badge=document.querySelector('.app-version-badge');
    if(badge)badge.textContent='V2.27 • APPLICATION COMPLETE • AUTOFOCUS • ÉTALON LOCAL';
    const hdr=document.querySelector('header p');
    if(hdr)hdr.textContent=hdr.textContent.replace('V2.26','V2.27');
    const testBox=document.querySelector('main .card .status.ok');
    if(testBox){
      testBox.innerHTML=testBox.innerHTML
        .replace('V2.26 — contrôle anti-faux positif actif.','V2.27 — contrôle par étalon local actif.')
        .replace('V2.25 — test réel de l’application complète.','V2.27 — contrôle par étalon local actif.');
    }
    const camVer=document.querySelector('.cam-version');
    if(camVer)camVer.textContent='V2.27 • APPLICATION';
    const camTop=document.querySelector('.cam-top');
    if(camTop)camTop.innerHTML=camTop.innerHTML.replace('V2.25','V2.27').replace('V2.26','V2.27');
    const cards=document.querySelectorAll('main .card');
    if(cards[2]){
      const h2=cards[2].querySelector('h2');
      if(h2)h2.textContent='3. Base étalon — apprentissage local V2.27';
      const p=cards[2].querySelector('.small');
      if(p)p.innerHTML='Enregistrez ici une clé dont la référence est certaine. <b>La V2.27 utilisera ensuite cet étalon pour confirmer la même référence ou signaler un conflit avec une référence saisie différente.</b>';
    }
  }catch(e){}

  const previousVerify=verifyManualReference;
  verifyManualReference=function(auto=false){
    previousVerify(auto);
    try{
      const typed=el('manualRef').value.trim();
      const canon=normalizeKnownRef(typed);
      if(!canon||!currentSig)return;
      const local=localTemplateDecision(canon);
      appendLocalInfo(local);

      const fd=el('finalDecision');
      if(local.state==='same'){
        fd.className='status ok';
        fd.innerHTML=`<b>VALIDÉ PAR ÉTALON LOCAL : ${canon}</b><br>La clé photographiée correspond fortement à votre étalon enregistré (${local.first.score} %). Le catalogue 2D peut rester non discriminant, mais l’étalon local confirme cette référence.`;
      }else if(local.state==='conflict'){
        fd.className='status bad';
        fd.innerHTML=`<b>CONFLIT ÉTALON LOCAL</b><br>Référence saisie : <b>${canon}</b>.<br>La clé photographiée correspond fortement à l’étalon <b>${local.first.ref}</b> (${local.first.score} %). <b>${canon} n’est donc pas validée.</b> Contrôlez le marquage, le profil ou la référence de l’étalon avant toute utilisation.`;
      }else if(local.state==='ambiguous'){
        fd.className='status warn';
        fd.innerHTML+=`<br><b>Étalo ns locaux ambigus :</b> ${local.first.ref} ${local.first.score} % / ${local.second.ref} ${local.second.score} %. Aucun étalon ne départage suffisamment.`.replace('Étalo ns','Étalons');
      }
    }catch(e){
      console.warn('Correctif V2.27 non appliqué',e);
    }
  };
})();