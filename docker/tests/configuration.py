#!/usr/bin/env python3
"""Check the migration switch before any database or WordPress bootstrap."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
for disabled in ("false", "0"):
    result = subprocess.run(
        ["php", str(ROOT / "docker/migrate.php")],
        env={**os.environ, "MAKE_REPALCE": disabled, "PROD_DOMAIN": ""},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Domain replacement is disabled" in result.stdout, result.stdout
print("Migration disabled without a database or production domain: OK")

for domain in ("", "https://example.test/path"):
    result = subprocess.run(
        ["php", str(ROOT / "docker/migrate.php")],
        env={**os.environ, "MAKE_REPALCE": "true", "PROD_DOMAIN": domain},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Set PROD_DOMAIN to a hostname" in result.stderr, result.stderr
print("Enabled migration rejects a missing or malformed production hostname: OK")
