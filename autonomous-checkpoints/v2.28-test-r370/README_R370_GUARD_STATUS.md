# BRES Clés V2.28 – R370, prototype garde-fou colonnes 5+ (2026-11-05)

**État : prototype autonome testé sur données synthétiques, NON intégré à V2.28. Ne pas promouvoir, distribuer ou fusionner.**

La garde R369 vérifie les 5 premières colonnes de 5 103 lignes. Une mutation d'un champ supplémentaire peut donc échapper à sa double empreinte 32 bits. Ce jalon prépare une garde additionnelle couvrant toutes les colonnes et rejetant les trous de tableaux ou valeurs non finies. Les contrôles passent sur 10 cas synthétiques dans un moteur JavaScript V8 local à l'orchestrateur.

Commande de non-régression reproductible lorsque Node est disponible : `node autonomous-checkpoints/v2.28-test-r370/test_full_row_guard_r370.js`.

Limites importantes : le premier instantané complet est mémorisé **après** la validation de R369 ; il ne prouve pas l'authenticité des colonnes supplémentaires **avant** cette capture. Les deux empreintes ne sont pas cryptographiques. Le catalogue réel, l'interpréteur OCR, Chromium et le Samsung n'ont pas été testés à ce jalon. Intégration en attente de contrôle des types réels dans les 10 fragments canoniques et d'une empreinte complète issue d'une source fiable. Les versions V2.27 et V2.28 R369 restent intactes.

Ressources : `full_row_guard_r370.js` et `test_full_row_guard_r370.js`. Aucun ZIP R370 n'a été créé : dépôt GitHub uniquement.
