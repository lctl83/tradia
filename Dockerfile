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

# Copier le fichier proxy (toujours créé par start.sh, peut être vide)
COPY host-proxy.conf /tmp/

# Dépendances système pour lxml avec détection automatique du proxy + curl pour healthcheck
RUN set -eux; \
    if [ -f /tmp/host-proxy.conf ] && [ -s /tmp/host-proxy.conf ]; then \
        cp /tmp/host-proxy.conf /etc/apt/apt.conf.d/01proxy; \
        echo "✓ Using host proxy configuration"; \
        cat /etc/apt/apt.conf.d/01proxy; \
        PROXY_URL=$(grep -oP 'http://[^\"]+' /tmp/host-proxy.conf | head -1); \
        export HTTP_PROXY="$PROXY_URL"; \
        export HTTPS_PROXY="$PROXY_URL"; \
        export http_proxy="$PROXY_URL"; \
        export https_proxy="$PROXY_URL"; \
        echo "✓ Proxy configured for pip: $PROXY_URL"; \
    elif [ -n "${HTTP_PROXY}" ]; then \
        echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" >> /etc/apt/apt.conf.d/01proxy; \
        echo "Acquire::https::Proxy \"${HTTPS_PROXY}\";" >> /etc/apt/apt.conf.d/01proxy; \
        echo "✓ Using proxy from environment variables"; \
    else \
        echo "⚠ No proxy configuration found, using direct connection"; \
    fi; \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/apt.conf.d/01proxy

# Copier les requirements et installer les dépendances
COPY requirements.txt .
RUN set -eux; \
    if [ -f /tmp/host-proxy.conf ] && [ -s /tmp/host-proxy.conf ]; then \
        PROXY_URL=$(grep -oP 'http://[^\"]+' /tmp/host-proxy.conf | head -1); \
        export HTTP_PROXY="$PROXY_URL"; \
        export HTTPS_PROXY="$PROXY_URL"; \
        export http_proxy="$PROXY_URL"; \
        export https_proxy="$PROXY_URL"; \
        echo "✓ Installing Python packages via proxy: $PROXY_URL"; \
    fi; \
    pip install --no-cache-dir -r requirements.txt && \
    rm -f /tmp/host-proxy.conf

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

ENV RUN_AS_USER=appuser

# Exposer le port par défaut HTTP
EXPOSE 8000

# Healthcheck avec curl au lieu de Python requests
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${UVICORN_PORT:-8000}/healthz || exit 1

# Démarrage
CMD ["/entrypoint.sh"]
