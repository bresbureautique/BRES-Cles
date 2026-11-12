#!/usr/bin/env python3
"""Reproduce R377 from an untouched R376 app/index.html (never V2.27)."""
from pathlib import Path
import sys
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).with_name('index.html')
s=p.read_text(encoding='utf8')
assert 'function escapeOCRDisplayR377' not in s
s=s.replace('async function runOCR(){', '''// R377 TEST: OCR text and manually supplied labels are untrusted presentation data.
// Escape only values interpolated into preformatted status HTML, never the HTML
// layout or the original strings used by the interpreter. V2.27 untouched.
function escapeOCRDisplayR377(value){return escapeManualHtmlR357(value);}
function escapeOCRDisplayListR377(values,sep=", "){
  return (values||[]).map(escapeOCRDisplayR377).join(sep);
}
async function runOCR(){''', 1)
sub={
 '${a.text||"—"}':'${escapeOCRDisplayR377(a.text||"—")}',
 '${b.text||"—"}':'${escapeOCRDisplayR377(b.text||"—")}',
 '${a.mode}':'${escapeOCRDisplayR377(a.mode)}',
 '${b.mode}':'${escapeOCRDisplayR377(b.mode)}',
 '${r.text||"—"}':'${escapeOCRDisplayR377(r.text||"—")}',
 '${r.mode||""}':'${escapeOCRDisplayR377(r.mode||"")}',
 '${r.side}':'${escapeOCRDisplayR377(r.side)}',
 '${info.makers.join(", ")}':'${escapeOCRDisplayListR377(info.makers)}',
 '${info.candidates.join(", ")}':'${escapeOCRDisplayListR377(info.candidates)}',
 '${info.passMakerConsensus.join(", ")}':'${escapeOCRDisplayListR377(info.passMakerConsensus)}',
 '${info.conflictingCanons.join(" / ")}':'${escapeOCRDisplayListR377(info.conflictingCanons," / ")}',
 '${info.ambiguousCanons.join(" / ")}':'${escapeOCRDisplayListR377(info.ambiguousCanons," / ")}',
 '${info.catalogueGeometryResolution.ref}':'${escapeOCRDisplayR377(info.catalogueGeometryResolution.ref)}',
 '${faceReason}':'${escapeOCRDisplayR377(faceReason)}',
 '${info.best.canon}':'${escapeOCRDisplayR377(info.best.canon)}',
 '${el("manualRef").value.trim()}':'${escapeOCRDisplayR377(el("manualRef").value.trim())}',
 "${info.ocrCatalogueStatusR369||'inconnu'}":"${escapeOCRDisplayR377(info.ocrCatalogueStatusR369||'inconnu')}",
}
for a,b in [('async function runOCR(){','el("ocrBtn").onclick=runOCR;'),
            ('async function searchFromHeadPhotos(){','el("headSearchBtn").onclick=searchFromHeadPhotos;')]:
    start=s.index(a);end=s.index(b,start)
    fragment=s[start:end]
    for old,new in sub.items():fragment=fragment.replace(old,new)
    s=s[:start]+fragment+s[end:]
p.write_text(s,encoding='utf8')
