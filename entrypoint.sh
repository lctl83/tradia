#!/bin/bash
set -euo pipefail

UVICORN_PORT=${UVICORN_PORT:-8443}

CMD=("uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "${UVICORN_PORT}" "--proxy-headers" "--forwarded-allow-ips" "*")

if [[ -n "${SSL_CERTFILE:-}" && -n "${SSL_KEYFILE:-}" ]]; then
    CMD+=("--ssl-certfile" "${SSL_CERTFILE}" "--ssl-keyfile" "${SSL_KEYFILE}")
    if [[ -n "${SSL_KEYFILE_PASSWORD:-}" ]]; then
        CMD+=("--ssl-keyfile-password" "${SSL_KEYFILE_PASSWORD}")
    fi
fi

exec "${CMD[@]}"
