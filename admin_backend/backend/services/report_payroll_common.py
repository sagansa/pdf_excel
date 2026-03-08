import logging
import os
import re

from sqlalchemy import text

from backend.db.session import get_sagansa_engine

logger = logging.getLogger(__name__)


def _safe_identifier(value, fallback):
    raw = str(value or fallback).strip()
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', raw):
        return fallback
    return raw


def _fetch_sagansa_user_map():
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        logger.warning("Failed to connect to Sagansa DB for payroll summary: %s", error_msg)
        return {}

    user_table = _safe_identifier(os.environ.get('SAGANSA_USER_TABLE'), 'users')
    user_id_col = _safe_identifier(os.environ.get('SAGANSA_USER_ID_COLUMN'), 'id')
    user_name_col = _safe_identifier(os.environ.get('SAGANSA_USER_NAME_COLUMN'), 'name')
    user_active_col = _safe_identifier(os.environ.get('SAGANSA_USER_ACTIVE_COLUMN'), '')

    where_active_sql = f"WHERE COALESCE(`{user_active_col}`, 1) = 1" if user_active_col else ''
    query = text(f"""
        SELECT
            CAST(`{user_id_col}` AS CHAR) AS id,
            CAST(`{user_name_col}` AS CHAR) AS name
        FROM `{user_table}`
        {where_active_sql}
        ORDER BY `{user_name_col}` ASC
        LIMIT 5000
    """)

    user_map = {}
    try:
        with engine.connect() as conn:
            for row in conn.execute(query):
                user_id = str(row.id or '').strip()
                if not user_id:
                    continue
                user_map[user_id] = {
                    'id': user_id,
                    'name': str(row.name or '').strip() or user_id,
                }
    except Exception as exc:
        logger.warning("Failed to fetch Sagansa users for payroll summary: %s", exc)
        return {}

    return user_map
