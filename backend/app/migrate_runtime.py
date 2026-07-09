"""Ledger-guarded runtime migration runner.

Applies numbered SQL migrations from the repo-root ``sql/`` directory exactly
once each, tracked in a ``schema_migration`` ledger table. A bare re-run of
``0003_multitenancy.sql`` errors with "duplicate column name"; the ledger guard
prevents that by skipping any migration already recorded.

Usable both as a CLI::

    python -m app.migrate_runtime --db-path ./str_qc.sqlite

and importable::

    from app.migrate_runtime import apply_pending
    apply_pending("./str_qc.sqlite")
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SQL_DIR = _REPO_ROOT / "sql"

# Migrations applied by this runner, in order. Name = filename stem (ledger key).
_MIGRATIONS: List[str] = [
    "0003_multitenancy",
]


def _resolve_db_path(db_path: str | os.PathLike[str]) -> Path:
    raw = Path(db_path)
    return raw if raw.is_absolute() else _REPO_ROOT / raw


def _ensure_ledger(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            name       TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _already_applied(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migration WHERE name = ?", (name,)
    ).fetchone()
    return row is not None


def _record(conn: sqlite3.Connection, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migration (name) VALUES (?)", (name,)
    )
    conn.commit()


def apply_pending(db_path: str | os.PathLike[str]) -> List[str]:
    """Apply any not-yet-applied migrations. Returns the list applied this run.

    Each migration's SQL file manages its own transaction (BEGIN/COMMIT). The
    ledger is updated only after the SQL executes successfully, so a failure
    leaves the migration un-recorded and re-runnable after the cause is fixed.
    """
    resolved = _resolve_db_path(db_path)
    applied: List[str] = []

    conn = sqlite3.connect(resolved)
    try:
        # The migration files drive their own PRAGMA/BEGIN/COMMIT; keep the
        # connection in autocommit so executescript does not wrap them.
        conn.isolation_level = None
        _ensure_ledger(conn)

        for name in _MIGRATIONS:
            if _already_applied(conn, name):
                print(f"[migrate] skip {name} (already applied)")
                continue
            sql_file = _SQL_DIR / f"{name}.sql"
            if not sql_file.exists():
                raise FileNotFoundError(f"migration SQL not found: {sql_file}")
            print(f"[migrate] applying {name} ...")
            sql = sql_file.read_text()
            conn.executescript(sql)
            _record(conn, name)
            applied.append(name)
            print(f"[migrate] applied {name}")
    finally:
        conn.close()

    if not applied:
        print("[migrate] nothing to apply")
    return applied


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply pending STRQC migrations.")
    parser.add_argument(
        "--db-path",
        default=os.getenv("STRQC_DB_PATH", "./str_qc.sqlite"),
        help="Path to the SQLite database (default: STRQC_DB_PATH or ./str_qc.sqlite).",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    apply_pending(args.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
