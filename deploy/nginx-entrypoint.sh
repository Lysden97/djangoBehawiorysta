#!/bin/sh
set -eu

CERTIFICATE=/etc/letsencrypt/live/${LETSENCRYPT_DOMAIN:?}/fullchain.pem

if [ -f "$CERTIFICATE" ]; then
    /bin/sh /usr/local/bin/render-nginx /etc/nginx/project/nginx.conf
else
    /bin/sh /usr/local/bin/render-nginx /etc/nginx/project/nginx.bootstrap.conf
fi

exec nginx -g 'daemon off;'
