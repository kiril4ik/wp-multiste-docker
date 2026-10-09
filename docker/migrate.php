<?php
$replace = getenv('MAKE_REPALCE');
if ($replace !== false && !filter_var($replace, FILTER_VALIDATE_BOOLEAN)) {
    echo "Domain replacement is disabled (MAKE_REPALCE=false).\n";
    exit(0);
}
$source = trim(getenv('PROD_DOMAIN') ?: '');
if ($source === '' || !filter_var($source, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME)) {
    throw new RuntimeException('Set PROD_DOMAIN to a hostname without a scheme, port or path in .env.');
}
require '/opt/local-wordpress/settings.php';

$original = is_file('/workspace/wp-config.php') ? file_get_contents('/workspace/wp-config.php') : '';
$prefix = getenv('WP_TABLE_PREFIX') ?: local_config_value($original, 'table_prefix', 'wp_');
if (!preg_match('/^[a-zA-Z0-9_]+$/', $prefix)) {
    throw new RuntimeException('Invalid WP_TABLE_PREFIX.');
}
$db = new mysqli(getenv('WORDPRESS_DB_HOST'), getenv('WORDPRESS_DB_USER'), getenv('WORDPRESS_DB_PASSWORD'), getenv('WORDPRESS_DB_NAME'));
$db->set_charset('utf8mb4');
$options = '`' . $prefix . 'options`';
try {
    $previous = $db->query("SELECT option_value FROM $options WHERE option_name = '_docker_local_domain_migration'")->fetch_assoc();
} catch (mysqli_sql_exception $error) {
    throw new RuntimeException("Missing {$prefix}options table. Check the dump's database name and WP_TABLE_PREFIX.", 0, $error);
}
$target = getenv('WP_LOCAL_DOMAIN') ?: 'localhost:8777';
$marker = 'v2:' . hash('sha256', strtolower($source) . "\n" . $target);
if (($previous['option_value'] ?? '') === $marker) {
    echo "Local domain migration already applied.\n";
    exit(0);
}

putenv('WP_LOCAL_MIGRATION=1');
// Avoid discovering production wp-cli.yml or loading production plugins/drop-ins.
chdir('/tmp');
$base = ['wp', '--allow-root', '--path=/usr/src/wordpress', '--skip-plugins', '--skip-themes'];
function run_wp(array $arguments): void {
    global $base;
    $process = proc_open(array_merge($base, $arguments), [STDIN, STDOUT, STDERR], $pipes);
    if (!is_resource($process) || proc_close($process) !== 0) {
        throw new RuntimeException('WP-CLI migration failed; Apache has not started.');
    }
}

echo "Migrating production domains to $target ...\n";
echo "Apache starts after migration finishes; large databases may take several minutes.\n";
foreach (local_domain_rules($source, $target) as $step => [$pattern, $replacement]) {
    echo 'Domain replacement pass ' . ($step + 1) . " of 2 ...\n";
    run_wp(['search-replace', $pattern, $replacement, '--regex', '--regex-flags=i', '--all-tables-with-prefix', '--precise', '--report-changed-only']);
}
run_wp(['option', 'update', '_docker_local_domain_migration', $marker, '--autoload=no']);
echo "Local domain migration complete.\n";
