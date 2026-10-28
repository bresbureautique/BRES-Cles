#!/usr/bin/env python3
"""Add a Samsung-friendly, self-contained R336 benchmark download to V2.28 test.

Safe replay: only the benchmark launcher in index.html changes. The V2.27 stable
build, OCR rule, catalogue data and original R336 benchmark are untouched.
"""
from __future__ import annotations
import base64, hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
PARENT_INDEX_SHA='af6433b071e3ec45e3e67267381b1092b6941169d6051c7cc11af2416f067a51'
OLD='<div class="status warn" id="deviceBenchmarkR336Link"><b>Diagnostic R336 — benchmark Samsung avec contrôle de chronologie et empreinte du moteur (sans influence sur l’identification).</b><br><a class="btn alt" href="device_benchmark_r336.html">Ouvrir le benchmark Samsung R336</a></div>'
NEW='<div class="status warn" id="deviceBenchmarkR336Link"><b>Diagnostic R336 — benchmark Samsung (sans effet sur l’identification).</b><br><a class="btn alt" id="r362BenchmarkStandaloneDownload" href="#" role="button">Télécharger le benchmark Samsung R336 autonome</a><p class="small" id="r362BenchmarkHelp">Sur Samsung : dans Mes fichiers &gt; Téléchargements, ouvrez ensuite <b>BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html</b> avec Chrome. Le lien vers un fichier voisin ne fonctionne pas toujours depuis content://.</p></div>'
OLD_TRACE='<div id="checkpointTrace" class="status ok"><b>Checkpoint de travail : R319</b> — moteur V2.28 TEST R156 conservé ; V2.27 reste la version stable. Tous les exports utilisateur portent maintenant le checkpoint R319 ; les données conservent V2.28 TEST R156 comme version moteur.</div>'
NEW_TRACE='<div id="checkpointTrace" class="status ok"><b>Checkpoint de travail : R362 (outil Samsung)</b> — moteur V2.28 TEST R156 conservé ; V2.27 reste la version stable. La sortie du benchmark R336 est désormais autonome. Les exports métier historiques conservent leur provenance R319 (moteur R156).</div>'
OLD_TAIL='<script src="v228-catalogue.js?v=228r156"></script></body></html>'

def standalone():
    html=(R/'device_benchmark_r336.html').read_text(encoding='utf-8')
    js=(R/'r331-device-benchmark.js').read_text(encoding='utf-8')
    marker='<script src="r331-device-benchmark.js"></script>'
    if html.count(marker)!=1:raise ValueError('Unexpected R336 script ref count')
    return html.replace(marker,'<script>\n'+js+'\n</script>',1).encode('utf-8')

def launcher(payload_base64):
    # Binary base64 representation preserves non-ASCII text exactly.
    return ('''<script id="r362-benchmark-payload" type="application/octet-stream">'''+payload_base64+'''</script>
<script>
/* R362: generate a self-contained R336 diagnostic file without resolving sibling paths.
   Deliberately download, not iframe/open content://: Android Chrome refuses that route. */
(function(){
 const btn=document.getElementById('r362BenchmarkStandaloneDownload');
 const help=document.getElementById('r362BenchmarkHelp');
 const encoded=document.getElementById('r362-benchmark-payload');
 if(!btn||!help||!encoded)return;
 btn.addEventListener('click',function(event){
   event.preventDefault();
   try{
     const binary=atob(encoded.textContent.trim());
     const bytes=new Uint8Array(binary.length);
     for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
     const blob=new Blob([bytes],{type:'text/html;charset=utf-8'});
     const url=URL.createObjectURL(blob);
     const download=document.createElement('a');
     download.href=url;
     download.download='BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html';
     document.body.appendChild(download);
     download.click();
     download.remove();
     setTimeout(()=>URL.revokeObjectURL(url),30000);
     help.textContent='Fichier autonome téléchargé. Ouvrez Mes fichiers > Téléchargements, puis ouvrez le fichier HTML avec Chrome. La V2.27 stable n’a pas été touchée.';
   }catch(e){
     help.textContent='Téléchargement impossible depuis cette application : ouvrez le fichier autonome fourni séparément. '+(e.message||e);
   }
 });
})();
</script>''')

def patch(contents):
    if contents.count(OLD)!=1 or contents.count(OLD_TAIL)!=1 or contents.count(OLD_TRACE)!=1:raise ValueError('Expected R361 source not found')
    standalone_bytes=standalone()
    (R/'BRES_Cles_Benchmark_Samsung_R336_AUTONOME.html').write_bytes(standalone_bytes)
    changed=contents.replace(OLD,NEW,1).replace(OLD_TRACE,NEW_TRACE,1)
    changed=changed.replace(OLD_TAIL,OLD_TAIL.replace('</body>',launcher(base64.b64encode(standalone_bytes).decode('ascii'))+'</body>'),1)
    return changed

def run():
    path=R/'index.html'
    original=path.read_text(encoding='utf-8')
    actual=hashlib.sha256(original.encode('utf-8')).hexdigest()
    if actual!=PARENT_INDEX_SHA:raise RuntimeError(f'Parent R361 mismatch: {actual}')
    result=patch(original)
    path.write_text(result,encoding='utf-8')
    print('R362 patch OK; standalone bytes:',len(standalone()),'index bytes:',len(result.encode('utf-8')))
if __name__=='__main__':run()