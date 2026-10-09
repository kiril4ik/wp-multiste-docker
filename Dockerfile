FROM wordpress:php8.3-apache

ARG WP_CLI_VERSION=2.12.0
RUN curl -fsSL "https://github.com/wp-cli/wp-cli/releases/download/v${WP_CLI_VERSION}/wp-cli-${WP_CLI_VERSION}.phar" \
        -o /usr/local/bin/wp \
    && chmod +x /usr/local/bin/wp

COPY docker/ /opt/local-wordpress/
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/local-development.ini
COPY docker/wp-config.php /usr/src/wordpress/wp-config.php

WORKDIR /var/www/html
ENTRYPOINT ["/bin/sh", "/opt/local-wordpress/entrypoint.sh"]
CMD ["apache2-foreground"]
