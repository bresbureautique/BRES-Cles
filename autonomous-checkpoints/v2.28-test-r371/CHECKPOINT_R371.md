# BRES Clés V2.28 TEST R371 — 6 novembre 2026

**V2.27 / main reste l'unique version stable. Ne pas fusionner.**

Parent: archive R369, index SHA-256 `R371_FULL_ROW_CHROMIUM.json: parent_index_sha256` (archivée dans le ZIP). Le prototype isolé R370 n'avait pas de valeur attendue fiable pour les champs 5 à 11; la version R371 utilise les empreintes attendues calculées depuis les 10 fragments canoniques (5103 lignes, chacune avec 12 champs, dont 3 profils de 24 valeurs). Ces signatures 32 bits ne sont pas cryptographiques.

Insertion dans **index.html V2.28 TEST uniquement**, avant `function ocrLossyGlyphGroupsR367`. Dans `interpretOCR`, après `const catalogueInventoryR369=ocrCatalogueInventoryR369();` :

```js
const catalogueAllFieldsR371=catalogueInventoryR369.ok
  ?ocrCatalogueAllFieldsR371():{ok:false,reason:catalogueInventoryR369.reason};
const ocrCatalogueReadyR368=catalogueInventoryR369.ok&&catalogueAllFieldsR371.ok;
const ocrCatalogueStatusR369=ocrCatalogueReadyR368?'expected-inventory':catalogueAllFieldsR371.reason;
```

Ces trois lignes remplacent les deux précédentes d'affectation `ocrCatalogueReadyR368` et `ocrCatalogueStatusR369`. Le libellé d'erreur précise « inventaire complet ». Le patch exact, les sources Python, les manifestes et l'index intégral figurent dans le ZIP R371 (SHA-256 `4d7924dd23f2d263a1eafbb7c536f4a11e449bdbec6e47d5063a9f5180e1c75f`).

**Contrôles exécutés :** 13/13 essais Chromium hors réseau, 12 altérations/rétablissements, 64 chaînes théoriquement ambiguës sans présélection, décisions de l'échantillon comparées à R369, absence d'erreurs JS, 17/17 vérifications indépendantes. Un vrai OCR, le hors-ligne froid et l'identification photographique sur Samsung ne sont **pas** certifiés.

Les 10 fragments canoniques, R331, R336 et la règle OCR R305 sont identiques au parent R369. GitHub sauvegarde le code et la preuve. L'archive intégrale est fournie comme artefact conversation; son écriture dans Library n'a pas pu être effectuée (AccessDeny).
