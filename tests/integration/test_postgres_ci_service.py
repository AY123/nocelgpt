"""Real PostgreSQL service checks, with the original isolated lifecycle locally."""

import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from test_postgres_environment import postgres

ROOT = Path(__file__).resolve().parents[2]


def assert_postgres_service(environment):
    dsn = environment.get("ANOVELOS_TEST_DSN")
    assert dsn, "A real ephemeral PostgreSQL DSN is required; missing service must fail"
    last = None
    for _ in range(30):
        last = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/check_postgres.py")],
            text=True,
            capture_output=True,
            timeout=10,
            env=environment,
        )
        if last.returncode == 0:
            break
        if last.returncode == 2:
            break
        time.sleep(1)
    assert last is not None and last.returncode == 0, (
        "Real PostgreSQL service did not become available"
    )
    engine = create_engine(dsn)
    try:
        with engine.connect() as first, engine.connect() as second:
            assert (
                first.execute(text("SHOW server_version_num")).scalar_one() == "170011"
            )
            assert (
                first.execute(text("SELECT current_database()")).scalar_one()
                == "bootstrap_test"
            )
            assert (
                first.execute(text("SELECT pg_backend_pid()")).scalar_one()
                != second.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            assert (
                first.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                    )
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()
    print(
        "POSTGRES_SERVICE_CONNECTED exact_version=170011 independent_connections=2 public_tables=0 pool_disposed=true"
    )


def test_exact_postgres_service_and_connections():
    if os.environ.get("GITLAB_CI") == "true" or os.environ.get("ANOVELOS_TEST_DSN"):
        assert_postgres_service(os.environ.copy())
    else:
        # Real Docker lifecycle; no skip/mock or SQLite fallback.
        with postgres() as (environment, _project):
            assert_postgres_service(environment)
