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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
