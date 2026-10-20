"""Checksummed transactional PostgreSQL schema; never seeds Canon contents."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from sqlalchemy import Engine, text

from anovel.canon.models import CanonIntegrityError


def migrate(engine: Engine) -> str:
    if engine.dialect.name != "postgresql":
        raise ValueError("Canon requires PostgreSQL")
    sources = [
        (version, (Path(__file__).parent / "sql" / name).read_bytes())
        for version, name in ((1, "0001_root.sql"), (2, "0002_chapter.sql"))
    ]
    expected = [(version, sha256(raw).hexdigest()) for version, raw in sources]
    with engine.connect() as conn:
        conn.execution_options(isolation_level="READ COMMITTED")
        with conn.begin():
            # Application-specific transaction lock serializes concurrent installers.
            conn.execute(text("SELECT pg_advisory_xact_lock(194001, 9)"))
            exists = conn.execute(
                text("SELECT to_regclass('anovel_canon.schema_migrations')")
            ).scalar_one()
            if exists is None:
                conn.exec_driver_sql(sources[0][1].decode("utf-8"))
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.schema_migrations(version,checksum) VALUES (1,:checksum)"
                    ),
                    {"checksum": expected[0][1]},
                )
                applied = expected[:1]
            else:
                rows = conn.execute(
                    text(
                        "SELECT version,checksum FROM anovel_canon.schema_migrations ORDER BY version"
                    )
                ).all()
                applied = [tuple(row) for row in rows]
                if not applied or applied != expected[: len(applied)]:
                    raise CanonIntegrityError(
                        "unknown migration version or checksum drift"
                    )
            for (version, raw), (_number, checksum) in zip(
                sources[len(applied) :], expected[len(applied) :], strict=True
            ):
                conn.exec_driver_sql(raw.decode("utf-8"))
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.schema_migrations(version,checksum) VALUES (:version,:checksum)"
                    ),
                    {"version": version, "checksum": checksum},
                )
    return expected[-1][1]
