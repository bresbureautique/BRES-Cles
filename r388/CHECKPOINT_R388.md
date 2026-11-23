# BRES Clés V2.28 TEST — R388 (23 novembre 2026)

**V2.27 reste l'unique version stable** : GitHub `main` est à `9a5ea3c256e05a4049d568c9afc6d03e2c0eb1c8`, sans fusion depuis les branches de test.

## Travail réalisé
- **Jalon de non-régression, pas de changement du moteur applicatif** : `v228-catalogue.js` est inchangé par rapport à R387, SHA-256 `10e28efc474ef78f5dbd54d815f84fa5f1c2d7615dd489c273f40dc5d6e68f62`.
- Nouvelle suite Chromium offline `tests/r388_catalogue_concurrency_chromium.py` : 42/42 vérifications réussies. Défaut réseau simulé sur chaque fragment 01–10, purge des données, trois relances simultanées sans doublon, catalogue déjà chargé volontairement altéré puis réinitialisé et reconstruit.
- Suite R387 relancée sur les mêmes sources : 63/63 réussies. **Total sélectionné : 105/105**.
- Sources canoniques : dix fragments et 5 103 références inchangés.

## Preuves locales vérifiées
- ZIP application complet : `BRES_Cles_Mobile_V2_28_CHECKPOINT_R388.zip`, 9 073 entrées ; CRC et manifeste SHA-256 contrôlés ; SHA-256 du ZIP : `238d1922ffd28a60618cdc43c3e20b2af418268b1a1a6fab36fa5fc8151416eb`.
- Empreinte SHA-256 de la suite de test : `b43c508978db6f0df4e8d6e5b6ac06246b66dfe3aec2636ba59469c4c808c126`.
- Les photos de vraies clés sur Samsung et l'OCR Tesseract intégralement hors connexion ne sont pas certifiés.

## Sauvegardes
- Cette branche GitHub conserve le script de test et le présent reçu, sans toucher à `main`.
- Upload des deux ZIP et du rapport dans `Library/BRES Cles/Sauvegardes` **tenté, refusé (AccessDeny)** ; aucune sauvegarde Library revendiquée. L'archive locale reste vérifiée.
