BRES CLÉS V2.28 TEST R4 — SAUVEGARDE RECONSTRUCTIBLE DU MODULE

Base : autonomous-checkpoints/v2.28-test-r3/v228-catalogue.js
Cible : v228-catalogue.js de V2.28 TEST R4
SHA-256 cible : 7cfe5a91dbace39f92d0f6ddd6a417ece36ee7f7746cd6f220b51ac9e1e8974d

Le patch exact R3 -> R4 est découpé en 3 fichiers afin de conserver une copie texte vérifiable dans GitHub :
- R3_to_R4_v228.patch.part00 — 6500 octets — Git blob f446dddf00f6bb7697eabd3b68ed8bb457da02b6 — SHA-256 9cf200cdea0ab3202d826abab643e8651bd5209b7296f9d35bb0e5fc00fc411b
- R3_to_R4_v228.patch.part01 — 6500 octets — Git blob 42176cc1811bfcb7517fef7b28f0b47c085fb075 — SHA-256 c40623ae855356476e218a91733ff69a2e452ff8ac87c4d72bf38c96ff18cc19
- R3_to_R4_v228.patch.part02 — 2557 octets — Git blob 76341358f7588218f292ad0a7bb721b6c6c0c637 — SHA-256 dc2cce63a449b0640903f0d95e5affc3dd0e47b67f6910dc5b776f0558abc464

SHA-256 du patch concaténé : f5c24db392df316d61fd7ec48bd51c0f7b3110aa2bc55ffcdafb483551a6ac32

Reconstruction :
cat R3_to_R4_v228.patch.part00 R3_to_R4_v228.patch.part01 R3_to_R4_v228.patch.part02 > R3_to_R4_v228.patch
patch v228-catalogue.js < R3_to_R4_v228.patch
sha256sum v228-catalogue.js

La sauvegarde complète (index, module, 10 morceaux catalogue, gabarit, rapports et vérificateur) est conservée dans la Library :
/BRES Cles/Sauvegardes/BRES_Cles_Mobile_V2_28_TEST_R4.zip
SHA-256 du ZIP : 1704415a1add32d276f7ce949dde463fca22dc1d8fcc35bbf9464079d3c06925

La branche main / V2.27 ne doit pas être modifiée par ce checkpoint.
