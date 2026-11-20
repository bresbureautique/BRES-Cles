# BRES Clés V2.28 EXPERIMENTALE — R385 — 20 novembre 2026

**Version stable : V2.27 sur GitHub `main`. NE PAS FUSIONNER.**

## Application (expérimentale uniquement)

R385 introduit un délai maximal de 4 secondes par fragment de catalogue V3 dans le chargeur `v228-catalogue.js`. Si le navigateur n'émet ni `load` ni `error`, le chargement est rejeté, l'élément `<script>` est détaché, et le mécanisme de récupération R384 peut libérer les données partielles et retenter un chargement propre. Les événements tardifs sont ignorés. Les saisies manuelles sont préservées par le contrôle OCR R383. Les références et les fragments canoniques sont inchangés.

Reconstruction: `python r385_apply_chunk_timeout.py` à partir de `v228-catalogue_R384.js`, SHA-256 et `R385_APPLY.diff` vérifiés. `index.html` identique à R384.

## Tests

- R385 Chromium hors réseau (scripts canoniques réels exécutés dans Chromium, absence de réponse réseau simulée) : **16/16**. Scénarios de blocage sur le premier et le quatrième fragment, expiration, rejet, suppression du script, rechargement sans doublons et appels simultanés.
- Non-régressions Chromium : R384 **19/19**, R383 **30/30**, R382 **68/68**, R381 **83/83**, R380 **36/36**.
- R377 nécessite le ZIP R376 absent de l'environnement de cette exécution : **non réexécuté**, ne pas revendiquer ce test comme passé ici.
- Catalogue indépendant CAT-R385 **22/22**, appariement strict des collisions OCR de l'index runtime et du catalogue. CAT-R384 **68/68**, CAT-R383 **17/17**, CAT-R382 **23/23**.

## Limites

Le test porte sur des événements réseau simulés dans Chromium, sans OCR Tesseract intégral hors connexion, sans véritable photographie Samsung et sans reçu original R336. La suppression du script couvre la requête navigateur normale, pas une injection externe de code tardif. Aucune équivalence physique ni attribution de fabricant validée. Ne pas promouvoir en stable.
