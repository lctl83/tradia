# IA DCI

Suite d'assistants linguistiques internes DCI pour traduire, corriger, reformuler et résumer vos contenus grâce aux modèles Ollama.

## 🎯 Fonctionnalités

- ✅ **Traduction instantanée** : Texte source à texte cible (FR/EN/AR) avec synchronisation des zones de saisie
- ✅ **Correction orthographique** : Texte corrigé prêt à copier, avec explications des modifications
- ✅ **Reformulation** : Reformulation professionnelle avec points clés mis en évidence
- ✅ **Compte rendu** : Génération de résumés de réunion structurés (résumé, décisions, actions)
- ✅ **Support multilingue** : Français, Anglais, Arabe (avec gestion RTL)
- ✅ **Interface web moderne** : Simple, responsive et intuitive
- ✅ **Robustesse** : Retries exponentiels, circuit-breaker, timeouts
- ✅ **Observabilité** : Logs structurés JSON, métriques, healthcheck
- ✅ **Déploiement facile** : Docker Compose prêt à l'emploi
- ✅ **Sans stockage** : Traitement en mémoire, aucune persistance

## 📋 Prérequis

- Docker et Docker Compose
- Un serveur IA Ollama accessible (sur un serveur distant ou local)
- Un modèle Ollama installé (ex: `mistral-small3.2:latest`)

> [!NOTE]
> L'application et le serveur IA Ollama peuvent être déployés sur des serveurs **distincts**. Cette séparation permet une meilleure allocation des ressources (GPU pour l'IA, CPU classique pour l'application).

## 🚀 Installation et déploiement

### Déploiement rapide avec Docker Compose

1. **Cloner ou télécharger le projet** :

```bash
cd tradia
```

1. **Configurer les variables d'environnement** (optionnel) :

```bash
cp .env.example .env
# Éditer .env selon vos besoins
```

1. **Construire et démarrer l'application** :

```bash
docker compose up -d --build
```

1. **Vérifier le déploiement** :

```bash
# Vérifier les logs
docker compose logs -f

# Tester le healthcheck (via Traefik)
curl -k https://localhost/healthz
```

1. **Accéder à l'application** :
Ouvrir votre navigateur à : **<https://localhost>**

Traefik gère la terminaison TLS sur le port 443 et redirige automatiquement le trafic HTTP (port 80) vers HTTPS.

Les certificats TLS attendus par Traefik sont montés depuis l'hôte :

- Dossier hôte : `/etc/ssl/tradia`
- Fichiers requis : `tradia.cer` et `tradia.key`

Ces fichiers sont exposés dans le conteneur Traefik sous `/etc/traefik/certs`, conformément au `docker compose.yml`.

### Architecture recommandée : Application et IA sur serveurs distincts

Pour une utilisation en production, il est recommandé de déployer l'application et le serveur IA Ollama sur des serveurs séparés :

```
┌─────────────────────┐         HTTPS/API Key          ┌─────────────────────┐
│   Serveur Applicatif│ ◄───────────────────────────► │    Serveur IA       │
│   (Tradia + Traefik)│                                │ (Ollama + Traefik)  │
└─────────────────────┘                                └─────────────────────┘
```

#### 1. Déployer le serveur IA (sur le serveur avec GPU)

```bash
# Sur le serveur IA
docker compose -f docker-compose.ai.yml up -d
```

Ce fichier déploie :

- **Ollama** : serveur de modèles IA
- **Traefik** : reverse proxy avec terminaison HTTPS et authentification par API Key

#### 2. Configurer le serveur applicatif

```bash
# Dans votre fichier .env sur le serveur applicatif
OLLAMA_BASE_URL=https://IP_SERVEUR_IA
OLLAMA_API_KEY=votre_cle_api_secrete
```

Ou directement dans `docker-compose.yml` :

```yaml
environment:
  - OLLAMA_BASE_URL=https://IP_SERVEUR_IA
  - OLLAMA_API_KEY=votre_cle_api_secrete
```

> [!IMPORTANT]
> Le serveur IA est protégé par une API Key. Assurez-vous que la même clé est configurée côté serveur IA (`docker-compose.ai.yml`) et côté application.

### Déploiement derrière un proxy

Si votre infrastructure nécessite un proxy :

```bash
# Dans votre fichier .env
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

### Installation et vérification d'Ollama (sur le serveur IA)

```bash
# Vérifier qu'Ollama est bien accessible
curl http://localhost:11434/api/tags

# Si Ollama n'est pas installé, installez-le :
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger un modèle
ollama pull mistral-small3.2:latest

