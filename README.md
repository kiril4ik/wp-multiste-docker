# Local WordPress

This Docker setup runs an existing WordPress project locally for development and debugging. It imports a database dump, optionally replaces production domains with local addresses, supports Multisite subdomains on port 8777, and disables WordPress/PHP mail by default while keeping internet access available.

PHP 8.3 + Apache and MariaDB 11.4 run in two containers. The current directory is mounted at `/var/www/html`; file changes are visible immediately.

## First startup

1. Extract the project directly into this directory. `index.php`, `wp-load.php`, `wp-admin/`, `wp-includes/` and `wp-content/` must be next to `compose.yaml`.
2. Put a dump of the project's database in `./db-dump/`. Supported formats: `.sql`, `.sql.gz`, `.sql.xz`, `.sql.zst`. Extract ZIP archives first. Keep only one copy of each dump: all matching files are imported.
3. Review `.env` for this project. For another project, copy `.env.example` to `.env` and set `PROD_DOMAIN` and the flags below.
4. Start the services:

   ```sh
   docker compose up -d --build
   docker compose logs -f db wordpress
   ```

5. Wait for `Local domain migration complete` (or `Domain replacement is disabled` when disabled) and Apache startup, then open `http://localhost:8777`.

The web container can be running while URL migration is still in progress. Apache starts after migration completes; requests made earlier may return `ERR_EMPTY_RESPONSE`. Its HTTP health check stays in `starting` until the login page responds. To wait for both services to become ready:

```sh
docker compose up -d --build --wait --wait-timeout 1800
```

Use `docker compose ps` to check readiness and `docker compose logs -f wordpress` to follow the two migration passes. Do not interrupt the initial import or migration merely because the containers are still starting.

MariaDB creates the `wordpress` database and imports the dump only when the `db_data` volume is empty. WordPress waits for MariaDB, then uses WP-CLI to update addresses in every table with the project's prefix, including serialized settings. Migration can take time on a large database. Regular restarts preserve the database and skip an already completed migration.

If the dump contains `CREATE DATABASE` / `USE` statements with the original database name, set `DB_NAME` in `.env` to that name **before the first startup**, or use a dump without those statements. The dump must contain one project database.

Original dumps and the host's `wp-config.php` are preserved. Missing WordPress files or an empty dump directory on first startup produce an explicit log error.

## Domains

| Production address | Local address |
| --- | --- |
| `https://example.test` | `http://localhost:8777` |
| `https://shop.example.test` | `http://shop.localhost:8777` |
| `https://a.b.example.test` | `http://a.b.localhost:8777` |

Subdomain prefixes are preserved, HTTPS is converted to HTTP, and the port is included in URLs and Multisite domain fields. Email addresses are preserved. All sites **already present in the database** are served by the same Apache instance on port 8777. Using a new hostname does not create a new WordPress site. Independently mapped domains outside `example.test` need additional mappings.

If your browser does not resolve a required `*.localhost` hostname, add the specific names to `/etc/hosts`:

```text
127.0.0.1 localhost shop.localhost a.b.localhost
```

`/etc/hosts` does not support wildcard entries. Test routing without changing DNS:

```sh
curl --resolve shop.localhost:8777:127.0.0.1 http://shop.localhost:8777/
```

## Configuration

Project settings live in `.env`, which is excluded from Git. To configure a new project:

```sh
cp .env.example .env
```

The flag names below intentionally use the requested spelling:

```dotenv
MAKE_REPALCE=true
PROD_DOMAIN=example.test
IS_MULTISTE=true
DISABLE_MAIL=true
```

- `MAKE_REPALCE=true` replaces `PROD_DOMAIN` and its subdomains with local addresses at startup. `false` skips replacement and leaves database URLs unchanged. It does not undo a previous replacement.
- `PROD_DOMAIN` is the production hostname without a scheme, port or path. It is required when replacement is enabled. Change it in `.env` for each project.
- `IS_MULTISTE=true` enables WordPress Multisite. Set it to `false` for a single-site installation.
- `DISABLE_MAIL=true` disables WordPress mail, WP Mail SMTP sending and PHP's `mail()` transport. Internet access remains available. Set it to `false` to remove these local mail blocks.

The domains shown in this README and the tests are generic examples. Replacement runs once per production/local domain pair; changing `PROD_DOMAIN` runs a new replacement against the current database.

`DB_NAME`, `DB_USER`, `DB_PASSWORD` and `DB_ROOT_PASSWORD` configure local database credentials. WordPress connects to `db:3306`; the database port is not published to the host. The web port is bound to `127.0.0.1:8777`.

Inside the container, `docker/wp-config.php` overrides the original `wp-config.php`. It reads literal values for `$table_prefix`, `SUBDOMAIN_INSTALL` and current-network settings from the original file. The network's `DOMAIN_CURRENT_SITE` is mapped using `PROD_DOMAIN` while preserving its subdomain; the original main-site and network IDs are preserved. `IS_MULTISTE` controls whether Multisite is enabled, regardless of the original config. Without an original config, the default table prefix is `wp_`. To specify a custom prefix or run a single-site installation, set these in `.env`:

```dotenv
WP_TABLE_PREFIX=custom_
IS_MULTISTE=false
```

Other production configuration is not executed automatically. If the project needs custom constants or paths, add the corresponding local values to `docker/wp-config.php`. `WP_HOME` and `WP_SITEURL` are not forced to one shared address: each network site uses its own database URL. Production `SUNRISE`, configuration-based caching and forced SSL are disabled.

Email sending through WordPress and PHP is disabled by default with `DISABLE_MAIL=true`. `WPMS_ON` and `WPMS_DO_NOT_SEND` are enabled, the `pre_wp_mail` filter rejects WordPress mail even without the SMTP plugin, and PHP's sendmail transport is set to `/bin/false`. Internet access, updates and external API calls remain available. Custom code that sends directly through SMTP or an email HTTP API bypasses these application-level blocks and must be disabled separately.

After changing `.env`, apply the settings with `docker compose up -d --build --wait --wait-timeout 1800`. `DISABLE_MAIL=false` removes the local blocks; it does not install or configure a mail transport.

Apache uses local rewrite rules and ignores the original `.htaccess` so production domain/HTTPS redirects do not interfere. The `db-dump/`, `docker/` and `docs/` directories, hidden files and archives are blocked from HTTP access. Project plugins may need additional local configuration after the actual files are downloaded.

## Stop and reimport

Stop while preserving the database:

```sh
docker compose down
```

To **delete the entire local database** and reimport the current contents of `db-dump/`:

```sh
docker compose down -v
docker compose up -d --build
```

This discards local database changes. Project files and dumps remain. A reset is also required after a failed first import: MariaDB does not automatically reimport into an existing volume.

## Verification

```sh
docker compose config --quiet
docker compose build
docker run --rm --entrypoint php multisite-wordpress:local /opt/local-wordpress/tests/settings.php
python3 docker/tests/configuration.py
python3 docker/tests/integration.py
```

The integration test uses temporary files, a separate database and an available HTTP port. It removes only its own test containers and volume and never starts the downloaded production project.
