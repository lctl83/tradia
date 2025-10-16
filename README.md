# SCENARI Translator

Application web pour traduire des fichiers XML SCENARI via Ollama avec support multilingue (FR, EN, AR).

## 🎯 Fonctionnalités

- ✅ **Traduction XML SCENARI** : Préservation stricte de la structure, namespaces et attributs
- ✅ **Support multilingue** : Français, Anglais, Arabe (avec RTL)
- ✅ **Interface web moderne** : Simple, responsive et intuitive
- ✅ **Robustesse** : Retries exponentiels, circuit-breaker, timeouts
- ✅ **Observabilité** : Logs structurés JSON, métriques, healthcheck
- ✅ **Déploiement facile** : Docker Compose prêt à l'emploi
- ✅ **Sans stockage** : Traitement en mémoire, aucune persistance

## 📋 Prérequis

- Docker et Docker Compose
- Ollama installé et accessible (par défaut sur `http://localhost:11434`)
- Un modèle Ollama installé (ex: `llama3.2:latest`)

### Vérification d'Ollama

```bash
# Vérifier qu'Ollama est bien accessible
curl http://localhost:11434/api/tags

# Si Ollama n'est pas installé, installez-le :
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger un modèle
ollama pull llama3.2:latest
```

## 🚀 Installation et déploiement

### Déploiement rapide avec Docker Compose

1. **Cloner ou télécharger le projet** :
```bash
cd scenari-translator
```

2. **Configurer les variables d'environnement** (optionnel) :
```bash
cp .env.example .env
# Éditer .env selon vos besoins
```

3. **Construire et démarrer l'application** :
```bash
docker-compose up -d --build
```

4. **Vérifier le déploiement** :
```bash
# Vérifier les logs
docker-compose logs -f

# Tester le healthcheck
curl http://localhost:8000/healthz
```

5. **Accéder à l'application** :
Ouvrir votre navigateur à : **http://localhost:8000**

### Déploiement sur un serveur distant

Si vous déployez sur un serveur différent de celui hébergeant Ollama :

1. **Modifier l'URL d'Ollama dans docker-compose.yml** :
```yaml
environment:
  - OLLAMA_BASE_URL=http://IP_SERVEUR_OLLAMA:11434
```

2. **Ou utiliser un fichier .env** :
```bash
echo "OLLAMA_BASE_URL=http://IP_SERVEUR_OLLAMA:11434" > .env
```

### Déploiement derrière un proxy

Si votre infrastructure nécessite un proxy :

```bash
# Dans votre fichier .env
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

## 🔧 Configuration

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL du service Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modèle par défaut |
| `OLLAMA_TIMEOUT` | `120` | Timeout en secondes |
| `OLLAMA_MAX_RETRIES` | `3` | Nombre de retries |
| `MAX_UPLOAD_MB` | `50` | Taille max fichier (MB) |
| `BATCH_SIZE` | `10` | Taille des lots de traduction |
| `LOG_LEVEL` | `INFO` | Niveau de log |
| `DEBUG` | `false` | Mode debug |

### Personnalisation du modèle

Vous pouvez utiliser différents modèles Ollama :

```bash
# Installer d'autres modèles
ollama pull mistral
ollama pull codellama

# Utiliser dans l'interface ou modifier la config
OLLAMA_MODEL=mistral
```

## 📖 Utilisation

### Via l'interface web

1. Sélectionner la **langue source** (FR/EN/AR)
2. Sélectionner la **langue cible** (FR/EN/AR)
3. Choisir le **modèle Ollama** (optionnel)
4. **Téléverser le fichier XML** SCENARI
5. Cliquer sur **"Traduire le fichier"**
6. **Télécharger le résultat** une fois la traduction terminée

### Format de sortie

Les fichiers traduits suivent ce format de nom :
```
{nom_original}.{source}-{cible}.{hash}.xml
```

Exemple : `document.fr-en.a3b5c7d9.xml`

## 🔍 Observabilité

### Healthcheck

```bash
curl http://localhost:8000/healthz
```

Réponse :
```json
{
  "status": "healthy",
  "ollama_available": true,
  "ollama_url": "http://localhost:11434"
}
```

### Métriques

```bash
curl http://localhost:8000/metrics
```

Réponse :
```json
{
  "total_translations": 42,
  "total_segments_translated": 1250,
  "total_segments_failed": 3,
  "average_duration": 45.2
}
```

### Logs

Les logs sont structurés en JSON pour faciliter l'analyse :

```bash
# Voir les logs en temps réel
docker-compose logs -f scenari-translator

