# BRES Clés — V2.28 TEST R381 — 2026-11-16

Stable V2.27 is strictly isolated and unchanged. R381 is experimental only.

- On an explicit main OCR attempt without published current geometry, or a head OCR attempt without a head photo, abort closed and invalidate stale OCR-derived reference, maker, result, proof, JMA link and diagnostic. Preserve manual typing.
- No Tesseract worker is started in these missing-input flows. This does not certify recognition offline or physical-key matches.
- Reconstruct from `index_R380_BASE.html` using `r381_apply_missing_input_guard.py`; `R381_APPLY.diff` records exactly the changes.
- Browser synthetic stale-state R381 regression: 83/83; R380 offline guard: 36/36; R377 display/124 OCR synthetic scenarios: 11/11.
- 5,103 canonical catalogue references and ten canonical fragments unchanged; catalogue audit separately in CAT-R381.

Pending: real Samsung photos, actual cold-offline Tesseract assets/worker/WASM/English model, original Samsung benchmark R336 JSON. Do not promote to stable.
