# Catalogue CAT-R370 : triage des étiquettes fabricant dans les risques OCR (2026-11-05)

Audit **indépendant de l'application**, calculé sur le registre de revue CAT-R363 (`snapshots/CAT-R363/CAT_R363_PAIR_REVIEW_LEDGER.csv`, Git blob `042b84ef1a44d3e28ef73ec6b1b76fd2e64b1957`). Les données sont des scénarios de confusion de texte et des étiquettes de fabricant **non vérifiées** : aucune équivalence mécanique ou identité de fabricant n'en découle.

Sur **393 paires théoriques** dans **345 groupes** (732 références concernées) :
- **68 paires OCR** : **61** comportent des étiquettes fabricant différentes, **1** une étiquette manquante, **6** une étiquette identique. Les **62 premières** forment une file spécifique de vérification **non automatique**.
- **325 paires de frappe** : **212** comportent des étiquettes différentes, **25** une étiquette manquante, **88** une étiquette identique.

Toutes les paires restent `UNVERIFIED_TEXT_ONLY` et `auto_validate=False`. Ce triage **ne classe pas les 6 paires OCR de même étiquette comme sûres** ; elles doivent également rester ambiguës jusqu'à validation physique. Aucune des 5 103 lignes canoniques ni aucun des dix fragments n'a été modifié.

Reproduction (dans ce dépôt, avec Node) : `node autonomous-checkpoints/catalogue-cat-r370/catalogue_r370_ocr_maker_triage.js` ; le résultat JSON de cet audit est conservé séparément. Les 7 invariants ont passé dans un moteur JS V8 lors de la préparation de ce jalon. Cela **ne teste pas** le moteur OCR réel, la photographie, l'algorithme géométrique ou le Samsung.

Il s'agit d'un jalon d'analyse sauvegardé dans une branche distincte, sans ZIP R370 ni promotion du moteur V2.28.
