from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from app.config import settings

SCHEMA = Path(__file__).with_name("schema.sql")

def connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.database_path, timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def migrate() -> None:
    with connect() as con:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','1')")

@contextmanager
def transaction():
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
