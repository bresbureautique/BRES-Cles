# BRES Clés — V2.28 TEST R382 — 2026-11-17

V2.27 remains the only stable release. This is an experimental branch; never merge into `main` without explicit approval and real-device validation.

- Race fixed in **both** main and head OCR: a new request now invalidates previous automatic OCR fields, published decision, catalogue visual/link, and diagnostic **before** awaiting the asynchronous catalogue. Manual typed values remain untouched. Missing input / missing API fail immediately before the catalogue wait.
- After the await, an out-of-date request is prevented from continuing and reclaiming the OCR epoch.
- Rebuild exactly with `r382_apply_catalogue_wait_guard.py` using `index_R381_BASE.html`; patch `R382_APPLY.diff` records the change. `index_R382.html` matches production test `index.html`.
- Real Chromium, offline, delayed catalogue mocked: R382 **68/68** assertions passed, including 14 synthetic evidence mutation scenarios of the separate catalogue audit and browser old/new race reproductions. Legacy browser R381 **83/83**, R380 **36/36**, R377 **11/11** (124 synthetic OCR scenarios). [Catalogue independently certified by CAT-R382 checks.]
- Not tested: real Tesseract recognition offline, actual Samsung key photos or original benchmark receipt R336.