#!/bin/sh
set -eu

test -f /etc/letsencrypt/live/behawiorysta.warszawa.pl/fullchain.pem
test -f /etc/letsencrypt/live/behawiorysta.warszawa.pl/privkey.pem
cp /etc/nginx/project/nginx.conf /etc/nginx/nginx.conf
nginx -t
nginx -s reload
