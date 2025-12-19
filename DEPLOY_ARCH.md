# Guide de Déploiement : Architecture Multi-Serveurs

Ce guide détaille l'installation de l'infrastructure Tradia sur deux serveurs distincts.

## Prérequis

*   **Serveur 1 (Serveur IA)** :
    *   OS : Linux (Ubuntu/Debian recommandé)
    *   GPU : NVIDIA avec drivers installés + `nvidia-container-toolkit`
    *   Docker & Docker Compose
*   **Serveur 2 (Serveur App)** :
    *   OS : Linux
    *   CPU/RAM : Standard (2 vCPU, 4Go RAM min)
    *   Docker & Docker Compose
    *   Accès réseau au port 11434 du Serveur IA

## Recommandations Hardware (Pour 15-20 utilisateurs)
Ces estimations dépendent de l'usage simultané (concurrence).

### Serveur IA (GPU)
Le goulot d'étranglement sera la VRAM (mémoire vidéo) et la vitesse d'inférence.
*   **Modèle Petit (Ministral 8B / Llama 3 8B)** :
    *   **GPU** : NVIDIA RTX 3090 / 4090 (24 Go VRAM) ou T4/L4 (si Cloud).
        *   *Capacité* : Peut gérer ~2-4 requêtes parallèles confortables.
    *   **RAM Système** : 32 Go (pour charger les modèles et gérer la file d'attente).
    *   **CPU** : 8 vCPU (pour le prétraitement Ollama).
    *   **Stockage** : 100 Go SSD NVMe (les modèles sont gros).

*   **Modèle Grand (Mixtral 8x7B / Llama 3 70B)** :
    *   **GPU** : 2x A100 ou 2x A6000 (besoin de ~48 Go+ VRAM).

### Serveur App (Front)
Charge légère, principalement du relais HTTP.
*   **CPU** : 4 vCPU (suffisant pour FastAPI + Traefik).
*   **RAM** : 8 Go (pour être large avec l'OS et les logs).
*   **Disque** : 50 Go SSD.

---

## 1. Installation du Serveur IA (GPU)

Ce serveur hébergera uniquement le moteur d'intelligence artificielle (Ollama).

1.  Copiez le fichier `docker-compose.ai.yml` sur ce serveur.
2.  Démarrez le service :
    ```bash
    docker compose -f docker-compose.ai.yml up -d
    ```
3.  **Vérification** :
    ```bash
    curl http://localhost:11434/api/tags
    ```
4.  Noter l'adresse IP de ce serveur (ex: `192.168.1.50`).

---

## 2. Installation du Serveur App (Front/Back)

Ce serveur hébergera l'interface web Tradia et le reverse proxy Traefik.

1.  Copiez le code source de l'application et le fichier `docker-compose.prod.yml`.
2.  Créez un fichier `.env` pour configurer l'adresse du Serveur IA :
    ```bash
    # Créez le fichier .env
    echo "OLLAMA_BASE_URL=http://192.168.1.50:11434" > .env
    ```
    *(Remplacez `192.168.1.50` par l'IP réelle du Serveur IA)*

3.  Démarrez l'application :
    ```bash
    docker compose -f docker-compose.prod.yml up -d --build
    ```

## 3. Architecture Réseau et Sécurité

Nous avons sécurisé la connexion entre les serveurs :
*   **Utilisateurs** ➔ HTTPS (443) ➔ **Serveur App** (Traefik) ➔ **Container Tradia**
*   **Container Tradia** ➔ HTTP + Auth (11434) ➔ **Serveur IA** (Traefik + Basic Auth) ➔ **Container Ollama**

### Configuration de la Sécurité (Serveur IA)

1.  Générez un mot de passe pour l'utilisateur `api` (votre "Clé API") :
    ```bash
    # Exemple pour créer le hash du mot de passe "ma-super-cle-secrete"
    # Vous pouvez utiliser un outil en ligne htpasswd ou la commande :
    htpasswd -nb api ma-super-cle-secrete
    # Résultat : api:$apr1$ExampleHash...
    ```

2.  Mettez à jour le fichier `.env` sur le Serveur IA :
    ```bash
    # .env sur Serveur IA
    API_AUTH_USER_PASS='api:$apr1$ExampleHash...'
    ```

### Configuration de la Connexion (Serveur App)

Sur le Serveur App, configurez le fichier `.env` pour utiliser cette clé :

```bash
# .env sur Serveur App
OLLAMA_BASE_URL=http://192.168.1.50:11434
OLLAMA_API_KEY=ma-super-cle-secrete
```
> [!NOTE]
> L'application utilisera automatiquement Basic Auth (`api` / `ma-super-cle-secrete`) pour s'authentifier auprès du Serveur IA.

> [!IMPORTANT]
> Assurez-vous que le pare-feu du Serveur IA autorise les connexions entrantes sur le port 11434 uniquement depuis l'IP du Serveur App.
