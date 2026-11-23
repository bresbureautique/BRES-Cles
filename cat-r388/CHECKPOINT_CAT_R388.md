# BRES Clés — catalogue CAT-R388 (23 novembre 2026)

Audit **en lecture seule**, distinct du moteur V2.28. La V2.27 stable et GitHub `main` ne sont pas modifiés.

## Résultats vérifiés
- 5 103 références uniques, 12 champs, dix fragments canoniques intacts et identiques aux SHA-256 de CAT-R386.
- 164 fabricants non renseignés ; les 66 groupes et 70 paires historiques de collision OCR restent inchangés.
- Recherche indépendante des références séparées par **une erreur de transcription** : 19 882 paires par substitution, 4 368 par insertion/suppression, 326 par inversion adjacente, **24 576 paires au total**.
- 2 459 paires présentent des écarts de dimension d'au plus 1 mm dans les deux axes. Parmi elles, **170 paires avec au moins un fabricant manquant** ont été placées dans une liste de revue.
- Audit CAT-R388 : **29/29** vérifications réussies ; audit CAT-R387 relancé : **47/47** ; total sélectionné **76/76**.

**Précaution :** ressemblances textuelles et géométriques ne sont PAS des équivalences de clés. Aucune référence ni marque attribuée automatiquement.

## Sources et sauvegardes
- Script de reconstruction et d'audit complet : `audit/catalogue_cat_r388_typo_ambiguity_audit.py` ; SHA-256 `70a9687fffe5184727798dec270590332b1d7d4613ee3f2336f979a23f5c951a`.
- Liste de 170 paires générable de manière déterministe depuis les fragments canoniques ; CSV local : `CAT_R388_MANUAL_REVIEW_QUEUE.csv` ; SHA-256 `593d1ce73cfc6fcb4d23562e5f23f98a10e5775cfde65f7eab3db956939e1830`.
- ZIP catalogue intégral local `BRES_Cles_Catalogue_Audit_CAT_R388.zip` : **1 659 entrées**, CRC et manifeste SHA-256 vérifiés ; SHA-256 du ZIP `260c26583e6d110547c1108adac1559e57afa8f677053c3e8c795dd314c56135`.
- Tentative de dépôt dans `Library/BRES Cles/Sauvegardes` : **AccessDeny**. Ne pas déclarer une sauvegarde Library réussie.

Les photographies étalons réelles et l'OCR Tesseract totalement hors connexion restent à valider séparément.
