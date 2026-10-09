<?php
// Register before plugins load; WordPress converts these arrays into WP_Hook objects.
$block_local_mail = static function () {
    return false;
};
foreach ([PHP_INT_MIN, PHP_INT_MAX] as $priority) {
    if (function_exists('add_filter')) {
        add_filter('pre_wp_mail', $block_local_mail, $priority, 0);
    } else {
        $GLOBALS['wp_filter']['pre_wp_mail'][$priority][] = [
            'function' => $block_local_mail,
            'accepted_args' => 0,
        ];
    }
}
