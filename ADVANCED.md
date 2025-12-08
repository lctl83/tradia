# Configuration avancée - Guide DSI

## Architecture de déploiement

### Scénario 1 : Tout sur un seul serveur

```
┌─────────────────────────┐
│   Serveur Dell R760     │
│   (GPU L40S 48GB)       │
│                         │
│  ┌─────────────────┐   │
│  │  Ollama         │   │
│  │  :11434         │   │
│  └─────────────────┘   │
│           ↑             │
│           │             │
│  ┌─────────────────┐   │
│  │  Translator     │   │
│  │  :8000          │   │
│  └─────────────────┘   │
└─────────────────────────┘
```

**Configuration** :
```yaml
# docker compose.yml
environment:
  - OLLAMA_BASE_URL=http://localhost:11434
```

---

### Scénario 2 : Serveurs séparés

```
┌──────────────────┐      ┌──────────────────┐
│  Serveur IA      │      │  Serveur Web     │
│  (GPU L40S)      │      │                  │
│                  │      │                  │
│  ┌───────────┐  │      │  ┌───────────┐  │
│  │  Ollama   │  │◄─────┼─►│Translator │  │
│  │  :11434   │  │      │  │  :8000    │  │
│  └───────────┘  │      │  └───────────┘  │
└──────────────────┘      └──────────────────┘
```

**Configuration** :
```yaml
# Sur le serveur web
environment:
  - OLLAMA_BASE_URL=http://IP_SERVEUR_IA:11434
```

**Firewall** :
```bash
# Sur le serveur IA, autoriser le port Ollama
ufw allow from IP_SERVEUR_WEB to any port 11434
```

---

### Scénario 3 : Avec reverse proxy (Nginx/Traefik)

```
                    ┌──────────────┐
Internet ──────────►│    Proxy     │
                    │  (Nginx)     │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ↓                         ↓
     ┌─────────────┐          ┌─────────────┐
     │ Translator  │          │   Ollama    │
     │   :8000     │◄─────────┤   :11434    │
     └─────────────┘          └─────────────┘
```

**Configuration Nginx** :
```nginx
# /etc/nginx/sites-available/translator

upstream translator {
    server localhost:8000;
}

server {
    listen 80;
    server_name translator.votredomaine.fr;
    
    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name translator.votredomaine.fr;
    
    # Certificats SSL
    ssl_certificate /etc/letsencrypt/live/translator.votredomaine.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/translator.votredomaine.fr/privkey.pem;
    
    # Sécurité
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Taille max upload (ajuster selon vos besoins)
    client_max_body_size 100M;
    
    # Timeouts
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    location / {
        proxy_pass http://translator;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Activer la configuration** :
```bash
ln -s /etc/nginx/sites-available/translator /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

---

## Configuration Ollama en production

### Service systemd personnalisé

```bash
# /etc/systemd/system/ollama.service

[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10

# Limites de ressources
MemoryLimit=32G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
```

**Appliquer** :
```bash
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama
```

### Précharger les modèles

```bash
# Télécharger les modèles à l'avance
ollama pull mistral-small3.2:latest
ollama pull mistral:latest

# Vérifier
ollama list
```

### Monitorer Ollama

```bash
# Voir les logs
journalctl -u ollama -f

# Stats GPU
nvidia-smi -l 1

# Utilisation mémoire
watch -n 1 'ps aux | grep ollama'
```

---

## Optimisations de performance

### 1. Augmenter les ressources Docker

```yaml
# docker compose.yml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 2G
```

### 2. Optimiser le batch size

```bash
# Pour des traductions plus rapides (mais plus de mémoire)
BATCH_SIZE=20

# Pour économiser la mémoire
BATCH_SIZE=5
```

### 3. Ajuster les timeouts

```bash
# Pour des modèles lents/gros
OLLAMA_TIMEOUT=300

# Pour des modèles rapides/petits
OLLAMA_TIMEOUT=60
```

### 4. Utiliser un modèle plus rapide

```bash
# Modèle le plus rapide
OLLAMA_MODEL=llama3.2:1b

# Bon compromis
OLLAMA_MODEL=mistral:latest

# Meilleure qualité (plus lent)
OLLAMA_MODEL=llama3:70b
```

---

## Sécurité

### 1. Réseau Docker isolé

