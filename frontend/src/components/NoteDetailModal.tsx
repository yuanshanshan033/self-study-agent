import { useEffect, useState } from "react";
import type { Note } from "../types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface NoteDetailModalProps {
  note: Note | null;
  onClose: () => void;
}

/**
 * 笔记详情弹窗组件
 * 点击笔记卡片后弹出，左侧图片、右侧文本
 */
export function NoteDetailModal({ note, onClose }: NoteDetailModalProps) {
  const [activeImage, setActiveImage] = useState(0);

  // ESC 键关闭弹窗
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  // 切换笔记时重置当前图片
  useEffect(() => {
    setActiveImage(0);
  }, [note?.id]);

  if (!note) return null;

  // 解析图片列表
  const getImages = () => {
    if (!note.images) return [];
    return note.images.split(",").filter(Boolean).map((img) => {
      const trimmed = img.trim();
      if (trimmed.startsWith("/screenshots/")) {
        return `http://localhost:3001${trimmed}`;
      }
      return trimmed;
    });
  };

  const images = getImages();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container modal-horizontal" onClick={(e) => e.stopPropagation()}>
        {/* 关闭按钮 */}
        <button className="modal-close" onClick={onClose}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* 左侧：图片区域 */}
        {images.length > 0 && (
          <div className="modal-left">
            <div className="modal-image-main">
              <img src={images[activeImage]} alt={note.title} />
            </div>
            {images.length > 1 && (
              <div className="modal-image-thumbnails">
                {images.map((img, idx) => (
                  <div
                    key={idx}
                    className={`modal-thumb ${idx === activeImage ? "active" : ""}`}
                    onClick={() => setActiveImage(idx)}
                  >
                    <img src={img} alt={`${note.title} - ${idx + 1}`} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 右侧：内容区域 */}
        <div className="modal-right">
          {/* 标题 */}
          <h2 className="modal-title">{note.title}</h2>

          {/* 元信息 */}
          <div className="modal-meta">
            <span className={`badge ${note.action_type}`}>
              {note.action_type === "bookmark" ? "⭐ 收藏" : "❤️ 点赞"}
            </span>
            {note.interest_score && (
              <span className="modal-score">兴趣度: {note.interest_score}/10</span>
            )}
            <span className="modal-date">{note.created_at}</span>
          </div>

          {/* 原文标签 */}
          {note.tags && (
            <div className="modal-tags">
              {note.tags.split(",").map((tag) => (
                <span key={tag} className="modal-tag">
                  #{tag.trim()}
                </span>
              ))}
            </div>
          )}

          {/* AI 摘要 */}
          {note.ai_summary && (
            <div className="modal-section">
              <h3 className="modal-section-title">🤖 AI 总结</h3>
              <div className="modal-summary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {note.ai_summary}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* AI 标签 */}
          {note.ai_tags && (
            <div className="modal-section">
              <h3 className="modal-section-title">🏷️ AI 标签</h3>
              <div className="modal-tags">
                {note.ai_tags.split(",").map((tag) => (
                  <span key={tag} className="modal-tag ai-tag">
                    {tag.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 原文内容 */}
          {note.text && (
            <div className="modal-section">
              <h3 className="modal-section-title">📝 原文内容</h3>
              <p className="modal-original">{note.text}</p>
            </div>
          )}

          {/* 链接 */}
          {note.url && (
            <div className="modal-section">
              <a
                href={note.url}
                target="_blank"
                rel="noopener noreferrer"
                className="modal-link"
              >
                🔗 查看原笔记
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
