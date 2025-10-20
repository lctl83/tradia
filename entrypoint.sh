#!/bin/bash
set -euo pipefail

UVICORN_PORT=${UVICORN_PORT:-8443}
RUN_AS_USER=${RUN_AS_USER:-appuser}

CMD=("uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "${UVICORN_PORT}" "--proxy-headers" "--forwarded-allow-ips" "*")

if [[ -n "${SSL_CERTFILE:-}" && -n "${SSL_KEYFILE:-}" ]]; then
    cert_file="${SSL_CERTFILE}"
    key_file="${SSL_KEYFILE}"

    if [[ ! -r "${cert_file}" || ! -r "${key_file}" ]]; then
        if [[ $(id -u) -ne 0 ]]; then
            echo "[entrypoint] Impossible de lire les certificats SSL et le conteneur n'est pas exécuté en tant que root." >&2
            exit 1
        fi

        tmp_cert="/tmp/tls-cert.pem"
        tmp_key="/tmp/tls-key.pem"
        cp "${cert_file}" "${tmp_cert}"
        cp "${key_file}" "${tmp_key}"
        chmod 644 "${tmp_cert}"
        chmod 600 "${tmp_key}"
        if id "${RUN_AS_USER}" >/dev/null 2>&1; then
            chown "${RUN_AS_USER}:${RUN_AS_USER}" "${tmp_cert}" "${tmp_key}"
        fi
        cert_file="${tmp_cert}"
        key_file="${tmp_key}"
    fi

    CMD+=("--ssl-certfile" "${cert_file}" "--ssl-keyfile" "${key_file}")
    if [[ -n "${SSL_KEYFILE_PASSWORD:-}" ]]; then
        CMD+=("--ssl-keyfile-password" "${SSL_KEYFILE_PASSWORD}")
    fi
fi

if [[ $(id -u) -eq 0 && -n "${RUN_AS_USER}" && "${RUN_AS_USER}" != "root" && id "${RUN_AS_USER}" >/dev/null 2>&1 ]]; then
    printf -v CMD_STR '%q ' "${CMD[@]}"
    CMD_STR=${CMD_STR% }
    exec su -s /bin/bash "${RUN_AS_USER}" -c "exec ${CMD_STR}"
else
    exec "${CMD[@]}"
fi
