#!/usr/bin/env python3
"""Exercise the real services with disposable files, database and HTTP port."""
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


with tempfile.TemporaryDirectory(prefix="multisite-docker-test-") as temporary:
    fixture = Path(temporary)
    site = fixture / "site"
    dumps = fixture / "dumps"
    site.mkdir()
    dumps.mkdir()
    (dumps / "seed.sql").write_text("SELECT 1;\n")
    original = "<?php\n$table_prefix = 'custom_';\ndefine('MULTISITE', true);\ndefine('SUBDOMAIN_INSTALL', true);\n"
    (site / "wp-config.php").write_text(original)

    config = json.loads(run(["docker", "compose", "config", "--format", "json"], cwd=ROOT, capture_output=True).stdout)
    image = config["services"]["wordpress"]["image"] if "image" in config["services"]["wordpress"] else "multisite-wordpress"
    config["name"] = "multisite-test-" + str(time.time_ns())
    config["networks"]["default"]["name"] = config["name"] + "_default"
    web = config["services"]["wordpress"]
    web.pop("build", None)
    web["image"] = image
    web["ports"] = [{"target": 80, "published": "0", "host_ip": "127.0.0.1", "protocol": "tcp"}]
    web["volumes"] = [
        {"type": "bind", "source": str(site), "target": "/var/www/html"},
        {"type": "bind", "source": str(site), "target": "/workspace", "read_only": True},
        {"type": "bind", "source": str(ROOT / "docker/wp-config.php"), "target": "/var/www/html/wp-config.php", "read_only": True},
    ]
    web["environment"].update(WORDPRESS_DB_NAME="wordpress", WORDPRESS_DB_USER="wordpress", WORDPRESS_DB_PASSWORD="wordpress_local", WP_TABLE_PREFIX="", MAKE_REPALCE="true", PROD_DOMAIN="example.test", IS_MULTISTE="true", DISABLE_MAIL="true")
    config["services"]["db"].pop("build", None)
    config["services"]["db"]["environment"].update(MARIADB_DATABASE="wordpress", MARIADB_USER="wordpress", MARIADB_PASSWORD="wordpress_local", MARIADB_ROOT_PASSWORD="root_local")
    config["services"]["db"]["volumes"][1]["source"] = str(dumps)
    # Resolved Compose output contains globally named volumes; isolate them explicitly.
    config["volumes"]["db_data"]["name"] = config["name"] + "_db_data"
    config_file = fixture / "compose.json"
    config_file.write_text(json.dumps(config))
    base = ["docker", "compose", "-f", str(config_file)]

    def compose(*args, **kwargs):
        return run(base + list(args), **kwargs)

    def wp(*args, single=False, url="http://example.test", capture=False, disable_mail="true"):
        return compose("run", "--rm", "--no-deps", "-T", "-e", "WP_LOCAL_DOMAIN=example.test", "-e", "WP_LOCAL_MIGRATION=" + ("1" if single else "0"),
                       "-e", "DISABLE_MAIL=" + disable_mail, "wordpress", "wp", "--allow-root", "--path=/usr/src/wordpress", "--skip-plugins", "--skip-themes", "--url=" + url,
                       *args, capture_output=capture)

    def get(host, path="/"):
        request = urllib.request.Request("http://" + address + path, headers={"Host": host})
        try:
            return urllib.request.build_opener(NoRedirect).open(request, timeout=10)
        except urllib.error.HTTPError as response:
            return response

    try:
        compose("up", "-d", "--wait", "--wait-timeout", "180", "db")
        wp("core", "multisite-install", "--subdomains", "--skip-config", "--title=ROOT-FIXTURE", "--admin_user=fixture", "--admin_password=fixture_local_password", "--admin_email=fixture@example.test", "--skip-email", single=True)
        wp("eval", 'if (apply_filters("pre_wp_mail", null, []) !== false) { throw new RuntimeException("WordPress mail is not blocked"); } if (ini_get("sendmail_path") !== "/bin/false") { throw new RuntimeException("PHP mail transport is not disabled"); }')
        for disabled in ("false", "0"):
            wp("eval", 'if (apply_filters("pre_wp_mail", null, []) !== null || defined("WPMS_DO_NOT_SEND")) { throw new RuntimeException("DISABLE_MAIL=false did not remove WordPress mail blocks"); } if (ini_get("sendmail_path") === "/bin/false") { throw new RuntimeException("DISABLE_MAIL=false did not remove the PHP transport block"); }', disable_mail=disabled)
        wp("site", "create", "--slug=shop", "--title=SHOP-FIXTURE")
        wp("option", "update", "local_fixture", '{"url":"https://shop.example.test/media","email":"admin@example.test","nested":{"url":"https://example.test/page"}}', "--format=json")
        wp("option", "update", "siteurl", "https://shop.example.test", url="http://shop.example.test")
        wp("option", "update", "home", "https://shop.example.test", url="http://shop.example.test")
        # A network whose main domain has a prefix must retain that prefix locally.
        (site / "wp-config.php").write_text(original + "define('DOMAIN_CURRENT_SITE', 'shop.example.test');\n")
        network = compose("run", "--rm", "--no-deps", "-T", "--entrypoint", "php", "wordpress", "-r",
                          'file_put_contents("/tmp/wp-settings.php", ""); define("ABSPATH", "/tmp/"); require "/var/www/html/wp-config.php"; echo DOMAIN_CURRENT_SITE;', capture_output=True)
        assert network.stdout == "shop.localhost:8777", network.stdout
        (site / "wp-config.php").write_text(original)
        # The flag must override the original config's MULTISITE=true value.
        compose("run", "--rm", "--no-deps", "-T", "-e", "IS_MULTISTE=false", "--entrypoint", "wp", "wordpress",
                "--allow-root", "--path=/usr/src/wordpress", "--skip-plugins", "--skip-themes", "eval",
                "if (is_multisite()) { throw new RuntimeException('IS_MULTISTE=false was ignored'); }")
        sql = compose("exec", "-T", "db", "mariadb-dump", "--user=wordpress", "--password=wordpress_local", "--skip-comments", "wordpress", capture_output=True).stdout
        (dumps / "seed.sql").unlink()
        with gzip.open(dumps / "fixture.sql.gz", "wt") as dump:
            dump.write(sql)
        # Remove only this test's volume, then exercise first-start dump import.
        compose("down", "-v")
        run(["docker", "run", "--rm", "--entrypoint", "sh", "-v", str(site) + ":/fixture", image,
             "-c", "tar -C /usr/src/wordpress --exclude=wp-config.php -cf - . | tar -C /fixture -xf -"])
        compose("up", "-d", "--wait", "--wait-timeout", "180", "db")
        disabled = compose("run", "--rm", "--no-deps", "-T", "-e", "MAKE_REPALCE=false", "wordpress",
                           "php", "/opt/local-wordpress/migrate.php", capture_output=True)
        assert "Domain replacement is disabled" in disabled.stdout
        untouched = wp("option", "get", "home", single=True, capture=True).stdout.strip()
        assert untouched == "http://example.test", untouched
        compose("up", "-d", "--wait", "--wait-timeout", "180")
        container = compose("ps", "-q", "wordpress", capture_output=True).stdout.strip()
        health = run(["docker", "inspect", container, "--format", "{{.State.Health.Status}}"], capture_output=True).stdout.strip()
        assert health == "healthy", health
        compose("exec", "-T", "wordpress", "curl", "--fail", "--silent", "--show-error", "--max-time", "15", "https://api.wordpress.org/", "--output", "/dev/null")
        address = compose("port", "wordpress", "80", capture_output=True).stdout.strip()
        for attempt in range(60):
            try:
                root_response = get("localhost:8777")
                if root_response.status == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            raise AssertionError("Root site did not become available")
        assert "ROOT-FIXTURE" in root_response.read().decode()
        shop_response = get("shop.localhost:8777")
        assert shop_response.status == 200, shop_response.status
        assert "SHOP-FIXTURE" in shop_response.read().decode()
        admin_redirect = get("shop.localhost:8777", "/wp-admin")
        assert admin_redirect.status == 301, admin_redirect.status
        assert admin_redirect.getheader("Location") == "http://shop.localhost:8777/wp-admin/", admin_redirect.getheader("Location")
        assert get("localhost:8777", "/wp-login.php").status == 200
        assert get("shop.localhost:8777", "/wp-login.php").status == 200
        assert get("localhost:8777", "/db-dump/fixture.sql.gz").status == 403
        assert get("localhost:8777", "/.env").status == 403
        assert get("localhost:8777", "/docker/wp-config.php").status == 403

        result = compose("exec", "-T", "wordpress", "wp", "--allow-root", "--path=/var/www/html", "--url=http://localhost:8777", "option", "get", "local_fixture", "--format=json", capture_output=True)
        assert json.loads(result.stdout) == {"url": "http://shop.localhost:8777/media", "email": "admin@example.test", "nested": {"url": "http://localhost:8777/page"}}
        assert (site / "wp-config.php").read_text() == original
        # Missing source files must fail, rather than install a fresh WordPress.
        (site / "wp-load.php").rename(site / "wp-load.php.hidden")
        missing = subprocess.run(base + ["run", "--rm", "--no-deps", "-T", "wordpress"], capture_output=True, text=True)
        assert missing.returncode != 0 and "WordPress files are missing" in missing.stderr
        (site / "wp-load.php.hidden").rename(site / "wp-load.php")
        # Removing the dump must not affect an already initialized database.
        (dumps / "fixture.sql.gz").unlink()
        compose("down")
        compose("up", "-d", "--wait", "--wait-timeout", "180")
        address = compose("port", "wordpress", "80", capture_output=True).stdout.strip()
        for attempt in range(30):
            try:
                if get("shop.localhost:8777").status == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            raise AssertionError("Restart did not preserve the database")
        logs = compose("logs", "wordpress", capture_output=True).stdout
        assert "Local domain migration already applied" in logs
        print("PASS: configurable production domain, replacement/multisite/mail flags, internet access, compressed dump import, custom prefix, root/subdomain sites and login, serialized values, protected files, original config, missing files and restart persistence")
    except Exception:
        compose("logs", "--tail", "80")
        raise
    finally:
        compose("down", "-v", "--remove-orphans")
