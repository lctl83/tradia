# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [2.1.0] - 2025-12-08

### Ajouté
- **Affichage progressif (Streaming)** : Les réponses de l'IA s'affichent maintenant en temps réel, token par token, comme sur ChatGPT ou Gemini
- Nouveaux endpoints streaming : `/translate-text-stream`, `/correct-text-stream`, `/reformulate-text-stream`, `/meeting-summary-stream`
- Fonction JavaScript `streamRequest()` pour gérer les flux SSE côté frontend
- Messages de progression adaptés pendant le streaming ("L'IA génère la traduction...")

### Modifié
- Le frontend utilise maintenant les endpoints streaming par défaut pour une meilleure UX
- Auto-scroll vers le bas pendant la génération progressivedu texte

## [2.0.0] - 2025-12-08

### Ajouté
- Correction orthographique avec explications détaillées
- Reformulation professionnelle avec points clés
- Génération de comptes rendus de réunion structurés
- Surlignage visuel des différences (diff) dans la correction
- Synchronisation des scrollbars entre panneaux
- Sélection dynamique du modèle Ollama

### Modifié
- Renommage du projet : DCIA → IA DCI / Tradia
- Renommage des services Docker : scenari-translator → tradia
- Interface utilisateur simplifiée et épurée
- Suppression des références SCENARI/XML

### Supprimé
- Fonctionnalité de traduction XML SCENARI
- Fichier exemple XML
- Module xml_processor.py

## [1.0.0] - 2025-01

### Ajouté
- Interface web responsive avec support RTL pour l'arabe
- Support de traduction multilingue (FR, EN, AR)
- Client Ollama avec retries exponentiels et circuit breaker
- API REST avec FastAPI
- Logging structuré en JSON
- Métriques de performance
- Endpoint de healthcheck
- Tests unitaires et d'intégration
- Déploiement Docker avec docker-compose
- Documentation complète (README, API, QUICKSTART, ADVANCED)
- Scripts de démarrage automatique (start.sh, dev.sh)
- Makefile pour automatisation
- Script de monitoring (monitor.py)
- Support des variables d'environnement
- Configuration proxy HTTP/HTTPS
- Gestion des timeouts configurables

### Fonctionnalités
- ✅ Traduction de texte brut
- ✅ Interface intuitive en français
- ✅ Support complet de l'arabe (RTL)
- ✅ Validation des entrées
- ✅ Gestion des erreurs robuste
- ✅ Aucune persistance (traitement en mémoire)

### Sécurité
- Utilisateur non-root dans Docker
- Pas de stockage persistant
- Validation des langues supportées

### Performance
- Circuit breaker pour éviter surcharge Ollama
- Retries avec backoff exponentiel
- Timeouts configurables
- Healthcheck intégré

## [Non publié]

### À venir
- Interface d'administration
- Authentification LDAP/SSO
- API REST documentée (Swagger)
- Cache de traductions (Redis)
- Métriques Prometheus

### En cours d'étude
- Support de plus de langues
- Intégration avec d'autres LLM
- Historique des traductions
- API de webhook
- Client CLI

---

## Convention de versioning

- **MAJOR** : Changements incompatibles de l'API
- **MINOR** : Ajout de fonctionnalités rétro-compatibles
- **PATCH** : Corrections de bugs rétro-compatibles

## Types de changements

- **Ajouté** : Nouvelles fonctionnalités
- **Modifié** : Changements dans des fonctionnalités existantes
- **Déprécié** : Fonctionnalités bientôt supprimées
- **Supprimé** : Fonctionnalités retirées
- **Corrigé** : Corrections de bugs
- **Sécurité** : Correctifs de vulnérabilités
