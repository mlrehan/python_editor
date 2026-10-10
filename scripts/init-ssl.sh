#!/bin/bash
# ========================================================
# Python Cloud Studio - Automated SSL / Let's Encrypt Setup
# ========================================================
set -e

# Load .env variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found. Copy .env.example to .env and configure DOMAIN_NAME."
    exit 1
fi

if [ -z "$DOMAIN_NAME" ] || [ "$DOMAIN_NAME" == "localhost" ]; then
    echo "Error: DOMAIN_NAME is not configured or set to localhost in .env."
    echo "Please set a valid public FQDN (e.g. studio.example.com) before requesting SSL."
    exit 1
fi

if [ -z "$LETSENCRYPT_EMAIL" ]; then
    echo "Error: LETSENCRYPT_EMAIL is not set in .env."
    exit 1
fi

echo "=========================================================="
echo "Initializing SSL Certificate for: ${DOMAIN_NAME}"
echo "Contact Email: ${LETSENCRYPT_EMAIL}"
echo "=========================================================="

# 1. Ensure Nginx is running in HTTP mode to handle ACME challenge
echo "[1/4] Ensuring Nginx reverse proxy is running..."
docker compose up -d nginx

# Wait for Nginx to be ready
sleep 3

# 2. Request certificate from Let's Encrypt
echo "[2/4] Requesting certificate from Let's Encrypt..."
docker compose run --rm --entrypoint "certbot" certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN_NAME}" \
    --email "${LETSENCRYPT_EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal

# 3. Restart Nginx to activate SSL configuration
echo "[3/4] Restarting Nginx to switch to HTTPS mode..."
docker compose restart nginx

# 4. Start certbot background renewal daemon
echo "[4/4] Starting certbot background renewal daemon..."
docker compose up -d certbot

echo "=========================================================="
echo "✔ SSL Certificate successfully provisioned and activated!"
echo "Access your secure studio at: https://${DOMAIN_NAME}"
echo "=========================================================="

