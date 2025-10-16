# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2025-01-XX

### Ajouté
- Interface web responsive avec support RTL pour l'arabe
- Support de traduction multilingue (FR, EN, AR)
- Processeur XML avec préservation stricte de la structure
- Client Ollama avec retries exponentiels et circuit breaker
- API REST avec FastAPI
- Logging structuré en JSON
- Métriques de performance (segments traduits, durée, échecs)
- Endpoint de healthcheck
- Tests unitaires et d'intégration
- Déploiement Docker avec docker-compose
- Documentation complète (README, API, QUICKSTART, ADVANCED)
- Scripts de démarrage automatique (start.sh, dev.sh)
- Makefile pour automatisation
- Script de monitoring (monitor.py)
- Fichier exemple XML SCENARI
- Support des variables d'environnement
- Configuration proxy HTTP/HTTPS
- Gestion des timeouts et batch size configurables
- Rapport de traduction détaillé en header HTTP

### Fonctionnalités
- ✅ Traduction de fichiers XML SCENARI
- ✅ Préservation des namespaces, attributs, commentaires
- ✅ Détection automatique des segments traduisibles
- ✅ Mise à jour automatique de xml:lang
- ✅ Aucune persistance (traitement en mémoire)
- ✅ Téléchargement direct du fichier traduit
- ✅ Interface intuitive en français
- ✅ Support complet de l'arabe (RTL)
- ✅ Validation des entrées
- ✅ Gestion des erreurs robuste

### Sécurité
- Validation stricte des types MIME
- Limitation de taille d'upload
- Utilisateur non-root dans Docker
- Pas de stockage persistant
- Validation des langues supportées

### Performance
- Circuit breaker pour éviter surcharge Ollama
- Batching configurable
- Retries avec backoff exponentiel
- Timeouts configurables
- Healthcheck intégré

## [Non publié]

### À venir
- Support de fichiers ZIP multiples
- Export du rapport en JSON/CSV
- Interface d'administration
- Authentification LDAP/SSO
- API REST documentée (Swagger)
- Cache de traductions (Redis)
- Support de plus de formats (DocBook, DITA)
- Métriques Prometheus
- Gestion de files d'attente (Celery)
- Mode asynchrone pour gros fichiers
- Notifications email de fin de traduction

### En cours d'étude
- Support de plus de langues
- Intégration avec d'autres LLM
- Mode de révision/correction
- Historique des traductions
- Comparaison de versions
- API de webhook
- Client CLI
- Plugin pour éditeurs SCENARI

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
