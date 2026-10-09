#!/bin/sh
set -eu

case "${DISABLE_MAIL:-true}" in
    false|FALSE|0|off|OFF|no|NO)
        rm -f /usr/local/etc/php/conf.d/local-mail.ini
        ;;
    *)
        printf '%s\n' 'sendmail_path = /bin/false' > /usr/local/etc/php/conf.d/local-mail.ini
        ;;
esac

if [ "${1:-}" = 'apache2-foreground' ]; then
    if [ ! -f /var/www/html/wp-load.php ] || [ ! -f /var/www/html/wp-includes/version.php ]; then
        echo >&2 'WordPress files are missing. Extract the project into the directory containing compose.yaml, then run docker compose up -d.'
        exit 1
    fi
    php /opt/local-wordpress/migrate.php
fi

exec "$@"
