import sqlite3

conn = sqlite3.connect("trackers.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS trackers (
    user_id TEXT,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    user_id TEXT,
    name TEXT,
    minutes INTEGER,
    date TEXT
)
""")

conn.commit()
conn.close()

cursor.execute("""
CREATE TABLE IF NOT EXISTS active_sessions (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    start TEXT
)
""")

