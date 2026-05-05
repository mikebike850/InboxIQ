import os
import sqlite3
from pathlib import Path


def _resolve_db_path():
    """Return the DB path from INBOXIQ_DB_PATH env var, st.secrets, or the default."""
    if env_path := os.environ.get('INBOXIQ_DB_PATH'):
        return Path(env_path)
    try:
        import streamlit as st
        if path := st.secrets.get('INBOXIQ_DB_PATH'):
            return Path(path)
    except Exception:
        pass
    return Path(__file__).parent.parent / 'inboxiq.db'


DB_PATH = _resolve_db_path()


def get_db():
    db_path = _resolve_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        schema = (Path(__file__).parent.parent / "schema.sql").read_text()
        conn.executescript(schema)
        conn.commit()
    except Exception:
        pass
    return conn
