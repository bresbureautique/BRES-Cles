# BRES Clés V2.28 TEST R372 — 2026-11-07

Parent : R371. Seul le fichier existant `index.html` est modifié. V2.27 stable sur `main` : commit `9a5ea3c256e05a4049d568c9afc6d03e2c0eb1c8` — à ne jamais modifier avec un test.

Correctif : traitement conservateur des confusions théoriques G/6 et Z/2, en plus d'O/0, I/L/1, S/5 et B/8. Dans le catalogue de 5 103 références, **2 paires supplémentaires** (TO22/TOZ2 et TO26/TOZ6) doivent désormais conduire à une revue manuelle au lieu d'une présélection OCR.

Test exécuté en Chromium réel, hors réseau, avec les dix fragments canoniques : **13/13 contrôles réussis** ; 64 anciens textes synthétiques maintenus, 120 références non ambiguës comparées sans changement de décision, trois corruptions/restaurations bloquées puis résolues. Aucune photographie, aucun test physique Samsung ni Tesseract OCR froid.

Source intégrale : `BRES_Cles_Mobile_V2_28_CHECKPOINT_R372.zip` (archive conversation), SHA-256 `b0026476be1417a72fe9de6120ebd5aa7e8f8871b21a7ea48c1561b044f95c83`, 8 934 fichiers, manifeste interne SHA-256 vérifié, intégrité ZIP/CRC vérifiée. Index patché SHA-256 `eb7052eabde13fa0fc482d327d110cd59bb313c6c8378cda38d20977370eb716`. Script de test SHA-256 `8d6efb62779317b2f286ab115a564375fb8eacb0fe3e98b26b9ec40d31381eff`.

La sauvegarde GitHub est limitée à ce correctif textuel et à ces preuves ; le ZIP intégral n'a pas été envoyé sur GitHub. Le dépôt Library a échoué (AccessDeny). Aucune identification physique n'est certifiée.
