# BRES Clés — V2.28 TEST R383 — 2026-11-18

V2.27 demeure seule version stable. Aucun fichier de la branche GitHub `main` n'a été modifié.

- Correction du blocage des traitements OCR quand le chargement asynchrone du catalogue ne se termine jamais : attente bornée à **3 secondes** pour les parcours principaux et photos de tête. L'ancien résultat reste invalidé dès le départ et aucune requête périmée ne reprend la main.
- Un chargement absent, échoué ou lent affiche un avertissement et l'OCR peut continuer. La validation de référence automatique exige toujours les contrôles de catalogue déjà présents ; une absence de catalogue complet ne constitue jamais une validation.
- Les rejets tardifs d'une promesse de chargement sont absorbés. Les saisies manuelles ne sont pas effacées.
- Reconstitution reproductible `python3 r383_apply_catalogue_timeout.py` depuis la base expérimentale `index_R382.html` ; `R383_APPLY.diff` conservé.
- Tests Chromium hors réseau R383 : **30/30** ; non-régression R382 **68/68**, R381 **83/83**, R380 **36/36**, R377 **11/11** incluant 124 scénarios synthétiques.
- L'intégrité de 5 103 références sur dix fragments canonisés est vérifiée. Aucun changement de données catalogue.

**Limites :** les tests n'exécutent pas Tesseract réel, aucune reconnaissance physique Samsung, OCR entièrement autonome sans connexion non certifié, reçu R336 absent.
