# Local WordPress implementation plan

**Goal:** Run the downloaded WordPress project from this directory at localhost:8777 and corresponding subdomains, with automatic dump import and local URL migration.

**Architecture:** Two services: WordPress PHP 8.3/Apache and MariaDB 11.4. Bind mount project files and a separate local wp-config.php. Use the image's isolated WordPress core for WP-CLI migration so production plugins, domain mapping and old multisite domains cannot prevent migration.

**Constraints:** Preserve the host wp-config.php and original dumps; retain subdomains; use HTTP locally; migrate serialized values safely; import only on an empty database volume; do not copy fresh core into the project; fail clearly if WordPress or dump files are missing.

## Tasks

- [x] Write failing behavioral tests for reading the original table prefix and mapping root/subdomain URLs, serialized values, email and unrelated-domain exclusions.
- [x] Add Dockerfile, compose.yaml, local configuration, Apache rules and initialization scripts. Check shell/PHP syntax and Docker Compose configuration.
- [x] Build the image and exercise startup using a temporary isolated multisite fixture and SQL dump. Verify SQL import, root/subdomain HTTP requests, serialized data, restart persistence, and a missing-files error. Never use or reset the real project database for tests.
- [x] Document startup, dump formats, subdomain hosts fallback, configuration and explicit database reset. Report actual checks and the limitation that downloaded production files are not yet available.

Execute inline in the current directory: the user requested infrastructure here and the directory is not a Git checkout.
