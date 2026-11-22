# BRES Clés V2.28 TEST — R387 — 22 novembre 2026

V2.27 est l'unique version stable : `main` ne doit pas être modifiée.

Le chargement des fragments contrôle désormais immédiatement les douze champs,
à l'aide de deux empreintes 32 bits indépendantes par fragment canonique.
Une altération interne ne nécessite plus d'attendre le dixième fragment :
rejet immédiat, purge des données partielles et nouvelle tentative sans doublons.
Le contrôle complet R371 reste obligatoire. Les empreintes sont des détecteurs
de corruption accidentelle, **pas des signatures cryptographiques**.

Tests hors réseau Chromium R387 : 63/63 (20 corruptions simulées couvrant 10 fragments).
Ancienne suite R386 adaptée à la nouvelle détection anticipée : 46/46.
Autres suites R384 adaptée : 19/19, R385 : 16/16, R383 : 30/30,
R382 : 68/68, R381 : 83/83, R380 : 36/36. Ensemble 361/361.
Les suites historiques R384 non adaptée et R377 ne sont pas revendiquées.

SHA-256 du JS complet : 10e28efc474ef78f5dbd54d815f84fa5f1c2d7615dd489c273f40dc5d6e68f62
Catalogue immuable : 5 103 références, 12 champs, 10 fragments.
Limites : Tesseract totalement hors ligne et Samsung réel non certifiés ; reçu R336 absent.
