#!/bin/bash

# Script de démarrage rapide pour SCENARI Translator
# Usage: ./start.sh [options]

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

log_error() {
    echo -e "${RED}✗ ${NC}$1"
}

# Chargement automatique des proxys depuis la configuration APT
load_proxy_from_apt() {
    local apt_proxy_conf="/etc/apt/apt.conf.d/90curtin-aptproxy"

    if [ ! -f "${apt_proxy_conf}" ]; then
        return
    fi

    local http_proxy_conf
    http_proxy_conf=$(awk -F'"' '/Acquire::http::Proxy/ {print $2}' "${apt_proxy_conf}" | tail -n1)

    local https_proxy_conf
    https_proxy_conf=$(awk -F'"' '/Acquire::https::Proxy/ {print $2}' "${apt_proxy_conf}" | tail -n1)

    if [ -z "${HTTP_PROXY:-}" ] && [ -n "${http_proxy_conf}" ] && [ "${http_proxy_conf}" != "DIRECT" ]; then
        export HTTP_PROXY="${http_proxy_conf}"
        export http_proxy="${http_proxy_conf}"
        log_info "HTTP_PROXY détecté dans ${apt_proxy_conf}"
    fi

    if [ -z "${HTTPS_PROXY:-}" ]; then
        if [ -n "${https_proxy_conf}" ] && [ "${https_proxy_conf}" != "DIRECT" ]; then
            export HTTPS_PROXY="${https_proxy_conf}"
            export https_proxy="${https_proxy_conf}"
            log_info "HTTPS_PROXY détecté dans ${apt_proxy_conf}"
        elif [ -n "${http_proxy_conf}" ] && [ "${http_proxy_conf}" != "DIRECT" ]; then
            export HTTPS_PROXY="${http_proxy_conf}"
            export https_proxy="${http_proxy_conf}"
            log_info "HTTPS_PROXY non défini, utilisation de HTTP_PROXY"
        fi
    fi
}

# Détection automatique de la configuration proxy système
log_info "Détection de la configuration proxy..."
PROXY_FOUND=false

for proxy_file in /etc/apt/apt.conf.d/90curtin-aptproxy \
                  /etc/apt/apt.conf.d/proxy.conf \
                  /etc/apt/apt.conf.d/*proxy*; do
    if [ -f "$proxy_file" ] && [ -s "$proxy_file" ]; then
        log_success "Configuration proxy trouvée : $proxy_file"
        cp "$proxy_file" host-proxy.conf
        PROXY_FOUND=true
        echo "Contenu du fichier proxy :"
        cat host-proxy.conf
        break
    fi
done

if [ "$PROXY_FOUND" = false ]; then
    log_info "Aucune configuration proxy système détectée (connexion directe)"
    : > host-proxy.conf
fi

load_proxy_from_apt

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════╗
║     SCENARI Translator Deployment        ║
║          FastAPI + Ollama                 ║
╚═══════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Vérification de Docker
log_info "Vérification de Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérifier Docker Compose (v1 ou v2)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    log_success "Docker Compose v2 détecté"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    log_success "Docker Compose v1 détecté"
else
    log_error "Docker Compose n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérification d'Ollama
log_info "Vérification d'Ollama..."
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

if curl -s -f "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    log_success "Ollama est accessible à ${OLLAMA_URL}"
else
    log_warning "Ollama ne semble pas accessible à ${OLLAMA_URL}"
    log_info "L'application démarrera mais pourrait ne pas fonctionner correctement"
    read -p "Continuer quand même ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Création du fichier .env si inexistant
if [ ! -f .env ]; then
    log_info "Création du fichier .env à partir de .env.example..."
    cp .env.example .env
    log_success "Fichier .env créé"
fi

# Création du répertoire logs
if [ ! -d logs ]; then
    log_info "Création du répertoire logs..."
    mkdir -p logs
    log_success "Répertoire logs créé"
fi

# Construction et démarrage
log_info "Construction de l'image Docker..."
$DOCKER_COMPOSE build

log_success "Image construite avec succès"

log_info "Démarrage de l'application..."
$DOCKER_COMPOSE up -d

log_success "Application démarrée"

# Attendre que l'application soit prête
log_info "Attente du démarrage de l'application..."
for i in {1..30}; do
    if curl -k -s -f https://localhost/healthz > /dev/null 2>&1; then
        log_success "Application prête !"
        break
    fi
    sleep 1
    echo -n "."
done
echo

# Affichage des informations
echo
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Déploiement réussi ! 🎉          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo
log_info "Interface web : ${BLUE}https://localhost${NC}"
log_info "Healthcheck   : ${BLUE}https://localhost/healthz${NC}"
log_info "Métriques     : ${BLUE}https://localhost/metrics${NC}"
echo
log_info "Commandes utiles :"
echo "  - Voir les logs : $DOCKER_COMPOSE logs -f"
echo "  - Arrêter       : $DOCKER_COMPOSE down"
echo "  - Redémarrer    : $DOCKER_COMPOSE restart"
echo "  - État          : $DOCKER_COMPOSE ps"
echo
log_success "Bon usage ! 🚀"
