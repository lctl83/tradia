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
- Ollama installé et accessible (par défaut sur `http://localhost:11434`)
- Un modèle Ollama installé (ex: `mistral-small3.2:latest`)

### Vérification d'Ollama

```bash
# Vérifier qu'Ollama est bien accessible
curl http://localhost:11434/api/tags

# Si Ollama n'est pas installé, installez-le :
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger un modèle
ollama pull mistral-small3.2:latest
```

## 🚀 Installation et déploiement

### Déploiement rapide avec Docker Compose

1. **Cloner ou télécharger le projet** :
```bash
cd tradia
```

2. **Configurer les variables d'environnement** (optionnel) :
```bash
cp .env.example .env
# Éditer .env selon vos besoins
```

3. **Construire et démarrer l'application** :
```bash
docker compose up -d --build
```

4. **Vérifier le déploiement** :
```bash
# Vérifier les logs
docker compose logs -f

# Tester le healthcheck (via Traefik)
curl -k https://localhost/healthz
```

5. **Accéder à l'application** :
Ouvrir votre navigateur à : **https://localhost**

Traefik gère la terminaison TLS sur le port 443 et redirige automatiquement le trafic HTTP (port 80) vers HTTPS.

Les certificats TLS attendus par Traefik sont montés depuis l'hôte :

- Dossier hôte : `/etc/ssl/itapprspia`
- Fichiers requis : `itapprspia.cer` et `itapprspia.key`

Ces fichiers sont exposés dans le conteneur Traefik sous `/etc/traefik/certs`, conformément au `docker compose.yml`.

### Déploiement sur un serveur distant

Si vous déployez sur un serveur différent de celui hébergeant Ollama :

1. **Modifier l'URL d'Ollama dans docker compose.yml** :
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

2. Réduire la taille des lots :
```bash
BATCH_SIZE=5
```

3. Utiliser un modèle plus petit/rapide

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
