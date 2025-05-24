import os
import sqlite3            # только для локальной разработки
import psycopg2           # драйвер для Postgres
from psycopg2.extras import RealDictCursor

# 1. Тянем URL из переменных окружения
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # 2. Подключаемся к Postgres (Render автоматически доставит sslmode=require в URL)
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
else:
    # 3. Fallback на SQLite (локальная разработка)
    conn = sqlite3.connect("trackers.db", check_same_thread=False)
    cursor = conn.cursor()

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
