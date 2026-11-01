#!/usr/bin/env python3
"""R366: conservative URI classification in read-only OCR diagnostic, TEST only.
Does not change the engine, OCR rule, schema, catalogue, or stable build.
"""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent/'index.html'
PARENT_SHA='d96713286ec99d4717c25aa209bb307f4fa2107d1842d3f5f7e42b5bd154d4ae'
OLD=r"""   const scriptRef=scriptTag?(scriptTag.getAttribute('src')||''):'';
   const originClass=/^https?:\/\//i.test(scriptRef)
     ? 'remote-cdn-not-embedded'
     : (scriptRef ? 'local-script-tag-unverified' : 'script-tag-absent');"""
NEW=r"""   // URI classification is deliberately conservative: even a relative tag
   // cannot demonstrate that any worker/WASM/language asset is available.
   const scriptRef=scriptTag?(scriptTag.getAttribute('src')||'').trim():'';
   const originClass=/^(?:https?:)?\/\//i.test(scriptRef)
     ? 'remote-cdn-not-embedded'
     : (/^[a-z][a-z0-9+.-]*:/i.test(scriptRef)
       ? 'explicit-scheme-not-certifiable'
       : (scriptRef ? 'local-script-tag-unverified' : 'script-tag-absent'));"""
OLD_LABEL='<b>Checkpoint de travail : R365 (provenance du diagnostic OCR)</b>'
NEW_LABEL='<b>Checkpoint de travail : R366 (diagnostic OCR conservateur)</b>'

def patch(src):
    assert src.count(OLD)==1, 'R365 origin block not unique'
    assert src.count(OLD_LABEL)==1, 'R365 label absent or duplicated'
    return src.replace(OLD,NEW,1).replace(OLD_LABEL,NEW_LABEL,1)

def main():
    original=P.read_bytes()
    if hashlib.sha256(original).hexdigest()!=PARENT_SHA:
        raise SystemExit('R366 REFUSED: exact R365 parent index hash mismatch')
    patched=patch(original.decode('utf-8'))
    P.write_text(patched,encoding='utf-8')
    print('R366 app index sha256:',hashlib.sha256(P.read_bytes()).hexdigest())
if __name__=='__main__': main()