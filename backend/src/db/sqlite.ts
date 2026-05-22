import Database, { Database as DatabaseType } from "better-sqlite3";
import path from "path";
import fs from "fs";

const DB_PATH = process.env.SQLITE_PATH || path.resolve(__dirname, "..", "..", "..", "data", "xiaohongshu.db");

// 确保数据库目录存在
const dbDir = path.dirname(DB_PATH);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

const db: DatabaseType = new Database(DB_PATH);

db.exec(`
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
`);

export interface Note {
  id: number;
  title: string;
  url: string | null;
  cover_url: string | null;
  action_type: "like" | "bookmark";
  interest_score: number | null;
  ai_summary: string | null;
  original_content: string | null;
  tags: string | null;
  created_at: string;
}

export function getNotes(page: number = 1, pageSize: number = 20): { notes: Note[]; total: number } {
  const offset = (page - 1) * pageSize;
  const total = db.prepare("SELECT COUNT(*) as count FROM notes").get() as { count: number };
  const notes = db
    .prepare("SELECT * FROM notes ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?")
    .all(pageSize, offset) as Note[];
  return { notes, total: total.count };
}

export function getNoteById(id: number): Note | undefined {
  return db.prepare("SELECT * FROM notes WHERE id = ?").get(id) as Note | undefined;
}

export function getNotesByDate(date: string): Note[] {
  return db.prepare("SELECT * FROM notes WHERE created_at = ? ORDER BY id DESC").all(date) as Note[];
}

export function getNotesByTag(tag: string): Note[] {
  return db.prepare("SELECT * FROM notes WHERE tags LIKE ? ORDER BY created_at DESC").all(`%${tag}%`) as Note[];
}

export default db;