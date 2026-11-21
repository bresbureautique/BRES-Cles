# BRES Clés V2.28 TEST — R386 — 21 novembre 2026

**V2.27 est l'unique version stable.** Ne jamais fusionner le test avec `main`.

## Correctif expérimental

Chaque fragment catalogue signale maintenant immédiatement un chargement incomplet, un doublon, un échange de fragment ou des colonnes manquantes, même si le navigateur déclenche `load`. Les contrôles vérifient pour chaque fragment le nombre de lignes, les première/dernière références, la forme 12 colonnes et l'identité du tableau global. Une erreur entraîne la purge du catalogue partiel et autorise une nouvelle tentative. La validation finale des 12 champs R371 reste indispensable : ces contrôles de transport ne sont PAS des empreintes cryptographiques par fragment.

Reconstruction reproductible de R385 avec `python r386_apply_fragment_guard.py`. SHA-256 V2.28 TEST R386 : `eaff91aa1784fb7cb6e845de42feb83c9dd4122338f8710275c445b2483f68bf`.

## Tests indépendants

- Chromium hors connexion R386 : **46/46** contrôles réussis, 11 scénarios de fragments défectueux, avec récupération de 5 103 références sans doublons.
- Adaptation sémantique de la suite R384 aux rejets anticipés R386 : **19/19**.
- Suites R385, R383, R382, R381 et R380 exécutées contre R386 : respectivement **16/16, 30/30, 68/68, 83/83 et 36/36**.
- La suite R384 **historique, non adaptée** présente 17/19 : deux attentes obsolètes (erreur seulement à la fin et 20 chargements au lieu de 19) sont invalidées par le rejet plus précoce de R386. L'adaptation R386 documente et vérifie les nouvelles attentes, sans dissimuler l'écart.
- Suite R377 non exécutée : l'archive R376 requise n'est pas disponible.

## Limites

Essais Chromium sans réseau, erreurs de scripts simulées, avec fragments canoniques exécutés dans un navigateur. Pas de certification OCR Tesseract en mode entièrement hors connexion ni de reconnaissance physique sur Samsung. Aucune modification des 5 103 références et aucune équivalence matérielle inventée. Ne pas promouvoir cette version en stable.
