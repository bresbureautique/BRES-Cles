# BRES Clés — jalon V2.28 TEST R1

Ce jalon est isolé de la version stable. La branche `v2.28-test-r1` ne remplace pas `main` et ne déploie pas cette version de test à la place de la version utilisée sur le téléphone.

## Résultat vérifié

- 5 103 références Silca dans la base de recherche massive.
- 5 103 références uniques, aucun doublon.
- 10 blocs de catalogue.
- signatures dimensionnelles présentes pour les 5 103 entrées.
- contrôle de syntaxe JavaScript réussi pour `v228-catalogue.js` et les 10 blocs.
- garde-fous : une recherche silhouette forte reste un candidat tant qu'un critère discriminant (marquage, profil ou étalon local) n'est pas disponible.

## Sauvegarde exacte

Le ZIP complet est sauvegardé dans ChatGPT Library :

`/BRES Cles/Sauvegardes/BRES_Cles_Mobile_V2_28_TEST_R1.zip`

SHA-256 :

`645ed3c92896538392c6323032351080c1ac258e9802e3aaf67a2141bc03d299`

Le fichier `BUILD_MANIFEST.json` de ce dossier contient les SHA-256 des fichiers internes du paquet. Le fichier `v228-catalogue.js` contient le module ajouté pour la recherche catalogue massive et les garde-fous anti-faux-positif.
