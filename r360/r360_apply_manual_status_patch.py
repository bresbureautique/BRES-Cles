#!/usr/bin/env python3
"""R360 test-branch-only patch: invalidate manual lookup feedback immediately.

The final decision was already invalidated on edits, but the green `manualRefStatus`
continued displaying the previous successful lookup until the user clicked Verify.
This fixes *only* this stale user-visible feedback in the V2.28 test branch.
"""
from __future__ import annotations
from pathlib import Path
import difflib, hashlib
R=Path(__file__).resolve().parent
f=R/'index.html'
original=f.read_text(encoding='utf-8')
for target, text in (
    ('manualRef','Référence modifiée : ancienne correspondance annulée. Vérifiez à nouveau.'),
    ('manualBrand','Marque modifiée : ancienne correspondance annulée. Vérifiez à nouveau.'),
):
    old=(f'el("{target}").addEventListener("input",()=>{{\n'
         '  bumpIdentificationEpoch();')
    new=(f'el("{target}").addEventListener("input",()=>{{\n'
         '  // R360: cancel the previous green manual lookup feedback synchronously.\n'
         '  el("manualRefStatus").className="status warn";\n'
         f'  el("manualRefStatus").textContent="{text}";\n'
         '  bumpIdentificationEpoch();')
    if original.count(old)!=1:raise ValueError(f'R360 anchor mismatch for {target}')
    original=original.replace(old,new,1)
pre=f.read_text(encoding='utf-8')
if pre==original:raise ValueError('patch had no effect')
patch=''.join(difflib.unified_diff(pre.splitlines(keepends=True),original.splitlines(keepends=True),fromfile='a/index.html',tofile='b/index.html',n=5))
f.write_text(original,encoding='utf-8')
(R/'R359_TO_R360_MANUAL_STATUS.patch').write_text(patch,encoding='utf-8')
print({'new_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'patch_lines':len(patch.splitlines())})