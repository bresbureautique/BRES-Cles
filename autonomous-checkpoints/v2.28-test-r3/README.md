# BRES Clés — V2.28 TEST R3

Checkpoint autonome séparé de la version stable V2.27.

## R3
- classement par groupes de silhouettes catalogue exactes plutôt que par références individuelles ;
- les références de forme strictement identique restent groupées et ne produisent plus de faux gagnant arbitraire ;
- indication du pouvoir discriminant du profil catalogue ;
- marque lue/saisie utilisée seulement comme préférence secondaire lorsque les scores géométriques sont à 3 points ou moins ;
- la silhouette seule reste toujours `À CONFIRMER` ;
- priorité aux étalons locaux conservée.

## Analyse catalogue
- 5 103 références avec silhouette ;
- 3 712 groupes de formes ;
- 1 053 groupes de collision, 2 444 références ;
- 1 051 groupes de collision entièrement séparables par profil (2 438 références sur 2 444) ;
- 1 groupe RONIS partiellement séparable ;
- VAC151 / VAC151SM (VACHETTE) non séparables avec les données actuelles.

La branche `main` reste la V2.27 stable et n'est pas modifiée par ce checkpoint.
