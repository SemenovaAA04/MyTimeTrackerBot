import os
import psycopg2
from psycopg2 import sql

# Тянем URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("В ENV не найдена DATABASE_URL!")

# Коннектимся к Postgres (Render требует sslmode=require)
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# Создаём таблицы, если их ещё нет
cursor.execute("""
CREATE TABLE IF NOT EXISTS trackers (
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (user_id, name)
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_sessions (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    start TIMESTAMP NOT NULL
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    date DATE NOT NULL
);
""")
conn.commit()
