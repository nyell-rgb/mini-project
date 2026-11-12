"""Koneksi ke MySQL db_dapur (pengembangan dari connect.py)."""
import os

from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="dapur_pool",
            pool_size=5,
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "db_dapur"),
        )
    return _pool


def get_db():
    """Dependency FastAPI: satu koneksi per request, otomatis dikembalikan ke pool."""
    conn = get_pool().get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(conn, sql, params=(), one=False):
    """SELECT -> list of dict (atau satu dict / None kalau one=True)."""
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close()


def execute(conn, sql, params=()):
    """INSERT/UPDATE/DELETE -> mengembalikan lastrowid. Commit dilakukan di pemanggil."""
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return cur.lastrowid
    finally:
        cur.close()


def execute_many(conn, sql, rows):
    cur = conn.cursor()
    try:
        cur.executemany(sql, rows)
    finally:
        cur.close()
