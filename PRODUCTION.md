# 🖥️ Guide de Déploiement Production - Tradia

## Architecture

```
┌─────────────────────┐         HTTPS (443)        ┌──────────────────────────────────┐
│   SOURCES EXTERNES  │ ────────────────────────►  │  SERVEUR IA                      │
│   (n8n, EDOC, ...)  │      + X-API-Key           │  itapprspia01.dci.local              │
└─────────────────────┘                            │  (172.20.30.131)                 │
                                                   │                                  │
                                                   │  ┌────────────────────────────┐  │
                                                   │  │ CADDY (Passerelle)         │  │
                                                   │  │ • Port 443: API Ollama     │  │
                                                   │  │ • Port 8080: Health Check  │  │
                                                   │  │ • Port 9180: Métriques     │  │
                                                   │  └─────────────┬──────────────┘  │
                                                   │                │                 │
                                                   │                ▼ localhost:11434 │
                                                   │  ┌────────────────────────────┐  │
                                                   │  │ OLLAMA (natif)             │  │
                                                   │  │ • GPU: NVIDIA L40S (48GB)  │  │
                                                   │  │ • Modèles: ministral,      │  │
                                                   │  │            Magistral       │  │
                                                   │  └────────────────────────────┘  │
                                                   └──────────────────────────────────┘
```

## Spécifications

### Serveur Tradia (Application)

| Composant | Configuration |
|-----------|---------------|
| **OS** | Debian 13 |
| **CPU** | 2 vCPU |
| **RAM** | 8 Go |
| **Stockage** | 50 Go HDD |
| **Runtime** | Docker |

### Serveur IA

| Composant | Configuration |
|-----------|---------------|
| **Hostname** | itapprspia01.dci.local |
| **IP** | 172.20.30.131 |
| **GPU** | NVIDIA L40S (48 Go VRAM) |
| **Passerelle** | Caddy (HTTPS + X-API-Key) |
| **Modèles** | ministral, Magistral |

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

## 🚀 Déploiement

### 1. Configuration

Créez le fichier `.env` avec vos paramètres :

```bash
# .env
OLLAMA_BASE_URL=https://itapprspia01.dci.local/api
OLLAMA_API_KEY=<votre-clé-api>
OLLAMA_MODEL=ministral-3:latest
```

### 2. Lancement

```bash
# Déployer en production
docker compose -f docker-compose.prod.yml up -d --build

# Vérifier les logs
docker compose -f docker-compose.prod.yml logs -f tradia

# Vérifier l'état
docker compose -f docker-compose.prod.yml ps
```

### 3. Vérification

```bash
# Health check local
curl http://localhost:8000/healthz

# Test connexion serveur IA
curl -H "X-API-Key: <votre-clé>" https://itapprspia01.dci.local/api/tags
```

---

## 📊 Modèles disponibles

| Modèle | VRAM | Vitesse | Qualité | Usage |
|--------|------|---------|---------|-------|
| `ministral-3:latest` | ~8-15 Go | ⚡⚡⚡⚡ Rapide | ⭐⭐⭐ | **Par défaut** - Réponses rapides |
| `magistral:latest` | ~15-24 Go | ⚡⚡ Lent | ⭐⭐⭐⭐⭐ | **Qualitatif** - Meilleur raisonnement |

---

## 📈 Benchmarks attendus

### Avec `ministral-3:latest` (⚡ Rapide)

| Opération | Temps attendu |
|-----------|---------------|
| Traduction (100 mots) | ~1-2 secondes |
| Correction (500 mots) | ~2-3 secondes |
| Reformulation (500 mots) | ~2-4 secondes |
| Compte rendu (1000 mots) | ~4-6 secondes |

### Avec `magistral:latest` (✨ Qualitatif)

| Opération | Temps attendu |
|-----------|---------------|
| Traduction (100 mots) | ~3-5 secondes |
| Correction (500 mots) | ~5-8 secondes |
| Reformulation (500 mots) | ~6-10 secondes |
| Compte rendu (1000 mots) | ~10-15 secondes |

---

## 🔄 Maintenance

### Mise à jour de l'application

```bash
# Récupérer les dernières modifications
git pull

# Reconstruire et redéployer
docker compose -f docker-compose.prod.yml up -d --build
```

### Sauvegarde

```bash
# Sauvegarder la configuration
cp docker-compose.prod.yml /backup/tradia/
cp .env /backup/tradia/
```

---

**Configuration validée pour** : Serveur Tradia (2vCPU/8Go) + Serveur IA itapprspia01.dci.local
