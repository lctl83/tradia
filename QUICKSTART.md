# 🚀 Guide de démarrage rapide

## Installation en 3 étapes

### 1. Vérifier les prérequis

```bash
# Vérifier Docker
docker --version

# Vérifier Ollama
curl http://localhost:11434/api/tags
```

### 2. Démarrer l'application

**Option A : Avec le script automatique**
```bash
./start.sh
```

**Option B : Manuellement**
```bash
docker-compose up -d --build
```

**Option C : Avec Make**
```bash
make deploy
```

### 3. Accéder à l'interface

Ouvrir : **http://localhost:8000**

## Commandes rapides

```bash
# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Vérifier la santé
curl http://localhost:8000/healthz

# Voir les métriques
curl http://localhost:8000/metrics
```

## Résolution de problèmes rapide

### Ollama n'est pas accessible

```bash
# Démarrer Ollama
systemctl start ollama

# Tester
curl http://localhost:11434/api/tags
```

### L'application ne démarre pas

```bash
# Voir les logs
docker-compose logs

# Reconstruire
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port 8000 déjà utilisé

Modifier le port dans `docker-compose.yml` :
```yaml
ports:
  - "8001:8000"  # Utiliser 8001 au lieu de 8000
```

## Configuration minimale

Créer un fichier `.env` :
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
MAX_UPLOAD_MB=50
```

## Test rapide

1. Téléverser le fichier `example.xml`
2. Sélectionner FR → EN
3. Cliquer sur "Traduire"
4. Télécharger le résultat

## Support

- 📖 Documentation complète : voir `README.md`
- 🐛 Problème ? Vérifier les logs : `docker-compose logs -f`
- 💡 Questions ? Contacter l'équipe infrastructure DSI

---

**Temps de déploiement** : < 5 minutes  
**Temps de première traduction** : < 2 minutes