# Filtrer par niveau
docker-compose logs scenari-translator | grep ERROR
```

## 🧪 Tests

### Exécuter les tests

```bash
# Dans le conteneur
docker-compose exec scenari-translator pytest

# Avec coverage
docker-compose exec scenari-translator pytest --cov=app --cov-report=html

# Tests spécifiques
docker-compose exec scenari-translator pytest tests/test_xml_processor.py -v
```

### Tests locaux (sans Docker)

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer les tests
pytest
```

## 🛠️ Maintenance

### Mise à jour de l'application

```bash
# Arrêter l'application
docker-compose down

# Mettre à jour le code
git pull  # si vous utilisez git

# Reconstruire et redémarrer
docker-compose up -d --build
```

### Vérifier l'état

```bash
# État des conteneurs
docker-compose ps

# Utilisation des ressources
docker stats scenari-translator

# Espace disque
docker system df
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs
docker-compose down

# Supprimer les volumes (si créés)
docker-compose down -v

# Nettoyer les images inutilisées
docker image prune -a
```

## 🐛 Dépannage

### Ollama n'est pas accessible

```bash
# Vérifier qu'Ollama est démarré
systemctl status ollama

# Redémarrer Ollama
systemctl restart ollama

# Tester la connexion
curl http://localhost:11434/api/tags
```

### L'application ne démarre pas

```bash
# Vérifier les logs
docker-compose logs scenari-translator

# Vérifier la configuration
docker-compose config

# Reconstruire depuis zéro
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Erreur de traduction

1. Vérifier les logs pour identifier le segment problématique
2. Vérifier que le modèle Ollama est bien chargé : `ollama list`
3. Tester manuellement la traduction avec Ollama
4. Vérifier la taille du fichier (< 50MB par défaut)

### Performance lente

1. Augmenter les ressources Docker :
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

2. Réduire la taille des lots :
```bash
BATCH_SIZE=5
```

3. Utiliser un modèle plus petit/rapide

## 📊 Architecture technique

### Stack technologique

- **Backend** : FastAPI + Uvicorn
- **XML** : lxml (préservation stricte)
- **HTTP** : httpx (avec retries)
- **Templating** : Jinja2
- **Tests** : pytest
- **Conteneurisation** : Docker

### Flux de traduction

```
1. Upload XML → Validation MIME type et taille
2. Parsing XML → lxml avec préservation complète
3. Extraction → Segments traduisibles (sc:para, sc:title, etc.)
4. Traduction → Ollama avec retries exponentiels
5. Réinjection → Mise à jour des nœuds + xml:lang
6. Génération → XML avec structure préservée
7. Download → Fichier .xml avec rapport en header
```

### Caractéristiques du processeur XML

- ✅ Préserve tous les namespaces
- ✅ Préserve les commentaires et PI
- ✅ Préserve l'ordre des attributs
- ✅ Ne touche pas aux éléments code/math/ref
- ✅ Ignore les éléments vides
- ✅ Génère des XPath uniques pour chaque segment

### Robustesse du client Ollama

- ✅ Retries exponentiels (backoff 2^n)
- ✅ Circuit breaker (arrêt après 5 échecs)
- ✅ Timeout configurable
- ✅ Support proxy
- ✅ Logs structurés par segment

## 📝 Licence

Ce projet est développé pour un usage interne DSI.

## 🤝 Support

Pour toute question ou problème :
1. Consulter cette documentation
2. Vérifier les logs : `docker-compose logs`
3. Tester le healthcheck : `curl http://localhost:8000/healthz`
4. Contacter l'équipe infrastructure DSI

## 🔄 Roadmap

- [ ] Support de fichiers ZIP multiples
- [ ] Export du rapport en JSON/CSV
- [ ] Interface d'administration
- [ ] Authentification LDAP/SSO
- [ ] API REST documentée (Swagger)
- [ ] Traductions en cache (Redis)
- [ ] Support de plus de formats (DocBook, DITA)

---

**Version** : 1.0.0  
**Dernière mise à jour** : 2025-01-XX  
**Responsable** : Infrastructure DSI
