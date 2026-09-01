"""Static validation of the production Docker assets.

These do not start containers - the full stack smoke test lives in
``scripts/prod-smoke-test.sh`` (run in CI and locally). They only check that
the compose file and the smoke script are internally valid.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.prod.yml"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "prod-smoke-test.sh"

# CI-safe dummy values - never real secrets.
DUMMY_ENV = {
    "SECRET_KEY": "ci-dummy-secret-key-not-real",
    "ALLOWED_HOSTS": "localhost",
    "DB_NAME": "nexus",
    "DB_USER": "nexus",
    "DB_PASSWORD": "ci-dummy-db-password",
}


def test_production_compose_file_exists():
    assert COMPOSE_FILE.is_file()


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")
def test_production_compose_config_is_valid():
    import os

    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
        cwd=REPO_ROOT,
        env={**os.environ, **DUMMY_ENV},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_smoke_test_script_exists_and_is_syntactically_valid():
    assert SMOKE_SCRIPT.is_file()
    shell = shutil.which("bash") or shutil.which("sh")
    if shell:
        result = subprocess.run([shell, "-n", str(SMOKE_SCRIPT)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