# Vérifier les modèles disponibles
ollama list
```

## 🔧 Configuration

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL du service Ollama (distant ou local) |
| `OLLAMA_API_KEY` | - | Clé API pour authentification au serveur IA |
| `OLLAMA_MODEL` | `mistral-small3.2:latest` | Modèle par défaut |
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

1. Choisir le **modèle Ollama** (Mistral Small par défaut).
2. Sélectionner l'onglet correspondant à votre besoin :
   - 📝 Traduction : choisissez les langues source/cible puis collez votre texte.
   - ✅ Correction : collez votre texte pour obtenir la version corrigée et les explications.
   - ♻️ Reformulation : collez votre texte pour une reformulation professionnelle.
   - 🗂️ Compte rendu : collez vos notes de réunion pour générer un résumé structuré.
3. Cliquez sur le bouton de l'onglet pour lancer l'analyse.
4. Copiez le résultat ou téléchargez les éléments utiles (résumé, décisions, actions).

Les zones de texte de la traduction sont synchronisées pour faciliter la comparaison entre l'original et le résultat.

## 🔍 Observabilité

### Healthcheck

```bash
curl -k https://localhost/healthz
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
curl -k https://localhost/metrics
```

Réponse :

```json
{
  "text_translations": 10,
  "corrections": 5,
  "reformulations": 3,
  "meeting_summaries": 2
}
```

### Logs

Les logs sont structurés en JSON pour faciliter l'analyse :

```bash
# Voir les logs en temps réel
docker compose logs -f tradia

# Filtrer par niveau
docker compose logs tradia | grep ERROR
```

## 🧪 Tests

### Exécuter les tests

```bash
# Dans le conteneur
docker compose exec tradia pytest

# Avec coverage
docker compose exec tradia pytest --cov=app --cov-report=html

# Tests spécifiques
docker compose exec tradia pytest tests/ -v
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
docker compose down

# Mettre à jour le code
git pull  # si vous utilisez git

# Reconstruire et redémarrer
docker compose up -d --build
```

### Vérifier l'état

```bash
# État des conteneurs
docker compose ps

# Utilisation des ressources
docker stats tradia

# Espace disque
docker system df
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs
docker compose down

# Supprimer les volumes (si créés)
docker compose down -v

# Nettoyer les images inutilisées
docker image prune -a
```

## 🐛 Dépannage

### Ollama n'est pas accessible

**Si Ollama est sur le même serveur :**

```bash
# Vérifier qu'Ollama est démarré
systemctl status ollama

# Redémarrer Ollama
systemctl restart ollama

# Tester la connexion
curl http://localhost:11434/api/tags
```

**Si Ollama est sur un serveur distant :**

```bash
# Vérifier la connectivité HTTPS
curl -k https://IP_SERVEUR_IA/api/tags \
  -H "Authorization: Bearer VOTRE_API_KEY"

# Vérifier les logs du conteneur IA
docker compose -f docker-compose.ai.yml logs -f
```

### L'application ne démarre pas

```bash
# Vérifier les logs
docker compose logs tradia

# Vérifier la configuration
docker compose config

# Reconstruire depuis zéro
docker compose down
docker compose build --no-cache
docker compose up -d
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

1. Réduire la taille des lots :

```bash
BATCH_SIZE=5
```

1. Utiliser un modèle plus petit/rapide

## 📊 Architecture technique

### Stack technologique

- **Backend** : FastAPI + Uvicorn
- **HTTP** : httpx (avec retries)
- **Templating** : Jinja2
- **Tests** : pytest
- **Conteneurisation** : Docker

### Robustesse du client Ollama

- ✅ Retries exponentiels (backoff 2^n)
- ✅ Circuit breaker (arrêt après 5 échecs)
- ✅ Timeout configurable
- ✅ Support proxy
- ✅ Logs structurés JSON

## 📝 Licence

Ce projet est développé pour un usage interne DSI.

## 🤝 Support

Pour toute question ou problème :

1. Consulter cette documentation
2. Vérifier les logs : `docker compose logs`
3. Tester le healthcheck : `curl -k https://localhost/healthz`
4. Contacter l'équipe infrastructure DSI

## 🔄 Roadmap

- [ ] Interface d'administration
- [ ] Authentification LDAP/SSO
- [ ] API REST documentée (Swagger)
- [ ] Traductions en cache (Redis)

---

**Version** : 2.0.0  
**Dernière mise à jour** : 2025-12-08  
**Responsable** : Infrastructure DSI
