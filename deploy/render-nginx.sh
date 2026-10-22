#!/bin/sh
set -eu
: "${LETSENCRYPT_DOMAIN:?Set LETSENCRYPT_DOMAIN in .env.ssl}"
LETSENCRYPT_WWW_DOMAIN=${LETSENCRYPT_WWW_DOMAIN:-}
export LETSENCRYPT_WWW_DOMAIN
for domain in "$LETSENCRYPT_DOMAIN" "$LETSENCRYPT_WWW_DOMAIN"; do
    case "$domain" in *[!a-zA-Z0-9.-]*) echo "Invalid domain" >&2; exit 1;; esac
done
# Explicit allowlist preserves Nginx variables such as $host and $request_uri.
envsubst '${LETSENCRYPT_DOMAIN} ${LETSENCRYPT_WWW_DOMAIN}' < "$1" > /etc/nginx/nginx.conf
