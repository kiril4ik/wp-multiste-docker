<?php

// Read literal values without executing the production configuration.
function local_config_value(string $source, string $name, $default) {
    $source = implode('', array_map(static function ($token) {
        return is_array($token)
            ? (in_array($token[0], [T_COMMENT, T_DOC_COMMENT], true) ? '' : $token[1])
            : $token;
    }, token_get_all($source)));

    if ($name === 'table_prefix') {
        return preg_match('/\$table_prefix\s*=\s*([\'"])([a-zA-Z0-9_]+)\1\s*;/', $source, $match)
            ? $match[2] : $default;
    }
    $pattern = '/define\s*\(\s*([\'"])' . preg_quote($name, '/')
        . '\1\s*,\s*(true|false|[0-9]+|\'[^\']*\'|"[^"]*")\s*\)/i';
    if (!preg_match($pattern, $source, $match)) {
        return $default;
    }
    $value = $match[2];
    if (strtolower($value) === 'true' || strtolower($value) === 'false') {
        return strtolower($value) === 'true';
    }
    return ctype_digit($value) ? (int) $value : substr($value, 1, -1);
}

function local_domain_rules(string $source, string $target): array {
    $domain = preg_quote($source, '~');
    $subdomains = '((?:[a-z0-9-]+\.)*)';
    $end = '(?::[0-9]+)?(?![a-z0-9_.-])';
    return [
        // Preserve normal and JSON-escaped slashes; use HTTP for local URLs.
        ['\bhttps?:(//|\\\\/\\\\/)' . $subdomains . $domain . $end, 'http:${1}${2}' . $target],
        // Includes wp_blogs/wp_site domains, but excludes emails and other hosts.
        ['(?<![a-z0-9_@.-])' . $subdomains . $domain . $end, '${1}' . $target],
    ];
}
