#!/bin/sh
set -e

# Default domain if not specified
DOMAIN_NAME=${DOMAIN_NAME:-localhost}
export DOMAIN_NAME

CERT_PATH="/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem"
CONF_DIR="/etc/nginx/conf.d"

mkdir -p "$CONF_DIR" /var/www/certbot

if [ -f "$CERT_PATH" ]; then
    echo "[NGINX ENTRYPOINT] SSL certificate found for ${DOMAIN_NAME}. Activating HTTPS configuration..."
    envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/ssl.conf.template > "${CONF_DIR}/default.conf"
else
    echo "[NGINX ENTRYPOINT] No SSL certificate found for ${DOMAIN_NAME}. Starting in HTTP mode..."
    envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/default.conf.template > "${CONF_DIR}/default.conf"
fi

echo "[NGINX ENTRYPOINT] Starting Nginx daemon..."
exec nginx -g "daemon off;"

