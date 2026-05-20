import { useState, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Note } from "../types";
import { fetchNotes } from "../api";

export default function NoteList() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Note | null>(null);
  const pageSize = 12;

  const load = useCallback((p: number) => {
    fetchNotes(p, pageSize).then(({ notes: n, total: t }) => {
      setNotes(n);
      setTotal(t);
      setPage(p);
    });
  }, []);

  useEffect(() => { load(1); }, [load]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="note-section">
      <h2>我的收藏 ({total}篇)</h2>

      <div className="note-grid">
        {notes.map((n) => (
          <div key={n.id} className="note-card" onClick={() => setSelected(n)}>
            {n.cover_url && <img src={n.cover_url} alt="" className="note-cover" />}
            <div className="note-card-body">
              <h3>{n.title}</h3>
              <div className="note-meta">
                <span className={`badge ${n.action_type}`}>
                  {n.action_type === "bookmark" ? "⭐收藏" : "❤️点赞"}
                </span>
                {n.tags && n.tags.split(",").slice(0, 2).map((tag) => (
                  <span key={tag} className="tag">{tag.trim()}</span>
                ))}
                <span className="date">{n.created_at}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => load(page - 1)}>上一页</button>
          <span>{page} / {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => load(page + 1)}>下一页</button>
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelected(null)}>✕</button>
            {selected.cover_url && <img src={selected.cover_url} alt="" className="modal-cover" />}
            <h2>{selected.title}</h2>
            <div className="modal-meta">
              <span className={`badge ${selected.action_type}`}>
                {selected.action_type === "bookmark" ? "⭐收藏" : "❤️点赞"}
              </span>
              <span>{selected.created_at}</span>
            </div>
            <div className="modal-summary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selected.ai_summary || "暂无摘要"}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}