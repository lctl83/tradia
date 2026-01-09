# Tradia - IA DCI

Suite d'assistants linguistiques internes DCI pour traduire, corriger, reformuler et résumer vos contenus grâce aux modèles Ollama.

## 🎯 Fonctionnalités

- **Traduction instantanée** : FR ↔ EN ↔ AR avec streaming temps réel
- **Correction orthographique** : Texte corrigé avec explications des modifications
- **Reformulation** : Reformulation professionnelle avec points clés
- **Compte rendu** : Génération de résumés de réunion structurés
- **Interface web moderne** : Simple, responsive et intuitive

## 📋 Prérequis

- Docker et Docker Compose
- Accès au serveur IA Ollama (`itapprspia01.dci.local`)
- Clé API pour le serveur IA

> [!NOTE]
> L'application et le serveur IA Ollama sont déployés sur des serveurs **distincts**.
> Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour l'architecture complète.

## 🚀 Installation rapide

### 1. Cloner le projet

```bash
git clone <repo-url> tradia
cd tradia
```

### 2. Configurer

```bash
# Créer le fichier .env
cat > .env << EOF
OLLAMA_BASE_URL=https://itapprspia01.dci.local/api
OLLAMA_API_KEY=<votre-clé-api>
OLLAMA_MODEL=ministral-3:latest
EOF
```

### 3. Démarrer

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Accéder

Ouvrir : **<https://localhost>**

## 🔧 Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `OLLAMA_BASE_URL` | URL du serveur IA | - |
| `OLLAMA_API_KEY` | Clé d'authentification | - |
| `OLLAMA_MODEL` | Modèle par défaut | `ministral-3:latest` |
| `OLLAMA_TIMEOUT` | Timeout (secondes) | `300` |

## 🔍 Vérification

```bash
# Health check
curl -k https://localhost/healthz

# Logs
docker compose -f docker-compose.prod.yml logs -f tradia
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Guide de déploiement complet |
| [API.md](API.md) | Documentation de l'API REST |
| [CHANGELOG.md](CHANGELOG.md) | Historique des versions |

## 🛠️ Maintenance

```bash
# Mise à jour
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Arrêt
docker compose -f docker-compose.prod.yml down
```

## 🤝 Support

Pour toute question ou problème :

1. Vérifier les logs : `docker compose logs tradia`
2. Tester le healthcheck : `curl -k https://localhost/healthz`
3. Contacter l'équipe infrastructure DSI

---

**Version** : 2.1.0 | **Responsable** : Infrastructure DSI
