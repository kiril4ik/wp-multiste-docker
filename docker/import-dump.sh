#!/bin/sh
# MariaDB sources this script with docker_process_init_files already available.
local_wp_dump_found=false
for local_wp_dump in /dumps/*.sql /dumps/*.sql.gz /dumps/*.sql.xz /dumps/*.sql.zst; do
    if [ -f "$local_wp_dump" ]; then
        local_wp_dump_found=true
        docker_process_init_files "$local_wp_dump"
    fi
done
if [ "$local_wp_dump_found" = false ]; then
    echo >&2 'No SQL dump found. Put a .sql or .sql.gz dump in ./db-dump before the first startup.'
    exit 1
fi
