import type { Note } from "../types";
import { formatNumber } from "../api";

interface NoteCardProps {
  note: Note;
}

/**
 * 笔记卡片组件
 * 显示笔记封面、标题、摘要和统计数据
 */
export function NoteCard({ note }: NoteCardProps) {
  // 获取笔记摘要（优先使用AI摘要，否则使用原文前100字）
  const getSummary = () => {
    const aiSummary = note.ai_summary ?? "";
    const originalContent = note.original_content ?? "";

    if (aiSummary) {
      return aiSummary.slice(0, 80) + "...";
    }
    if (originalContent) {
      return originalContent.slice(0, 80) + "...";
    }
    return "暂无内容摘要";
  };

  // 获取封面图URL
  const getCoverUrl = () => {
    if (note.cover_url) {
      return note.cover_url;
    }
    // 默认占位图
    return "https://via.placeholder.com/300x200/2a2a3e/ffffff?text=No+Image";
  };

  return (
    <div className="note-card">
      {/* 封面图 */}
      <div className="note-card-cover">
        <img src={getCoverUrl()} alt={note.title} loading="lazy" />
      </div>

      {/* 内容区域 */}
      <div className="note-card-content">
        {/* 标题 */}
        <h3 className="note-card-title">{note.title}</h3>

        {/* 摘要 */}
        <p className="note-card-summary">{getSummary()}</p>

        {/* 统计数据 */}
        <div className="note-card-stats">
          <div className="stat-item">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
            <span>{formatNumber(note.likes || 0)}</span>
          </div>
          <div className="stat-item">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            <span>{formatNumber(note.bookmarks || 0)}</span>
          </div>
          <div className="stat-item">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
            <span>{formatNumber(note.comments || 0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
