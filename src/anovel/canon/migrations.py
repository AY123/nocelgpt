"""Checksummed transactional PostgreSQL schema; never seeds Canon contents."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from sqlalchemy import Engine, text

from anovel.canon.models import CanonIntegrityError


def migrate(engine: Engine) -> str:
    if engine.dialect.name != "postgresql":
        raise ValueError("Canon requires PostgreSQL")
    raw = (Path(__file__).parent / "sql/0001_root.sql").read_bytes()
    checksum = sha256(raw).hexdigest()
    with engine.connect() as conn:
        conn.execution_options(isolation_level="READ COMMITTED")
        with conn.begin():
            # Application-specific transaction lock serializes concurrent installers.
            conn.execute(text("SELECT pg_advisory_xact_lock(194001, 9)"))
            exists = conn.execute(
                text("SELECT to_regclass('anovel_canon.schema_migrations')")
            ).scalar_one()
            if exists is None:
                conn.exec_driver_sql(raw.decode("utf-8"))
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.schema_migrations(version,checksum) VALUES (1,:checksum)"
                    ),
                    {"checksum": checksum},
                )
            else:
                rows = conn.execute(
                    text(
                        "SELECT version,checksum FROM anovel_canon.schema_migrations ORDER BY version"
                    )
                ).all()
                if [tuple(row) for row in rows] != [(1, checksum)]:
                    raise CanonIntegrityError(
                        "unknown migration version or checksum drift"
                    )
    return checksum
