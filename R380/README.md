# BRES Clés — V2.28 TEST R380 (15 novembre 2026)

**V2.27 est la seule stable. Ne jamais fusionner cette branche dans `main`.**

## Correction
Une nouvelle lecture OCR tête ou recto/verso principal, lorsque Tesseract est absent ou que son API `createWorker` est incomplète, laissait parfois affichés un ancien code OCR, son fabricant, une ancienne validation, un lien d'équivalence JMA et un diagnostic exportable. Le correctif R380 invalide ces résultats et les requêtes en cours, sans effacer les saisies **manuelles**. Aucun changement des décisions OCR quand Tesseract fonctionne, de la géométrie, des seuils ou de la base catalogue.

Source de départ R379 `index.html` SHA-256 : `1cc7a0f4c8cf9ce05b3b0734737a41a864191662e64168d4138e4d518f93cd9d`.

Source après patch R380 SHA-256 : `243aaf49c8b8c243ad464c8e44284565d2d4d4b1b2426a019fc53e1837793fa7`.

Patch reproductible : [R380_APPLY.diff](R380_APPLY.diff), empreinte Git `1ac8829d7eb56ca8acd914c58e3bfb1a0454086d`. `patch -p0` sur la source R379 reproduit exactement R380.

## Contrôles
Chromium hors réseau **36/36** (défaut reproduit sur R379 puis corrigé sur R380, champs OCR/manuels, diagnostic, résultats). Non-régression R377 sur source R380 **11/11** : 124 textes OCR synthétiques et 14 tentatives d'injection dans l'affichage. Audit indépendant CAT-R380 **15/15**.

Archive intégrale R380 (Library `/BRES Cles/Sauvegardes`) SHA-256 `038f9c55f98337c3b1b621d4822f8493b2c31d3368541b807dba7a4091bb15f2`, 9 000 entrées; CRC et 8 999 empreintes internes vérifiés avant dépôt.

**Limites :** les worker/WASM/données linguistiques Tesseract hors connexion ne sont pas embarqués et l'OCR à froid sans Internet reste non certifié. Les essais sont synthétiques, sans photo réelle du Samsung. Aucun reçu JSON benchmark R336 original.
