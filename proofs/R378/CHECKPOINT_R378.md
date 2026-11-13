# BRES Clés V2.28 TEST — R378 — 13/11/2026

**Stable V2.27 intégralement préservée** : aucune fusion vers GitHub `main` ni changement de la V2.27. R378 est expérimental.

Échappement HTML *uniquement à l’affichage* des sorties « photos de tête » : référence probable, fiches correspondantes, noms de fabricants et candidats de la recherche par marque. Les URL JMA ne génèrent un lien que si elles commencent par HTTPS, avec protection `noopener noreferrer`. Le moteur d’identification, les comparateurs, les données canoniques et les fonctions OCR ne sont pas modifiés.

Preuves locales : script reproductible `r378_apply_head_result_escape.py` appliqué à `index_R377_BASE.html` ; résultat **identique octet par octet** à `index.html`. Tests Chromium réel hors réseau **10/10** sur branches avec contenu HTML synthétique trompeur, contrôle des URL, intégrité du catalogue (5 103 références). Suite R377 complète rejouée sur le code R378 : **11/11**, dont 124 décisions OCR synthétiques sans régression.

**Ce jalon ne certifie pas** l’OCR à froid entièrement hors connexion, ni les performances Samsung, ni une référence physique. Le reçu JSON original du benchmark R336 manque encore.