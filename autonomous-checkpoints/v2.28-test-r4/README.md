# BRES Clés — V2.28 TEST R4

Checkpoint autonome séparé de la V2.27 stable.

## Changements
- La recherche Silca massive se lance automatiquement après l'analyse recto/verso.
- Les profils catalogue 16×8 sont affichés pour les références d'un groupe de silhouette ambigu.
- Une photo optionnelle du bout de la clé peut être comparée expérimentalement aux profils des candidats.
- Le comparateur applique un seuil strict et ne produit jamais de validation finale à lui seul.

## Contrôles
- 5 103 références uniques.
- 3 712 groupes de silhouettes.
- 1 053 groupes en collision, 2 444 références concernées.
- 1 051 groupes entièrement séparables par la signature de profil catalogue.
- `node --check` OK et `verify_build.py` OK.
- ZIP complet testé sans erreur et sauvegardé dans la Library.

## Sécurité
`main` reste sur la V2.27 au commit `9a5ea3c256e05a4049d568c9afc6d03e2c0eb1c8`.
