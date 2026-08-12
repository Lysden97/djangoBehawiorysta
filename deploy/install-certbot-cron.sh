#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Uruchom ten skrypt przez sudo." >&2
    exit 1
fi

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CRON_FILE=/etc/cron.d/django-behawiorysta-certbot

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

17 3 * * * root /bin/bash ${PROJECT_DIR}/deploy/renew-certificate.sh >> /var/log/django-behawiorysta-certbot.log 2>&1
EOF

chmod 0644 "$CRON_FILE"
echo "Zainstalowano codzienne odnawianie w $CRON_FILE."
