# BRES Clés V2.28 TEST — R384 (19 novembre 2026)

**Unique stable version: V2.27, branch `main` unchanged.** This folder is an experimental V2.28 snapshot reconstructed from R383. There is no merge to stable.

## Application change

The catalogue loading helper in `v228-catalogue.js` now recovers from transient script errors and rejects partial, duplicated or corrupted V3 inventory. A failed load clears its partial rows and its cached rejected promise; the next user action can retry all 10 fragments cleanly. Concurrent requests share the same load. Full 12-field integrity remains guarded by the fixed expected R371 inventory; it does not authenticate a manufacturer's reference or prove physical key compatibility.

Rebuild from R383: `python r384_apply_catalogue_retry.py` with `v228-catalogue_R383.js` present. `R384_APPLY.diff` reproduces the exact change. `index.html` and canonical V3 catalogue fragments are unchanged.

## Verified tests

- R384 real Chromium JavaScript engine, simulated script network failures: **19/19** checks passed. Includes failed fourth chunk, content-short ninth chunk, fresh retry, simultaneous callers, recovery after full-array mutation, and fail-closed when inventory verifier is missing.
- Chromium non-regressions: R383 **30/30**, R382 **68/68**, R381 **83/83**, R380 **36/36**. These use mocked OCR, not real Samsung photos.
- CAT-R384 independent fragment integrity: **68/68**; 39 mutation/omission/duplication/reordering cases detected across 10 fragments.
- CAT-R383 OCR reconstruction: **17/17**; CAT-R382 integrity regression: **23/23**.

## Still unverified

Cold-offline Tesseract worker/WebAssembly/language data, actual physical photographs on Samsung, and original R336 JSON evidence. Do not promote to stable. No real manufacturer attribution or physical equivalence inferred.