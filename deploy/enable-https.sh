#!/bin/sh
set -eu

test -f /etc/letsencrypt/live/${LETSENCRYPT_DOMAIN:?}/fullchain.pem
test -f /etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/privkey.pem
/bin/sh /usr/local/bin/render-nginx /etc/nginx/project/nginx.conf
nginx -t
nginx -s reload
