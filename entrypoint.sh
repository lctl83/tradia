#!/bin/bash
set -euo pipefail

UVICORN_PORT=${UVICORN_PORT:-8000}
RUN_AS_USER=${RUN_AS_USER:-appuser}

CMD=("uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "${UVICORN_PORT}" "--proxy-headers" "--forwarded-allow-ips" "*")

if [[ $(id -u) -eq 0 && -n "${RUN_AS_USER}" && "${RUN_AS_USER}" != "root" ]]; then
    if id "${RUN_AS_USER}" >/dev/null 2>&1; then
        printf -v CMD_STR '%q ' "${CMD[@]}"
        CMD_STR=${CMD_STR% }
        exec su -s /bin/bash "${RUN_AS_USER}" -c "exec ${CMD_STR}"
    fi
fi

exec "${CMD[@]}"
