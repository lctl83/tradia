# Guide de Déploiement : Architecture Tradia

Ce guide détaille l'infrastructure Tradia et les configurations disponibles.

## Architecture

```
┌─────────────────┐                              ┌─────────────────────────────┐
│  Serveur App    │       HTTPS + X-API-Key      │  Serveur IA                 │
│  (Tradia)       │ ──────────────────────────►  │  itapprspia01.dci.local     │
│                 │                              │                             │
│  • 2 vCPU       │                              │  • Caddy (passerelle)       │
│  • 8 Go RAM     │                              │  • Ollama (natif)           │
│  • Docker       │                              │  • NVIDIA L40S (48GB)       │
│  • Debian 13    │                              │                             │
└─────────────────┘                              └─────────────────────────────┘
```

## Prérequis

### Serveur Application (Tradia)

- **OS** : Debian 13
- **CPU** : 2 vCPU minimum
- **RAM** : 8 Go
- **Stockage** : 50 Go
- **Runtime** : Docker & Docker Compose
- **Réseau** : Accès HTTPS au serveur IA

### Serveur IA (déjà configuré)

- **Endpoint** : `https://itapprspia01.dci.local/api/`
- **Authentification** : Header `X-API-Key`
- **Passerelle** : Caddy
- **Moteur IA** : Ollama (natif, non Docker)
- **GPU** : NVIDIA L40S (48 Go VRAM)

---

## Installation Serveur Application

### 1. Cloner le projet

```bash
git clone <repo-url> tradia
cd tradia
```

### 2. Configuration

Créez le fichier `.env` :

```bash
# .env pour la production
OLLAMA_BASE_URL=https://itapprspia01.dci.local/api
OLLAMA_API_KEY=<votre-clé-api>
OLLAMA_MODEL=ministral-3:latest

# Proxy entreprise (si nécessaire)
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080
```

### 3. Déploiement

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Fichiers Docker Compose

| Fichier | Usage | Description |
|---------|-------|-------------|
| `docker-compose.prod.yml` | **Production** | Connexion au serveur IA DCI via HTTPS |
| `docker-compose.test.yml` | **Tests locaux** | Connexion à Ollama local |

### Production

```bash
# Démarrer
docker compose -f docker-compose.prod.yml up -d --build

# Logs
docker compose -f docker-compose.prod.yml logs -f

# Arrêter
docker compose -f docker-compose.prod.yml down
```

### Tests locaux

Prérequis : Ollama installé localement avec le modèle `ministral-3:3b-cloud`

```bash
# Installer le modèle de test
ollama pull ministral-3:3b-cloud

# Démarrer l'application
docker compose -f docker-compose.test.yml up -d --build

# Accéder à l'interface
open http://localhost:8000
```

---

## Sécurité

### Authentification API

L'API IA est protégée par une clé API :

```bash
# Test de connexion
curl -H "X-API-Key: <clé>" https://itapprspia01.dci.local/api/tags
```

### Clés disponibles

| Application | Description |
|-------------|-------------|
| `APP_INTERNE` | Applications internes DCI |
| `N8N` | Workflows automatisés |
| `DEV` | Développement et tests |
| `EDOC` | Plateforme SCENARI |

> 📧 **Demande de clé** : Contacter l'administrateur

### Réseau

- Le serveur IA n'est accessible que depuis le réseau interne DCI
- HTTPS obligatoire avec certificats PKI internes
- Logs d'accès avec traçabilité par application

---

## Endpoints du Serveur IA

| Port | Service | Description |
|------|---------|-------------|
| 443 | API Ollama | Endpoint principal (HTTPS) |
| 8080 | Health Check | Vérification de l'état |
| 9180 | Métriques | Monitoring |

---

## Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | URL du serveur IA | `https://itapprspia01.dci.local/api` |
| `OLLAMA_API_KEY` | Clé d'authentification | `sk-xxxxx` |
| `OLLAMA_MODEL` | Modèle par défaut | `ministral-3:latest` |
| `OLLAMA_TIMEOUT` | Timeout en secondes | `300` |
| `HTTP_PROXY` | Proxy HTTP (optionnel) | `http://proxy:8080` |
| `HTTPS_PROXY` | Proxy HTTPS (optionnel) | `http://proxy:8080` |
