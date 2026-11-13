#!/usr/bin/env python3
"""R378 isolated, reproducible display-only patch over R377 index.html.
No catalogue record, OCR ranking, or decision predicate is changed.
Usage: python r378_apply_head_result_escape.py INPUT_R377_INDEX OUTPUT_R378_INDEX
"""
from pathlib import Path
import sys,hashlib
src=Path(sys.argv[1]);out=Path(sys.argv[2]);s=src.read_text('utf8')
begin=s.index('async function searchFromHeadPhotos(){')
end=s.index('el("headSearchBtn").onclick=searchFromHeadPhotos;',begin)
a,section,z=s[:begin],s[begin:end],s[end:]
rep={
'${canon} (${Math.round(info.best.sim*100)} %)':'${escapeOCRDisplayR377(canon)} (${Math.round(info.best.sim*100)} %)',
'`<b>Référence catalogue probable : ${canon}</b><br>`':'`<b>Référence catalogue probable : ${escapeOCRDisplayR377(canon)}</b><br>`',
'`Pour : ${x.Pour}<br>`':'`Pour : ${escapeOCRDisplayR377(x.Pour)}<br>`',
'`<span class="pill"><b>${k}</b> ${v}</span>`':'`<span class="pill"><b>${escapeOCRDisplayR377(k)}</b> ${escapeOCRDisplayR377(v)}</span>`',
'if(x.JMA_URL) cat+=`<br><a class="btn alt" href="${x.JMA_URL}" target="_blank">Ouvrir la fiche JMA</a>`;':
 r'if(x.JMA_URL && /^https:\/\//i.test(String(x.JMA_URL))) cat+=`<br><a class="btn alt" href="${escapeOCRDisplayR377(x.JMA_URL)}" target="_blank" rel="noopener noreferrer">Ouvrir la fiche JMA</a>`;',
'`<b>VALIDÉ : ${canon}</b><br>':'`<b>VALIDÉ : ${escapeOCRDisplayR377(canon)}</b><br>',
'`<b>À VÉRIFIER</b><br>Les photos de tête indiquent ${canon}, mais la géométrie préfère ${top.ref}':'`<b>À VÉRIFIER</b><br>Les photos de tête indiquent ${escapeOCRDisplayR377(canon)}, mais la géométrie préfère ${escapeOCRDisplayR377(top.ref)}',
'`<b>À CONFIRMER : ${canon}</b><br>':'`<b>À CONFIRMER : ${escapeOCRDisplayR377(canon)}</b><br>',
'`<b>CANDIDAT PAR MARQUAGE : ${canon}</b><br>':'`<b>CANDIDAT PAR MARQUAGE : ${escapeOCRDisplayR377(canon)}</b><br>',
'${maker}. La forme réduit la recherche à ${strongBrand.map(c=>`${c.canon} (${c.score} %)`).join(" / ")}':
 '${escapeOCRDisplayR377(maker)}. La forme réduit la recherche à ${strongBrand.map(c=>`${escapeOCRDisplayR377(c.canon)} (${c.score} %)`).join(" / ")}',
'${strongBrand.map(c=>`${c.canon} → ${c.silca}`).join(" ; ")}':
 '${strongBrand.map(c=>`${escapeOCRDisplayR377(c.canon)} → ${escapeOCRDisplayR377(c.silca)}`).join(" ; ")}',
'${strongBrand.map(c=>c.canon).join(" / ")} : aucune validation automatique.':
 '${escapeOCRDisplayListR377(strongBrand.map(c=>c.canon)," / ")} : aucune validation automatique.',
'${maker}. La forme est seulement indicative':'${escapeOCRDisplayR377(maker)}. La forme est seulement indicative',
'${preview}${brandCandidates.length>6?" …":""}':'${escapeOCRDisplayR377(preview)}${brandCandidates.length>6?" …":""}',
'${brandCandidates.length} référence(s) ${maker}.':'${brandCandidates.length} référence(s) ${escapeOCRDisplayR377(maker)}.'
}
for old,new in rep.items():
 count=section.count(old)
 if count not in (1,2):
  raise RuntimeError(f'Expected 1 or 2 occurrences, got {count}: {old[:100]}')
 section=section.replace(old,new)
# Catalog data display protection applies only in the OCR head-photo flow;
# canonical storage, scoring and automatic decision logic must not change.
assert 'function escapeOCRDisplayR377' in s
new=a+section+z
out.write_text(new,'utf8')
print({'substitutions':len(rep),'changed_index_sha256':hashlib.sha256(new.encode()).hexdigest(), 'original_sha256':hashlib.sha256(s.encode()).hexdigest()})