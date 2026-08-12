#!/bin/sh
set -eu

CERTIFICATE=/etc/letsencrypt/live/behawiorysta.warszawa.pl/fullchain.pem

if [ -f "$CERTIFICATE" ]; then
    cp /etc/nginx/project/nginx.conf /etc/nginx/nginx.conf
else
    cp /etc/nginx/project/nginx.bootstrap.conf /etc/nginx/nginx.conf
fi

exec nginx -g 'daemon off;'
