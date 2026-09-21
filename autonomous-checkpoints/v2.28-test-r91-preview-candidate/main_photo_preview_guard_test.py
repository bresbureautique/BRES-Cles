from pathlib import Path
import re, subprocess, tempfile, sys, json
ROOT=Path(__file__).resolve().parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
errors=[]
required=[
 'id="mainPhotoPreviewGrid"',
 'id="mainPhotoPreviewRecto"',
 'id="mainPhotoPreviewVerso"',
 'id="retakeRecto"',
 'id="retakeVerso"',
 'const mainPhotoPreviewUrls={recto:null,verso:null};',
 "function refreshMainPhotoPreview(side)",
 "function refreshMainPhotoPreviews()",
 "refreshMainPhotoPreviews();",
 "el('retakeRecto').onclick=()=>openGuidedCamera('recto');",
 "el('retakeVerso').onclick=()=>openGuidedCamera('verso');",
 'URL.createObjectURL(file)',
 'URL.revokeObjectURL(mainPhotoPreviewUrls[side])'
]
for marker in required:
    if marker not in html: errors.append('missing marker: '+marker)
m=re.search(r'function photoRefresh\(\)\{(.*?)\n\}',html,re.S)
if not m or 'refreshMainPhotoPreviews();' not in m.group(1): errors.append('photoRefresh does not refresh previews')
m=re.search(r'function refreshMainPhotoPreview\(side\)\{(.*?)\n\}',html,re.S)
if not m or 'getMainPhoto(side)' not in m.group(1): errors.append('preview does not use getMainPhoto(side)')
scripts=re.findall(r'<script(?: [^>]*)?>(.*?)</script>',html,flags=re.S)
inline='\n'.join(x for x in scripts if x.strip())
with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as f:
    f.write(inline); tmp=f.name
cp=subprocess.run(['node','--check',tmp],capture_output=True,text=True)
Path(tmp).unlink(missing_ok=True)
if cp.returncode: errors.append('inline javascript syntax: '+cp.stderr.strip())
report={'schema':'bres-main-photo-preview-guard-v1','source_revision':'V2.28 TEST R91','errors':errors,'ok':not errors}
(ROOT/'MAIN_PHOTO_PREVIEW_GUARD_CANDIDATE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MAIN PHOTO PREVIEW GUARD: '+('SELFTEST OK' if not errors else 'ECHEC'))
if errors:
    print('\n'.join('- '+e for e in errors))
sys.exit(1 if errors else 0)
