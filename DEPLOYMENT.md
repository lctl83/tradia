# 🚀 Guide de Déploiement - Tradia

Guide complet pour déployer Tradia en production avec architecture serveur applicatif + serveur IA.

## Architecture

```
┌─────────────────────┐         HTTPS (443)         ┌──────────────────────────────────┐
│   Serveur Applicatif│ ─────────────────────────►  │  Serveur IA                      │
│   (Tradia)          │      + X-API-Key            │  itapprspia01.dci.local          │
│                     │                             │  (172.20.30.131)                 │
│  • 2 vCPU / 8 Go    │                             │                                  │
│  • Debian 13        │                             │  ┌────────────────────────────┐  │
│  • Docker + Traefik │                             │  │ CADDY (Passerelle)         │  │
│                     │                             │  │ • Port 443: API Ollama     │  │
│  Certificats :      │                             │  │ • Port 8080: Health Check  │  │
│  /etc/ssl/tradia/   │                             │  │ • Port 9180: Métriques     │  │
│  tradia.cer/.key    │                             │  └─────────────┬──────────────┘  │
└─────────────────────┘                             │                │                 │
                                                    │                ▼ localhost:11434 │
                                                    │  ┌────────────────────────────┐  │
                                                    │  │ OLLAMA (natif)             │  │
                                                    │  │ • GPU: NVIDIA L40S (48GB)  │  │
                                                    │  │ • Modèles: ministral,      │  │
                                                    │  │            Magistral       │  │
                                                    │  └────────────────────────────┘  │
                                                    └──────────────────────────────────┘
```

---

## Prérequis

### Serveur Applicatif

| Composant | Configuration |
|-----------|---------------|
| **OS** | Debian 13 |
| **CPU** | 2 vCPU minimum |
| **RAM** | 8 Go |
| **Stockage** | 50 Go |
| **Runtime** | Docker & Docker Compose |
| **Réseau** | Accès HTTPS au serveur IA |
| **Certificats** | `/etc/ssl/tradia/tradia.cer` et `tradia.key` |

### Serveur IA (déjà configuré)

| Composant | Configuration |
|-----------|---------------|
| **Hostname** | itapprspia01.dci.local |
| **IP** | 172.20.30.131 |
| **GPU** | NVIDIA L40S (48 Go VRAM) |
| **Passerelle** | Caddy (HTTPS + X-API-Key) |
| **Modèles** | ministral, Magistral |

---

## Installation

### 1. Cloner le projet

```bash
git clone <repo-url> tradia
cd tradia
```

### 2. Configuration

Créez le fichier `.env` :

```bash
# .env
OLLAMA_BASE_URL=https://itapprspia01.dci.local/api
OLLAMA_API_KEY=<votre-clé-api>
OLLAMA_MODEL=ministral-3:latest
```

### 3. Déploiement

```bash
# Démarrer en production
docker compose -f docker-compose.prod.yml up -d --build

# Vérifier les logs
docker compose -f docker-compose.prod.yml logs -f tradia

# Vérifier l'état
docker compose -f docker-compose.prod.yml ps
```

### 4. Vérification

```bash
# Health check local
curl http://localhost:8000/healthz

# Test connexion serveur IA
curl -H "X-API-Key: <votre-clé>" https://itapprspia01.dci.local/api/tags
```

---

## Accès à l'API IA

### Endpoint

```
https://itapprspia01.dci.local/api/
```

### Authentification

Toutes les requêtes doivent inclure le header `X-API-Key` :

```bash
curl -H "X-API-Key: <votre-clé>" https://itapprspia01.dci.local/api/tags
```

### Clés API disponibles

| Application | Usage |
|-------------|-------|
| `APP_INTERNE` | Applications internes DCI |
| `N8N` | Workflows automatisés |
| `DEV` | Développement et tests |
| `EDOC` | Plateforme SCENARI |

> ⚠️ **Les clés sont disponibles sur demande.**

---

## Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | URL du serveur IA | `https://itapprspia01.dci.local/api` |
| `OLLAMA_API_KEY` | Clé d'authentification | `sk-xxxxx` |
| `OLLAMA_MODEL` | Modèle par défaut | `ministral-3:latest` |
| `OLLAMA_TIMEOUT` | Timeout en secondes | `300` |
| `OLLAMA_MAX_RETRIES` | Nombre de retries | `5` |
| `MAX_UPLOAD_MB` | Taille max fichier | `100` |
| `LOG_LEVEL` | Niveau de log | `WARNING` |

---

## Modèles disponibles

| Modèle | VRAM | Vitesse | Qualité | Usage |
|--------|------|---------|---------|-------|
| `ministral-3:latest` | ~8-15 Go | ⚡⚡⚡⚡ Rapide | ⭐⭐⭐ | **Par défaut** - Réponses rapides |
| `magistral:latest` | ~15-24 Go | ⚡⚡ Lent | ⭐⭐⭐⭐⭐ | **Qualitatif** - Meilleur raisonnement |

---

## Fichiers Docker Compose

| Fichier | Usage | Description |
|---------|-------|-------------|
| `docker-compose.prod.yml` | **Production** | Connexion au serveur IA DCI via HTTPS |
| `docker-compose.test.yml` | **Tests locaux** | Connexion à Ollama local |

---

## Maintenance

### Mise à jour

```bash
# Récupérer les dernières modifications
git pull

# Reconstruire et redéployer
docker compose -f docker-compose.prod.yml up -d --build
```

### Sauvegarde

```bash
cp docker-compose.prod.yml /backup/tradia/
cp .env /backup/tradia/
```

---

## Dépannage

### L'application ne démarre pas

```bash
docker compose -f docker-compose.prod.yml logs tradia
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### Erreur de connexion au serveur IA

```bash
# Vérifier la connectivité HTTPS
curl -H "X-API-Key: <clé>" https://itapprspia01.dci.local/api/tags

# Vérifier que l'API Key est correcte dans .env
cat .env | grep OLLAMA_API_KEY
```

### Certificats TLS

Les certificats sont montés depuis `/etc/ssl/tradia/` :

- `tradia.cer` - Certificat
- `tradia.key` - Clé privée

---

**Configuration validée pour** : Serveur Tradia (2vCPU/8Go) + Serveur IA itapprspia01.dci.local
