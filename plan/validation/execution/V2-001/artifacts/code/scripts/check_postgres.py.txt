"""Probe an explicitly configured disposable PostgreSQL database; no migrations."""
from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError


def main() -> int:
    raw = os.environ.get("ANOVELOS_TEST_DSN", "").strip()
    if not raw:
        print("ANOVELOS_TEST_DSN is required; no default database is used.", file=sys.stderr)
        return 2
    try:
        url = make_url(raw)
        if url.drivername != "postgresql+psycopg":
            raise ValueError("explicit PostgreSQL psycopg driver required")
        if not all((url.host, url.port, url.database, url.username, url.password)):
            raise ValueError("incomplete database configuration")
        # libpq options in a DSN could redirect the connection or change timeouts.
        if url.query:
            raise ValueError("query overrides are unsupported by this bootstrap probe")
    except (ArgumentError, TypeError, ValueError):
        print("Invalid ANOVELOS_TEST_DSN: require postgresql+psycopg with explicit host, port, database, user and password; no query options.", file=sys.stderr)
        return 2
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database(), current_setting('server_version_num')::int")).one()
        print(json.dumps({"database": result[0], "server_version_num": result[1], "driver": "postgresql+psycopg"}))
        return 0
    except SQLAlchemyError:
        # Driver exception messages may contain credentials or connection options.
        print("PostgreSQL connection/query failed; check the isolated test service and configuration.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
