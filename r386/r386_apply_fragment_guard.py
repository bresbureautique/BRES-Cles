#!/usr/bin/env python3
"""Reproducible R385 -> R386 experimental change; stable V2.27 is untouched."""
from pathlib import Path
import difflib,hashlib
A=Path(__file__).resolve().parent
old=(A/'v228-catalogue_R385.js').read_text('utf8')
needle='''        for(let i=0;i<CHUNKS.length;i++){
          if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
          await loadScript(CHUNKS[i]);
        }
'''
replacement='''        // R386 TEST: fail immediately if a script reports "load" without the
        // expected canonical fragment (empty, repeated, swapped, malformed or
        // a replacement array). This is a transport guard, NOT key recognition.
        // The R371 all-fields digest remains the final integrity authority.
        const fragmentShapeR386=[
          [511,'TRF1','ZOL1'],[511,'TRF2','ZO1'],[511,'TRF1R','MTK2P'],
          [510,'TRF3','CA12'],[510,'TRF3R','CA7'],[510,'TRF4','CA10'],
          [510,'TRF6R','CA11'],[510,'TRF5R','CA11R'],
          [510,'TRM1R','CA10R'],[510,'TRM2','ZH1R']
        ];
        for(let i=0;i<CHUNKS.length;i++){
          if(status)status.textContent=`Chargement catalogue Silca ${i+1}/${CHUNKS.length}…`;
          const before=window.BRES_CATALOG_V3, start=before.length;
          await loadScript(CHUNKS[i]);
          const db=window.BRES_CATALOG_V3;
          const [count,first,last]=fragmentShapeR386[i];
          if(db!==before || !Array.isArray(db) || db.length!==start+count ||
             db[start]?.[0]!==first || db[db.length-1]?.[0]!==last ||
             !db.slice(start).every(row=>Array.isArray(row)&&row.length===12))
            throw new Error(`Fragment catalogue non conforme : ${CHUNKS[i]}`);
        }
'''
assert old.count(needle)==1, f'Expected loader signature, found {old.count(needle)}'
new=old.replace(needle,replacement,1)
(A/'v228-catalogue.js').write_text(new,'utf8')
(A/'v228-catalogue_R386.js').write_text(new,'utf8')
(A/'R386_APPLY.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='v228-catalogue_R385.js',tofile='v228-catalogue_R386.js')),'utf8')
print('R385 SHA256',hashlib.sha256(old.encode()).hexdigest())
print('R386 SHA256',hashlib.sha256(new.encode()).hexdigest())
