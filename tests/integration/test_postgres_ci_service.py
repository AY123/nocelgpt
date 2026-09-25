"""PostgreSQL CI service validation - uses GitLab CI provided service, not docker-compose.

This test is designed for CI environments where postgres is provided as a service.
For local docker-compose testing, see test_postgres_environment.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/check_postgres.py"


def test_ci_postgres_service_connection():
    """Verify PostgreSQL service is accessible in CI environment.

    Expects ANOVELOS_TEST_DSN to be set by CI configuration.
    """
    dsn = os.environ.get("ANOVELOS_TEST_DSN")
    if not dsn:
        pytest.skip("ANOVELOS_TEST_DSN not set - not in CI environment with postgres service")

    # Run check_postgres.py probe
    result = subprocess.run(
        [sys.executable, str(PROBE)],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"check_postgres failed: {result.stderr}"

    probe_result = json.loads(result.stdout)
    assert probe_result["driver"] == "postgresql+psycopg"
    assert probe_result["database"] == "bootstrap_test"
    assert probe_result["server_version_num"] >= 170000

    print(f"✓ PostgreSQL probe: {probe_result}")


def test_ci_postgres_service_concurrent_connections():
    """Verify concurrent connections work correctly."""
    dsn = os.environ.get("ANOVELOS_TEST_DSN")
    if not dsn:
        pytest.skip("ANOVELOS_TEST_DSN not set")

    engine = create_engine(dsn, pool_pre_ping=True)
    try:
        with engine.connect() as conn1, engine.connect() as conn2:
            pid1 = conn1.execute(text("SELECT pg_backend_pid()")).scalar_one()
            pid2 = conn2.execute(text("SELECT pg_backend_pid()")).scalar_one()

            # Different connections should have different backend PIDs
            assert pid1 != pid2, "Concurrent connections should use different backend processes"

            # Verify basic query works
            result = conn1.execute(text("SELECT 1 + 1 AS answer")).scalar_one()
            assert result == 2

            print(f"✓ Concurrent connections: PID1={pid1}, PID2={pid2}")
    finally:
        engine.dispose()


def test_ci_postgres_service_schema_isolation():
    """Verify database starts clean with no tables in public schema."""
    dsn = os.environ.get("ANOVELOS_TEST_DSN")
    if not dsn:
        pytest.skip("ANOVELOS_TEST_DSN not set")

    engine = create_engine(dsn)
    try:
        with engine.connect() as conn:
            table_count = conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public'"
                )
            ).scalar_one()

            assert table_count == 0, (
                f"Expected clean public schema, found {table_count} tables. "
                "CI service should start with empty database."
            )

            print("✓ Public schema is clean")
    finally:
        engine.dispose()
