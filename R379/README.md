# BRES Clés — V2.28 TEST R379 — 14/11/2026

**V2.27 reste stable : ne jamais fusionner cette branche vers main.**

Protection des liens pilotes JMA et de l'affichage XREF (données texte non fiables) dans trois parcours : recherche d'équivalences, référence manuelle et résultat OCR tête. Le correctif modifie exclusivement l'affichage, sans changer les données du catalogue, la reconnaissance, les seuils ou la géométrie.

Base R378 index SHA-256: `a68f211e403b7b6047f1494af186004b6bdb1497a0edee12494d77bcc38c35d1`.
Source R379 index SHA-256: `1cc7a0f4c8cf9ce05b3b0734737a41a864191662e64168d4138e4d518f93cd9d`.
Diff `R379_APPLY.diff` : Git blob `d0ccf28edc9552812198a2e11b4380b68fe6c141`.

Tests effectifs : **20/20** Chromium hors réseau pour l'affichage/XREF et les URL, **10/10** régression OCR tête, **11/11** régression R377 (124 scénarios OCR synthétiques). Catalogue séparé **17/17** contrôles, **5 103** lignes intactes.

Archivage complet R379 : ZIP application SHA-256 `deea42145976459a5deb6b7d8f3e0a66381ac73c8b98a4e40bee2cef4a7f892b`, 8 991 entrées. Toutes les empreintes de fichiers internes vérifiées ; se reporter à la Library pour l'archive et les tests complets.

**Limites :** ni l'OCR à froid entièrement hors connexion, ni un essai réel de clé sur Samsung, ni le reçu benchmark R336 ne sont validés.
