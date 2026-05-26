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
        images TEXT,
        action_type TEXT NOT NULL DEFAULT 'like',
        interest_score INTEGER,
        ai_summary TEXT,
        text TEXT,
        tags TEXT,
        ai_tags TEXT,
        created_at TEXT NOT NULL DEFAULT (date('now'))
    )
""")

# 迁移：如果旧表缺少新字段，自动添加
cursor.execute("PRAGMA table_info(notes)")
columns = [row[1] for row in cursor.fetchall()]
if "text" not in columns:
    cursor.execute("ALTER TABLE notes ADD COLUMN text TEXT")
if "ai_tags" not in columns:
    cursor.execute("ALTER TABLE notes ADD COLUMN ai_tags TEXT")
if "images" not in columns:
    cursor.execute("ALTER TABLE notes ADD COLUMN images TEXT")
if "cover_url" not in columns:
    cursor.execute("ALTER TABLE notes ADD COLUMN cover_url TEXT")
if "original_content" in columns and "text" not in columns:
    cursor.execute("UPDATE notes SET text = original_content WHERE text IS NULL AND original_content IS NOT NULL")

conn.commit()
conn.close()

print(f"SQLite database initialized at: {SQLITE_PATH}")
