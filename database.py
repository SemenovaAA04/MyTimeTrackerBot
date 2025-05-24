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


# 4. Создаём все таблицы, если их ещё нет
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
