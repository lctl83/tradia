FROM python:3.11-slim

# Métadonnées
LABEL maintainer="Infrastructure DSI"
LABEL description="SCENARI Translator - Traduction de fichiers XML via Ollama"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Gestion des proxys (optionnelle)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

# Répertoire de travail
WORKDIR /app

# Dépendances système pour lxml
RUN set -eux; \
    if [ -n "${HTTP_PROXY}" ]; then \
        echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi; \
    if [ -n "${HTTPS_PROXY}" ]; then \
        echo "Acquire::https::Proxy \"${HTTPS_PROXY}\";" >> /etc/apt/apt.conf.d/01proxy; \
    fi; \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/apt.conf.d/01proxy

# Copier les requirements et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY app/ ./app/
COPY static/ ./static/

# Copier le script de démarrage
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown appuser:appuser /entrypoint.sh

# L'utilisateur root est conservé pour permettre la copie des certificats
# SSL montés en lecture seule avant de relancer le service sous un utilisateur
# non privilégié.
ENV RUN_AS_USER=appuser

# Exposer le port par défaut HTTPS
EXPOSE 8443

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://localhost:${UVICORN_PORT:-8443}/healthz', timeout=5, verify=False)"

# Démarrage
CMD ["/entrypoint.sh"]
