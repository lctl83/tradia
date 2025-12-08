# 🖥️ Guide de déploiement Production - DELL PowerEdge R760

## Spécifications du serveur

| Composant | Configuration |
|-----------|---------------|
| **CPU** | Intel Xeon Gold 6526Y (16C/32T @ 2.8 GHz, Turbo) |
| **RAM** | 256 Go DDR5 @ 5600 MT/s |
| **GPU** | NVIDIA L40S 48 Go VRAM (PCIe, 350W) |
| **Stockage** | 1.92 To SSD SAS + 1.92 To NVMe |

## 🚀 Optimisations recommandées

### 1. Configuration GPU pour Ollama

```bash
# Vérifier que le GPU est détecté
nvidia-smi

# Afficher les processus GPU
nvidia-smi -l 1

# Vérifier CUDA
nvcc --version
```

**Si le GPU n'est pas utilisé par Ollama** :
```bash
# Installer/mettre à jour les drivers NVIDIA
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit

# Redémarrer
sudo reboot

# Après redémarrage, vérifier
ollama run llama3.2:1b --verbose 2>&1 | grep -i gpu
```

### 2. Modèles recommandés pour Tradia

| Modèle | VRAM | Vitesse | Qualité | Usage |
|--------|------|---------|---------|-------|
| `ministral-3:latest` | ~8-15 Go | ⚡⚡⚡⚡ Rapide | ⭐⭐⭐ | **Par défaut** - Réponses rapides |
| `magistral:latest` | ~15-24 Go | ⚡⚡ Lent | ⭐⭐⭐⭐⭐ | **Qualitatif** - Meilleur raisonnement |

> **Note** : Avec 48 Go de VRAM, les deux modèles tournent confortablement. Vous pouvez même les charger simultanément.

```bash
# Installer les modèles recommandés
ollama pull ministral-3:latest
ollama pull magistral:latest

# Tester les performances
time ollama run ministral-3:latest "Traduis en anglais: Bonjour le monde"
time ollama run magistral:latest "Traduis en anglais: Bonjour le monde"
```

### 3. Configuration Ollama optimisée

Créer `/etc/systemd/system/ollama.service.d/override.conf` :

```ini
[Service]
# Écouter sur toutes les interfaces (si frontend distant)
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Nombre de requêtes parallèles
Environment="OLLAMA_NUM_PARALLEL=4"

# Garder les modèles en mémoire GPU plus longtemps (5 minutes)
Environment="OLLAMA_KEEP_ALIVE=5m"

# Utiliser toute la VRAM disponible
Environment="OLLAMA_GPU_MEMORY_FRACTION=0.95"
```

Puis :
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 4. Déploiement en production

```bash
# Utiliser la configuration de production
docker compose -f docker-compose.prod.yml up -d --build

# Vérifier les logs
docker compose -f docker-compose.prod.yml logs -f tradia

# Vérifier l'état
docker compose -f docker-compose.prod.yml ps
```

## 📊 Monitoring GPU

### Script de surveillance

Créer `monitor-gpu.sh` :

```bash
#!/bin/bash
watch -n 1 "nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv"
```

### Métriques clés à surveiller

| Métrique | Valeur normale | Alerte si |
|----------|----------------|-----------|
| Température GPU | < 75°C | > 85°C |
| Utilisation GPU | Variable | 100% constant |
| Mémoire GPU | < 45 Go | > 47 Go |
| Utilisation CPU | < 50% | > 80% constant |

## 🔒 Sécurité production

### Firewall

```bash
# Autoriser uniquement les ports nécessaires
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Bloquer l'accès direct, passer par Traefik
sudo ufw deny 11434/tcp  # Bloquer Ollama de l'extérieur
sudo ufw enable
```

### Limiter l'accès Ollama

Si le frontend est sur le même serveur, Ollama ne doit écouter que localement :
```bash
# Dans /etc/systemd/system/ollama.service.d/override.conf
Environment="OLLAMA_HOST=127.0.0.1:11434"
```

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

## 🔄 Maintenance

### Mise à jour des modèles

```bash
# Mettre à jour les modèles
ollama pull ministral-3:latest
ollama pull magistral:latest

# Nettoyer les anciens modèles
ollama list
ollama rm ancien-modele
```

### Sauvegarde

```bash
# Sauvegarder la configuration
cp docker-compose.prod.yml /backup/tradia/
cp .env /backup/tradia/

# Les modèles Ollama sont dans ~/.ollama/models
```

---

**Configuration validée pour** : DELL PowerEdge R760 + NVIDIA L40S 48 Go
