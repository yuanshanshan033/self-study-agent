import sqlite3
import os

from config import SQLITE_PATH

os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)

conn = sqlite3.connect(SQLITE_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT,
        cover_url TEXT,
        action_type TEXT NOT NULL DEFAULT 'like',
        interest_score INTEGER,
        ai_summary TEXT,
        original_content TEXT,
        tags TEXT,
        created_at TEXT NOT NULL DEFAULT (date('now'))
    )
""")

conn.commit()
conn.close()

print(f"SQLite database initialized at: {SQLITE_PATH}")
