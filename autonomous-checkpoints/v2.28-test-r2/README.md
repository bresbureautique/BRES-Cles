# BRES Clés — jalon V2.28 TEST R2

Ce jalon reste isolé sur la branche `v2.28-test-r1` et ne remplace pas la version stable.

## Ce qui a été ajouté

- signalement explicite des silhouettes catalogue non discriminantes ;
- affichage de la qualité d'extraction du dessin catalogue ;
- interdiction de considérer une silhouette seule comme une validation certaine ;
- rapport de validation croisée du moteur de recherche.

## Résultat de la validation croisée

La base contient 5 103 références uniques. L'analyse a trouvé **1 053 groupes de signatures de silhouette exactement identiques**, représentant **2 444 références**. Cela confirme qu'une photo de silhouette seule ne peut pas, dans de nombreux cas, distinguer deux références proches ou recto/verso. Le moteur R2 affiche donc ces groupes comme `À CONFIRMER` et attend un critère discriminant : profil, marquage ou étalon local.

Sur un échantillon de 300 signatures catalogue exactes, la bonne référence est dans le Top 5 dans environ 98,7 % des cas ; le Top 1 est volontairement moins fiable à cause des silhouettes identiques. Cette mesure sert à sécuriser le comportement : le classement est une présélection, pas une validation.

## Sauvegarde exacte

Library : `/BRES Cles/Sauvegardes/BRES_Cles_Mobile_V2_28_TEST_R2.zip`

SHA-256 du ZIP :

`7f04f632efc7a10d69dc12abc3bb6b831b740bcc9a9300d3b51449ae2085b748`
