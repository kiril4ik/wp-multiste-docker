<?php
require_once '/opt/local-wordpress/settings.php';

$original = is_file('/workspace/wp-config.php') ? file_get_contents('/workspace/wp-config.php') : '';
$table_prefix = getenv('WP_TABLE_PREFIX') ?: local_config_value($original, 'table_prefix', 'wp_');
if (!preg_match('/^[a-zA-Z0-9_]+$/', $table_prefix)) {
    throw new RuntimeException('WP_TABLE_PREFIX may contain only letters, digits and underscores.');
}

define('DB_NAME', getenv('WORDPRESS_DB_NAME') ?: 'wordpress');
define('DB_USER', getenv('WORDPRESS_DB_USER') ?: 'wordpress');
define('DB_PASSWORD', getenv('WORDPRESS_DB_PASSWORD') ?: 'wordpress_local');
define('DB_HOST', getenv('WORDPRESS_DB_HOST') ?: 'db');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');
define('WP_ENVIRONMENT_TYPE', 'local');
define('WP_CACHE', false);
define('FORCE_SSL_ADMIN', false);
$disable_mail_setting = getenv('DISABLE_MAIL');
$disable_mail = $disable_mail_setting === false || $disable_mail_setting === ''
    ? true
    : (filter_var($disable_mail_setting, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE) ?? true);
if ($disable_mail) {
    // Disable WP Mail SMTP sending in the local environment.
    define('WPMS_ON', true);
    define('WPMS_DO_NOT_SEND', true);
}
// Host-only cookies: cookie domains cannot contain :8777.
define('COOKIE_DOMAIN', false);

foreach (['AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY', 'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT'] as $salt) {
    define($salt, hash('sha256', 'local-wordpress:' . $salt . ':' . DB_PASSWORD));
}

$multisite = getenv('IS_MULTISTE');
$multisite = $multisite !== false && $multisite !== ''
    ? filter_var($multisite, FILTER_VALIDATE_BOOLEAN)
    : true;
// Run migration using the clean core in single-site mode, before local network domains exist.
if (getenv('WP_LOCAL_MIGRATION') !== '1' && $multisite) {
    define('WP_ALLOW_MULTISITE', true);
    define('MULTISITE', true);
    define('SUBDOMAIN_INSTALL', local_config_value($original, 'SUBDOMAIN_INSTALL', true));
    $local_domain = getenv('WP_LOCAL_DOMAIN') ?: 'localhost:8777';
    $network_domain = local_config_value($original, 'DOMAIN_CURRENT_SITE', $local_domain);
    $production_domain = getenv('PROD_DOMAIN') ?: '';
    if ($production_domain !== '') {
        foreach (local_domain_rules($production_domain, $local_domain) as [$pattern, $replacement]) {
            $network_domain = preg_replace('~' . $pattern . '~i', $replacement, $network_domain);
        }
    }
    define('DOMAIN_CURRENT_SITE', $network_domain);
    define('PATH_CURRENT_SITE', local_config_value($original, 'PATH_CURRENT_SITE', '/'));
    define('SITE_ID_CURRENT_SITE', local_config_value($original, 'SITE_ID_CURRENT_SITE', 1));
    define('BLOG_ID_CURRENT_SITE', local_config_value($original, 'BLOG_ID_CURRENT_SITE', 1));
}

if (!defined('ABSPATH')) {
    define('ABSPATH', __DIR__ . '/');
}
if ($disable_mail) {
    require_once '/opt/local-wordpress/disable-mail.php';
}
require_once ABSPATH . 'wp-settings.php';
