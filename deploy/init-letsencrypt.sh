#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "Nie znaleziono Docker Compose (docker compose ani docker-compose)." >&2
    exit 1
fi

if [[ ! -f .env.ssl ]]; then
    echo "Brak pliku .env.ssl. Skopiuj .env.ssl.example do .env.ssl i ustaw LETSENCRYPT_EMAIL." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.ssl
set +a

: "${LETSENCRYPT_EMAIL:?Ustaw LETSENCRYPT_EMAIL w .env.ssl}"
LETSENCRYPT_DOMAIN="${LETSENCRYPT_DOMAIN:-behawiorysta.warszawa.pl}"
LETSENCRYPT_WWW_DOMAIN="${LETSENCRYPT_WWW_DOMAIN:-www.behawiorysta.warszawa.pl}"

if [[ "$LETSENCRYPT_DOMAIN" != "behawiorysta.warszawa.pl" ]] || \
   [[ "$LETSENCRYPT_WWW_DOMAIN" != "www.behawiorysta.warszawa.pl" ]]; then
    echo "Domeny muszą odpowiadać nazwom i ścieżkom ustawionym w nginx.conf." >&2
    exit 1
fi

mkdir -p data/certbot/conf data/certbot/www
"${COMPOSE[@]}" up -d --build django-web nginx

if [[ ! -f "data/certbot/conf/live/${LETSENCRYPT_DOMAIN}/fullchain.pem" ]]; then
    "${COMPOSE[@]}" run --rm certbot certonly \
        --webroot --webroot-path /var/www/certbot \
        --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email \
        --domain "$LETSENCRYPT_DOMAIN" \
        --domain "$LETSENCRYPT_WWW_DOMAIN"
fi

"${COMPOSE[@]}" exec nginx /bin/sh /usr/local/bin/enable-https
"${COMPOSE[@]}" up -d

echo "Certyfikat Let's Encrypt jest aktywny."
echo "Uruchom teraz: sudo bash deploy/install-certbot-cron.sh"
