<?php
// Guards against using wp_ for a custom-prefix dump, or rewriting email/unrelated hosts.
require dirname(__DIR__) . '/settings.php';

function check($actual, $expected): void {
    if ($actual !== $expected) {
        throw new RuntimeException(var_export($actual, true) . ' != ' . var_export($expected, true));
    }
}

$original = <<<'PHP'
<?php
// $table_prefix = 'wrong_';
$table_prefix = 'custom_';
define('MULTISITE', true);
define('SUBDOMAIN_INSTALL', true);
define('BLOG_ID_CURRENT_SITE', 3);
PHP;
check(local_config_value($original, 'table_prefix', 'wp_'), 'custom_');
check(local_config_value($original, 'MULTISITE', false), true);
check(local_config_value($original, 'BLOG_ID_CURRENT_SITE', 1), 3);
check(local_config_value('', 'table_prefix', 'wp_'), 'wp_');

$rules = local_domain_rules('example.test', 'localhost:8777');
foreach ([
    ['https://example.test/page', 'http://localhost:8777/page'],
    ['http://shop.example.test/a', 'http://shop.localhost:8777/a'],
    ['https://a.b.example.test:443/a', 'http://a.b.localhost:8777/a'],
    ['//shop.example.test/image.png', '//shop.localhost:8777/image.png'],
    ['shop.example.test', 'shop.localhost:8777'],
    ['example.test', 'localhost:8777'],
    ['admin@example.test admin@shop.example.test', 'admin@example.test admin@shop.example.test'],
    ['https://example.test.evil.test/', 'https://example.test.evil.test/'],
    ['https://otherexample.test/', 'https://otherexample.test/'],
    ['https:\/\/shop.example.test\/a', 'http:\/\/shop.localhost:8777\/a'],
] as [$input, $expected]) {
    $actual = $input;
    foreach ($rules as [$pattern, $replacement]) {
        $actual = preg_replace('~' . $pattern . '~i', $replacement, $actual);
    }
    check($actual, $expected);
}
echo "Settings and domain rules: OK\n";
