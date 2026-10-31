#!/usr/bin/env python3
"""R365, strictly additive diagnostic provenance patch on R364 TEST (no OCR decisions)."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent/'index.html'
PARENT_SHA='f44156a51e3727f443ce19a3d4db2bd2cbe7c8a50bbb50fd79e5ebce482df0fd'
OLD="   const libraryPresent=!!(globalThis.Tesseract&&typeof globalThis.Tesseract.createWorker==='function');"
NEW="""   const libraryPresent=!!(globalThis.Tesseract&&typeof globalThis.Tesseract.createWorker==='function');
   // Read script *markup*, never probe the network or create a worker.
   // A local script tag is not evidence that worker/WASM/language data exist.
   const scriptTag=Array.from(document.scripts).find(function(el){
     const s=el.getAttribute('src')||'';
     return /(?:^|\\/)tesseract(?:\\.min)?\\.js(?:[?#]|$)/i.test(s);
   });
   const scriptRef=scriptTag?(scriptTag.getAttribute('src')||''):'';
   const originClass=/^https?:\\/\\//i.test(scriptRef)
     ? 'remote-cdn-not-embedded'
     : (scriptRef ? 'local-script-tag-unverified' : 'script-tag-absent');"""
FLAG="     scriptOriginClass:'remote-cdn-not-embedded',"
CHECKPOINT='<b>Checkpoint de travail : R364 (export diagnostic OCR local)</b>'

def patch(src):
    for a in (OLD,FLAG,CHECKPOINT):
        if src.count(a)!=1:raise ValueError('unexpected R364 parent for '+a[:50])
    return src.replace(OLD,NEW,1).replace(FLAG,'     scriptOriginClass:originClass,',1).replace(CHECKPOINT,'<b>Checkpoint de travail : R365 (provenance du diagnostic OCR)</b>',1)

def main():
    parent=P.read_text(encoding='utf-8')
    if hashlib.sha256(parent.encode('utf-8')).hexdigest()!=PARENT_SHA:
        raise RuntimeError('R365 expected exact R364 index, refusing destructive patch')
    out=patch(parent)
    P.write_text(out,encoding='utf-8')
    print('R365 patch ok',hashlib.sha256(P.read_bytes()).hexdigest())
if __name__=='__main__':main()