```yaml
# docker compose.yml
networks:
  translator-net:
    driver: bridge
    internal: true  # Pas d'accès Internet

services:
  translator:
    networks:
      - translator-net
```

### 2. Utilisateur non-root

Le Dockerfile utilise déjà un utilisateur non-root (`appuser`).

### 3. Limiter les uploads

```bash
# Réduire la taille max
MAX_UPLOAD_MB=10
```

### 4. Rate limiting avec Nginx

```nginx
# Dans http block
limit_req_zone $binary_remote_addr zone=translator:10m rate=10r/m;

# Dans server block
location / {
    limit_req zone=translator burst=5;
    # ... reste de la config
}
```

### 5. Firewall

```bash
# Autoriser uniquement les ports nécessaires
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp  # N'exposer que via Nginx
```

---

## Monitoring et observabilité

### 1. Prometheus + Grafana

**Exposer les métriques** :
```python
# Ajouter dans app/main.py
from prometheus_client import Counter, Histogram, generate_latest

translations = Counter('translations_total', 'Total translations')
translation_duration = Histogram('translation_duration_seconds', 'Translation duration')

@app.get("/metrics")
async def prometheus_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 2. Centralisation des logs (ELK Stack)

```yaml
# docker compose.yml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logstash:5000"
    tag: "tradia"
```

### 3. Alerting

**Exemple avec Uptime Kuma** :
- Monitor : http://translator.votredomaine.fr/healthz
- Interval : 60s
- Alerts : Email/Slack si down

### 4. Backup des logs

```bash
# Crontab
0 2 * * * docker compose -f /path/to/docker compose.yml logs > /backup/logs-$(date +\%Y\%m\%d).txt
```

---

## Haute disponibilité

### Avec Docker Swarm

```yaml
# docker compose-swarm.yml
version: '3.8'

services:
  translator:
    image: tradia:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    # ... reste de la config
```

**Déployer** :
```bash
docker stack deploy -c docker compose-swarm.yml translator
```

### Load balancing avec Nginx

```nginx
upstream translator_cluster {
    least_conn;
    server translator1:8000;
    server translator2:8000;
    server translator3:8000;
}
```

---

## Maintenance

### Mise à jour de l'application

```bash
# 1. Récupérer la nouvelle version
git pull

# 2. Reconstruire
docker compose build

# 3. Déploiement progressif
docker compose up -d --no-deps --build translator

# 4. Vérifier
curl http://localhost:8000/healthz
```

### Mise à jour d'Ollama

```bash
# 1. Arrêter Ollama
systemctl stop ollama

# 2. Télécharger nouvelle version
curl -fsSL https://ollama.com/install.sh | sh

# 3. Redémarrer
systemctl start ollama

# 4. Mettre à jour les modèles
ollama pull mistral-small3.2:latest
```

### Rotation des logs

```bash
# /etc/logrotate.d/translator
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## Troubleshooting avancé

### Ollama ne répond plus

```bash
# Redémarrer avec clear cache
systemctl stop ollama
rm -rf /tmp/ollama-*
systemctl start ollama
```

### Fuites mémoire

```bash
# Monitorer
docker stats tradia

# Redémarrer si nécessaire
docker compose restart

# Limiter la mémoire
docker update --memory 2G --memory-swap 2G tradia
```

### Performance GPU

```bash
# Vérifier utilisation GPU
nvidia-smi

# Stress test
for i in {1..10}; do
    curl -X POST http://localhost:11434/api/generate \
        -d '{"model":"mistral-small3.2:latest","prompt":"test"}' &
done
```

---

## Checklist de déploiement production

- [ ] Ollama installé et configuré
- [ ] Modèles téléchargés
- [ ] Firewall configuré
- [ ] Reverse proxy avec SSL
- [ ] Logs centralisés
- [ ] Monitoring actif
- [ ] Alertes configurées
- [ ] Backups réguliers
- [ ] Documentation à jour
- [ ] Procédure de rollback testée

---

## Support et escalade

**Niveaux de support** :

1. **L1** : Vérifier logs, redémarrer service
2. **L2** : Analyser métriques, ajuster config
3. **L3** : Debugging code, patchs custom

**Contacts** :
- Infrastructure DSI : dsi-infra@example.com
- Équipe IA : ia-team@example.com
- Urgence : +33 X XX XX XX XX

---

**Version** : 1.0.0  
**Dernière révision** : 2025-01-XX  
**Responsable** : Infrastructure DSI
