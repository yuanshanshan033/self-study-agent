import Database, { Database as DatabaseType } from "better-sqlite3";
import path from "path";
import fs from "fs";
import dotenv from "dotenv";

// 确保 .env 在数据库连接前加载
dotenv.config({ path: path.resolve(__dirname, "..", "..", "..", ".env") });

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
    images TEXT,
    action_type TEXT NOT NULL DEFAULT 'like',
    interest_score INTEGER,
    ai_summary TEXT,
    text TEXT,
    tags TEXT,
    ai_tags TEXT,
    created_at TEXT NOT NULL DEFAULT (date('now'))
  )
`);

// 迁移：如果旧表缺少新字段，自动添加
const columns = db.prepare("PRAGMA table_info(notes)").all() as { name: string }[];
const columnNames = columns.map(c => c.name);
if (!columnNames.includes("text")) {
  db.exec("ALTER TABLE notes ADD COLUMN text TEXT");
}
if (!columnNames.includes("ai_tags")) {
  db.exec("ALTER TABLE notes ADD COLUMN ai_tags TEXT");
}
if (!columnNames.includes("images")) {
  db.exec("ALTER TABLE notes ADD COLUMN images TEXT");
}
if (!columnNames.includes("cover_url")) {
  db.exec("ALTER TABLE notes ADD COLUMN cover_url TEXT");
}
if (columnNames.includes("original_content") && !columnNames.includes("text")) {
  db.exec("UPDATE notes SET text = original_content WHERE text IS NULL AND original_content IS NOT NULL");
}

export interface Note {
  id: number;
  title: string;
  url: string | null;
  cover_url: string | null;
  images: string | null;
  action_type: "like" | "bookmark";
  interest_score: number | null;
  ai_summary: string | null;
  text: string | null;
  tags: string | null;
  ai_tags: string | null;
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