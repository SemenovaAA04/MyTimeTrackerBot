import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn_cursor():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
    else:
        conn = sqlite3.connect("trackers.db", check_same_thread=False)
        cursor = conn.cursor()
    return conn, cursor

def init_db():
    conn, cursor = get_conn_cursor()
    # Твои таблицы, как раньше
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trackers (
      user_id TEXT,
      name TEXT,
      PRIMARY KEY (user_id, name)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_sessions (
      user_id TEXT PRIMARY KEY,
      name TEXT,
      start TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
      id SERIAL PRIMARY KEY,
      user_id TEXT,
      name TEXT,
      minutes INTEGER,
      date DATE
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()

def add_tracker(user_id, name):
    conn, cursor = get_conn_cursor()
    try:
        # Для Postgres — %s, для SQLite — ?
        if DATABASE_URL:
            cursor.execute(
                "INSERT INTO trackers (user_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                (user_id, name)
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO trackers (user_id, name) VALUES (?, ?);",
                (user_id, name)
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def tracker_exists(user_id, name):
    conn, cursor = get_conn_cursor()
    try:
        if DATABASE_URL:
            cursor.execute("SELECT 1 FROM trackers WHERE user_id = %s AND name = %s", (user_id, name))
        else:
            cursor.execute("SELECT 1 FROM trackers WHERE user_id = ? AND name = ?", (user_id, name))
        result = cursor.fetchone()
        return result is not None
    finally:
        cursor.close()
        conn.close()

def get_trackers(user_id):
    conn, cursor = get_conn_cursor()
    try:
        if DATABASE_URL:
            cursor.execute("SELECT name FROM trackers WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        return [row[0] if not DATABASE_URL else row["name"] for row in rows]
    finally:
        cursor.close()
        conn.close()


