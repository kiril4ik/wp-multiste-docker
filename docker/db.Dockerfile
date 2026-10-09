FROM mariadb:11.4

# A real image file gives consistent executable-bit behavior on Docker Desktop.
COPY --chmod=0644 docker/import-dump.sh /docker-entrypoint-initdb.d/10-import-dump.sh
